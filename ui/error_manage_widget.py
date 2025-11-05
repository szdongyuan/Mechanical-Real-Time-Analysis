"""
错误管理表格（ErrorManageWidget）模块

对外接口（推荐调用）：
- ErrorManageWidget.load_warning_data():
    从数据库查询最新数据并写入表格（清空旧数据后再填充）。
- ErrorManageWidget.show():
    已重载，展示窗口前会自动调用 load_warning_data()。
- ErrorManageWidget.add_warning_data(audio_datas):
    传入已查询好的数据列表并写入表格（无需直接操作数据库）。

使用方法：
    from ui.error_manage_widget import ErrorManageWidget

    widget = ErrorManageWidget()
    # 方式一：手动加载
    widget.load_warning_data()
    widget.show()

    # 方式二：直接 show（内部会自动加载）
    widget = ErrorManageWidget()
    widget.show()

注意：
- 数据库查询依赖 base.audio_data_manager.get_warning_audio_data_from_db。
- 若需要刷新表格（例如外部更新了数据库），再次调用 load_warning_data() 即可。
"""

import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView
from PyQt5.QtWidgets import QItemDelegate, QPushButton, QComboBox

from base.audio_data_manager import get_warning_audio_data_from_db
from consts import ui_style_const


class ErrorManageWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.error_manage_table = QTableView()
        self.error_manage_table.setIconSize(QSize(25, 25))
        self.error_manage_model = CustomStandardItemModel(0, 10, [9])
        self.error_manage_table.setModel(self.error_manage_model)

        self.init_ui()

    def init_ui(self):
        error_manage_table_layout = self.create_error_manage_table_layout()
        self.setLayout(error_manage_table_layout)

    def create_error_manage_table_layout(self):
        self.error_manage_table.verticalHeader().setDefaultSectionSize(40)
        self.error_manage_table.setStyleSheet(
            """QTableView::item {
                border-top: 1px solid rgb(130, 135, 144);
                color: black;
            }"""
        )
        self.error_manage_table.model().setHorizontalHeaderLabels(
            [
                "警告时间",
                "警告级别",
                "警告状态",
                "负责人员",
                "文件名称",
                "录制时间",
                "结束时间",
                "操作",
                "处理状态",
                "备注",
            ]
        )
        header = self.error_manage_table.horizontalHeader()
        for i in range(self.error_manage_model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        # header.setStretchLastSection(True)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        # 数据加载改为显式接口调用：请调用 load_warning_data()

        error_manage_table_layout = QVBoxLayout()
        error_manage_table_layout.addWidget(self.error_manage_table)

        return error_manage_table_layout

    def load_warning_data(self):
        """
        显式从数据库查询并写入表格。
        可在外部初始化完控件后调用，以避免在构造阶段自动加载。
        """
        result = get_warning_audio_data_from_db()
        # 清空现有数据
        try:
            self.error_manage_model.removeRows(0, self.error_manage_model.rowCount())
        except Exception:
            pass

        if result:
            self.add_warning_data(result)
        # 组件（按钮/下拉）依赖数据存在后再设置
        self.setup_buttons_in_btn_column()
        if result:
            self.setup_combobox(result)

    def add_warning_data(self, audio_datas):
        for audio_data in audio_datas:
            (
                warning_time,
                warning_level,
                warning_status,
                charge_person,
                file_name,
                record_time,
                stop_time,
                deal_status,
                description,
            ) = audio_data
            self.add_history_data_to_table(
                warning_time,
                warning_level,
                warning_status,
                charge_person,
                file_name,
                record_time,
                stop_time,
                description,
            )

    def add_history_data_to_table(
        self,
        warning_time: str,
        warning_level: str,
        warning_status: str,
        charge_person: str,
        file_name: str,
        record_time: str,
        stop_time: str,
        description,
    ):
        audio_data_items = []
        warning_time_item = QStandardItem(str(warning_time))
        warning_level_item = QStandardItem(warning_level)
        warning_status_item = QStandardItem(warning_status)
        charge_person_item = QStandardItem(charge_person)
        record_audio_name_item = QStandardItem(file_name)
        record_time_item = QStandardItem(str(record_time))
        stop_time_item = QStandardItem(str(stop_time))
        description_item = QStandardItem(description)
        audio_data_items.append(warning_time_item)
        audio_data_items.append(warning_level_item)
        audio_data_items.append(warning_status_item)
        audio_data_items.append(charge_person_item)
        audio_data_items.append(record_audio_name_item)
        audio_data_items.append(record_time_item)
        audio_data_items.append(stop_time_item)
        audio_data_items.append(QStandardItem(""))
        audio_data_items.append(QStandardItem(""))
        audio_data_items.append(description_item)

        self.error_manage_model.appendRow(audio_data_items)

    def get_record_audio_data_name(self, record_audio_data_path: str):
        if record_audio_data_path:
            return record_audio_data_path.split("/")[-1].split(".")[0]
        return ""

    def setup_combobox(self, audio_datas):
        for row in range(self.error_manage_model.rowCount()):
            index = self.error_manage_model.index(row, 8)
            combobox = QComboBox()
            combobox.addItems(["确认已处理", "确认未处理", "未确认", "忽略"])
            combobox.setStyleSheet(ui_style_const.qcombobox_stytle)
            combobox.setCurrentText(audio_datas[row][8])
            self.error_manage_table.setIndexWidget(index, combobox)

    def setup_buttons_in_btn_column(self):
        table = self.error_manage_table  # 修正变量名
        model = table.model()  # 获取当前模型
        btn_col = model.columnCount() - 3  # 使用模型列数

        for row in range(model.rowCount()):
            deal_btn = QPushButton("处理")
            deal_btn.clicked.connect(lambda _, r=row: self.on_deal_btn_clicked(r))

            ignore_btn = QPushButton("忽略")
            ignore_btn.clicked.connect(lambda _, r=row: self.on_ignore_btn_clicked(r))

            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(deal_btn)
            layout.addWidget(ignore_btn)
            layout.setContentsMargins(0, 0, 0, 0)

            # 使用 QTableView 的 setIndexWidget 方法
            index = model.index(row, btn_col)
            table.setIndexWidget(index, container)

    def on_deal_btn_clicked(self, row):
        print(f"处理第 {row} 行")

    def on_ignore_btn_clicked(self, row):
        print(f"忽略第 {row} 行")

    def show(self):
        self.load_warning_data()
        super().show()


class CustomStandardItemModel(QStandardItemModel):
    def __init__(self, rows, columns, editable_column: list, parent=None):
        super().__init__(rows, columns, parent)
        self.editable_column = editable_column

    def flags(self, index):
        if index.isValid():
            if index.column() in self.editable_column:
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
            else:
                return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return super().flags(index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ErrorManageWidget()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())
