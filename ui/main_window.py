import json
import os
import tempfile
import time

import numpy as np
from scipy.signal import spectrogram

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMessageBox, QFileDialog

from base.audio_data_manager import auto_save_data
from base.database.fixed_time_ng_total import query_warning_between
from base.indicator_engine import IndicatorEngine, PredictionItem
from base.load_device_info import load_devices_data
from base.sound_device_manager import get_default_device
from base.log_manager import LogManager
from base.record_audio import AudioDataManager
from base.data_struct.data_deal_struct import DataDealStruct
from base.data_struct.audio_segment_extractor import AudioSegmentExtractor
from base.sound_device_manager import sd, change_default_mic
from base.tcp.tcp_client import send_dict
# from base.training_model_management import TrainingModelManagement

from consts import error_code
from consts.running_consts import DEFAULT_DIR

# from ui.center_widget import CenterWidget
from my_controls.countdown import Countdown
from ui.device_list import DeviceListWindow
from ui.machine_record_view.center_widget import CenterWidget


class MainWindowMode:
    def __init__(self):
        self.logger = LogManager.set_log_handler("core")
        self.data_struct = DataDealStruct()
        self.page_index = 0
        
        self.sampling_rate = 44100
        self.channels = None
        self.selected_channels = list()
        self.infor_limit_config = dict()
        self.tcp_config = dict()
        self.ai_analysis_config = dict()
        self.read_channel = 0
        
        self.total_display_time = 600
        self.nfft = 256
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
        self.infor_limit_count = Countdown(self.infor_limit_config.get("duration_min", 100) * 60)
        self.auto_write_timer = QTimer()
        self.auto_write_timer.setInterval(100)  # 从200ms优化到100ms，提高流畅度
        # self.auto_write_timer.timeout.connect(self.flush_audio_queue_to_array)

        self.segment_extractor = None

        self.audio_store_path = ""

        self.channel_index = []
        self.storage_filled_len = []

    def load_device_info(self):
        device_name, channels, selected_channels, _, mic_index = load_devices_data()
        change_default_mic(mic_index)
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
        store_path_file = DEFAULT_DIR + "ui/ui_config/audio_store_path.txt"
        if os.path.exists(store_path_file):
            with open(store_path_file, "r") as f:
                self.audio_store_path = f.readline()

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


    # @staticmethod
    # def get_model_info(model_name):
    #     code, query_result = TrainingModelManagement().get_model_path_from_json(model_name)
    #     if code == error_code.OK and query_result:
    #         item = query_result[0]
    #         model_path = (item.get("path") or item.get("model_path") or "").strip()
    #         config_path = (item.get("config_path") or "").strip()
    #         gmm_path = (item.get("gmm_path") or "").strip()
    #         scaler_path = (item.get("scaler_path") or "").strip()
    #         if not os.path.isabs(model_path):
    #             really_model_path = os.path.normpath(os.path.join(DEFAULT_DIR, model_path))
    #         else:
    #             really_model_path = os.path.normpath(model_path)
    #         if not os.path.isabs(config_path):
    #             really_config_path = os.path.normpath(os.path.join(DEFAULT_DIR, config_path))
    #         else:
    #             really_config_path = os.path.normpath(config_path)
    #         return error_code.OK, (really_model_path, really_config_path, gmm_path, scaler_path)
    #     return error_code.INVALID_QUERY, None


