from PyQt5.QtCore import QTimer, QDateTime, Qt
from PyQt5.QtWidgets import QLabel

class MyDateTimeLabel(QLabel, QTimer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("")
        self.setAlignment(Qt.AlignCenter)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 每秒更新一次

    def update_time(self):
        current_time = QDateTime.currentDateTime()
        formatted_time = current_time.toString("yyyy-MM-dd HH:mm:ss")
        self.setText("时间：%s" % formatted_time)
    