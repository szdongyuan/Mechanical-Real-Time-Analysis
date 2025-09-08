import numpy as np
import sounddevice as sd
import time
import threading
from collections import deque

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon, QDesktopServices, QFont
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit
from PyQt5.QtWidgets import QFileDialog, QFrame, QMessageBox
from scipy.signal import spectrogram

from base.audio_data_manager import auto_save_data
from base.load_device_info import load_devices_data
from base.record_audio import AudioDataManager
from base.data_struct.data_deal_struct import DataDealStruct
from my_controls.multiple_chartsgraph import MultipleChartsGraph
from my_controls.countdown import Countdown


class RecordMachineAudioWidget(QWidget):

    def __init__(self, parent=None):
        super(RecordMachineAudioWidget, self).__init__(parent)
        self.data_struct = DataDealStruct()

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
        self.warning_light = QLabel()

        self.select_device_name = None
        self.plot_time = 5
        self.start_record_time = None
        self.t = None
        self.max_points = self.total_display_time * self.sampling_rate
        self.plot_points_section = self.plot_time * self.sampling_rate

        self.load_device_info()
        self.data_struct.audio_data = np.zeros((len(self.selected_channels), self.max_points), dtype=np.float32)
        self.data_struct.audio_data_queue = [deque(maxlen=self.max_points) for _ in range(len(self.selected_channels))]

        self.audio_manager = AudioDataManager()
        # self.audio_manager.signal_for_update.connect(self.update_data)
        self.auto_save_count = Countdown(self.total_display_time - 10)
        self.auto_save_count.signal_for_update.connect(self.save_audio_data)

        self.chart_graph = MultipleChartsGraph()
        self.init_ui()

    def init_ui(self):
        record_operation_layout = self.create_record_operation_layout()

        h_line = QFrame()
        h_line.setFrameShape(QFrame.HLine)
        h_line.setFrameShadow(QFrame.Sunken)

        layout = QVBoxLayout()
        layout.addLayout(record_operation_layout)
        layout.addWidget(h_line)
        layout.addWidget(self.chart_graph)
        self.setLayout(layout)

    def create_record_operation_layout(self):
        self.set_record_and_stop_btn_function()
        audio_store_path_label = QLabel("音频存储路径")
        self.set_audio_store_path_lineedit_function()

        about_dy_btn = QPushButton("关于东原")
        about_dy_btn.clicked.connect(self.on_about_dy)
        self.set_light_color(self.warning_light, "gray")

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
        layout.addWidget(self.warning_light)

        return layout

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
        light.setFixedSize(20, 20)
        light.setStyleSheet(f"background-color: {color}; border-radius: 10px;")

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
        self.set_light_color(self.warning_light, "green")

        self.auto_save_count.count_start()
        self.data_struct.record_flag = True
        self.start_record_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        self.chart_graph.clear()
        self.init_new_canvas()

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
        self.set_light_color(self.warning_light, "gray")
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.audio_store_path_lineedit.setEnabled(True)
        self.data_struct.record_flag = False
        self.auto_save_count.count_stop()
        self.start_record_time = None
        self.audio_manager.stop_recording()

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

    def update_data(self, data):
        """槽函数：接收并处理音频数据"""
        for i in range(len(self.selected_channels)):
            data1 = np.array(data[i], dtype=np.float32)
            width = data1.size
            self.data_struct.audio_data[i, :-width] = self.data_struct.audio_data[i, width:]
            self.data_struct.audio_data[i, -width:] = data1

    def flush_audio_queue_to_array(self):
        for i in range(len(self.selected_channels)):
            queue = self.data_struct.audio_data_queue[i]
            if queue:  # 如果队列中有数据
                new_data = np.array(queue, dtype=np.float32)

                # 替换整个通道的数据（自动截断或填充）
                self.data_struct.audio_data[i, :] = 0  # 可选：先清空原数据
                if len(new_data) >= self.max_points:
                    # 如果新数据长度超过 max_points，只保留最新部分
                    self.data_struct.audio_data[i, :] = new_data[-self.max_points :]
                else:
                    # 否则将新数据放在末尾
                    self.data_struct.audio_data[i, -len(new_data) :] = new_data

    def init_new_canvas(self):
        print("init new canvas")
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
