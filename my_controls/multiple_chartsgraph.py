import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel


class MultipleChartsGraph(QWidget):
    def __init__(self, channels=1):
        super().__init__()

        self.wavefrom_list = list()
        self.stftfrom_list = list()
        self.curve_line_list = list()
        self.spec_im_list = list()
        self.channel_light_list = list()

        self.chart_layout = QHBoxLayout()
        self.setLayout(self.chart_layout)
        # self.create_chart(channels)

    def create_chart(self, channels):
        self.wavefrom_list = list()
        self.stftfrom_list = list()
        self.del_layout(self.layout())
        for channel in range(channels):
            waveform_plot = FigureCanvas(plt.figure(constrained_layout=True))
            stft_plot = FigureCanvas(plt.figure(constrained_layout=True))
            input_title_layout = self.create_wavefrom_title(channel)
            sv_label = QLabel(" SV Intensity Graph %s" % (channel + 1))

            self.wavefrom_list.append(waveform_plot)
            self.stftfrom_list.append(stft_plot)

            hertical_line = QFrame()
            hertical_line.setFrameShape(QFrame.HLine)

            layout = QVBoxLayout()
            layout.addLayout(input_title_layout)
            layout.addWidget(self.wavefrom_list[channel], 1)
            layout.addWidget(hertical_line)
            layout.addWidget(sv_label, alignment=Qt.AlignLeft)
            layout.addWidget(self.stftfrom_list[channel], 2)
            layout.setSpacing(10)
            self.chart_layout.addLayout(layout)
            if channel != channels - 1:
                vertical_line = QFrame()
                vertical_line.setFrameShape(QFrame.VLine)
                self.chart_layout.addWidget(vertical_line)
        self.chart_layout.setSpacing(0)

    def create_wavefrom_title(self, channel):
        title = QLabel("INPUT %s" % (channel + 1))
        green_light = QLabel()
        red_light = QLabel()
        self.set_light_color(red_light, "gray")
        self.set_light_color(green_light, "gray")

        self.store_channel_light(red_light, green_light)

        title_layout = QHBoxLayout()
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(green_light)
        title_layout.addWidget(red_light)
        title_layout.setContentsMargins(10, 0, 10, 0)

        return title_layout

    def store_channel_light(self, red_light, green_light):
        channel_light_dict = {"red_light": red_light, "green_light": green_light}
        self.channel_light_list.append(channel_light_dict)

    def set_light_color(self, light, color):
        light.setFixedSize(20, 20)
        light.setStyleSheet(f"background-color: {color}; border-radius: 10px;")

    def del_layout(self, old_layout=None):
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                layout = item.layout()

                if widget is not None:
                    widget.setParent(None)
                elif layout is not None:
                    self.del_layout(layout)

    def draw_waveform(self, audio_data, x_duration, channel):
        ax = self.wavefrom_list[channel].figure.subplots()
        ax.margins(0)
        line_i_curve = ax.plot(x_duration, audio_data)
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Amplitude", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)
        self.curve_line_list.append(line_i_curve[0])

    def draw_stftfrom(self, freqs, time, sxx, channel):
        shifted_time = time - time[-1]
        ax = self.stftfrom_list[channel].figure.subplots()
        im = ax.pcolormesh(shifted_time, freqs, sxx, shading="auto")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Frequency (Hz)", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)
        self.spec_im_list.append(im)

    def update_waveform(self, audio_data, channel):
        self.curve_line_list[channel].set_ydata(audio_data)
        self.wavefrom_list[channel].draw()

    def update_stftfrom(self, freqs, time, np_sxx_log, channel):
        shifted_time = time - time[-1]
        ax = self.stftfrom_list[channel].figure.gca()
        self.spec_im_list[channel].remove()
        im = ax.pcolormesh(shifted_time, freqs, np_sxx_log, shading="auto")
        self.spec_im_list[channel] = im
        self.stftfrom_list[channel].draw()

    def clear(self):
        for channel in range(len(self.wavefrom_list)):
            self.wavefrom_list[channel].figure.clear()
            self.stftfrom_list[channel].figure.clear()
        self.curve_line_list = list()

    def set_warning_light(self, channel, flag):
        if flag:
            self.set_light_color(self.channel_light_list[channel]["red_light"], "red")
            self.set_light_color(self.channel_light_list[channel]["green_light"], "gray")
        else:
            self.set_light_color(self.channel_light_list[channel]["green_light"], "green")
            self.set_light_color(self.channel_light_list[channel]["red_light"], "gray")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MultipleChartsGraph(channels=4)
    window.create_chart(channels=2)
    window.show()
    sys.exit(app.exec_())
