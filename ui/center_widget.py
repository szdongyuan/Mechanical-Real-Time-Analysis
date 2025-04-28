import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox

from ui.navigation_bar import NavigationBar
from ui.historical_data import HistoryDataWindow
from ui.device_list import DeviceListWindow
from ui.error_information_textedit import ErrorInformationTextEdit
from ui.test import MainWidget
from ui.error_manage_widget import ErrorManageWidget
from ui.login_window import LoginWindow


class CenterWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.history_data_window = HistoryDataWindow()
        self.device_list_window = DeviceListWindow()
        self.error_information_textedit = ErrorInformationTextEdit()
        self.navigation_bar = NavigationBar()
        self.main_widget = MainWidget(self)
        self.error_manage_widget = ErrorManageWidget()
        
        self.widget_sequence = [self.main_widget, self.history_data_window, self.error_manage_widget, self.device_list_window, None]
        self.navigation_bar.navition_listview.clicked.connect(lambda index: self.swap_model_widget(index.row()))

        self.init_ui()
        self.showMaximized()
        self.swap_model_widget()

    def init_ui(self):
        self.create_layout()

    def create_right_layout(self):
        self.error_information_textedit.setMaximumHeight(500)
        error_information_box = self.create_rror_information_box()
        right_layout = QVBoxLayout()
        for i in range(len(self.widget_sequence)):
            if self.widget_sequence[i] == None:
                continue
            right_layout.addWidget(self.widget_sequence[i])
            if i != 0:
                self.widget_sequence[i].hide()
        right_layout.addWidget(error_information_box, alignment=Qt.AlignBottom)

        return right_layout
    
    def create_navigation_bar_box(self):
        navigation_bar_box = QGroupBox()
        navigation_bar_box.setMaximumWidth(230)
        layout = QVBoxLayout()
        layout.addWidget(self.navigation_bar) 
        navigation_bar_box.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        return navigation_bar_box
    
    def create_rror_information_box(self):
        error_information_box = QGroupBox()
        error_information_box.setMaximumHeight(300)
        layout = QVBoxLayout()
        layout.addWidget(self.error_information_textedit)
        error_information_box.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)

        return error_information_box
    
    def swap_model_widget(self, widget_sequence: int = 0):
        for i in range(len(self.widget_sequence)):
            if self.widget_sequence[i] == None:
                if i == widget_sequence:
                    login_window = LoginWindow()
                    login_window.on_exec()
                continue
            if self.widget_sequence[i].isVisible():
                if i== widget_sequence:
                    continue
                self.widget_sequence[i].hide()
            else:
                if i == widget_sequence:
                    self.widget_sequence[i].show()    

    def create_layout(self):
        layout = QHBoxLayout()
        navigation_bar_box = self.create_navigation_bar_box()
        layout.addWidget(navigation_bar_box)
        layout.addLayout(self.create_right_layout())
        self.setLayout(layout)

    def closeEvent(self, event):
        self.main_widget.audio_manager.stop_recording()
        self.main_widget.audio_manager.quit()
        self.main_widget.audio_manager.wait()
        self.main_widget.recording = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    center_widget = CenterWidget()
    center_widget.show()
    sys.exit(app.exec_())