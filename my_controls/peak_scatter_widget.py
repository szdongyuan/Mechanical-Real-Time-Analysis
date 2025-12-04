import math
import random
from collections import deque
from typing import Deque, Dict, List, Optional, Union

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPixmap, QFont
from PyQt5.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget, QGraphicsEllipseItem

import pyqtgraph as pg


class PeakScatterWidget(QWidget):
    """
    可视化峰值检测结果的散点图。
    - 两通道使用不同形状；
    - OK 点保持在中心绿色安全带内；
    - NG 点显示在安全带外；
    - 最近一批结果尺寸更大用于突出。
    """

    _SYMBOLS = ["o", "x", "t", "+", "star", "d"]

    def __init__(
        self,
        max_points: int = 100,
        ok_radius: float = 0.6,
        max_radius: float = 1.4,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.max_points = max_points
        self._history: Deque[Dict] = deque(maxlen=max_points)
        self._channel_names: List[str] = []
        self._channel_map: Dict[str, int] = {}
        self._default_threshold: float = 3.5
        self._index_counter = 0
        self._batch_counter = 0
        self._latest_batch_id = -1
        self._ok_radius = float(ok_radius)
        self._max_radius = float(max_radius)

        self._plot = pg.PlotWidget(background="#1b1b1b")
        self._plot.showGrid(x=False, y=False)  # 禁用笛卡尔网格
        self._plot.hideAxis("bottom")
        self._plot.hideAxis("left")
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.setMenuEnabled(False)
        self._plot.setAspectLocked(True, ratio=1)
        self._plot.setRange(xRange=(-1.5, 1.5), yRange=(-1.5, 1.5), padding=0.02)
        
        # 绘制极坐标网格（同心圆和放射线）
        self._polar_grid_items = []
        self._legend_item = None
        self._draw_polar_grid()
        self._create_legend()
        
        self._scatter = pg.ScatterPlotItem()
        self._plot.addItem(self._scatter)
        
        # OK 安全区（中心绿色圆）
        self._ok_zone = QGraphicsEllipseItem()
        self._update_ok_zone()
        self._ok_zone.setBrush(pg.mkBrush(0, 180, 120, 35))
        self._ok_zone.setPen(pg.mkPen(pg.mkColor(120, 220, 180), width=2, style=Qt.SolidLine))
        self._plot.addItem(self._ok_zone)

        # 颜色映射：均衡分布，OK=绿色，NG从黄色开始
        # OK 点 severity=0 显示绿色，NG 点 severity>=0.25 从黄色开始
        self._severity_cmap = pg.ColorMap(
            np.array([0.0, 0.25, 0.5, 0.75, 1.0]),
            np.array(
                [
                    [30, 150, 85, 255],     # 绿色 - OK 区域 (severity=0)
                    [255, 220, 80, 255],    # 黄色 - 刚超出阈值
                    [255, 160, 50, 255],    # 橙黄色 - 轻度异常
                    [255, 100, 50, 255],    # 橙红色 - 中度异常
                    [210, 30, 60, 255],     # 红色 - 严重异常
                ]
            ),
        )
        self._colorbar_label = QLabel()
        self._colorbar_label.setFixedWidth(28)  # 与 12px 字体的"健康/异常"宽度匹配
        self._colorbar_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._colorbar_label.setScaledContents(True)  # 让 pixmap 自适应 label 大小
        self._colorbar_label.setToolTip("颜色越接近红色表示评分越差/越异常")
        # 上方标签：异常（红色端）
        self._colorbar_top_caption = QLabel("异常")
        self._colorbar_top_caption.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        self._colorbar_top_caption.setStyleSheet("color: rgb(210,30,60); font-size: 12px; font-weight: bold;")
        # 下方标签：健康（绿色端）
        self._colorbar_bottom_caption = QLabel("健康")
        self._colorbar_bottom_caption.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self._colorbar_bottom_caption.setStyleSheet("color: rgb(30,150,85); font-size: 12px; font-weight: bold;")
        self._refresh_colorbar_pixmap()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot, 1)
        bar_layout = QVBoxLayout()
        bar_layout.setContentsMargins(4, 8, 4, 8)
        bar_layout.setSpacing(2)
        bar_layout.addWidget(self._colorbar_top_caption, 0, Qt.AlignHCenter)
        bar_layout.addWidget(self._colorbar_label, 1, Qt.AlignHCenter)
        bar_layout.addWidget(self._colorbar_bottom_caption, 0, Qt.AlignHCenter)
        # bar_layout.addStretch(1)
        layout.addLayout(bar_layout)
        self.set_plot_font_size()

    # ------------------------------------------------------------------ #
    def _draw_polar_grid(self):
        """
        绘制极坐标网格：同心圆 + 放射线
        """
        # 清除旧的网格项
        for item in self._polar_grid_items:
            self._plot.removeItem(item)
        self._polar_grid_items.clear()
        
        # 更明显的网格颜色
        grid_pen = pg.mkPen(color=(140, 140, 140, 160), width=1)
        radial_pen = pg.mkPen(color=(120, 120, 120, 140), width=1)
        
        # 绘制同心圆（半径刻度）
        radii = [0.3, 0.6, 0.9, 1.2, 1.5]
        for r in radii:
            if r <= 0:
                continue
            circle = QGraphicsEllipseItem(-r, -r, r * 2, r * 2)
            circle.setPen(grid_pen)
            circle.setBrush(pg.mkBrush(None))
            self._plot.addItem(circle)
            self._polar_grid_items.append(circle)
        
        # 绘制放射线（角度刻度，每45度一条）
        num_radials = 8
        for i in range(num_radials):
            angle = i * (2 * math.pi / num_radials)
            x_end = self._max_radius * math.cos(angle)
            y_end = self._max_radius * math.sin(angle)
            line = pg.PlotDataItem(
                [0, x_end], [0, y_end],
                pen=radial_pen
            )
            self._plot.addItem(line)
            self._polar_grid_items.append(line)
        
        # 添加中心点标记
        center_marker = pg.ScatterPlotItem(
            [0], [0],
            symbol='o',
            size=8,
            brush=pg.mkBrush(30, 150, 85, 200),
            pen=pg.mkPen(120, 220, 180, width=1)
        )
        self._plot.addItem(center_marker)
        self._polar_grid_items.append(center_marker)
    
    def _create_legend(self):
        """创建图例"""
        # 移除旧图例
        if hasattr(self, '_legend_item') and self._legend_item is not None:
            self._plot.removeItem(self._legend_item)
        
        legend = pg.LegendItem(offset=(10, 10), labelTextColor='#cccccc')
        legend.setParentItem(self._plot.getPlotItem())
        
        # 系统一：圆形
        scatter1 = pg.ScatterPlotItem(
            [], [], symbol='o', size=10,
            brush=pg.mkBrush(100, 180, 120, 200),
            pen=pg.mkPen('#888888', width=1)
        )
        legend.addItem(scatter1, '系统一')
        
        # 系统二：十字
        scatter2 = pg.ScatterPlotItem(
            [], [], symbol='+', size=10,
            brush=pg.mkBrush(100, 160, 200, 200),
            pen=pg.mkPen('#888888', width=1)
        )
        legend.addItem(scatter2, '系统二')
        
        self._legend_item = legend
    
    def set_plot_font_size(self):
        """极坐标模式下坐标轴已隐藏，此方法保留兼容性"""
        pass
        
    def set_channels(self, channels: List[Union[str, int]]):
        """
        设置通道名称，用于固定符号映射。
        """
        unique = []
        for ch in channels:
            name = str(ch)
            if name not in unique:
                unique.append(name)
        self._channel_names = unique
        self._channel_map = {name: idx for idx, name in enumerate(unique)}

    def set_default_threshold(self, threshold: float):
        if threshold and threshold > 0:
            self._default_threshold = float(threshold)

    def reset(self):
        self._history.clear()
        self._index_counter = 0
        self._batch_counter = 0
        self._latest_batch_id = -1
        self._scatter.clear()
        limit = max(1.0, self._max_radius)
        self._plot.setRange(xRange=(-limit, limit), yRange=(-limit, limit), padding=0.02)

    def append_results(self, results: List[Dict]):
        """
        追加一批峰值检测结果。
        result dict 需要包含：
        - channel: 通道索引或名称
        - peak_value: 峰值 (max_zscore)
        - threshold: 阈值
        - status: "OK" / "NG"
        """
        if not results:
            return
        self._batch_counter += 1
        batch_id = self._batch_counter

        for item in results:
            raw_channel = item.get("channel")
            channel_idx = self._resolve_channel(raw_channel)
            ratio = self._compute_ratio(
                peak_value=item.get("peak_value"),
                threshold=item.get("threshold"),
            )
            status = "NG" if str(item.get("status", "OK")).upper() == "NG" else "OK"
            health_score = item.get("health_score")
            angle, radius, severity = self._sample_point(raw_channel, status, health_score, ratio)
            record = {
                "channel_idx": channel_idx,
                "channel_name": str(raw_channel or ""),
                "ratio": ratio,
                "status": status,
                "index": self._index_counter,
                "batch_id": batch_id,
                "label": str(item.get("channel", f"CH{channel_idx + 1}")),
                "angle": angle,
                "radius": radius,
                "health_score": health_score,
                "severity": severity,
            }
            self._history.append(record)
            self._index_counter += 1

        self._latest_batch_id = batch_id
        self._refresh_plot()

    # ------------------------------------------------------------------ #
    def _resolve_channel(self, channel: Union[str, int, None]) -> int:
        if isinstance(channel, int):
            idx = channel
            label = f"CH{idx + 1}"
            if label not in self._channel_map:
                self._channel_map[label] = idx
            if idx >= len(self._channel_names):
                if len(self._channel_names) <= idx:
                    self._channel_names.extend(
                        f"CH{i + 1}" for i in range(len(self._channel_names), idx + 1)
                    )
            return idx

        name = str(channel) if channel not in (None, "") else f"CH{len(self._channel_map) + 1}"
        if name not in self._channel_map:
            self._channel_map[name] = len(self._channel_map)
            self._channel_names.append(name)
        return self._channel_map[name]

    def _compute_ratio(self, peak_value: Optional[float], threshold: Optional[float]) -> float:
        pv = float(peak_value or 0.0)
        th = float(threshold or self._default_threshold or 1.0)
        if th <= 0:
            th = 1.0
        ratio = pv / th
        return max(ratio, 0.0)

    def _update_ok_zone(self):
        radius = max(0.1, min(self._ok_radius, self._max_radius))
        self._ok_zone.setRect(-radius, -radius, radius * 2, radius * 2)

    def set_ok_radius(self, radius: float):
        self._ok_radius = max(0.1, min(float(radius), self._max_radius))
        self._update_ok_zone()

    def set_max_radius(self, radius: float):
        self._max_radius = max(self._ok_radius + 0.1, float(radius))
        self._update_ok_zone()
        self._draw_polar_grid()  # 重绘极坐标网格
        limit = max(self._max_radius, 1.0)
        self._plot.setRange(xRange=(-limit, limit), yRange=(-limit, limit), padding=0.02)

    @staticmethod
    def _normalize_score(score: Optional[float]) -> float:
        """
        将 health_score 归一化到 [0, 1] 范围。
        - 输入 0-100 或 0-1 的分数
        - 返回 0.0-1.0 的归一化值，None 默认返回 0.5
        """
        if score is None:
            return 0.5  # 默认中等分数
        try:
            value = float(score)
        except Exception:
            return 0.5
        # 如果值大于1，假设是0-100的范围
        if value > 1.0:
            value = value / 100.0
        return float(np.clip(value, 0.0, 1.0))

    def _sample_point(self, channel_name: str, status: str, health_score: Optional[float], ratio: float):
        """
        基于 health_score 计算极坐标位置和颜色严重度。
        - health_score 接近 100：靠近中心，绿色 (severity=0)
        - health_score 接近 0：远离中心，红色 (severity=1)
        - 角度采用随机数
        """
        # 归一化分数到 [0, 1]
        score_norm = self._normalize_score(health_score)
        
        # 随机角度 [0, 2π]
        angle = random.uniform(0, 2 * math.pi)
        
        # severity: 分数越高越接近0（绿色），分数越低越接近1（红色）
        severity = 1.0 - score_norm
        
        # 半径计算：severity 越大，半径越大（远离中心）
        # 使用非线性映射让分布更自然
        # 最小半径 0.05（中心附近），最大半径 _max_radius
        min_radius = 0.05
        radial_factor = severity ** 0.8  # 非线性映射
        radius = min_radius + radial_factor * (self._max_radius - min_radius)
        
        # 添加小随机扰动，避免点完全重叠
        noise = np.random.normal(0.0, self._max_radius * 0.03)
        radius = radius + abs(noise)
        radius = np.clip(radius, min_radius, self._max_radius)
        
        return angle, radius, severity

    def _refresh_plot(self):
        if not self._history:
            self._scatter.clear()
            return

        spots = []
        latest_batch = self._latest_batch_id
        base_size = 9
        highlight_size = 18
        max_index = self._history[-1]["index"]
        min_index = max(0, max_index - self.max_points + 1)
        used_radius = self._ok_radius
        for record in self._history:
            if record["index"] < min_index:
                continue
            radius = record.get("radius")
            angle = record.get("angle", 0.0)
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            used_radius = max(used_radius, math.hypot(x, y))
            channel_name = str(record.get("channel_name", "")).lower()
            symbol = "o" if channel_name.endswith("good_motor") else "+"
            severity = record.get("severity")
            color = self._severity_to_color(severity)
            size = highlight_size if record["batch_id"] == latest_batch else base_size
            spots.append(
                {
                    "pos": (x, y),
                    "data": record,
                    "symbol": symbol,
                    "size": size,
                    "brush": pg.mkBrush(color),
                    "pen": pg.mkPen(color.darker(120)),
                }
            )

        self._scatter.setData(spots)
        limit = max(self._max_radius, used_radius + 0.15)
        self._plot.setRange(xRange=(-limit, limit), yRange=(-limit, limit), padding=0.02)

    def _severity_to_color(self, severity: Optional[float]) -> QColor:
        if severity is None:
            severity = 0.0
        val = float(np.clip(severity, 0.0, 1.0))
        qcolor = self._severity_cmap.map(np.array([val]), mode="qcolor")[0]
        return qcolor

    def _refresh_colorbar_pixmap(self):
        width, height = 24, 160 # 与标签宽度协调
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        gradient = QLinearGradient(0, height, 0, 0)
        for pos in np.linspace(0.0, 1.0, 32):
            gradient.setColorAt(pos, self._severity_to_color(pos))
        painter = QPainter(pixmap)
        painter.fillRect(0, 0, width, height, gradient)
        painter.end()
        self._colorbar_label.setPixmap(pixmap)

