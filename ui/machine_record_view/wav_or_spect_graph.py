import json
import os

import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPalette, QColor, QFont
from PyQt5.QtWidgets import QLayout, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame, QButtonGroup, QPushButton
from pyqtgraph import PlotWidget, ImageItem, ColorMap
import pyqtgraph as pg

from consts.running_consts import DEFAULT_DIR

class WavOrSpectGraph(QWidget):
    def __init__(self):
        super().__init__()

        self.limit_config = None
        self.prev_page = QPushButton("上一页")
        self.next_page = QPushButton("下一页")

        self.channels = 0
        self.chart_wav_graph_widgets:list[PlotWidget] = []
        self.chart_spect_graph_widgets:list[PlotWidget] = []
        self.label_wav_widgets:list[QLabel] = []
        self.label_spect_widgets:list[QLabel] = []
        self.hide_list:list[QWidget] = list()

        self.chart_graph = QWidget()

        self.init_ui()
        self.init_limit_config()
        self.create_chart_graph()

    def init_ui(self):

        # 设置窗口与图表容器背景色（不使用样式表）
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        chart_palette = self.chart_graph.palette()
        chart_palette.setColor(QPalette.Window, QColor(25, 25, 25))
        self.chart_graph.setAutoFillBackground(True)
        self.chart_graph.setPalette(chart_palette)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.chart_graph)
        main_layout.setContentsMargins(0, 10, 0, 10)
        self.setLayout(main_layout)

        self.setStyleSheet("""
            QPushButton {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                font-size: 14px;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgb(24, 144, 255);
            }
            QLabel {
                color: rgb(255, 255, 255);
                font-size: 14px;
            }
        """)

    def create_header_layout(self):
        header_layout = QHBoxLayout()
        header_layout.addSpacing(10)
        header_layout.addWidget(self.now_wav_btn)
        header_layout.addWidget(self.now_spect_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.green_light)
        header_layout.addWidget(self.red_light)
        header_layout.addSpacing(10)
        return header_layout

    def create_chart_graph(self):
        layout = QVBoxLayout()
        wav_label_left = QLabel()
        wav_label_right = QLabel()
        spect_label_left = QLabel()
        spect_label_right = QLabel()
        waveform_graph_left = PlotWidget()
        waveform_graph_right = PlotWidget()

        font = QFont()
        font.setPixelSize(12)
        
        for graph in [waveform_graph_left, waveform_graph_right]:
            graph.getAxis('bottom').setStyle(tickFont=font)
            graph.getAxis('left').setStyle(tickFont=font)
            graph.getAxis('bottom').label.setFont(font)
            graph.getAxis('left').label.setFont(font)

        waveform_graph_left.setYRange(self.limit_config["lower"], self.limit_config["upper"])
        waveform_graph_right.setYRange(self.limit_config["lower"], self.limit_config["upper"])
        spect_graph_left = PlotWidget()
        spect_graph_right = PlotWidget()
        for graph in [spect_graph_left, spect_graph_right]:
            graph.getAxis('bottom').setStyle(tickFont=font)
            graph.getAxis('left').setStyle(tickFont=font)
            graph.getAxis('bottom').label.setFont(font)
            graph.getAxis('left').label.setFont(font)
        self.chart_wav_graph_widgets.append(waveform_graph_left)
        self.chart_wav_graph_widgets.append(waveform_graph_right)
        self.chart_spect_graph_widgets.append(spect_graph_left)
        self.chart_spect_graph_widgets.append(spect_graph_right)
        self.label_wav_widgets.append(wav_label_left)
        self.label_wav_widgets.append(wav_label_right)
        self.label_spect_widgets.append(spect_label_left)
        self.label_spect_widgets.append(spect_label_right)
        self.hide_list.append(waveform_graph_right)
        self.hide_list.append(spect_graph_right)
        self.hide_list.append(wav_label_right)
        self.hide_list.append(spect_label_right)

        header_layout = QHBoxLayout()
        header_layout_left = QHBoxLayout()
        header_layout_right = QHBoxLayout()
        header_layout_left.addWidget(wav_label_left)
        # header_layout_left.addStretch()
        header_layout_right.addWidget(wav_label_right)
        # header_layout_right.addStretch()
        header_layout_right.addWidget(self.prev_page)
        header_layout_right.addWidget(self.next_page)
        header_layout.addLayout(header_layout_left)
        header_layout.addLayout(header_layout_right)

        wav_layout = QHBoxLayout()
        wav_layout.addWidget(waveform_graph_left)
        wav_layout.addWidget(waveform_graph_right)

        spect_header_layout = QHBoxLayout()
        spect_header_layout.addWidget(spect_label_left)
        # spect_header_layout.addStretch()
        spect_header_layout.addWidget(spect_label_right)

        spect_layout = QHBoxLayout()
        spect_layout.addWidget(spect_graph_left)
        spect_layout.addWidget(spect_graph_right)

        layout.addLayout(header_layout)
        layout.addLayout(wav_layout, 1)
        layout.addLayout(spect_header_layout)
        layout.addLayout(spect_layout, 2)
        self.chart_graph.setLayout(layout)

    def hide_right_part_widget(self, is_true: bool):
        if is_true:
            for widget in self.hide_list:
                widget.hide()
        else:
            for widget in self.hide_list:
                widget.show()

    def plot_waveform(self, audio_data: list, position: str, sampling_rate: int, downsample_factor: int = 10):
        """
        绘制波形图
        
        参数:
            audio_data: 包含音频信号的列表
            position: "left" 或 "right"，控制使用哪个图表
            sampling_rate: 采样率
            downsample_factor: 降采样因子，默认10（每10个点取1个）
        """
        if position == "left":
            graph_widget = self.chart_wav_graph_widgets[0]
        elif position == "right":
            graph_widget = self.chart_wav_graph_widgets[1]
        else:
            print(f"无效的位置参数: {position}，应该是 'left' 或 'right'")
            return
        
        # 对数据进行降采样以提高性能
        if len(audio_data) > 5000 and downsample_factor > 1:
            # 使用最大-最小降采样保留波形特征
            audio_data_downsampled = audio_data[::downsample_factor]
            x = np.linspace(-len(audio_data) / sampling_rate, 0, num=len(audio_data_downsampled))
        else:
            audio_data_downsampled = audio_data
            x = np.linspace(-len(audio_data) / sampling_rate, 0, num=len(audio_data))
        
        graph_widget.clear()
        graph_widget.plot(x, audio_data_downsampled, pen='c')
        
        # 设置纵坐标范围
        # graph_widget.setYRange(-1.0, 1.0)

    def plot_spectrogram(self, spect_data: tuple, position: str):
        """
        绘制时频图（频谱图）
        
        参数:
            spect_data: 包含 (freqs, times_arr, np_sxx_log) 的元组
            position: "left" 或 "right"，控制使用哪个图表
        """
        if position == "left":
            graph_widget = self.chart_spect_graph_widgets[0]
        elif position == "right":
            graph_widget = self.chart_spect_graph_widgets[1]
        else:
            print(f"无效的位置参数: {position}，应该是 'left' 或 'right'")
            return
        
        # 解包频谱图数据
        freqs, times_arr, np_sxx_log = spect_data
        
        # 清除之前的图表
        graph_widget.clear()
        
        # 创建 ImageItem 用于显示频谱图
        img_item = ImageItem()
        
        # 获取 inferno colormap 并应用
        inferno_colormap = pg.colormap.get('inferno')
        img_item.setColorMap(inferno_colormap)
        
        # 设置图像数据
        img_item.setImage(np_sxx_log)
        # print(img_item.getLevels())
        
        # 设置 colormap 的上下限（从配置文件读取）
        if self.limit_config:
            spec_lower = self.limit_config.get("spec_lower", 0.0)
            spec_upper = self.limit_config.get("spec_upper", 1.0)
            img_item.setLevels([spec_lower, spec_upper])
        else:
            # 默认范围 0 到 1
            img_item.setLevels([0.1, 2])
        
        # 设置图像的位置和缩放，使其与坐标轴对应
        # 频率范围：0 到 freqs[-1]
        # 时间范围：times_arr[0] 到 times_arr[-1]
        img_item.setRect(times_arr[0], 0, times_arr[-1] - times_arr[0], freqs[-1])
        
        # 添加图像到图表
        graph_widget.addItem(img_item)
        
        # 隐藏右键菜单中的 colorbar 按钮
        # graph_widget.hideButtons()
        
        # 设置坐标轴标签
        graph_widget.setLabel('left', '频率', units='Hz')
        graph_widget.setLabel('bottom', '时间', units='s')

    def set_waveform_title(self, channel_index: list):
        for i in range(len(channel_index)):
            self.label_wav_widgets[i].setText(f"INPUT {channel_index[i]}")
            self.label_spect_widgets[i].setText(f"SV Intensity Graph {channel_index[i]}")

    def set_light_color(self, light, color):
        light.setFixedSize(40, 40)
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

    def init_limit_config(self):
        limit_config_path = DEFAULT_DIR + "ui/ui_config/limit.json"
        if os.path.exists(limit_config_path):
            with open(limit_config_path, "r", encoding="utf-8") as f:
                limit_config = json.load(f)
                self.limit_config = limit_config


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = WavOrSpectGraph()
    window.create_chart_graph(4)
    window.show()
    sys.exit(app.exec())

