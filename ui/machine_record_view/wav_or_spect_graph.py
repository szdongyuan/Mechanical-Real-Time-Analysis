import json
import os
import time

import numpy as np

from PyQt5.QtCore import Qt, QTimer
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
        self.next_page.setFixedWidth(150)
        self.prev_page.setFixedWidth(150)

        self.channels = 0
        self.chart_wav_graph_widgets:list[PlotWidget] = []
        self.chart_spect_graph_widgets:list[PlotWidget] = []
        self.label_wav_widgets:list[QLabel] = []
        self.label_spect_widgets:list[QLabel] = []
        self.hide_list:list[QWidget] = list()

        self.chart_graph = QWidget()

        # Y轴动态阈值相关变量
        self.current_y_range = {"lower": -0.02, "upper": 0.02}  # 当前Y轴范围
        self.max_value_history = []  # 记录历史最大值 [(timestamp, max_abs_value), ...]
        self.history_window = 1.0  # 历史窗口大小（秒）
        self.recovery_duration = 2.0  # 恢复到默认值的时间（秒）
        self.recovery_start_time = None  # 开始恢复的时间
        self.recovery_start_range = None  # 开始恢复时的Y轴范围
        self.is_recovering = False  # 是否正在恢复中
        
        # 定时器用于平滑恢复Y轴范围
        self.recovery_timer = QTimer()
        self.recovery_timer.timeout.connect(self._update_recovery)
        self.recovery_interval = 100  # 每100ms更新一次

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
        main_layout.setContentsMargins(0, 0, 0, 0)
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
            graph.setLabel('bottom', "时间", units='s')
            graph.setLabel('left', "电压", units='V')
            graph.getAxis('bottom').setStyle(tickFont=font)
            graph.getAxis('left').setStyle(tickFont=font)
            graph.getAxis('bottom').label.setFont(font)
            graph.getAxis('left').label.setFont(font)

        waveform_graph_left.setYRange(self.limit_config["lower"], self.limit_config["upper"])
        waveform_graph_right.setYRange(self.limit_config["lower"], self.limit_config["upper"])
        spect_graph_left = PlotWidget()
        spect_graph_right = PlotWidget()
        for graph in [spect_graph_left, spect_graph_right]:
            graph.setLabel('bottom', "时间", units='s')
            graph.setLabel('left', "频率", units='Hz')
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
        header_layout_right.addWidget(wav_label_right)
        header_layout_right.addWidget(self.prev_page)
        header_layout_right.addWidget(self.next_page)
        header_layout.addLayout(header_layout_left)
        header_layout.addLayout(header_layout_right)

        wav_layout = QHBoxLayout()
        wav_layout.addWidget(waveform_graph_left)
        wav_layout.addWidget(waveform_graph_right)

        spect_header_layout = QHBoxLayout()
        spect_header_layout.addWidget(spect_label_left)
        spect_header_layout.addWidget(spect_label_right)

        spect_layout = QHBoxLayout()
        spect_layout.addWidget(spect_graph_left)
        spect_layout.addWidget(spect_graph_right)

        layout.addLayout(header_layout)
        layout.addLayout(wav_layout)
        layout.addLayout(spect_header_layout)
        layout.addLayout(spect_layout)
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
        
        # 动态调整Y轴阈值
        self._update_y_range(audio_data, graph_widget)

    def _update_y_range(self, audio_data, graph_widget):
        """
        动态更新Y轴范围
        
        策略：
        1. 启动时采用 limit_config 的值
        2. 如果波形绝对值最大值超过阈值，立即调整阈值范围适应新波形
        3. 如果10秒内的最大值都小于 limit_config，阈值在5秒内逐渐调回 limit_config
        """
        current_time = time.time()
        
        # 计算当前波形的绝对值最大值
        if len(audio_data) > 0:
            current_max = float(np.max(np.abs(audio_data)))
        else:
            current_max = 0.0
        
        # 记录当前最大值到历史
        self.max_value_history.append((current_time, current_max))
        
        # 清理超过10秒的历史记录
        self.max_value_history = [
            (t, v) for t, v in self.max_value_history 
            if current_time - t <= self.history_window
        ]
        
        # 获取配置的默认阈值
        config_upper = self.limit_config.get("upper", 0.02) if self.limit_config else 0.02
        config_lower = self.limit_config.get("lower", -0.02) if self.limit_config else -0.02
        config_range = config_upper  # 假设上下对称
        
        # 获取当前Y轴范围的绝对值
        current_range = self.current_y_range["upper"]
        
        # 情况1：当前波形超过阈值，立即扩大范围
        if current_max > current_range:
            # 停止恢复过程
            self.is_recovering = False
            self.recovery_timer.stop()
            self.recovery_start_time = None
            
            # 扩大范围（留10%余量）
            new_range = current_max * 1.1
            self.current_y_range["upper"] = new_range
            self.current_y_range["lower"] = -new_range
            
            # 更新所有波形图的Y轴范围
            self._apply_y_range_to_all_graphs()
        else:
            # 检查10秒内的最大值是否都小于配置值
            max_in_history = max((v for t, v in self.max_value_history), default=0.0)
            
            # 情况2：当前范围大于配置值，且10秒内最大值都小于配置值
            if current_range > config_range and max_in_history < config_range:
                # 开始恢复过程（如果还没开始）
                if not self.is_recovering:
                    self.is_recovering = True
                    self.recovery_start_time = current_time
                    self.recovery_start_range = current_range
                    self.recovery_timer.start(self.recovery_interval)
            else:
                # 如果10秒内有超过配置值的数据，停止恢复
                if max_in_history >= config_range and self.is_recovering:
                    self.is_recovering = False
                    self.recovery_timer.stop()
                    self.recovery_start_time = None
        
        # 应用当前Y轴范围到图表
        graph_widget.setYRange(self.current_y_range["lower"], self.current_y_range["upper"])

    def _update_recovery(self):
        """
        定时器回调：平滑恢复Y轴范围到配置值
        """
        if not self.is_recovering or self.recovery_start_time is None:
            self.recovery_timer.stop()
            return
        
        current_time = time.time()
        elapsed = current_time - self.recovery_start_time
        
        # 获取配置的默认阈值
        config_upper = self.limit_config.get("upper", 0.02) if self.limit_config else 0.02
        
        if elapsed >= self.recovery_duration:
            # 恢复完成
            self.current_y_range["upper"] = config_upper
            self.current_y_range["lower"] = -config_upper
            self.is_recovering = False
            self.recovery_timer.stop()
            self.recovery_start_time = None
        else:
            # 线性插值恢复
            progress = elapsed / self.recovery_duration
            start_range = self.recovery_start_range
            new_range = start_range + (config_upper - start_range) * progress
            self.current_y_range["upper"] = new_range
            self.current_y_range["lower"] = -new_range
        
        # 更新所有波形图的Y轴范围
        self._apply_y_range_to_all_graphs()

    def _apply_y_range_to_all_graphs(self):
        """
        将当前Y轴范围应用到所有波形图
        """
        for graph_widget in self.chart_wav_graph_widgets:
            graph_widget.setYRange(self.current_y_range["lower"], self.current_y_range["upper"])

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
                # 初始化当前Y轴范围为配置值
                self.current_y_range = {
                    "lower": limit_config.get("lower", -0.02),
                    "upper": limit_config.get("upper", 0.02)
                }


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = WavOrSpectGraph()
    window.create_chart_graph(4)
    window.show()
    sys.exit(app.exec())

