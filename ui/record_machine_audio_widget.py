"""
模块说明
========
本文件实现基于 MVC 的音频采集/可视化/分析组件，向外暴露统一的 `RecordMachineAudioWidget`（继承 `QWidget`）。

类结构
------
- `RecordMachineAudioModel`: 负责状态与数据（设备信息、环形缓冲、保存逻辑、片段提取器装配）。
- `RecordMachineAudioView`: 负责界面与控件（按钮、路径输入、指示灯与图表容器）。
- `RecordMachineAudioController`: 负责业务流程（录制启停、绘图线程、分析子进程、回调/信号转发）。
- `RecordMachineAudioWidget` (Facade): 对外唯一入口，保持原有接口与信号不变，内部委派给 MVC。

对外信号（在 `RecordMachineAudioWidget` 上）
-----------------------------------------
- `recording_started`: 开始录音时发射。
- `recording_stopped`: 停止录音时发射。
- `analysis_completed(object)`: 分析结果就绪时发射，参数为结果列表（见“结果数据约定”）。

对外方法（在 `RecordMachineAudioWidget` 上）
-------------------------------------------
- `update_model_name(model_name: str) -> None`: 设置/更新使用的 AI 模型名。
- `build_audio_segment_extractor(extract_flag: bool, extract_interval: Optional[float] = None, segment_duration: Optional[float] = None) -> None`
  配置/启用音频片段提取器；启用后提取到的片段会自动投递至分析进程并通过 `analysis_completed` 回传结果。
- `record_audio() -> None`: 开始录音（UI上“Record”按钮同效）。
- `stop_record() -> None`: 停止录音（UI上“Stop”按钮同效）。
- `save_audio_data(countdown_time: int) -> None`: 自动保存倒计时回调触发的保存逻辑（通常无需手调）。
- `select_store_path() -> None`: 打开目录选择并设置保存路径。
- `change_audio_store_path() -> None`: 路径输入框变更回调（通常由 UI 触发）。
- `get_model_info(model_name: str) -> Tuple[int, Tuple[str, str]]`: 查询模型与配置路径（返回码与路径元组）。
- `init_new_canvas() -> None`: 初始化/刷新绘图画布。
- `flush_audio_queue_to_array() -> None`: 将环形缓冲区追加到线性存储（供绘图/保存）。
- `update_plot(selected_channels, audio_data, canvas) -> None`: 绘图线程调用的帧更新逻辑。
- `show() -> None`: 显示前刷新设备/通道并创建图表。
- `closeEvent(event) -> None`: 关闭时清理资源（停止录制/进程/线程）。

向后兼容属性（在 `RecordMachineAudioWidget` 上直接可访问）
--------------------------------------------------------
`data_struct`、`audio_manager`、`segment_extractor`、`chart_graph`、`selected_channels`、`sampling_rate`、
`channels`、`plot_points_section`、`storage_filled_len`、`channel_index` 等，仍保留与旧实现一致的命名与语义。

最简使用示例
------------
```python
from PyQt5.QtWidgets import QApplication
from ui.record_machine_audio_widget import RecordMachineAudioWidget

app = QApplication([])
w = RecordMachineAudioWidget()

# 监听分析结果（每次片段完成分析后触发）
w.analysis_completed.connect(lambda results: print("分析结果:", results))

# 选择模型（可选）
w.update_model_name("your_model_name")

# 启用片段提取与自动分析（可选）
w.build_audio_segment_extractor(True, extract_interval=2.0, segment_duration=1.0)

w.show()
app.exec_()
```

结果数据约定
------------
`analysis_completed` 发出的 `results` 为 `List[Dict]`：
- `channel: int` — 通道索引
- `data: { ret_code: int, ret_msg: str, result: list }` — 模型返回信息与结果

注意事项
--------
- Windows 下多进程启动方式为 `spawn`，请在 `if __name__ == '__main__':` 保护下启动顶层应用。
- 依赖可用的音频输入设备；设备信息优先从配置读取，无法获取时回退到默认麦克风（首通道）。
"""

