from re import T
import numpy as np
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import sounddevice as sd
import time
import threading

from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtWidgets import QFileDialog, QFrame, QMessageBox
from scipy.signal import spectrogram

from base.audio_data_manager import auto_save_data
from base.load_device_info import load_devices_data
from base.sound_device_manager import get_default_device
from base.log_manager import LogManager
from base.record_audio import AudioDataManager
from base.data_struct.data_deal_struct import DataDealStruct
from base.data_struct.audio_segment_extractor import AudioSegmentExtractor
from base.predict_model import predict_from_audio
from base.training_model_management import TrainingModelManagement
from consts import model_consts, error_code
from consts.running_consts import DEFAULT_DIR
from ui.system_information_textedit import log_controller
from my_controls.multiple_chartsgraph import MultipleChartsGraph
from my_controls.countdown import Countdown
from ui.device_list import DeviceListWindow


class RecordMachineAudioWidget(QWidget):
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    analysis_completed = pyqtSignal(object)  # 发送分析结果到主程序

    def __init__(self, parent=None):
        super(RecordMachineAudioWidget, self).__init__(parent)
        self.data_struct = DataDealStruct()

        self.logger = LogManager.set_log_handler("core")

        self.sampling_rate = 44100
        self.channels = None
        self.selected_channels = list()
        self.total_display_time = 600  # s
        self.nfft = 256
        self.fs = 44100
        self.ctx = sd._CallbackContext()

        self.record_btn = QPushButton("Record")
        self.stop_btn = QPushButton("Stop")
        self.audio_store_path_lineedit = QLineEdit()
        # self.warning_light = QLabel()
        self.red_light = QLabel()
        self.green_light = QLabel()
        self.status_label = QLabel("状态：")
        self.status_label.setStyleSheet("font-size: 35px;")
        self.red_light_color = "gray"
        self.green_light_color = "gray"

        self.select_device_name = None
        self.plot_time = 5
        self.start_record_time = None
        self.model_name:str = ""
        self.t = None
        self.max_points = self.total_display_time * self.sampling_rate
        self.plot_points_section = self.plot_time * self.sampling_rate
        self.buffer_len = 30 * self.sampling_rate

        self.load_device_info()
        self.set_up_audio_store_zero()

        self.audio_manager = AudioDataManager()
        # self.audio_manager.signal_for_update.connect(self.update_data)
        self.auto_save_count = Countdown(self.total_display_time - 10)
        self.auto_save_count.signal_for_update.connect(self.save_audio_data)

        # 初始化音频片段提取器（遵循开闭原则，通过组合扩展功能）
        self.segment_extractor = None

        self.chart_graph = MultipleChartsGraph()
        self.init_ui()

    def init_ui(self):
        record_operation_layout = self.create_record_operation_layout()

        h_line = QFrame()
        h_line.setFrameShape(QFrame.HLine)
        h_line.setFrameShadow(QFrame.Sunken)

        solid_graph_layout = self.create_solid_graph_layout()

        layout = QVBoxLayout()
        layout.addLayout(record_operation_layout)
        layout.addWidget(h_line)
        # layout.addWidget(self.chart_graph)
        layout.addLayout(solid_graph_layout)
        self.setLayout(layout)

    def set_up_audio_store_zero(self):
        self.data_struct.audio_data = np.zeros((len(self.selected_channels), self.max_points), dtype=np.float16)
        self.data_struct.audio_data_arr = [
            np.zeros(self.buffer_len, dtype=np.float16) for _ in range(len(self.selected_channels))
        ]
        self.data_struct.write_index = [0] * len(self.selected_channels)  #
        self.channel_index = [0] * len(self.selected_channels)
        # 存储区当前已填充长度（按通道跟踪）
        self.storage_filled_len = [0] * len(self.selected_channels)

    def build_audio_segment_extractor(self, extract_flag, extract_interval=None, segment_duration=None):
        """
        创建并配置音频片段提取器，变量参数由外部传入。
        """
        if extract_flag:
            self.segment_extractor = AudioSegmentExtractor(
                extract_interval=extract_interval,
                segment_duration=segment_duration,
                sampling_rate=self.sampling_rate,
            )
            self.segment_extractor.set_audio_source(
                self.data_struct.audio_data_arr,
                write_index_ref=self.data_struct.write_index
            )
            # 设置提取完成回调：进行多线程预测并回传结果
            self.segment_extractor.set_on_extracted_callback(self._handle_segments_extracted)
            self.data_struct.segment_extractor = self.segment_extractor
        else:
            self.segment_extractor = None
            self.data_struct.segment_extractor = None

    def update_model_name(self, model_name):
        self.model_name = model_name

    def create_record_operation_layout(self):
        self.set_record_and_stop_btn_function()
        audio_store_path_label = QLabel("音频存储路径")
        self.set_audio_store_path_lineedit_function()

        about_dy_btn = QPushButton("关于东原")
        about_dy_btn.clicked.connect(self.on_about_dy)
        # self.set_light_color(self.warning_light, "gray")

        font = QFont()
        font.setPointSize(15)
        self.record_btn.setFont(font)
        self.stop_btn.setFont(font)
        about_dy_btn.setFont(font)

        layout = QHBoxLayout()
        layout.addWidget(self.record_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(audio_store_path_label)
        layout.addWidget(self.audio_store_path_lineedit)
        layout.addWidget(about_dy_btn)
        # layout.addWidget(self.warning_light)

        return layout

    def create_solid_graph_layout(self):
        solid_graph = QLabel()
        solid_graph.setPixmap(QPixmap(DEFAULT_DIR + "ui/ui_pic/solid_graph.png"))
        solid_graph.setMaximumSize(500,350)
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
        # solid_graph_layout.addWidget(solid_graph)
        solid_graph_layout.addLayout(solid_light_layout)
        solid_graph_layout.addWidget(vertical_line)
        solid_graph_layout.addWidget(self.chart_graph)
        return solid_graph_layout

    def set_record_and_stop_btn_function(self):
        self.stop_btn.setEnabled(False)
        self.record_btn.setStyleSheet("color: green;")
        self.stop_btn.setStyleSheet("color: red;")
        self.record_btn.clicked.connect(self.record_audio)
        self.stop_btn.clicked.connect(self.stop_record)

    def set_audio_store_path_lineedit_function(self):
        self.audio_store_path_lineedit.setPlaceholderText("请选择音频存储路径")
        self.audio_store_path_lineedit.textChanged.connect(self.change_audio_store_path)
        self.init_store_path()
        icon_path = DEFAULT_DIR + "ui/ui_pic/ai_window_pic/folder-s.png"
        select_store_path_action = self.audio_store_path_lineedit.addAction(
            QIcon(icon_path), QLineEdit.TrailingPosition
        )
        select_store_path_action.triggered.connect(self.select_store_path)

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
        # 固定为“状态：”，不随录音或灯色改变
        self.status_label.setText("状态：")

    def init_store_path(self):
        try:
            with open( DEFAULT_DIR + "ui/ui_config/audio_store_path.txt", "r") as f:
                    self.audio_store_path = f.readline()
                    self.audio_store_path_lineedit.setText(self.audio_store_path)
        except Exception as e:
            self.logger.error(f"init_store_path failed: {e}")

    def record_audio(self):
        if not self.audio_store_path_lineedit.text():
            QMessageBox.warning(self, "提示", "请选择保存音频的路径")
            return
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.audio_store_path_lineedit.setEnabled(False)
        # self.set_light_color(self.warning_light, "green")
        self.data_struct.record_flag = True
        self.set_light_color(self.green_light, "green")
        self.set_light_color(self.red_light, "gray")
        # 发射录音开始信号，用于禁用菜单
        self.recording_started.emit()

        self.auto_save_count.count_start()
        self.start_record_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.chart_graph.clear()
        self.init_new_canvas()
        log_controller.info("开始录制音频")

        # 启动音频片段提取器
        if self.segment_extractor:
            if not self.segment_extractor.is_running:
                self.segment_extractor.start()
            else:
                print("音频片段提取器已经在运行")

        print("被传入的声道： %s" %self.selected_channels)
        
        self.audio_manager.start_recording(self.ctx, self.selected_channels, self.sampling_rate, self.channels)
        if self.t is None:
            print("start")
            self.t = threading.Thread(
                target=self.update_plot, args=(self.selected_channels, self.data_struct.audio_data, self.chart_graph)
            ).start()
        else:
            print("restart")
            self.t._restart()

    def stop_record(self):
        # self.set_light_color(self.warning_light, "gray")
        # self.set_light_color(self.red_light, "red")
        self.data_struct.record_flag = False
        self.set_light_color(self.green_light, "gray")
        self.set_light_color(self.red_light, "gray")
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.audio_store_path_lineedit.setEnabled(True)
        self.auto_save_count.count_stop()
        self.set_up_audio_store_zero()
        self.start_record_time = None
        
        # 停止音频片段提取器
        if self.segment_extractor:
            if self.segment_extractor.is_running:
                self.segment_extractor.stop()
            else:
                print("音频片段提取器已经在停止")
        
        self.audio_manager.stop_recording()
        log_controller.info("停止录制音频")
        # 发射录音停止信号，用于恢复菜单
        self.recording_stopped.emit()

    @staticmethod
    def get_model_info(model_name):
        code, query_result = TrainingModelManagement().get_model_path_from_json(model_name)
        if code == error_code.OK and query_result:
            item = query_result[0]
            model_path = (item.get("path") or item.get("model_path") or "").strip()
            config_path = (item.get("config_path") or "").strip()
            # 统一转为绝对路径（若为相对路径则相对 DEFAULT_DIR）
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

    def _handle_segments_extracted(self, segments: np.ndarray, sampling_rate: int):
        """
        在每次提取片段结束后，对每个通道的数据并行执行 predict_from_audio，
        并通过 analysis_completed 信号把结果回传到主程序。
        """
        try:
            num_channels = segments.shape[0]
        except Exception:
            return

        def analyze_channel(channel_index: int, model_path: str, config_path: str):
            signal = segments[channel_index]
            try:
                ret_str = predict_from_audio(
                    signals=[signal],
                    file_names=[f"channel_{channel_index}"],
                    fs=[sampling_rate],
                    load_model_path=model_path,
                    model=None,
                    config_path=config_path,
                )
                ret = json.loads(ret_str)
            except Exception as e:
                ret = {"ret_code": -1, "ret_msg": f"predict error: {e}", "result": [[f"channel_{channel_index}", "ERR", "0.0"]]}
            return {"channel": channel_index, "data": ret}

        code, query_result = self.get_model_info(self.model_name)
        if code == error_code.OK:
            model_path, config_path = query_result
            max_workers = max(1, min(num_channels, 4))
            results = [None] * num_channels
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {executor.submit(analyze_channel, i, model_path, config_path): i for i in range(num_channels)}
                for future in as_completed(future_map):
                    idx = future_map[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        results[idx] = {"channel": idx, "data": {"ret_code": -1, "ret_msg": f"executor error: {e}", "result": []}}

            # 回传整批结果
            self.analysis_completed.emit(results)

    def load_device_info(self):
        # self.select_device_name, self.channels, self.selected_channels = load_devices_data()
        device_name, channels, selected_channels = load_devices_data()
        if device_name and channels and selected_channels:
            self.select_device_name, self.channels, self.selected_channels = (
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
                    # 使用第一个通道
                    self.selected_channels = [0]
                    # 保存到配置
                    DeviceListWindow.save_device_data_to_json(
                        self.select_device_name,
                        self.channels,
                        self.selected_channels,
                    )
                else:
                    # 极端情况下无法获取默认设备，设置安全默认值
                    self.select_device_name = "Default Microphone"
                    self.channels = 1
                    self.selected_channels = [0]
            except Exception as e:
                # 出错时回退到安全默认
                self.select_device_name = "Default Microphone"
                self.channels = 1
                self.selected_channels = [0]


    def select_store_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择存储路径")
        self.audio_store_path_lineedit.setText(path)
        self.audio_store_path = path
        self.save_store_path_to_txt(path)

    @staticmethod
    def save_store_path_to_txt(path):
        if not path:
            return
        with open(DEFAULT_DIR + "ui/ui_config/audio_store_path.txt", "w") as f:
            f.write(path)

    def change_audio_store_path(self):
        self.audio_store_path = self.sender().text()

    def on_about_dy(self):
        browser = QDesktopServices()
        browser.openUrl(QUrl("https://suzhoudongyuan.com/"))

    def show(self):
        self.load_device_info()
        if self.data_struct.channels_change_flag:
            self.set_up_audio_store_zero()
            self.chart_graph.create_chart(len(self.selected_channels))
            self.data_struct.channels_change_flag = False
        super().show()

    def closeEvent(self, event):
        """关闭窗口时确保资源释放"""
        # 停止音频片段提取器
        if self.segment_extractor:
            if self.segment_extractor.is_running:
                self.segment_extractor.stop()
        
        self.audio_manager.stop_recording()
        self.audio_manager.quit()
        self.audio_manager.wait()
        self.data_struct.record_flag = False
        event.accept()

    def save_audio_data(self):
        save_path = self.audio_store_path_lineedit.text()
        self.start_record_time = auto_save_data(
            self.data_struct.audio_data, self.sampling_rate, save_path, self.selected_channels, self.start_record_time
        )
        # print(len(self.data_struct.audio_data_arr[0]), len(self.data_struct.audio_data_arr[1]))
        # audio_data_array = np.array([list(queue) for queue in self.data_struct.audio_data_arr])
        # print(len(self.data_struct.audio_data_arr[0]), len(self.data_struct.audio_data_arr[1]))
        # self.start_record_time = auto_save_data(
        #     audio_data_array, self.sampling_rate, save_path, self.selected_channels, self.start_record_time
        # )

    count = 0

    def flush_audio_queue_to_array(self):
        """
        将环形缓冲区的数据转换为线性数组
        环形缓冲区中write_index指向下一个要写入的位置，
        因此最旧的数据在write_index位置，最新的数据在write_index-1位置
        """
        num_channels = len(self.selected_channels)
        if num_channels == 0:
            return

        # 在计算过程中通过 epoch 双读法保证一致快照
        while True:
            e1 = getattr(self.data_struct, "epoch", 0)
            print("e1 is %s " %e1)
            if e1 % 2 == 1:
                # 写入进行中，等待下一轮
                continue
            # 本轮缓存：每个通道的写指针快照
            new_write_indices = [None] * num_channels

            # 拍快照：若检测到 epoch 变化则整体重启
            restart_needed = False
            for i in range(num_channels):
                if e1 != getattr(self.data_struct, "epoch", 0):
                    restart_needed = True
                    break
                print("e1 is %s " %e1)
                # 获取当前写入位置快照
                write_idx_snapshot = int(self.data_struct.write_index[i])
                new_write_indices[i] = write_idx_snapshot

            # 若本轮检测到写入进行或 epoch 变化，则整体重启计算
            if restart_needed:
                continue

            # 先为所有通道计算新段，但不落盘，避免中途 epoch 变化造成脏写
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

                # 计算本次新录入的数据段（可能跨越尾部）
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

            # 再次确认 epoch 未变化且为稳定偶数
            e2 = getattr(self.data_struct, "epoch", 0)
            if e1 != e2 or (e2 % 2 == 1):
                continue

            # 统一将所有通道的新数据段追加到线性存储区（已确认一致快照）
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

                # 先在未满区域尾部追加
                filled = int(self.storage_filled_len[i])
                free = max(0, store_len - filled)
                if free > 0:
                    take = min(free, seg.size)
                    storage_array[filled:filled + take] = seg[:take]
                    filled += take
                    remaining = seg[take:]
                else:
                    remaining = seg

                # 若仍有剩余新数据且存储已满：
                if remaining.size > 0:
                    m = int(remaining.size)
                    if m >= store_len:
                        storage_array[:] = remaining[-store_len:]
                        filled = store_len
                    else:
                        storage_array[:-m] = storage_array[m:]
                        storage_array[-m:] = remaining
                        filled = store_len

                # 更新记录
                self.storage_filled_len[i] = min(store_len, filled)
                if staged_write_indices[i] is not None:
                    self.channel_index[i] = int(staged_write_indices[i])
                # 打印使用快照写指针，避免读取到回调中途的实时值
                print(f"Channel {i}: write_index={int(staged_write_indices[i])}")

            # 完成一轮无中断的计算与追加，退出
            break

    def init_new_canvas(self):
        print("init new canvas")
        print(time.strftime("%Y%m%d_%H%M%S", time.localtime()))
        self.x = np.linspace(-self.plot_points_section / self.sampling_rate, 0, num=self.plot_points_section)

        self.chart_graph.clear()
        for i in range(len(self.selected_channels)):
            plot_audio_section = self.data_struct.audio_data[i, -self.plot_points_section :]
            self.chart_graph.draw_waveform(plot_audio_section, self.x, i)
            # 设置绘图范围
            freqs, times, sxx = spectrogram(plot_audio_section, nfft=self.nfft, fs=self.fs)
            self.chart_graph.draw_stftfrom(freqs, times, sxx, i)

    def update_plot(self, selected_channels, audio_data, canvas):
        print("start update plot")
        while True:
            if not self.data_struct.record_flag:
                break

            self.count += 1
            # print(self.count)
            self.flush_audio_queue_to_array()

            for i in range(len(selected_channels)):
                buf = audio_data[i]
                pps = self.plot_points_section
                # 情况1：全为非零，按现有逻辑取末尾窗口
                if np.all(buf != 0):
                    y = buf[-pps:]
                else:
                    # 情况2：存在零，按“最后一个非零位置”为终点构造窗口
                    nz = np.flatnonzero(buf)
                    if nz.size == 0:
                        y = np.zeros(pps, dtype=buf.dtype)
                    else:
                        last_idx = int(nz[-1]) + 1  # 使其可作为切片右边界
                        if last_idx >= pps:
                            y = buf[last_idx - pps:last_idx]
                        else:
                            y = np.zeros(pps, dtype=buf.dtype)
                            y[-last_idx:] = buf[:last_idx]

                # 更新绘图数据
                canvas.update_waveform(y, i)

                freqs, times, sxx = spectrogram(y, nfft=self.nfft, fs=self.fs)
                sxx_log = np.log(sxx / 1e-11)
                np_sxx_log = sxx_log / np.max(sxx_log)
                canvas.update_stftfrom(freqs, times, np_sxx_log, i)

            time.sleep(1)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    main_window = RecordMachineAudioWidget()
    main_window.show()
    sys.exit(app.exec_())
