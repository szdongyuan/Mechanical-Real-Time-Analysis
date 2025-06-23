from PyQt5.QtCore import QTimer, pyqtSignal, QThread


class Countdown(QThread):

    signal_for_update = pyqtSignal(bool)

    def __init__(self, count):
        super().__init__()
        self.count = count
        self.countdown_time = None  # s

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)

    def update_time(self):
        if self.countdown_time > 0:
            # print("countdown_time", self.countdown_time)
            self.countdown_time -= 1
        else:
            self.countdown_time = self.count
            self.signal_for_update.emit(False)

    def count_stop(self):
        print("count_stop")
        self.timer.stop()

    def count_start(self):
        print("count_start")
        self.countdown_time = self.count
        self.timer.start(1000)