import numpy as np
import os
import uuid
import tempfile
import multiprocessing as mp

import time
import threading

from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QPixmap
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtWidgets import QFileDialog, QFrame, QMessageBox
from scipy.signal import spectrogram

from base.analysis_worker_process import analysis_worker
from base.audio_data_manager import auto_save_data
from base.load_device_info import load_devices_data
from base.sound_device_manager import get_default_device
from base.log_manager import LogManager
from base.record_audio import AudioDataManager
from base.data_struct.data_deal_struct import DataDealStruct
from base.data_struct.audio_segment_extractor import AudioSegmentExtractor
from base.sound_device_manager import sd
from base.training_model_management import TrainingModelManagement
from consts import error_code
from consts.running_consts import DEFAULT_DIR
from ui.system_information_textedit import log_controller
from my_controls.multiple_chartsgraph import MultipleChartsGraph
from my_controls.countdown import Countdown
from ui.device_list import DeviceListWindow


class RecordMachineAudioModel:
    def __init__(self):
        self.logger = LogManager.set_log_handler("core")
        self.data_struct = DataDealStruct()

        self.sampling_rate = 44100
        self.channels = None
        self.selected_channels = list()

        self.total_display_time = 600
        self.nfft = 256
        self.fs = 44100
        self.ctx = sd._CallbackContext()

        self.plot_time = 5
        self.start_record_time = None
        self.model_name = ""

        self.max_points = self.total_display_time * self.sampling_rate
        self.plot_points_section = self.plot_time * self.sampling_rate
        self.buffer_len = 30 * self.sampling_rate

        self.select_device_name = None

        self.audio_manager = AudioDataManager()
        self.auto_save_count = Countdown(self.total_display_time - 10)

        self.segment_extractor = None

        self.audio_store_path = ""

        self.channel_index = []
        self.storage_filled_len = []

    def load_device_info(self):
        device_name, channels, selected_channels, _, _ = load_devices_data()
        if device_name and channels and selected_channels:
            self.select_device_name, self.channels, self.selected_channels= (
                device_name,
                channels,
                selected_channels,
            )
        else:
            try:
                default_device = get_default_device()
                if default_device:
                    self.select_device_name = default_device.get("name")
                    self.channels = int(default_device.get("max_input_channels", 1)) or 1
                    self.selected_channels = [0]
                    DeviceListWindow.save_device_data_to_json(
                        self.select_device_name,
                        self.channels,
                        self.selected_channels,
                    )
                else:
                    self.select_device_name = "Default Microphone"
                    self.channels = 1
                    self.selected_channels = [0]
            except Exception:
                self.select_device_name = "Default Microphone"
                self.channels = 1
                self.selected_channels = [0]

    def set_up_audio_store_zero(self):
        self.data_struct.audio_data = np.zeros((len(self.selected_channels), self.max_points), dtype=np.float16)
        self.data_struct.audio_data_arr = [
            np.zeros(self.buffer_len, dtype=np.float16) for _ in range(len(self.selected_channels))
        ]
        self.data_struct.write_index = [0] * len(self.selected_channels)
        self.channel_index = [0] * len(self.selected_channels)
        self.storage_filled_len = [0] * len(self.selected_channels)

    def build_audio_segment_extractor(self, extract_flag, extract_interval=None, segment_duration=None, on_extracted=None):
        if extract_flag:
            self.segment_extractor = AudioSegmentExtractor(
                extract_interval=extract_interval,
                segment_duration=segment_duration,
                sampling_rate=self.sampling_rate,
            )
            self.segment_extractor.set_audio_source(
                self.data_struct.audio_data,
                write_index_ref=self.storage_filled_len
            )
            if on_extracted is not None:
                self.segment_extractor.set_on_extracted_callback(on_extracted)
            self.data_struct.segment_extractor = self.segment_extractor
        else:
            self.segment_extractor = None
            self.data_struct.segment_extractor = None

    def set_audio_store_path(self, path: str):
        self.audio_store_path = path or ""

    def init_store_path(self):
        try:
            with open(DEFAULT_DIR + "ui/ui_config/audio_store_path.txt", "r") as f:
                self.audio_store_path = f.readline()
        except Exception as e:
            self.logger.error(f"init_store_path failed: {e}")

    @staticmethod
    def save_store_path_to_txt(path):
        if not path:
            return
        with open(DEFAULT_DIR + "ui/ui_config/audio_store_path.txt", "w") as f:
            f.write(path)

    def flush_audio_queue_to_array(self):
        num_channels = len(self.selected_channels)
        if num_channels == 0:
            return
        while True:
            e1 = getattr(self.data_struct, "epoch", 0)
            if e1 % 2 == 1:
                continue
            new_write_indices = [None] * num_channels
            restart_needed = False
            for i in range(num_channels):
                if e1 != getattr(self.data_struct, "epoch", 0):
                    restart_needed = True
                    break
                write_idx_snapshot = int(self.data_struct.write_index[i])
                new_write_indices[i] = write_idx_snapshot
            if restart_needed:
                continue
            staged_segments = [None] * num_channels
            staged_write_indices = [None] * num_channels
            for i in range(num_channels):
                ring_buffer = self.data_struct.audio_data_arr[i]
                rb_len = int(len(ring_buffer))
                if rb_len <= 0:
                    staged_segments[i] = None
                    staged_write_indices[i] = new_write_indices[i]
                    continue
                write_idx_norm = int(new_write_indices[i]) % rb_len
                prev_idx = int(self.channel_index[i])
                prev_idx_norm = prev_idx % rb_len
                if write_idx_norm == prev_idx_norm:
                    seg = np.array([], dtype=ring_buffer.dtype)
                elif write_idx_norm > prev_idx_norm:
                    seg = ring_buffer[prev_idx_norm:write_idx_norm]
                else:
                    seg = np.concatenate([
                        ring_buffer[prev_idx_norm:],
                        ring_buffer[:write_idx_norm]
                    ])
                staged_segments[i] = seg
                staged_write_indices[i] = new_write_indices[i]
            e2 = getattr(self.data_struct, "epoch", 0)
            if e1 != e2 or (e2 % 2 == 1):
                continue
            for i in range(num_channels):
                seg = staged_segments[i]
                if seg is None or seg.size == 0:
                    if staged_write_indices[i] is not None:
                        self.channel_index[i] = int(staged_write_indices[i])
                    continue
                storage_array = self.data_struct.audio_data[i]
                store_len = int(len(storage_array))
                if store_len <= 0:
                    if staged_write_indices[i] is not None:
                        self.channel_index[i] = int(staged_write_indices[i])
                    continue
                filled = int(self.storage_filled_len[i])
                free = max(0, store_len - filled)
                if free > 0:
                    take = min(free, seg.size)
                    storage_array[filled:filled + take] = seg[:take]
                    filled += take
                    remaining = seg[take:]
                else:
                    remaining = seg
                if remaining.size > 0:
                    m = int(remaining.size)
                    if m >= store_len:
                        storage_array[:] = remaining[-store_len:]
                        filled = store_len
                    else:
                        storage_array[:-m] = storage_array[m:]
                        storage_array[-m:] = remaining
                        filled = store_len
                self.storage_filled_len[i] = min(store_len, filled)
                if staged_write_indices[i] is not None:
                    self.channel_index[i] = int(staged_write_indices[i])
            break

    def save_audio_data(self, countdown_time, save_path):
        if countdown_time == self.total_display_time - 10:
            audio_data = self.data_struct.audio_data
        elif countdown_time < self.total_display_time - 10:
            audio_data_duration = int(countdown_time * self.sampling_rate)
            num_ch = len(self.selected_channels)
            audio_data = np.zeros((num_ch, audio_data_duration), dtype=np.float32)
            for ch in range(num_ch):
                buf = self.data_struct.audio_data[ch]
                filled = int(self.storage_filled_len[ch])
                take = min(audio_data_duration, filled)
                if take > 0:
                    audio_data[ch, -take:] = buf[filled - take: filled]
        else:
            self.logger.error("save_audio_data failed: countdown_time is out of range")
            return None
        self.start_record_time = auto_save_data(
            audio_data, self.sampling_rate, save_path, self.selected_channels, self.start_record_time
        )
        return self.start_record_time

    @staticmethod
    def get_model_info(model_name):
        code, query_result = TrainingModelManagement().get_model_path_from_json(model_name)
        if code == error_code.OK and query_result:
            item = query_result[0]
            model_path = (item.get("path") or item.get("model_path") or "").strip()
            config_path = (item.get("config_path") or "").strip()
            if not os.path.isabs(model_path):
                really_model_path = os.path.normpath(os.path.join(DEFAULT_DIR, model_path))
            else:
                really_model_path = os.path.normpath(model_path)
            if not os.path.isabs(config_path):
                really_config_path = os.path.normpath(os.path.join(DEFAULT_DIR, config_path))
            else:
                really_config_path = os.path.normpath(config_path)
            return error_code.OK, (really_model_path, really_config_path)
        return error_code.INVALID_QUERY, None


