import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton
from PyQt5.QtCore import QPropertyAnimation, QRect, QEasingCurve


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('按钮跳动效果')

        # 创建按钮
        self.button = QPushButton('跳动按钮', self)
        self.button.setGeometry(100, 100, 100, 30)

        # 设置按钮样式表
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px 20px;
                text-align: center;
                text-decoration: none;
                font-size: 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # 启动动画
        self.button.clicked.connect(self.animate_button)
        # self.animate_button()

        self.show()

    def animate_button(self):
        start_rect = self.button.geometry()
        end_rect = QRect(start_rect.x(), start_rect.y() - 5, start_rect.width(), start_rect.height())

        self.animation = QPropertyAnimation(self.button, b"geometry")
        self.animation.setDuration(100)
        self.animation.setEasingCurve(QEasingCurve.Linear)
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.setLoopCount(1)
        # self.animation.setLoopCount(-1)  # 无限循环
        self.animation.finished.connect(lambda: self.button.setGeometry(start_rect))
        self.animation.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
    