import sys
import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QAbstractItemView, QWidget, QHBoxLayout, QLabel, QListView, QFrame
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QComboBox, QMessageBox

from base.data_struct.data_deal_struct import DataDealStruct
from base.sound_device_manager import get_device_info, change_default_mic
from base.load_device_info import load_devices_data
from consts.running_consts import DEFAULT_DIR
from ui.calibration_window import CalibrationWindow
# from ui.system_information_textedit import log_controller


class DeviceListWindow(QWidget):
    device_list_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.data_struct = DataDealStruct()
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
        # 设置深色背景，与主界面风格统一
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        api_layout = self.create_api_layout()
        device_list_layout = self.create_device_list_layout()
        channel_layout = self.create_channel_list_layout()
        btn_layout = self.create_btn_layout()

        # 应用深色主题样式
        self._apply_dark_theme()

        device_layout = QHBoxLayout()
        device_layout.addLayout(device_list_layout)
        device_layout.addLayout(channel_layout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: rgb(70, 70, 70); border: none;")

        layout = QVBoxLayout()
        layout.addLayout(api_layout)
        layout.addWidget(line)
        layout.addLayout(device_layout)
        layout.addSpacing(15)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _apply_dark_theme(self):
        """应用深色主题样式"""
        # 下拉框样式
        combobox_style = """
            QComboBox {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(90, 90, 90);
                border-radius: 3px;
                padding: 5px 10px;
                font-size: 15px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: url(./ui/ui_pic/shanglajiantou.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: rgb(55, 55, 55);
                color: rgb(255, 255, 255);
                selection-background-color: rgb(24, 144, 255);
                border: 1px solid rgb(70, 70, 70);
            }
        """
        self.api_combo_box.setStyleSheet(combobox_style)

        # 设备列表视图样式（与右侧通道列表保持一致的深色风格，使用复选框勾选）
        device_listview_style = """
            QListView {
                background-color: rgb(55, 55, 55);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(70, 70, 70);
                border-radius: 3px;
                font-size: 15px;
            }
            QListView::item {
                padding: 5px;
            }
            QListView::item:selected {
                /* 选中行使用与 hover 相同的深灰色，避免亮色块 */
                background-color: rgb(70, 70, 70);
            }
            QListView::item:hover {
                background-color: rgb(70, 70, 70);
            }
            QListView::indicator {
                background-color: rgb(45, 45, 45);
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid rgb(120, 120, 120);
            }
            QListView::indicator:unchecked {
                image: none;
            }
            QListView::indicator:checked {
                padding: 2px;
                image: url(./ui/ui_pic/sequence_pic/true.png);
            }
        """
        self.list_view.setStyleSheet(device_listview_style)

        self.channel_list.setStyleSheet(device_listview_style)

        # 标签样式
        label_style = "color: rgb(255, 255, 255); font-size: 15px;"
        self.setStyleSheet(f"QLabel {{ {label_style} }}")

        # 应用已保存配置到控件（若存在）
        self._apply_saved_config()

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
        # 取消左侧设备列表的选中高亮，仅通过复选框表示当前选中设备
        self.list_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_view.setSelectionRectVisible(False)
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        item_model = QStandardItemModel()
        current_api = self.api_combo_box.currentText()
        self.device_list = self.api_info[current_api][self.device_type]
        for device in self.device_list:
            item = QStandardItem(device["name"])
            # 使用复选框表示当前选中的设备，但仍保持单选逻辑
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            # 禁用 Qt 默认勾选行为，由 clicked 信号统一控制，保证只勾选一个
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            item_model.appendRow(item)
        self.list_view.setModel(item_model)
        self.list_view.setSelectionRectVisible(True)
        # 点击行时：更新复选框状态 + 保持原有选择逻辑（调用 on_select_item）
        self.list_view.clicked.connect(self.on_device_item_clicked)

        device_list_layout = QVBoxLayout()
        device_list_layout.addWidget(sellected_device_label)
        device_list_layout.addWidget(self.list_view)

        return device_list_layout

    def on_device_item_clicked(self, index):
        """
        左侧设备列表：使用复选框显示当前设备，但保持原来的“单选设备”逻辑。
        """
        model: QStandardItemModel = self.list_view.model()
        if model is None:
            return

        # 先全部取消勾选，保证只有一个设备被勾选
        for row in range(model.rowCount()):
            item = model.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.Unchecked)

        # 勾选当前点击的这一行
        item = model.itemFromIndex(index)
        if item is not None:
            item.setCheckState(Qt.Checked)

        # 保持原有逻辑：选中设备、刷新右侧通道列表等
        self.on_select_item(index)

    def create_channel_list_layout(self):
        channel_model = QStandardItemModel()
        self.channel_list.setModel(channel_model)
        sellected_channel_label = QLabel("选择通道")
        # 取消多选高亮模式，改用复选框
        self.channel_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.channel_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # 点击行时切换复选框状态
        self.channel_list.clicked.connect(self.on_channel_item_clicked)
        channel_layout = QVBoxLayout()
        channel_layout.addWidget(sellected_channel_label)
        channel_layout.addWidget(self.channel_list)

        return channel_layout

    def on_channel_item_clicked(self, index):
        """点击通道列表项时切换复选框状态"""
        item = self.channel_list.model().itemFromIndex(index)
        if item:
            # 切换复选框状态
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

    def create_btn_layout(self):
        btn_layout = QHBoxLayout()

        # 深色主题按钮样式
        btn_style = """
            QPushButton {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: rgb(24, 144, 255);
            }
            QPushButton:pressed {
                background-color: rgb(20, 120, 220);
            }
        """

        check_btn = QPushButton(" 校  准 ")
        check_btn.setStyleSheet(btn_style)
        check_btn.clicked.connect(self.on_click_check_btn)
        ok_btn = QPushButton(" 确  认 ")
        ok_btn.setStyleSheet(btn_style)
        ok_btn.clicked.connect(self.on_click_ok_btn)
        cancel_btn = QPushButton(" 取  消 ")
        cancel_btn.setStyleSheet(btn_style)
        cancel_btn.clicked.connect(self.on_click_cancel_btn)
        btn_layout.addWidget(check_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.setSpacing(45)
        btn_layout.setContentsMargins(30, 0, 30, 0)

        return btn_layout

    def _apply_saved_config(self):
        """
        从 ui/ui_config/device_data.json 读取配置，初始化 API、设备与通道选中状态。
        内部通道索引按 0 基存储，UI 显示为 1 基。
        """
        try:
            device_name, channels, selected_channels, current_api, mic_index = load_devices_data()
        except Exception:
            return
        if not device_name or not current_api:
            return

        # 1) 选择 API（将触发设备列表刷新）
        api_idx = self.api_combo_box.findText(current_api)
        if api_idx != -1:
            # 触发 update_api_device，刷新 self.device_list 与 list_view.model()
            self.api_combo_box.setCurrentIndex(api_idx)
        else:
            # 未找到对应 API，放弃恢复
            return

        # 2) 在设备列表中选中设备，并触发通道列表构建
        item_model: QStandardItemModel = self.list_view.model()
        if item_model is None:
            return
        target_index = None
        for row in range(item_model.rowCount()):
            item = item_model.item(row, 0)
            if item and item.text() == device_name:
                target_index = item_model.indexFromItem(item)
                break
        if target_index is None:
            return
        self.list_view.setCurrentIndex(target_index)
        # 同步内部 selected_device 与通道列表
        self.on_select_item(target_index)

        # 勾选当前设备对应的复选框，保持与 UI 一致
        model = self.list_view.model()
        if model is not None:
            for row in range(model.rowCount()):
                item = model.item(row, 0)
                if item is not None:
                    item.setCheckState(Qt.Unchecked)
            item = model.itemFromIndex(target_index)
            if item is not None:
                item.setCheckState(Qt.Checked)

        # 3) 选中通道（selected_channels 为 0 基索引），通过设置复选框状态
        ch_model: QStandardItemModel = self.channel_list.model()
        if ch_model is None:
            return
        for ch in selected_channels or []:
            row = int(ch)
            if 0 <= row < ch_model.rowCount():
                item = ch_model.item(row, 0)
                if item:
                    item.setCheckState(Qt.Checked)
        # 同步内部 selected_channels
        self.set_selected_channels()

    def update_api_device(self):
        item_model = QStandardItemModel()
        current_api = self.api_combo_box.currentText()
        self.device_list = self.api_info[current_api][self.device_type]
        for device in self.device_list:
            item = QStandardItem(device["name"])
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            item_model.appendRow(item)
        self.list_view.setModel(item_model)

    def on_click_check_btn(self):
        if self.selected_device:
            self.set_selected_channels()
            if len(self.selected_channels) == 0:
                QMessageBox.information(self, "提示", "请至少选择一个通道进行校准")
                return
            if self.about_device_checiked_info():
                self.mic_channel_check()
        else:
            QMessageBox.warning(self, "提示", "请选择设备")

    def about_device_checiked_info(self):
        about_device_checiked_info = QMessageBox()
        about_device_checiked_info.setWindowFlags(Qt.Dialog)
        about_device_checiked_info.setWindowTitle("关于设备校准")
        info_str = "您选择的设备共有%s个通道，本次校准将对通道%s进行校准。\n请确认是否继续？" % (
            self.selected_device["max_input_channels"],
            [channel + 1 for channel in self.selected_channels],
        )
        about_device_checiked_info.setText(info_str)
        about_device_checiked_info.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)

        if QMessageBox.Yes == about_device_checiked_info.exec():
            return True
        else:
            return False

    def mic_channel_check(self):
        check_mic_result = {}
        for channel in self.selected_channels:
            QMessageBox.information(self, "提示", "开始校准通道：" + str(channel + 1) + "，请将校准源放置到待校准通道处")
            calibration_window = CalibrationWindow(self.selected_device["max_input_channels"], int(channel + 1))
            check_result = calibration_window.exec()
            check_mic_result["channel-%s_deviation_value" % str(channel + 1)] = check_result
        check_mic_result["Datetime"] = datetime.now().strftime("%Y-%m-%d")
        self.save_mic_check_result_to_json(check_mic_result)

    @staticmethod
    def save_mic_check_result_to_json(check_mic_result):
        # dir_path = "D:/gqgit/new_project/ui/ui_config/"
        file_path = DEFAULT_DIR + "ui/ui_config/mic_check_data.json"
        try:
            with open(file_path, "w") as file:
                json.dump(check_mic_result, file)
        except Exception as e:
            print("Error saving device data:", e)

    def on_select_item(self, index):
        self.selected_device = self.device_list[index.row()]
        # log_controller.info(f"已选择硬件{self.selected_device['name']}")

        max_channels = self.selected_device.get("max_input_channels", 0)
        self.channel_list.model().clear()

        for channel in range(max_channels):
            item = QStandardItem(str(channel + 1))
            # 设置为可勾选的复选框
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            # 禁用 Qt 默认的复选框点击行为，完全由 clicked 信号控制
            # 这样点击文本和复选框都能正确切换状态
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            self.channel_list.model().appendRow(item)

    def set_selected_channels(self):
        # 从复选框状态获取选中的通道
        ch_model = self.channel_list.model()
        self.selected_channels = []
        if ch_model:
            for row in range(ch_model.rowCount()):
                item = ch_model.item(row, 0)
                if item and item.checkState() == Qt.Checked:
                    # UI 显示为 1 基，内部存储为 0 基整型
                    self.selected_channels.append(int(item.text()) - 1)

    @staticmethod
    def save_device_data_to_json(device_name, device_chanels, selected_channels, current_api, mic_index):
        selected_channels.sort()
        target_dir = DEFAULT_DIR + "ui/ui_config/"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        file_path = target_dir + "device_data.json"
        device_data = {
            "device_name": device_name,
            "device_chanels": device_chanels,
            "selected_channels": selected_channels,
            "current_api": current_api,
            "mic_index": mic_index,
        }
        try:
            with open(file_path, "w") as file:
                json.dump(device_data, file)
        except Exception as e:
            print("Error saving device data:", e)

    def on_click_ok_btn(self):
        print("on_click_ok_btn")
        self.data_struct.channels_change_flag = True
        current_api = self.api_combo_box.currentText()
        index = self.api_info[current_api]["input"].index(self.selected_device)
        mic_index = self.api_info[current_api]["input"][index]["index"]
        change_default_mic(mic_index)
        self.set_selected_channels()
        self.save_device_data_to_json(
            self.selected_device["name"],
            self.selected_device["max_input_channels"],
            self.selected_channels,
            current_api,
            mic_index
        )
        self.device_list_changed.emit(0)
        # log_controller.info(f"选择硬件{self.selected_device['name']}")

    def on_click_cancel_btn(self):
        self.selected_device = None

    def show(self):
        if self.data_struct.record_flag:
            self.channel_list.setEnabled(False)
        else:
            self.channel_list.setEnabled(True)
        super().show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeviceListWindow()
    window.show()
    sys.exit(app.exec())
