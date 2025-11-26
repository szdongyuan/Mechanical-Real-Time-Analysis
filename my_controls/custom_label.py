from PyQt5.QtCore import Qt, QSize, QRect, QRectF
from PyQt5.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QColor
from PyQt5.QtWidgets import QLabel, QWidget, QApplication, QVBoxLayout


class CustomInfoLabel(QLabel):
    """
    可定制信息标签（两行文本 + 底部彩色横线）
    - 第一行：白色字体，向左对齐，字体大小 15px
    - 第二行：颜色可定制，居中对齐，字体大小 30px
    - 底部横线颜色支持：red/yellow/green/white
    使用示例：
        label = CustomInfoLabel("标题文本", "158.2 dB", color="green")
        label.setMinimumSize(160, 90)
    """

    COLOR_MAP = {
        "red": "#ff4d4f",
        "yellow": "#faad14",
        "green": "#52c41a",
        "white": "#ffffff",
    }

    def __init__(self, first_line: str = "", second_line: str = "", color: str = "green", parent=None):
        super().__init__(parent)
        self._first_line = first_line or ""
        self._second_line = second_line or ""
        self._color_name = "green" if color not in self.COLOR_MAP else color

        # 第一行标签（白色，左对齐）
        self._first_label = QLabel(self)
        self._first_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._first_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._first_label.setStyleSheet("background: transparent; color: #ffffff;")
        font1 = QFont()
        font1.setPixelSize(14)
        self._first_label.setFont(font1)
        
        # 第二行标签（颜色可定制，居中对齐）
        self._second_label = QLabel(self)
        self._second_label.setAlignment(Qt.AlignCenter)
        self._second_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._second_label.setStyleSheet("background: transparent;")
        font2 = QFont()
        font2.setPixelSize(20)
        self._second_label.setFont(font2)

        # 底部横线（通过 paintEvent 绘制）
        self._bar_height = 4
        self._bar_color = self.COLOR_MAP[self._color_name]

        # 基础样式：深灰背景、圆角、无边框
        self.setStyleSheet(
            """
            QLabel {
                background-color: rgb(55,55,55);
                color: rgb(255,255,255);
                border: none;
                border-radius: 6px;
            }
            """
        )

        self._update_labels()

    def sizeHint(self) -> QSize:
        # 根据字体与最少内边距给出较合理默认尺寸
        fm1 = QFontMetrics(self._first_label.font())
        fm2 = QFontMetrics(self._second_label.font())
        text_w1 = fm1.horizontalAdvance(self._first_line) + 24
        text_w2 = fm2.horizontalAdvance(self._second_line) + 24
        text_h = fm1.height() + fm2.height() + 24
        return QSize(max(160, text_w1, text_w2), max(90, text_h + self._bar_height))

    # API: 设置底部横线与第二行文字的颜色
    def set_bar_color(self, color: str) -> None:
        if color not in self.COLOR_MAP:
            return
        self._color_name = color
        self._bar_color = self.COLOR_MAP[self._color_name]
        self._update_labels()
        self.update()

    # API: 设置两行文本
    def set_text(self, first_line: str, second_line: str) -> None:
        self._first_line = first_line or ""
        self._second_line = second_line or ""
        self._update_labels()
        self.update()
    
    # API: 单独设置第一行文本
    def set_first_line(self, first_line: str) -> None:
        self._first_line = first_line or ""
        self._update_labels()
        self.update()
    
    # API: 单独设置第二行文本
    def set_second_line(self, second_line: str) -> None:
        self._second_line = second_line or ""
        self._update_labels()
        self.update()

    # 内部：刷新两个标签的文本和颜色
    def _update_labels(self) -> None:
        # 第一行：白色
        self._first_label.setText(self._first_line)
        # 第二行：与底部横线同色
        self._second_label.setText(self._second_line)
        self._second_label.setStyleSheet(f"background: transparent; color: {self._bar_color};")

    # 布局：在 resize 时摆放两行文本与底部条
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        # 第一行：顶部，左对齐，留出上下左右内边距
        first_h = 20  # 第一行高度
        self._first_label.setGeometry(QRect(12, 8, max(0, w - 24), first_h))
        # 第二行：居中，占据剩余空间
        second_top = 8 + first_h + 4  # 第一行下方留 4px 间距
        second_h = max(0, h - second_top - self._bar_height - 8)
        self._second_label.setGeometry(QRect(12, second_top, max(0, w - 24), second_h))
    
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
    demo.setWindowTitle("CustomInfoLabel Demo")
    demo.setStyleSheet("background-color: rgb(45, 45, 45);")
    layout = QVBoxLayout(demo)
    layout.setSpacing(10)
    
    # 示例：第一行白色左对齐，第二行绿色居中，底部条为绿色
    label1 = CustomInfoLabel("声压级", "158.2 dB", color="green")
    label1.setMinimumSize(180, 90)
    layout.addWidget(label1)
    
    # 示例：红色
    label2 = CustomInfoLabel("温度", "85.6 ℃", color="red")
    label2.setMinimumSize(180, 90)
    layout.addWidget(label2)
    
    # 示例：黄色
    label3 = CustomInfoLabel("转速", "3600 RPM", color="yellow")
    label3.setMinimumSize(180, 90)
    layout.addWidget(label3)
    
    # 演示：动态更新第二行文本
    import threading
    def update_value():
        import time
        time.sleep(2)
        label1.set_second_line("165.8 dB")  # 只更新第二行
    threading.Thread(target=update_value, daemon=True).start()
    
    demo.resize(220, 320)
    demo.show()
    sys.exit(app.exec_())

