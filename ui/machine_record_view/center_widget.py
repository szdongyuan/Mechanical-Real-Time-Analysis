from typing import override

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame

from ui.device_list import DeviceListWindow
from ui.historical_data import HistoryDataWindow
from ui.error_manage_widget import ErrorManageWidget
from consts.running_consts import DEFAULT_DIR
from ui.machine_record_view.information_bar import InformationBar
from ui.machine_record_view.navigation_bar import NavigationBar
from ui.machine_record_view.start_record_widget import StartRecordWidget
from ui.machine_record_view.wav_or_spect_graph import WavOrSpectGraph


class CenterWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_index = 0

        self.information_bar = InformationBar()
        self.navigation_bar = NavigationBar()
        self.start_record_widget = StartRecordWidget()
        self.wav_or_spect_graph = WavOrSpectGraph()

        self.error_manage_widget = ErrorManageWidget()
        self.device_list_window = DeviceListWindow()
        self.history_data_window = HistoryDataWindow()

        self.widget_sequence = [
            self.start_record_widget,
            self.history_data_window,
            self.error_manage_widget,
            self.device_list_window,
        ]

        self.record_mode_btn.clicked.connect(self.on_record_mode_btn_clicked)
        self.history_data_btn.clicked.connect(self.on_history_data_btn_clicked)
        self.alarm_management_btn.clicked.connect(self.on_alarm_management_btn_clicked)
        self.device_list_btn.clicked.connect(self.on_device_list_btn_clicked)
        self.information_bar.swap_size_btn.clicked.connect(self.error_manage_widget.adjust_column_widths)
        self.navigation_bar.swap_size_btn.clicked.connect(self.error_manage_widget.adjust_column_widths)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("设备健康状态监测")
        self.setWindowIcon(QIcon(DEFAULT_DIR + "ui/ui_pic/sys_ico/icon.ico"))
        # 创建水平分割线，去掉 FrameShape 设置，直接用样式控制
        h_frame = QFrame()
        h_frame.setFixedHeight(1)  # 设置高度为1像素
        h_frame.setStyleSheet("background-color: rgb(70, 70, 70); border: none;")

        # 创建左侧垂直分割线
        v_frame_left = QFrame()
        v_frame_left.setFixedWidth(1)  # 设置宽度为1像素
        v_frame_left.setStyleSheet("background-color: rgb(70, 70, 70); border: none;")

        # 创建右侧垂直分割线
        v_frame_right = QFrame()
        v_frame_right.setFixedWidth(1)  # 设置宽度为1像素
        v_frame_right.setStyleSheet("background-color: rgb(70, 70, 70); border: none;")

        h_layout = QHBoxLayout()
        h_layout.setSpacing(0)
        h_layout.addWidget(self.navigation_bar)
        h_layout.addWidget(v_frame_left)
        h_layout.addWidget(self.cteate_center_splitter())
        h_layout.addWidget(v_frame_right)
        h_layout.addWidget(self.information_bar)

        h_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(h_layout)

    def cteate_center_splitter(self):
        contains_widget = QWidget()
        v_layout = QVBoxLayout()
        v_layout.setSpacing(0)
        v_layout.setContentsMargins(0, 0, 0, 0)
        
        for i in range(len(self.widget_sequence)):
            if self.widget_sequence[i] == None:
                continue
            v_layout.addWidget(self.widget_sequence[i])
            if i != 0:
                self.widget_sequence[i].hide()
        
        contains_widget.setLayout(v_layout)

        splitter = QSplitter()
        # 设置handle的高度为1像素（因为是垂直分割，所以是height）
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgb(70, 70, 70);
            }
        """)
        splitter.setOrientation(Qt.Vertical)
        splitter.addWidget(contains_widget)
        splitter.addWidget(self.wav_or_spect_graph)
        return splitter

    def on_record_mode_btn_clicked(self):
        self.current_index = 0
        self.swap_model_widget()

    def on_history_data_btn_clicked(self):
        self.current_index = 1
        self.swap_model_widget()

    def on_alarm_management_btn_clicked(self):
        self.current_index = 2
        self.swap_model_widget()

    def on_device_list_btn_clicked(self):
        self.current_index = 3
        self.swap_model_widget()

    def set_waveform_title(self, channel_index: list):
        self.wav_or_spect_graph.set_waveform_title(channel_index)

    def swap_model_widget(self):
        for i in range(len(self.widget_sequence)):
            if self.widget_sequence[i] == None:
                # if i == widget_sequence:
                #     login_window = LoginWindow()
                #     login_window.on_exec()
                continue
            if self.widget_sequence[i].isVisible():
                if i == self.current_index:
                    continue
                self.widget_sequence[i].hide()
            else:
                if i == self.current_index:
                    self.widget_sequence[i].show()

    def set_light_color(self, light, color):
        self.wav_or_spect_graph.set_light_color(light, color)

    def hide_right_part_widget(self, is_true: bool):
        self.wav_or_spect_graph.hide_right_part_widget(is_true)

    @override
    def changeEvent(self, event):
        super().changeEvent(event)
        # 只在窗口状态改变时调整列宽，避免拖动 Splitter 时的性能问题
        if event.type() == QEvent.WindowStateChange:
            self.error_manage_widget.adjust_column_widths()

    @property
    def record_mode_btn(self):
        return self.navigation_bar.created_buttons[0]

    @property
    def history_data_btn(self):
        return self.navigation_bar.created_buttons[1]

    @property
    def alarm_management_btn(self):
        return self.navigation_bar.created_buttons[2]

    @property
    def device_list_btn(self):
        return self.navigation_bar.created_buttons[3]

    @property
    def user_settings_btn(self):
        return self.navigation_bar.created_buttons[4]

    @property
    def record_btn(self):
        return self.start_record_widget.record_btn

    @property
    def stop_btn(self):
        return self.start_record_widget.stop_btn

    @property
    def audio_store_path_lineedit(self):
        return self.start_record_widget.audio_store_path_lineedit

    @property
    def select_store_path_action(self):
        return self.start_record_widget.select_store_path_action

    @property
    def warning_btn(self):
        return self.information_bar.information_level_widget.warning_btn

    @property
    def error_btn(self):
        return self.information_bar.information_level_widget.error_btn
    
    @property
    def info_btn(self):
        return self.information_bar.information_level_widget.info_btn
    
    @property
    def all_btn(self):
        return self.information_bar.information_level_widget.all_btn

    @property
    def text_edit(self):
        return self.information_bar.text_edit

    @property
    def prev_page(self):
        return self.wav_or_spect_graph.prev_page

    @property
    def next_page(self):
        return self.wav_or_spect_graph.next_page


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = CenterWidget()
    window.show()
    sys.exit(app.exec_())

