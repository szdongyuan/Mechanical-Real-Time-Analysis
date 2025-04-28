import sys
import time
import threading
import json

import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.signal import spectrogram
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLineEdit, QLabel, QHBoxLayout, QGroupBox

from base.audio_data_manager import save_audio_data
from base.record_audio import AudioDataManager
from consts import ui_style_const
from my_controls.my_datatime_label import MyDateTimeLabel
from my_controls.countdown import Countdown


class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 配置录音参数
        self.sampling_rate = 44100
        self.channels = None
        self.selected_channels = None
        self.blocksize = 1024
        self.total_display_time = 600  # s
        self.plot_time = 5
        self.analysis_interval = 1000  # ms
        self.ctx = sd._CallbackContext()

        self.nfft = 256
        self.fs = 44100

        # 初始化UI组件
        self.button = QPushButton()
        self.red_light = QLabel()
        self.green_light = QLabel()
        self.button.pressed.connect(self.on_button_pressed)
        self.button.released.connect(self.toggle_recording)

        # 创建画布和布局
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)

        # 初始化录音相关变量
        self.recording = False
        self.stream = None
        self.audio_data = []
        self.max_points = self.total_display_time * self.sampling_rate
        self.plot_points_section = self.plot_time * self.sampling_rate
        self.ax_list = []
        self.line_list = []

        self.auto_save_count = Countdown()
        self.auto_save_count.signal_for_update.connect(self.auto_save_data)

        self.t = None

        # # 创建定时器用于更新波形图
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.update_plot)

        self.audio_manager = AudioDataManager()
        self.audio_manager.signal_for_update.connect(self.update_data)

        self.init_ui()
        self.load_devices_data()

    def init_ui(self):
        self.setWindowTitle("实时波形显示")
        self.setGeometry(100, 100, 800, 600)

        date_device_layout = self.create_date_device_layout()
        chart_box = self.create_chart_layout()

        layout = QVBoxLayout()
        layout.addLayout(date_device_layout)
        layout.addWidget(chart_box)
        self.setLayout(layout)
        # container = QWidget()
        # container.setLayout(layout)
        # self.setCentralWidget(container)

    def create_chart_layout(self):
        chart_box = QGroupBox()
        layout = QHBoxLayout()
        record_layout = self.create_record_layout()
        layout.addLayout(record_layout)
        layout.addSpacing(20)
        layout.addWidget(self.canvas)
        chart_box.setLayout(layout)
        return chart_box
    
    def on_button_pressed(self):
        print(time.strftime("%Y%m%d_%H%M%S", time.localtime()), "\n", time.time())
        size = self.button.iconSize()
        self.button.setIconSize(QSize(size.width()-10, size.height()-10))

    def auto_save_data(self):
        save_audio_data(self.audio_data, self.sampling_rate, self.selected_channels)

    def create_record_layout(self):
        self.button.setFixedSize(150, 150)
        self.button.setIcon(QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/play.png"))
        self.button.setIconSize(QSize(110, 110))
        self.button.setStyleSheet(ui_style_const.toolbar_button_stytle)
        self.set_light_color(self.red_light, 'gray')
        self.set_light_color(self.green_light, 'gray')
        layout = QVBoxLayout()
        layout.addStretch()
        layout_btn = QHBoxLayout()
        layout_btn.addWidget(self.button)
        layout.addLayout(layout_btn)
        layout.addSpacing(30)
        layout_red_light = QHBoxLayout()
        layout_red_light.addWidget(self.red_light)
        layout.addLayout(layout_red_light)
        layout.addSpacing(30)
        layout_green_light = QHBoxLayout()
        layout_green_light.addWidget(self.green_light)
        layout.addLayout(layout_green_light)
        layout.addStretch()
        
        return layout 
    
    def create_date_device_layout(self):
        self.datetime_label = MyDateTimeLabel()
        device_label = QLabel("设备:")
        self.device_lineedit = QLineEdit()
        self.device_lineedit.setMinimumWidth(240)
        self.setStyleSheet("background-color: transparent; border: none; color: black;")
        self.device_lineedit.setEnabled(False)
        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(self.datetime_label, alignment=Qt.AlignLeft)
        layout.addStretch()
        layout.addWidget(device_label, alignment=Qt.AlignLeft)
        layout.addWidget(self.device_lineedit, alignment=Qt.AlignLeft)
        layout.addStretch()

        return layout

    def set_light_color(self, light, color):
        light.setFixedSize(110, 110)
        light.setStyleSheet(f"background-color: {color}; border-radius: 55px;")
        
    def toggle_recording(self):

        ts = threading.enumerate()
        for t in ts:
            print(1111111111111111111111,t.name, t.is_alive())
        if not self.recording:
            self.auto_save_count.count_start()
            # 开始录音
            self.button.setIcon(QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/pause.png"))
            self.button.setIconSize(self.button.size())
            self.recording = True
            self.set_light_color(self.green_light, 'green')

            # 初始化音频数据缓冲区和绘图
            self.audio_data = np.zeros((len(self.selected_channels), self.max_points), dtype=np.float32)
            self.figure.clear()
            self.ax_list = self.init_new_canvas()

            self.audio_manager.start_recording(self.ctx,
                                               self.selected_channels,
                                               self.audio_data,  
                                               self.sampling_rate,
                                               self.channels)
            # self.timer.start(self.analysis_interval)\

            if self.t is None:
                print("start")
                self.t =  threading.Thread(target=self.update_plot, args=(self.selected_channels,
                                                        self.audio_data,
                                                        self.ax_list,
                                                        self.canvas,)).start()
            else:
                print("restart")
                self.t._restart()

        else:
            # 停止录音
            self.button.setIcon(QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/play.png"))
            self.button.setIconSize(QSize(110, 110))
            self.set_light_color(self.green_light, 'gray')
            self.recording = False
            self.auto_save_count.count_stop()
            # AudioDataManager().stop_recording(self.ctx)
            # self.t._stop()
            # self.ctx.stop_stream()

            self.audio_manager.stop_recording()

            # self.timer.stop()

    def init_new_canvas(self):
        x = np.linspace(- self.plot_points_section / self.sampling_rate, 0,
                        num=self.plot_points_section)

        ax_list = []
        self.figure.clear()
        subplots = self.figure.subplots(nrows=2, ncols=len(self.selected_channels),
                                        height_ratios=[3, 2])
        subplots = np.array([subplots]).T if len(subplots.shape) == 1 else subplots

        for i in range(len(self.selected_channels)):
            ax_i_curve = subplots[0, i]
            plot_audio_section = self.audio_data[i, -self.plot_points_section:]

            line_i_curve = ax_i_curve.plot(x, plot_audio_section, linewidth=1)
            # 设置绘图范围
            ax_i_curve.set_xlim(-self.plot_time, 0)  # X轴表示时间，单位为秒
            ax_i_curve.set_ylim(-1, 1)

            ax_i_spec = subplots[1, i]
            _, _, sxx = spectrogram(plot_audio_section, nfft=self.nfft, fs=self.fs)
            im = ax_i_spec.imshow(sxx, vmin=0, vmax=1,
                                  origin="lower", aspect=2048//self.nfft)
            ax_i_spec.axis("off")

            ax_list.append({
                "curve_ax": ax_i_curve,
                "curve_line": line_i_curve[0],
                "spec_ax": ax_i_spec,
                "spec_im": im
            })

        return ax_list
    
    def update_data(self, data: np.ndarray):
        """槽函数：接收并处理音频数据"""
        self.audio_data = data  # 更新 UI 数据源

    def update_plot(self, selected_channels, audio_data, ax_list, canvas):
        print("start update plot")
        while True:
            if not self.recording:
                break
            # print(id(audio_data))
            t = time.time()
            for i in range(len(selected_channels)):
                y = audio_data[i,-self.plot_points_section:]
                # save_audio_data(y)

                # 更新绘图数据
                ax_info = ax_list[i]
                ax_info["curve_line"].set_ydata(y)

                _, _, sxx = spectrogram(y, nfft=self.nfft, fs=self.fs)
                sxx_log = np.log(sxx/1e-11)
                ax_info["spec_im"].set_data(sxx_log / np.max(sxx_log))

            # 强制重新绘制
            canvas.draw()
            # print(time.time() - t)
            QApplication.processEvents()
            time.sleep(1)  

    def load_devices_data(self):
        try:
            config_file = "D:/gqgit/new_project/ui/ui_config/device_data.json"
            with open(config_file, 'r') as f:
                default_config = json.load(f)
                self.device_lineedit.setText(default_config.get("device_name"))
                self.channels = int(default_config.get("device_chanels", 2))
                selected_channels = list()
                load_selected_channels = default_config.get("selected_channels", [0,1])
                for i in range(len(load_selected_channels)):
                    selected_channels.append(int(load_selected_channels[i]))
                self.selected_channels = selected_channels
                
        except Exception as e:
            print(f"Failed to load the default config file. {e}")

    def show(self):
        self.load_devices_data()
        super().show()

    def closeEvent(self, event):
        """关闭窗口时确保资源释放"""
        self.audio_manager.stop_recording()
        self.audio_manager.quit()
        self.audio_manager.wait()
        self.recording = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWidget()
    window.show()
    sys.exit(app.exec_())
