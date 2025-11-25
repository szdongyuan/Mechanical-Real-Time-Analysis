from PyQt5.QtCore import Qt, QSize, QRect, QRectF
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QColor
from PyQt5.QtWidgets import QPushButton, QLabel, QWidget, QApplication, QVBoxLayout


class CustomInfoButton(QPushButton):
    """
    可定制信息按钮（仅一行文本 + 底部彩色横线）
    - 文本由左右两部分组成：左侧白色，右侧与底部横线同色
    - 底部横线颜色支持：red/yellow/green/white
    使用示例：
        btn = CustomInfoButton("158.2", " dB", color="green")
        btn.setMinimumSize(160, 90)
    """

    COLOR_MAP = {
        "red": "#ff4d4f",
        "yellow": "#faad14",
        "green": "#52c41a",
        "white": "#ffffff",
    }

    def __init__(self, left_text: str = "", right_text: str = "", color: str = "green", parent=None):
        super().__init__(parent)
        self._left_text = left_text or ""
        self._right_text = right_text or ""
        self._color_name = "green" if color not in self.COLOR_MAP else color

        # 内部文本标签（使用富文本分色）
        self._label = QLabel(self)
        self._label.setTextFormat(Qt.RichText)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._label.setStyleSheet("background: transparent;")
        font = QFont()
        font.setPixelSize(15)
        # font.setBold(True)
        self._label.setFont(font)

        # 底部横线（通过 paintEvent 绘制）
        self._bar_height = 4
        self._bar_color = self.COLOR_MAP[self._color_name]

        self._label.setStyleSheet("background: transparent;")

        # 基础样式：深灰背景、圆角轻微、无边框
        self.setStyleSheet(
            """
            QPushButton {
                background-color: rgb(55,55,55);
                color: rgb(255,255,255);
                border: none;
                border-radius: 6px;
                text-align: left;
                padding-left: 12px;
                padding-right: 12px;
            }
            QPushButton:hover { background-color: rgb(65,65,65); }
            QPushButton:pressed { background-color: rgb(48,48,48); }
            """
        )

        self._update_label_html()

    def sizeHint(self) -> QSize:
        # 根据字体与最少内边距给出较合理默认尺寸
        fm = QFontMetrics(self._label.font())
        text_w = fm.horizontalAdvance(self._left_text + self._right_text) + 24
        text_h = fm.height() + 28
        return QSize(max(160, text_w), max(72, text_h + self._bar_height))

    # API: 设置底部横线与右侧文字的颜色
    def set_bar_color(self, color: str) -> None:
        if color not in self.COLOR_MAP:
            return
        self._color_name = color
        self._bar_color = self.COLOR_MAP[self._color_name]
        self._update_label_html()
        self.update()

    # API: 设置左右文本
    def set_text(self, left: str, right: str) -> None:
        self._left_text = left or ""
        self._right_text = right or ""
        self._update_label_html()
        self.update()

    # 内部：刷新标签富文本（左白右随底部条色）
    def _update_label_html(self) -> None:
        right_color = self._bar_color
        html = (
            f'<span style="color:#ffffff;">{self._left_text}</span>'
            f'<span style="color:{right_color};">{self._right_text}</span>'
        )
        self._label.setText(html)

    # 布局：在 resize 时摆放文本与底部条
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        # 文本区域留出一定内边距
        self._label.setGeometry(QRect(12, 8, max(0, w - 24), max(0, h - self._bar_height - 16)))
    
    # 绘制：使用圆角裁剪后绘制底部横线，避免破坏圆角
    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        # 与样式表中的 border-radius 一致
        radius = 6
        clip_path = QPainterPath()
        # 使用 QRectF 以匹配重载，并轻微收缩避免锯齿
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        clip_path.addRoundedRect(r, radius, radius)
        painter.setClipPath(clip_path)
        # 画底部横线
        w = self.width()
        h = self.height()
        painter.fillRect(0, max(0, h - self._bar_height), w, self._bar_height, QColor(self._bar_color))

 
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    demo = QWidget()
    demo.setWindowTitle("CustomInfoButton Demo")
    layout = QVBoxLayout(demo)
    # 示例：左白右彩，底部条为绿色
    btn = CustomInfoButton("158.2", " dB", color="green")
    btn.setMinimumSize(180, 90)
    layout.addWidget(btn)
    demo.resize(260, 140)
    demo.show()
    sys.exit(app.exec_())

