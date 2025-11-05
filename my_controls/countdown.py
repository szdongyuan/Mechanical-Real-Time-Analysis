from PyQt5.QtCore import QTimer, pyqtSignal, QThread


class Countdown(QThread):

    signal_for_update = pyqtSignal(int)

    def __init__(self, count):
        super().__init__()
        self.count = count
        self.countdown_time = 0  # s

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)

    def update_time(self):
        if self.countdown_time < self.count:
            self.countdown_time += 1
        else:
            self.countdown_time = 0
            self.signal_for_update.emit(self.countdown_time)

    def count_stop(self):
        print("count_stop")
        self.timer.stop()
        self.signal_for_update.emit(self.countdown_time)

    def count_start(self):
        print("count_start")
        self.countdown_time = 0
        self.timer.start(1000)
