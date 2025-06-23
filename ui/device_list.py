import sys
import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QDialog, QHBoxLayout, QLabel, QListView, QFrame
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QComboBox

from base.sound_device_manager import get_device_info
from ui.calibration_window import CalibrationWindow


class DeviceListWindow(QDialog):

    def __init__(self):
        super().__init__()
        self.device_type = "input"
        self.device_title = " —— 麦克风"

        self.selected_device = None
        self.api_info = get_device_info()

        self.api_combo_box = QComboBox()
        self.list_view = QListView()
        self.channel_list = QListView()
        self.selected_channels = []

        self.init_ui()

    def init_ui(self):
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        api_layout = self.create_api_layout()
        device_list_layout = self.create_device_list_layout()
        channel_layout = self.create_channel_list_layout()
        btn_layout = self.create_btn_layout()

        device_layout = QHBoxLayout()
        device_layout.addLayout(device_list_layout)
        device_layout.addLayout(channel_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(20)

        layout = QVBoxLayout()
        layout.addLayout(api_layout)
        layout.addWidget(line)
        layout.addLayout(device_layout)
        layout.addSpacing(15)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def create_api_layout(self):
        api_layout = QHBoxLayout()
        api_label = QLabel("选择驱动")
        self.api_combo_box.addItems([api for api in self.api_info])
        self.api_combo_box.currentTextChanged.connect(self.update_api_device)
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_combo_box)

        return api_layout

    def create_device_list_layout(self):
        sellected_device_label = QLabel("选择设备")
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        item_model = QStandardItemModel()
        current_api = self.api_combo_box.currentText()
        self.device_list = self.api_info[current_api][self.device_type]
        for device in self.device_list:
            item_model.appendRow(QStandardItem(device["name"]))
        self.list_view.setModel(item_model)
        self.list_view.setSelectionRectVisible(True)
        self.list_view.clicked.connect(self.on_select_item)

        device_list_layout = QVBoxLayout()
        device_list_layout.addWidget(sellected_device_label)
        device_list_layout.addWidget(self.list_view)

        return device_list_layout

    def create_channel_list_layout(self):
        channel_model = QStandardItemModel()
        self.channel_list.setModel(channel_model)
        sellected_channel_label = QLabel("选择通道")
        self.channel_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.channel_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(sellected_channel_label)
        channel_layout.addWidget(self.channel_list)

        return channel_layout

    def create_btn_layout(self):
        btn_layout = QHBoxLayout()

        check_btn = QPushButton(" 校  准 ")
        check_btn.clicked.connect(self.on_click_check_btn)
        ok_btn = QPushButton(" 确  认 ")
        ok_btn.clicked.connect(self.on_click_ok_btn)
        cancel_btn = QPushButton(" 取  消 ")
        cancel_btn.clicked.connect(self.on_click_cancel_btn)
        btn_layout.addWidget(check_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.setSpacing(45)
        btn_layout.setContentsMargins(30, 0, 30, 0)

        return btn_layout

    def update_api_device(self):
        item_model = QStandardItemModel()
        current_api = self.api_combo_box.currentText()
        self.device_list = self.api_info[current_api][self.device_type]
        for device in self.device_list:
            item_model.appendRow(QStandardItem(device["name"]))
        self.list_view.setModel(item_model)

    def on_click_check_btn(self):
        if self.selected_device:
            calibration_window = CalibrationWindow()
            calibration_window.exec()

    def on_select_item(self, index):
        self.selected_device = self.device_list[index.row()]

        max_channels = self.selected_device.get("max_input_channels", 0)
        self.channel_list.model().clear()

        for channel in range(max_channels):
            self.channel_list.model().appendRow(QStandardItem(str(channel)))

    @staticmethod
    def save_device_data_to_json(device_name, device_chanels, selected_channels):
        dir_path = "D:/gqgit/new_project/ui/ui_config/"
        file_path = dir_path + "device_data.json"
        device_data = {
            "device_name": device_name,
            "device_chanels": device_chanels,
            "selected_channels": selected_channels,
        }
        try:
            with open(file_path, "w") as file:
                json.dump(device_data, file)
        except Exception as e:
            print("Error saving device data:", e)

    def on_click_ok_btn(self):
        print("Selected device:", self.selected_device)
        selected_indices = self.channel_list.selectedIndexes()
        self.selected_channels = [idx.data() for idx in selected_indices]
        self.save_device_data_to_json(
            self.selected_device["name"], self.selected_device["max_input_channels"], self.selected_channels
        )
        # print("Selected channels:", self.selected_channels)

    def on_click_cancel_btn(self):
        self.selected_device = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceListWindow()
    window.show()
    sys.exit(app.exec())