class RecordMachineAudioView(QWidget):
    view_shown = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.record_btn = QPushButton("Record")
        self.stop_btn = QPushButton("Stop")
        self.audio_store_path_lineedit = QLineEdit()
        self.red_light = QLabel()
        self.green_light = QLabel()
        self.status_label = QLabel("状态：")
        self.status_label.setStyleSheet("font-size: 35px;")
        self.red_light_color = "gray"
        self.green_light_color = "gray"
        self.chart_graph = MultipleChartsGraph()

    def build(self, on_record, on_stop, on_select_path, on_about, on_audio_path_changed):
        self._init_record_bar(on_record, on_stop, on_select_path, on_audio_path_changed)
        solid_graph_layout = self._create_solid_graph_layout()
        h_line = QFrame()
        h_line.setFrameShape(QFrame.HLine)
        h_line.setFrameShadow(QFrame.Sunken)
        layout = QVBoxLayout()
        layout.addLayout(self._record_operation_layout)
        layout.addWidget(h_line)
        layout.addLayout(solid_graph_layout)
        self.setLayout(layout)

    def _init_record_bar(self, on_record, on_stop, on_select_path, on_audio_path_changed):
        self.stop_btn.setEnabled(False)
        self.record_btn.setStyleSheet("color: green;")
        self.stop_btn.setStyleSheet("color: red;")
        self.record_btn.clicked.connect(on_record)
        self.stop_btn.clicked.connect(on_stop)

        audio_store_path_label = QLabel("音频存储路径")
        self.audio_store_path_lineedit.setPlaceholderText("请选择音频存储路径")
        self.audio_store_path_lineedit.textChanged.connect(on_audio_path_changed)
        icon_path = DEFAULT_DIR + "ui/ui_pic/ai_window_pic/folder-s.png"
        select_store_path_action = self.audio_store_path_lineedit.addAction(
            QIcon(icon_path), QLineEdit.TrailingPosition
        )
        select_store_path_action.triggered.connect(on_select_path)

        font = QFont()
        font.setPointSize(15)
        self.record_btn.setFont(font)
        self.stop_btn.setFont(font)
        about_dy_btn = QPushButton("关于东原")
        about_dy_btn.setFont(font)
        about_dy_btn.clicked.connect(lambda: self.on_about_dy())

        layout = QHBoxLayout()
        layout.addWidget(self.record_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(audio_store_path_label)
        layout.addWidget(self.audio_store_path_lineedit)
        layout.addWidget(about_dy_btn)
        self._record_operation_layout = layout

    def _create_solid_graph_layout(self):
        solid_graph = QLabel()
        solid_graph.setPixmap(QPixmap(DEFAULT_DIR + "ui/ui_pic/solid_graph.png"))
        solid_graph.setMaximumSize(500, 350)
        solid_graph.setScaledContents(True)
        solid_graph.setAlignment(Qt.AlignCenter)

        self.set_light_color(self.red_light, "gray")
        self.set_light_color(self.green_light, "gray")

        vertical_line = QFrame()
        vertical_line.setFrameShape(QFrame.VLine)
        vertical_line.setFrameShadow(QFrame.Sunken)

        h_line = QFrame()
        h_line.setFrameShape(QFrame.HLine)
        h_line.setFrameShadow(QFrame.Sunken)

        light_layout = QHBoxLayout()
        light_layout.addStretch(1)
        light_layout.addWidget(self.status_label)
        light_layout.addSpacing(20)
        light_layout.addWidget(self.green_light)
        light_layout.addWidget(self.red_light)
        light_layout.addStretch(1)

        solid_light_layout = QVBoxLayout()
        solid_light_layout.addWidget(solid_graph, alignment=Qt.AlignTop)
        solid_light_layout.addWidget(h_line)
        solid_light_layout.addStretch(1)
        solid_light_layout.addLayout(light_layout)
        solid_light_layout.addStretch(1)
        solid_light_layout.setContentsMargins(0, 30, 10, 0)

        solid_graph_layout = QHBoxLayout()
        solid_graph_layout.addLayout(solid_light_layout)
        solid_graph_layout.addWidget(vertical_line)
        solid_graph_layout.addWidget(self.chart_graph)
        return solid_graph_layout

    def set_light_color(self, light, color):
        light.setFixedSize(80, 80)
        light.setAlignment(Qt.AlignCenter)
        path_map = {
            "red": DEFAULT_DIR + "ui/ui_pic/red_light.png",
            "green": DEFAULT_DIR + "ui/ui_pic/green_light.png",
            "gray": DEFAULT_DIR + "ui/ui_pic/gray_light.png",
        }
        img_path = path_map.get(color, path_map["gray"])
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(light.width(), light.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            light.setPixmap(scaled)
        else:
            light.setPixmap(QPixmap())
        if light is self.red_light:
            self.red_light_color = color
        elif light is self.green_light:
            self.green_light_color = color
        self.refresh_status_label()

    def refresh_status_label(self):
        self.status_label.setText("状态：")

    @staticmethod
    def on_about_dy():
        browser = QDesktopServices()
        browser.openUrl(QUrl("https://suzhoudongyuan.com/"))

    def showEvent(self, event):
        self.view_shown.emit()
        super().showEvent(event)


class RecordMachineAudioController:
    def __init__(self, model: RecordMachineAudioModel, view: RecordMachineAudioView, widget: QWidget, analysis_result_emitter):
        self.model = model
        self.view = view
        self.widget = widget
        self._emit_analysis_completed = analysis_result_emitter

        self._analysis_ctx = None
        self._analysis_job_q = None
        self._analysis_res_q = None
        self._analysis_proc = None
        self._analysis_running = False
        self._analysis_listener_thread = None
        self._analysis_starting = False
        self._temp_dir = os.path.join(tempfile.gettempdir(), "audio_segments_tmp")
        try:
            os.makedirs(self._temp_dir, exist_ok=True)
        except Exception:
            pass

        self._plot_thread = None
        self._plot_counter = 0

        self.model.auto_save_count.signal_for_update.connect(self.save_audio_data)

    def update_model_name(self, model_name: str):
        self.model.model_name = model_name or ""

    def record_audio(self):
        if not self.view.audio_store_path_lineedit.text():
            QMessageBox.warning(self.widget, "提示", "请选择保存音频的路径")
            return
        self.view.record_btn.setEnabled(False)
        self.view.stop_btn.setEnabled(True)
        self.view.audio_store_path_lineedit.setEnabled(False)
        self.model.data_struct.record_flag = True
        self.view.set_light_color(self.view.green_light, "green")
        self.view.set_light_color(self.view.red_light, "gray")
        if hasattr(self.widget, "recording_started"):
            self.widget.recording_started.emit()
        self.model.auto_save_count.count_start()
        self.model.start_record_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.view.chart_graph.clear()
        self.init_new_canvas()
        log_controller.info("开始录制音频")

        if self.model.segment_extractor:
            if not self.model.segment_extractor.is_running:
                self.model.segment_extractor.start()
        self._start_analysis_process()

        self.model.audio_manager.start_recording(self.model.ctx, self.model.selected_channels, self.model.sampling_rate, self.model.channels)
        if self._plot_thread is None or not self._plot_thread.is_alive():
            self._plot_thread = threading.Thread(target=self.update_plot, args=(self.model.selected_channels, self.model.data_struct.audio_data, self.view.chart_graph), daemon=True)
            self._plot_thread.start()

    def stop_record(self):
        self.model.data_struct.record_flag = False
        self.view.set_light_color(self.view.green_light, "gray")
        self.view.set_light_color(self.view.red_light, "gray")
        self.view.record_btn.setEnabled(True)
        self.view.stop_btn.setEnabled(False)
        self.view.audio_store_path_lineedit.setEnabled(True)
        self.model.auto_save_count.count_stop()
        self.model.set_up_audio_store_zero()
        self.model.start_record_time = None
        if self.model.segment_extractor and self.model.segment_extractor.is_running:
            self.model.segment_extractor.stop()
        self._stop_analysis_process()
        self.model.audio_manager.stop_recording()
        log_controller.info("停止录制音频")
        if hasattr(self.widget, "recording_stopped"):
            self.widget.recording_stopped.emit()

    def init_new_canvas(self):
        x = np.linspace(-self.model.plot_points_section / self.model.sampling_rate, 0, num=self.model.plot_points_section)
        self.view.chart_graph.clear()
        for i in range(len(self.model.selected_channels)):
            plot_audio_section = self.model.data_struct.audio_data[i, -self.model.plot_points_section:]
            self.view.chart_graph.draw_waveform(plot_audio_section, x, i)
            freqs, times_arr, sxx = spectrogram(plot_audio_section, nfft=self.model.nfft, fs=self.model.fs)
            self.view.chart_graph.draw_stftfrom(freqs, times_arr, sxx, i)

    def update_plot(self, selected_channels, audio_data, canvas):
        while True:
            if not self.model.data_struct.record_flag:
                break
            self._plot_counter += 1
            self.model.flush_audio_queue_to_array()
            for i in range(len(selected_channels)):
                buf = audio_data[i]
                pps = self.model.plot_points_section
                if np.all(buf != 0):
                    y = buf[-pps:]
                else:
                    nz = np.flatnonzero(buf)
                    if nz.size == 0:
                        y = np.zeros(pps, dtype=buf.dtype)
                    else:
                        last_idx = int(nz[-1]) + 1
                        if last_idx >= pps:
                            y = buf[last_idx - pps:last_idx]
                        else:
                            y = np.zeros(pps, dtype=buf.dtype)
                            y[-last_idx:] = buf[:last_idx]
                canvas.update_waveform(y, i)
                freqs, times_arr, sxx = spectrogram(y, nfft=self.model.nfft, fs=self.model.fs)
                sxx_log = np.log(sxx / 1e-11)
                np_sxx_log = sxx_log / np.max(sxx_log)
                canvas.update_stftfrom(freqs, times_arr, np_sxx_log, i)
            time.sleep(1)

    def on_audio_path_changed(self, text):
        self.model.set_audio_store_path(text)

    def select_store_path(self):
        path = QFileDialog.getExistingDirectory(self.widget, "选择存储路径")
        if path:
            self.view.audio_store_path_lineedit.setText(path)
            self.model.set_audio_store_path(path)
            self.model.save_store_path_to_txt(path)

    def on_show(self):
        self.model.load_device_info()
        if self.model.data_struct.channels_change_flag:
            self.model.set_up_audio_store_zero()
            self.view.chart_graph.create_chart(len(self.model.selected_channels))
            self.model.data_struct.channels_change_flag = False

    def on_close(self, event):
        if self.model.segment_extractor and self.model.segment_extractor.is_running:
            self.model.segment_extractor.stop()
        self._stop_analysis_process()
        self.model.audio_manager.stop_recording()
        self.model.audio_manager.quit()
        self.model.audio_manager.wait()
        self.model.data_struct.record_flag = False
        event.accept()

    def save_audio_data(self, countdown_time):
        if countdown_time > self.model.total_display_time:
            return
        start_time = self.model.save_audio_data(countdown_time, self.view.audio_store_path_lineedit.text())
        if start_time is None:
            QMessageBox.warning(self.widget, "提示", "录音时间不足，无法保存")

    def build_audio_segment_extractor(self, extract_flag, extract_interval=None, segment_duration=None):
        self.model.build_audio_segment_extractor(
            extract_flag,
            extract_interval=extract_interval,
            segment_duration=segment_duration,
            on_extracted=self._handle_segments_extracted,
        )

    def _handle_segments_extracted(self, segments: np.ndarray, sampling_rate: int):
        try:
            num_channels = segments.shape[0]
        except Exception:
            return
        code, query_result = RecordMachineAudioModel.get_model_info(self.model.model_name)
        if code != error_code.OK or not query_result:
            results = [{"channel": i, "data": {"ret_code": -1, "ret_msg": "model not found", "result": []}} for i in range(num_channels)]
            self._emit_analysis_completed(results)
            return
        model_path, config_path = query_result
        self._start_analysis_process()
        job_id = f"{int(time.time()*1000)}_{uuid.uuid4().hex}"
        npy_path = os.path.join(self._temp_dir, f"segments_{job_id}.npy")
        try:
            np.save(npy_path, segments)
            if self._analysis_job_q is not None:
                self._analysis_job_q.put({
                    "job_id": job_id,
                    "npy_path": npy_path,
                    "sampling_rate": sampling_rate,
                    "model_path": model_path,
                    "config_path": config_path,
                })
        except Exception as e:
            results = [{"channel": -1, "data": {"ret_code": -1, "ret_msg": f"enqueue error: {e}", "result": []}}]
            self._emit_analysis_completed(results)

    def _start_analysis_process(self):
        if self._analysis_starting:
            return
        if self._analysis_proc is not None and self._analysis_proc.is_alive():
            if not self._analysis_running:
                self._analysis_running = True
            if self._analysis_listener_thread is None:
                self._start_analysis_listener()
            return
        self._analysis_starting = True
        try:
            self._analysis_ctx = mp.get_context("spawn")
            self._analysis_job_q = self._analysis_ctx.Queue()
            self._analysis_res_q = self._analysis_ctx.Queue()
            self._analysis_proc = self._analysis_ctx.Process(target=analysis_worker, args=(self._analysis_job_q, self._analysis_res_q), daemon=True)
            self._analysis_proc.start()
            self._analysis_running = True
            self._start_analysis_listener()
        except Exception as e:
            print(f"启动分析进程失败: {e}")
        finally:
            self._analysis_starting = False

    def _start_analysis_listener(self):
        if self._analysis_listener_thread is not None:
            return
        def _listen():
            while self._analysis_running:
                try:
                    msg = self._analysis_res_q.get(timeout=0.5)
                except Exception:
                    continue
                try:
                    if msg and isinstance(msg, dict):
                        results = msg.get("results", [])
                        self._emit_analysis_completed(results)
                except Exception:
                    pass
        self._analysis_listener_thread = threading.Thread(target=_listen, daemon=True)
        self._analysis_listener_thread.start()

    def _stop_analysis_process(self):
        self._analysis_running = False
        try:
            if self._analysis_job_q is not None:
                try:
                    self._analysis_job_q.put(None)
                except Exception:
                    pass
            if self._analysis_proc is not None:
                self._analysis_proc.join(timeout=5)
                if self._analysis_proc.is_alive():
                    self._analysis_proc.terminate()
        except Exception:
            pass
        finally:
            try:
                if self._analysis_job_q is not None:
                    self._analysis_job_q.close()
                    self._analysis_job_q.join_thread()
            except Exception:
                pass
            try:
                if self._analysis_res_q is not None:
                    self._analysis_res_q.close()
                    self._analysis_res_q.join_thread()
            except Exception:
                pass
            self._analysis_proc = None
            self._analysis_job_q = None
            self._analysis_res_q = None
            self._analysis_listener_thread = None
            self._analysis_starting = False
