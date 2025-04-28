import sys

from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QComboBox, QTextEdit


class ErrorInformationTextEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_ui()
    
    def init_ui(self):
        title_layout = self.create_title_layout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addLayout(title_layout)
        layout.addWidget(text_edit)
        layout.setContentsMargins(0, 10, 0, 0)
        self.setLayout(layout)

    def create_title_layout(self):
        layout = QHBoxLayout()
        title_label = QLabel("错误信息")
        error_level = QComboBox()
        error_level.setMinimumWidth(100)
        error_level.addItems(["...", "错误", "警告"])

        layout.addSpacing(5)
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(error_level)
        layout.addSpacing(5)
        return layout
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ErrorInformationTextEdit()
    window.show()
    sys.exit(app.exec())
