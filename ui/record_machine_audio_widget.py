import numpy as np
import sounddevice as sd
import time
import threading

from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtWidgets import QFileDialog, QFrame, QMessageBox
from scipy.signal import spectrogram

from base.audio_data_manager import auto_save_data
from base.load_device_info import load_devices_data
from base.record_audio import AudioDataManager
from base.data_struct.data_deal_struct import DataDealStruct
from base.data_struct.audio_segment_extractor import AudioSegmentExtractor
from ui.system_information_textedit import log_controller
from my_controls.multiple_chartsgraph import MultipleChartsGraph
from my_controls.countdown import Countdown


class RecordMachineAudioWidget(QWidget):

    def __init__(self, parent=None):
        super(RecordMachineAudioWidget, self).__init__(parent)
        self.data_struct = DataDealStruct()

        self.sampling_rate = 44100
        self.channels = None
        self.selected_channels = list()
        self.total_display_time = 60  # s
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
        self.t = None
        self.max_points = self.total_display_time * self.sampling_rate
        self.plot_points_section = self.plot_time * self.sampling_rate
        self.queue_len = 60 * self.sampling_rate

        self.load_device_info()
        self.data_struct.audio_data = np.zeros((len(self.selected_channels), self.max_points), dtype=np.float32)
        self.data_struct.audio_data_arr = [
            np.zeros(self.max_points, dtype=np.float32) for _ in range(len(self.selected_channels))
        ]
        self.data_struct.write_index = [0] * len(self.selected_channels)  #
        self.channel_index = [0] * len(self.selected_channels)

        self.audio_manager = AudioDataManager()
        # self.audio_manager.signal_for_update.connect(self.update_data)
        self.auto_save_count = Countdown(self.total_display_time - 10)
        self.auto_save_count.signal_for_update.connect(self.save_audio_data)

        # 初始化音频片段提取器（遵循开闭原则，通过组合扩展功能）
        self.segment_extractor = AudioSegmentExtractor(
            extract_interval=3.5,  # 每隔3.5秒提取一次
            segment_duration=4.0,   # 提取最后4秒的数据
            sampling_rate=self.sampling_rate
        )
        # 设置音频数据源，传入环形缓冲区和写入位置索引
        self.segment_extractor.set_audio_source(
            self.data_struct.audio_data_arr,
            write_index_ref=self.data_struct.write_index
        )
        self.data_struct.segment_extractor = self.segment_extractor

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
        solid_graph.setPixmap(QPixmap("D:/gqgit/new_project/ui/ui_pic/solid_graph.png"))
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
        icon_path = "D:/gqgit/new_project/ui/ui_pic/ai_window_pic/folder-s.png"
        select_store_path_action = self.audio_store_path_lineedit.addAction(
            QIcon(icon_path), QLineEdit.TrailingPosition
        )
        select_store_path_action.triggered.connect(self.select_store_path)

    def set_light_color(self, light, color):
        light.setFixedSize(80, 80)
        light.setAlignment(Qt.AlignCenter)
        path_map = {
            "red": "D:/gqgit/new_project/ui/ui_pic/red_light.png",
            "green": "D:/gqgit/new_project/ui/ui_pic/green_light.png",
            "gray": "D:/gqgit/new_project/ui/ui_pic/gray_light.png",
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
        with open("D:/gqgit/new_project/ui/ui_config/audio_store_path.txt", "r") as f:
            self.audio_store_path = f.readline()
            self.audio_store_path_lineedit.setText(self.audio_store_path)

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

        self.auto_save_count.count_start()
        self.start_record_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.chart_graph.clear()
        self.init_new_canvas()
        log_controller.info("开始录制音频")

        # 启动音频片段提取器
        self.segment_extractor.start()
        
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
        self.start_record_time = None
        
        # 停止音频片段提取器
        self.segment_extractor.stop()
        
        self.audio_manager.stop_recording()
        log_controller.info("停止录制音频")

    def load_device_info(self):
        self.select_device_name, self.channels, self.selected_channels = load_devices_data()

    def select_store_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择存储路径")
        self.audio_store_path_lineedit.setText(path)
        self.audio_store_path = path
        self.save_store_path_to_txt(path)

    @staticmethod
    def save_store_path_to_txt(path):
        if not path:
            return
        with open("D:/gqgit/new_project/ui/ui_config/audio_store_path.txt", "w") as f:
            f.write(path)

    def change_audio_store_path(self):
        self.audio_store_path = self.sender().text()

    def on_about_dy(self):
        browser = QDesktopServices()
        browser.openUrl(QUrl("https://suzhoudongyuan.com/"))

    def show(self):
        self.load_device_info()
        if self.data_struct.channels_change_flag:
            self.chart_graph.create_chart(len(self.selected_channels))
            self.data_struct.channels_change_flag = False
        super().show()

    def closeEvent(self, event):
        """关闭窗口时确保资源释放"""
        # 停止音频片段提取器
        if self.segment_extractor and self.segment_extractor.is_running:
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

    # def update_data(self, data):
    #     """槽函数：接收并处理音频数据"""
    #     for i in range(len(self.selected_channels)):
    #         data1 = np.array(data[i], dtype=np.float32)
    #         width = data1.size
    #         self.data_struct.audio_data[i, :-width] = self.data_struct.audio_data[i, width:]
    #         self.data_struct.audio_data[i, -width:] = data1
    count = 0

    def flush_audio_queue_to_array(self):
        """
        将环形缓冲区的数据转换为线性数组
        环形缓冲区中write_index指向下一个要写入的位置，
        因此最旧的数据在write_index位置，最新的数据在write_index-1位置
        """
        for i in range(len(self.selected_channels)):
            # 获取当前写入位置
            write_idx = self.data_struct.write_index[i]
            
            # 只在写入位置发生变化时更新数据
            if write_idx != self.channel_index[i]:
                # 获取环形缓冲区
                ring_buffer = self.data_struct.audio_data_arr[i]
                
                # 将环形缓冲区重组为线性数组
                # 正确的顺序：[write_idx:] 是较旧的数据, [:write_idx] 是较新的数据
                # 拼接后得到按时间顺序排列的完整数据（从最旧到最新）
                linear_data = np.concatenate([ring_buffer[write_idx:], ring_buffer[:write_idx]])
                
                # 更新到线性数组
                self.data_struct.audio_data[i] = linear_data
                
                # 更新索引记录
                self.channel_index[i] = write_idx
                
                print(f"Channel {i}: write_index={write_idx}")

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
            print(self.count)
            self.flush_audio_queue_to_array()

            for i in range(len(selected_channels)):
                y = audio_data[i, -self.plot_points_section :]

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
