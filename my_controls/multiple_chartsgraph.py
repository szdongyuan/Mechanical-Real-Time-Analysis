import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox


class MultipleChartsGraph(QWidget):
    def __init__(self):
        super().__init__()

        self.curve_line_list = list()
        self.spec_im_list = list()

        self.title_label = QLabel()
        self.sv_label = QLabel()
        self.current_channel_combobox = QComboBox()
        self.waveform_plot = None
        self.stft_plot = None

        self.chart_layout = QVBoxLayout()
        self.setLayout(self.chart_layout)
        self.create_chart()

    def create_chart(self, ):
        self.del_layout(self.layout())
        self.waveform_plot = FigureCanvas(plt.figure(constrained_layout=True))
        self.stft_plot = FigureCanvas(plt.figure(constrained_layout=True))

        hertical_line = QFrame()
        hertical_line.setFrameShape(QFrame.HLine)
        current_channel_layout = self.set_current_channel_layout()
        
        self.chart_layout.addLayout(current_channel_layout)
        self.chart_layout.addWidget(self.waveform_plot, 1)
        self.chart_layout.addWidget(hertical_line)
        self.chart_layout.addWidget(self.sv_label, alignment=Qt.AlignLeft)
        self.chart_layout.addWidget(self.stft_plot, 2)
        self.chart_layout.setSpacing(10)

    def set_wavefrom_title(self, number):
        self.title_label.setText(" INPUT %s" % (number + 1))
        self.sv_label.setText(" SV Intensity Graph %s" % (number + 1))

    def set_current_channel_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(QLabel("当前通道："))
        layout.addWidget(self.current_channel_combobox)
        
        return layout

    def set_current_channel_combobox(self, channels:list):
        self.current_channel_combobox.clear()
        for channel in channels:
            self.current_channel_combobox.addItem(str(channel + 1))

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

    def draw_waveform(self, audio_data, x_duration):
        fig = self.waveform_plot.figure
        ax = fig.gca()
        ax.clear()
        ax.margins(0)
        line_i_curve = ax.plot(x_duration, audio_data)[0]
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Amplitude", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)
        if len(self.curve_line_list) == 0:
            self.curve_line_list.append(line_i_curve)
        else:
            self.curve_line_list[0] = line_i_curve
        self.waveform_plot.draw()

    def draw_stftfrom(self, freqs, time, sxx):
        shifted_time = time - time[-1]
        fig = self.stft_plot.figure
        ax = fig.gca()
        ax.clear()
        im = ax.pcolormesh(shifted_time, freqs, sxx, shading="auto")
        ax.set_xlabel("Time (s)", fontsize=8)
        ax.set_ylabel("Frequency (Hz)", fontsize=8)
        ax.tick_params(axis="both", labelsize=8)
        if len(self.spec_im_list) == 0:
            self.spec_im_list.append(im)
        else:
            self.spec_im_list[0] = im
        self.stft_plot.draw()

    def update_waveform(self, audio_data):
        if len(self.curve_line_list) == 0:
            return

        y_max = float(np.max(audio_data))
        y_min = float(np.min(audio_data))
        self.curve_line_list[0].set_ydata(audio_data)
        ax = self.waveform_plot.figure.gca()
        # 对称设置上下限，避免画面跳动过大；全零时给一个默认范围
        v = max(abs(y_min), abs(y_max))
        if v == 0:
            v = 1.0
        ax.set_ylim(-v, v)
        self.waveform_plot.draw()

    def update_stftfrom(self, freqs, time, np_sxx_log):
        shifted_time = time - time[-1]
        fig = self.stft_plot.figure
        ax = fig.gca()
        if len(self.spec_im_list) > 0 and self.spec_im_list[0] is not None:
            self.spec_im_list[0].remove()
        im = ax.pcolormesh(shifted_time, freqs, np_sxx_log, shading="auto")
        if len(self.spec_im_list) == 0:
            self.spec_im_list.append(im)
        else:
            self.spec_im_list[0] = im
        self.stft_plot.draw()

    def clear(self):
        if self.waveform_plot is not None:
            self.waveform_plot.figure.clear()
            self.waveform_plot.draw()
        if self.stft_plot is not None:
            self.stft_plot.figure.clear()
            self.stft_plot.draw()
        self.curve_line_list = list()
        self.spec_im_list = list()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MultipleChartsGraph(channels=4)
    window.create_chart(channels=2)
    window.show()
    sys.exit(app.exec_())
