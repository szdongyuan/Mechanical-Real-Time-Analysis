import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenuBar, QStatusBar, QLabel, QAction

from base.data_struct.data_deal_struct import DataDealStruct
from consts.model_consts import DEFAULT_DIR
from ui.ai.ai_analysis_config_mvc import AIConfigView, AIConfigController, AIModelStore
from ui.center_widget import CenterWidget


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.data_struct = DataDealStruct()

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("实时波形显示")
        self.center_widget = CenterWidget(self)

        self.setCentralWidget(self.center_widget)
        self.set_menu_bar()

    def set_menu_bar(self):
        menu_bar = QMenuBar()
        function_menu = menu_bar.addMenu("功能")
        ai_analysis_action = QAction("AI 分析", self)
        ai_analysis_action.triggered.connect(self.show_ai_analysis_window)
        function_menu.addAction(ai_analysis_action)
        hardware_menu = menu_bar.addMenu("硬件")
        user_menu = menu_bar.addMenu("用户")
        help_menu = menu_bar.addMenu("帮助")

        self.setMenuBar(menu_bar)

    def show_ai_analysis_window(self):
        json_path = DEFAULT_DIR + "ui/ui_config/models.json"
        model_store = AIModelStore.from_json_or_default(json_path)

        view = AIConfigView()
        controller = AIConfigController(model_store, view)  # noqa: F841 (保持引用)

        view.resize(420, 240)
        if view.exec_() == view.Accepted:
            result = view.get_result_data()  # 字典结果
            print(result)

    def show_statusbar_layout(self):
        # create status bar, show the user data and device data, and close drag status bar modify window size
        self.user_label = QLabel()
        self.user_label.setAlignment(Qt.AlignLeft)
        self.user_label.setText(
            "当前用户：{name}  用户等级：{level}".format(name=self.user_name, level=self.access_lvl)
        )
        self.device_label = QLabel()
        device_txt = "麦克风：{mic}  扬声器：{speaker}".format(mic=self.mic["name"], speaker=self.speaker["name"])
        self.device_label.setText(device_txt)

        statusbar = QStatusBar()
        statusbar.setSizeGripEnabled(False)
        statusbar.addWidget(self.user_label)
        statusbar.addPermanentWidget(self.device_label)
        self.setStatusBar(statusbar)

    def closeEvent(self, event):
        self.center_widget.main_widget.audio_manager.stop_recording()
        self.center_widget.main_widget.audio_manager.quit()
        self.center_widget.main_widget.audio_manager.wait()
        self.data_struct.record_flag = False
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
