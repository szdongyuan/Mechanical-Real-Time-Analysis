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

from PyQt5.QtCore import Qt, QSize, QEvent
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView
from PyQt5.QtWidgets import QItemDelegate, QPushButton, QComboBox

from base.audio_data_manager import get_warning_audio_data_from_db, update_warning_audio_data
from consts import ui_style_const
from consts.running_consts import DEFAULT_DIR

from my_controls.look_analysis_report import open_html_in_default_browser


class ErrorManageWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.error_manage_table = QTableView()
        self.error_manage_table.setIconSize(QSize(25, 25))
        self.error_manage_model = CustomStandardItemModel(0, 10, [9])
        self.error_manage_table.setModel(self.error_manage_model)

        # 监听单元格编辑变化（用于“备注”列）
        self.error_manage_model.dataChanged.connect(self.on_model_data_changed)

        self.init_ui()

    def init_ui(self):
        # 设置深色背景，与主界面风格统一
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        error_manage_table_layout = self.create_error_manage_table_layout()
        self.setLayout(error_manage_table_layout)

    def create_error_manage_table_layout(self):
        self.error_manage_table.verticalHeader().setDefaultSectionSize(40)
        # 隐藏左侧行号列，使其与背景色一致
        self.error_manage_table.verticalHeader().setVisible(False)
        # 深色主题样式，与主界面风格统一
        self.error_manage_table.setStyleSheet(
            """QTableView {
                    background-color: rgb(55, 55, 55);
                    color: rgb(255, 255, 255);
                    gridline-color: rgb(70, 70, 70);
                    border: none;
                    font-size: 15px;
            }
            QTableView::item {
                border-top: 1px solid rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                padding-left: 5px;
                padding-right: 5px;
            }
            QTableView::item:selected {
                    background-color: rgb(24, 144, 255);
            }
            QHeaderView::section {
                    background-color: rgb(45, 45, 45);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(70, 70, 70);
                    padding: 5px;
                    font-size: 15px;
            }
            QTableView QTableCornerButton::section {
                    background-color: rgb(45, 45, 45);
                    border: 1px solid rgb(70, 70, 70);
            }
            QScrollArea {
                border: none;
                background-color: rgb(25, 25, 25);
            }
            QScrollBar:vertical {
                background-color: rgb(30, 30, 30);
                width: 8px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: rgb(80, 80, 80);
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgb(100, 100, 100);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
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
                "查看结果",
            ]
        )
        header = self.error_manage_table.horizontalHeader()
        column_count = self.error_manage_model.columnCount()
        # 先将所有列设置为 Stretch，使其自动拉伸填满 QTableView 宽度
        for col in range(column_count):
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        # 最后三列设置为固定宽度：操作列、处理状态列、查看结果列
        fixed_columns = {
            7: 140,  # 操作按钮列
            8: 125,  # 处理状态下拉框列
            9: 90,   # 查看结果（常看报告）列
        }
        for col, width in fixed_columns.items():
            header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.error_manage_table.setColumnWidth(col, width)

        # 数据加载改为显式接口调用：请调用 load_warning_data()

        error_manage_table_layout = QVBoxLayout()
        # 让 QTableView 的宽度与 ErrorManageWidget 一致（去掉左右边距）
        error_manage_table_layout.setContentsMargins(0, 2, 0, 0)
        error_manage_table_layout.setSpacing(0)
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
            reversed_result = list(reversed(result))
            self.add_warning_data(reversed_result)
        # 组件（按钮/下拉）依赖数据存在后再设置
        self.setup_buttons_in_btn_column()
        if result:
            self.setup_combobox(reversed_result)

        # 在最后一列添加“常看报告”超链接按钮
        self.setup_report_link_column()

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
        audio_data_items.append(warning_time_item)
        audio_data_items.append(warning_level_item)
        audio_data_items.append(warning_status_item)
        audio_data_items.append(charge_person_item)
        audio_data_items.append(record_audio_name_item)
        audio_data_items.append(record_time_item)
        audio_data_items.append(stop_time_item)
        audio_data_items.append(QStandardItem(""))
        audio_data_items.append(QStandardItem(""))
        audio_data_items.append(QStandardItem(""))

        self.error_manage_model.appendRow(audio_data_items)

    def get_cell_value(self, row: int, column: int):
        """
        获取表格中指定行、指定列单元格的内容。

        :param row: 行号（从 0 开始）
        :param column: 列号（从 0 开始）
        :return: 单元格文本内容（若无效则返回空字符串）
        """
        model = self.error_manage_model
        index = model.index(row, column)
        if not index.isValid():
            return ""
        data = index.data()
        return "" if data is None else str(data)

    def get_record_audio_data_name(self, record_audio_data_path: str):
        if record_audio_data_path:
            return record_audio_data_path.split("/")[-1].split(".")[0]
        return ""

    def setup_combobox(self, audio_datas):
        # 深色主题下拉框样式
        dark_combobox_style = """
            QComboBox {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(90, 90, 90);
                border-radius: 3px;
                padding: 3px 8px;
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
        for row in range(self.error_manage_model.rowCount()):
            index = self.error_manage_model.index(row, 8)
            combobox = QComboBox()
            combobox.addItems(["确认已处理", "确认未处理", "未确认", "忽略"])
            combobox.setStyleSheet(dark_combobox_style)
            combobox.setCurrentText(audio_datas[row][7])
            # 下拉框宽度与所在单元格（列）宽度保持一致
            col_width = self.error_manage_table.columnWidth(8)
            combobox.setFixedWidth(col_width - 10)
            # 下拉列表弹出视图宽度也与单元格一致
            try:
                combobox.view().setFixedWidth(col_width - 10)
            except Exception:
                pass
            # 禁用滚轮修改选项
            combobox.installEventFilter(self)
            # 下拉变更即写库
            combobox.currentTextChanged.connect(lambda text, r=row: self.on_deal_status_changed(r, text))
            self.error_manage_table.setIndexWidget(index, combobox)

    def eventFilter(self, obj, event):
        # 屏蔽所有 QComboBox 的滚轮事件，防止意外修改选项
        if isinstance(obj, QComboBox) and event.type() == QEvent.Wheel:
            return True
        return super().eventFilter(obj, event)

    def setup_buttons_in_btn_column(self):
        table = self.error_manage_table  # 修正变量名
        model = table.model()  # 获取当前模型
        btn_col = model.columnCount() - 3  # 使用模型列数

        # 深色主题按钮样式
        dark_btn_style = """
            QPushButton {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: rgb(24, 144, 255);
            }
            QPushButton:pressed {
                background-color: rgb(20, 120, 220);
            }
        """

        for row in range(model.rowCount()):
            deal_btn = QPushButton("处理")
            deal_btn.setStyleSheet(dark_btn_style)
            deal_btn.clicked.connect(lambda _, r=row: self.on_deal_btn_clicked(r))

            ignore_btn = QPushButton("忽略")
            ignore_btn.setStyleSheet(dark_btn_style)
            ignore_btn.clicked.connect(lambda _, r=row: self.on_ignore_btn_clicked(r))

            container = QWidget()
            container.setStyleSheet("background-color: rgb(55, 55, 55);")
            layout = QHBoxLayout(container)
            layout.addWidget(deal_btn)
            layout.addWidget(ignore_btn)
            layout.setContentsMargins(0, 0, 0, 0)

            # 使用 QTableView 的 setIndexWidget 方法
            index = model.index(row, btn_col)
            table.setIndexWidget(index, container)

    def setup_report_link_column(self):
        """
        在表格最后一列添加“常看报告”超链接样式按钮，点击后打印行号。
        """
        table = self.error_manage_table
        model = table.model()
        link_col = model.columnCount() - 1  # 最后一列

        link_style = """
            QPushButton {
                color: rgb(24, 144, 255);
                background-color: transparent;
                border: none;
                text-decoration: underline;
                font-size: 15px;
            }
            QPushButton:hover {
                color: rgb(135, 206, 250);
            }
        """

        for row in range(model.rowCount()):
            link_btn = QPushButton("常看报告")
            link_btn.setStyleSheet(link_style)
            link_btn.setCursor(Qt.PointingHandCursor)
            link_btn.clicked.connect(lambda _, r=row: self.on_view_report_clicked(r))

            index = model.index(row, link_col)
            table.setIndexWidget(index, link_btn)

    def on_deal_btn_clicked(self, row):
        print(f"处理第 {row} 行")
        # 同步更新下拉框（将触发写库）
        model = self.error_manage_table.model()
        combo_index = model.index(row, 8)
        combo = self.error_manage_table.indexWidget(combo_index)
        if isinstance(combo, QComboBox):
            combo.setCurrentText("确认已处理")

    def on_ignore_btn_clicked(self, row):
        print(f"忽略第 {row} 行")
        # 同步更新下拉框（将触发写库）
        model = self.error_manage_table.model()
        combo_index = model.index(row, 8)
        combo = self.error_manage_table.indexWidget(combo_index)
        if isinstance(combo, QComboBox):
            combo.setCurrentText("忽略")

    def on_view_report_clicked(self, row: int):
        """
        “常看报告”超链接点击回调：当前只打印行号。
        """
        file_name = self.get_cell_value(row, 4)
        web_url = DEFAULT_DIR + "reports/Report_" + file_name + ".html"
        code = open_html_in_default_browser(web_url)
        if code == 0:
            print("打开报告失败")
        elif code == 1:
            print("打开报告失败")


    def on_deal_status_changed(self, row: int, new_text: str):
        # 使用关键信息定位记录
        model = self.error_manage_model
        warning_time = model.index(row, 0).data()
        file_name = model.index(row, 4).data()
        if warning_time and file_name:
            update_warning_audio_data({"deal_status": new_text}, {"warning_time": warning_time, "file_name": file_name})

    def on_model_data_changed(self, top_left, bottom_right, roles=None):
        # 仅处理“备注”列（索引 9）的编辑写库
        del roles  # 未使用
        if top_left.column() != 9:
            return
        row = top_left.row()
        model = self.error_manage_model
        description = model.index(row, 9).data()
        warning_time = model.index(row, 0).data()
        file_name = model.index(row, 4).data()
        if warning_time and file_name:
            update_warning_audio_data({"description": description}, {"warning_time": warning_time, "file_name": file_name})

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
