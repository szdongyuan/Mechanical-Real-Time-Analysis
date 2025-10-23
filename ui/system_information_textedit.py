import sys
from dataclasses import dataclass
from datetime import datetime

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QComboBox, QTextEdit


@dataclass
class LogEntry:
    level: str
    timestamp: datetime
    message: str


class LogModel(QObject):
    logs_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._entries = []

    def add_log(self, level: str, message: str):
        entry = LogEntry(level=level, timestamp=datetime.now(), message=message)
        self._entries.append(entry)
        self.logs_changed.emit()

    @property
    def entries(self):
        return list(self._entries)


class LogController:
    def __init__(self, model: LogModel):
        self.model = model

    def info(self, message: str):
        self.model.add_log("INFO", message)

    def warning(self, message: str):
        self.model.add_log("WARNING", message)

    def error(self, message: str):
        self.model.add_log("ERROR", message)


class SysInformationTextEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = None
        self.text_edit = None
        self.error_level = None
        self.init_ui()
    
    def init_ui(self):
        title_layout = self.create_title_layout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addLayout(title_layout)
        layout.addWidget(self.text_edit)
        layout.setContentsMargins(0, 10, 0, 0)
        self.setLayout(layout)

    def create_title_layout(self):
        layout = QHBoxLayout()
        title_label = QLabel("系统信息")
        self.error_level = QComboBox()
        self.error_level.setMinimumWidth(100)
        self.error_level.addItems(["...", "通知","错误", "警告"])

        layout.addSpacing(5)
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(self.error_level)
        layout.addSpacing(5)
        self.error_level.currentTextChanged.connect(self.refresh_view)
        return layout

    def set_model(self, model: LogModel):
        self.model = model
        self.model.logs_changed.connect(self.refresh_view)
        self.refresh_view()

    def refresh_view(self):
        if self.text_edit is None or self.model is None:
            return
        selected = self.error_level.currentText() if self.error_level else "..."
        # Map: "..." => all, "通知" => INFO, "错误" => ERROR, "警告" => WARNING
        level_filter = None
        if selected == "通知":
            level_filter = "INFO"
        elif selected == "错误":
            level_filter = "ERROR"
        elif selected == "警告":
            level_filter = "WARNING"

        lines = []
        for entry in self.model.entries:
            if level_filter and entry.level != level_filter:
                continue
            ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            # 格式: LEVEL yyyy-MM-dd HH:mm:ss 消息
            lines.append(f"{entry.level} {ts} {entry.message}")
        self.text_edit.setPlainText("\n".join(lines))
        # 光标移至末尾
        self.text_edit.moveCursor(self.text_edit.textCursor().End)
        

log_model = LogModel()
log_controller = LogController(log_model)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SysInformationTextEdit()
    window.set_model(log_model)
    log_controller.info("程序启动")
    window.show()
    sys.exit(app.exec())