class MainWindowController:
    def __init__(self, model: MainWindowMode, view: CenterWidget):
        self.logger = LogManager.set_log_handler("core")
        self.model = model
        self.view = view

        self._analysis_ctx = None
        self._analysis_job_q = None
        self._analysis_res_q = None
        self._analysis_proc = None
        self._analysis_running = False
        self._analysis_listener_thread = None
        self._analysis_starting = False
        self._temp_dir = os.path.join(tempfile.gettempdir(), "audio_segments_tmp")

        # 指示灯引擎与定时器
        self._indicator_engine = IndicatorEngine(red_add_seconds=3.0)
        self._light_timer = QTimer()
        self._light_timer.setInterval(200)  # 200ms 刷新
        self._light_timer.timeout.connect(self._on_light_tick)

        self.init_infor_limit_config()
        self.init_tcp_config()
        self.model.init_store_path()
        self.view.audio_store_path_lineedit.setText(self.model.audio_store_path)
        self.model.infor_limit_count.set_count(self.model.infor_limit_config.get("duration_min", 100) * 60)

        self.model.load_device_info()
        self.model.set_up_audio_store_zero()
        self.view.hide_right_part_widget(len(self.model.selected_channels) < 2 )
        self.change_waveform_title()

        self.view.prev_page.setEnabled(False)
        if len(self.model.selected_channels) > 2:
            self.view.next_page.setEnabled(True)
        else:
            self.view.next_page.setEnabled(False)
        self.view.prev_page.clicked.connect(self.prev_page)
        self.view.next_page.clicked.connect(self.next_page)
        
        self.view.record_btn.clicked.connect(self.record_audio)
        self.view.stop_btn.clicked.connect(self.stop_record)
        self.view.select_store_path_action.triggered.connect(self.select_store_path)
        self.model.auto_save_count.signal_for_update.connect(self.save_audio_data)
        self.model.auto_write_timer.timeout.connect(self.work_function)

    def prev_page(self):
        if self.model.page_index > 0:
            self.model.page_index -= 1
            # self.view.create_chart_graph(len(self.model.selected_channels))
            self.change_waveform_title()
            if not self.view.next_page.isEnabled():
                self.view.next_page.setEnabled(True)
        else:
            if self.view.prev_page.isEnabled():
                self.view.prev_page.setEnabled(False)
        
        if self.model.page_index == 0:
            self.view.prev_page.setEnabled(False)

    def next_page(self):
        if len(self.model.selected_channels) - self.model.page_index * 2 > 0:
            if not self.view.prev_page.isEnabled():
                self.view.prev_page.setEnabled(True)
            self.model.page_index += 1
            # self.view.create_chart_graph(len(self.model.selected_channels) - 2)
            self.change_waveform_title()
        else:
            if self.view.next_page.isEnabled():
                self.view.next_page.setEnabled(False)

        if self.model.page_index == (len(self.model.selected_channels)) // 2 - 1:
            self.view.next_page.setEnabled(False)

    def record_audio(self):
        if not self.view.audio_store_path_lineedit.text():
            self.view.record_btn.setChecked(False)
            self.view.record_btn.setEnabled(True)
            self.view.stop_btn.setEnabled(False)
            self.logger.warning("请选择保存音频的路径")
            QMessageBox.warning(self.view, "提示", "请选择保存音频的路径")
            return
        self.view.audio_store_path_lineedit.setEnabled(False)
        self.model.data_struct.record_flag = True
        # self.view.set_light_color(self.view.green_light, "green")
        # self.view.set_light_color(self.view.red_light, "gray")
        # if hasattr(self.widget, "recording_started"):
        #     self.widget.recording_started.emit()
        self.model.auto_write_timer.start()
        self.model.auto_save_count.count_start()
        # self.model.infor_limit_count.count_start()
        self.model.start_record_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        # self.view.chart_graph.clear()
        # self.init_new_canvas()
        # log_controller.info("开始录制音频")

        # 启动指示灯定时器
        if self.model.infor_limit_config.get("enable_limit", False):
            self._light_timer.start()

        if self.model.segment_extractor:
            if not self.model.segment_extractor.is_running:
                self.model.segment_extractor.start()
        # self.start_analysis_process()

        self.model.audio_manager.start_recording(self.model.ctx, self.model.selected_channels, self.model.sampling_rate, self.model.channels)
        
    def stop_record(self):
        self.model.data_struct.record_flag = False
        # 停止指示灯定时器
        if self.model.infor_limit_config.get("enable_limit", False):
            self._light_timer.stop()
        
        # self.view.set_light_color(self.view.green_light, "gray")
        # self.view.set_light_color(self.view.red_light, "gray")
        self.view.audio_store_path_lineedit.setEnabled(True)
        self.model.auto_save_count.count_stop()
        self.model.auto_write_timer.stop()
        # self.model.infor_limit_count.count_stop()
        self.model.set_up_audio_store_zero()
        self.model.start_record_time = None
        if self.model.segment_extractor and self.model.segment_extractor.is_running:
            self.model.segment_extractor.stop()
        # self.stop_analysis_process()
        self.model.audio_manager.stop_recording()
        # log_controller.info("停止录制音频")
        # if hasattr(self.widget, "recording_stopped"):
        #     self.widget.recording_stopped.emit()

        self._indicator_engine._colorindicator.red.remaining_seconds = 0

    def change_waveform_title(self):
        if len(self.model.selected_channels) - self.model.page_index * 2 > 0:
            if len(self.model.selected_channels) - self.model.page_index * 2 > 1:
                self.view.set_waveform_title([self.model.page_index * 2 + 1, self.model.page_index * 2 + 2])
            else:
                self.view.set_waveform_title([self.model.page_index * 2])

    def save_audio_data(self, countdown_time):
        if countdown_time > self.model.total_display_time:
            return
        start_time = self.model.save_audio_data(countdown_time, self.view.audio_store_path_lineedit.text())
        if start_time is None:
            QMessageBox.warning(self.view, "提示", "录音时间不足，无法保存")

    def select_store_path(self):
        path = QFileDialog.getExistingDirectory(self.view, "选择存储路径")
        if path:
            self.view.audio_store_path_lineedit.setText(path)
            self.model.set_audio_store_path(path)
            self.model.save_store_path_to_txt(path)

    def check_infor_limit(self, countdown_time):
        now_ts = int(time.time())
        now_cn = time.strftime("%Y年%m月%d日 %H时%M分%S秒", time.localtime(now_ts))
        duration_min = int(self.model.infor_limit_config.get("duration_min", 100))
        past_ts = now_ts - max(0, duration_min) * 60
        past_cn = time.strftime("%Y年%m月%d日 %H时%M分%S秒", time.localtime(past_ts))
        code, query_result = query_warning_between(past_cn, now_cn)
        if code != error_code.OK or not query_result:
            return
        warning_count = len(query_result)
        if warning_count >= int(self.model.infor_limit_config.get("max_count", 100)):
            self._indicator_engine.process_predictions([PredictionItem(result="NG")])
            self.by_tcp_send_warning("NG")
            return

    def by_tcp_send_warning(self, warning_type: str):
        data = {
            "warning_type": warning_type,
            "warning_time": time.time(),
            "warning_message": "设备异常，请检查设备状态",
        }
        if self.model.tcp_config.get("enable_tcp", False):
            server_host = str(self.model.tcp_config.get("ip", "127.0.0.1"))
            server_port = int(self.model.tcp_config.get("port", 50000))
            print(f"发送警告到 {server_host}:{server_port}")
            try:
                send_dict(
                    server_host=server_host,
                    server_port=server_port,
                    data_obj=data,
                )
            except Exception as e:
                QMessageBox.critical(self.widget, "错误", f"发送警告失败: {e}")

    def _on_light_tick(self):
        """指示灯定时器回调，更新灯状态"""
        try:
            # 未录音则不点亮指示灯
            if not self.model.data_struct.record_flag:
                self.view.set_light_color(self.view.green_light, "gray")
                self.view.set_light_color(self.view.red_light, "gray")
                return
            
            # 时间推进
            self._indicator_engine.tick(self._light_timer.interval() / 1000.0)
            
            # 获取当前状态并更新UI
            snapshot = self._indicator_engine.render_snapshot()
            if not snapshot:
                # 若尚无任何数据，默认点亮绿灯
                self.view.set_light_color(self.view.red_light, "gray")
                self.view.set_light_color(self.view.green_light, "green")
                return
            
            color = snapshot.get("color", "GREEN")
            if color == "RED":
                self.view.set_light_color(self.view.red_light, "red")
                self.view.set_light_color(self.view.green_light, "gray")
            else:  # GREEN
                self.view.set_light_color(self.view.red_light, "gray")
                self.view.set_light_color(self.view.green_light, "green")
        except Exception as e:
            self.logger.error(f"Failed to on light tick: {e}")

    def init_infor_limit_config(self):
        infor_limit_path = DEFAULT_DIR + "ui/ui_config/infor_limition.json"
        if os.path.exists(infor_limit_path):
            with open(infor_limit_path, "r", encoding="utf-8") as f:
                infor_limit_config = json.load(f)
                self.model.infor_limit_config = infor_limit_config

    def init_tcp_config(self):
        tcp_config_path = DEFAULT_DIR + "ui/ui_config/tcp_config.json"
        if os.path.exists(tcp_config_path):
            with open(tcp_config_path, "r", encoding="utf-8") as f:
                tcp_config = json.load(f)
                self.model.tcp_config = tcp_config

    def work_function(self):
        self.model.flush_audio_queue_to_array()
        if len(self.model.selected_channels) > 1:
            wavefrom_data: list = list()
            spect_data: list = list()
            for i in range(2):
                channel_idx = self.model.page_index * 2 + i
                buf = self.model.data_struct.audio_data[channel_idx]
                pps = self.model.plot_points_section
                
                # 优化：直接使用 storage_filled_len 获取有效数据长度，避免遍历整个数组
                # 原来的 np.all(buf != 0) 和 np.flatnonzero(buf) 需要遍历 2600 万个元素
                filled_len = int(self.model.storage_filled_len[channel_idx])
                
                if filled_len >= pps:
                    # 数据足够，直接取最后 pps 个点
                    y = buf[filled_len - pps:filled_len]
                elif filled_len > 0:
                    # 数据不足，前面补零
                    y = np.zeros(pps, dtype=buf.dtype)
                    y[-filled_len:] = buf[:filled_len]
                else:
                    # 没有数据
                    y = np.zeros(pps, dtype=buf.dtype)
                
                wavefrom_data.append(y)
                
                # 优化：对原始数据降采样后再计算 spectrogram，减少计算开销
                downsample_factor = 4
                y_for_spec = y[::downsample_factor] if len(y) > 10000 else y
                fs_for_spec = self.model.sampling_rate // downsample_factor if len(y) > 10000 else self.model.sampling_rate
                freqs, times_arr, sxx = spectrogram(y_for_spec, nfft=self.model.nfft, fs=fs_for_spec)
                
                sxx_log = np.log(sxx / 1e-11)
                max_val = np.max(sxx_log)
                np_sxx_log = (sxx_log / max_val).T if max_val != 0 else sxx_log.T
                spect_data.append((freqs, times_arr, np_sxx_log))
            
            # 绘制波形图
            self.view.wav_or_spect_graph.plot_waveform(wavefrom_data[0], "left", self.model.sampling_rate)
            self.view.wav_or_spect_graph.plot_waveform(wavefrom_data[1], "right", self.model.sampling_rate)
            
            # 绘制时频图
            self.view.wav_or_spect_graph.plot_spectrogram(spect_data[0], "left")
            self.view.wav_or_spect_graph.plot_spectrogram(spect_data[1], "right")

def open_main_window():
    model = MainWindowMode()
    view = CenterWidget()
    controller = MainWindowController(model, view)

    # 保持强引用，避免 controller 被 GC 导致信号失效
    view.rm_model = model
    view.rm_controller = controller
    
    # 禁用最大化/恢复按钮
    view.setWindowFlags(view.windowFlags() & ~Qt.WindowMaximizeButtonHint)
    
    # 设置窗口为最大化
    view.setWindowState(view.windowState() | Qt.WindowMaximized)

    return view

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    view = open_main_window()
    # model = MainWindowMode()
    # view = CenterWidget()
    # main_window_controller = MainWindowController(model, view)
    view.showMaximized()  # 最大化显示窗口
    sys.exit(app.exec_())