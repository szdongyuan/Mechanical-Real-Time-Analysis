import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QPushButton

from base.audio_data_manager import get_record_audio_data_from_db


class ErrorManageWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.error_manage_table = QTableView()
        self.error_manage_table.setIconSize(QSize(25, 25)) 
        self.error_manage_model = CustomStandardItemModel(0, 8, [6])
        self.error_manage_table.setModel(self.error_manage_model)

        self.init_ui()

    def init_ui(self):
        error_manage_table_layout = self.create_error_manage_table_layout()

        self.setLayout(error_manage_table_layout)

    def create_error_manage_table_layout(self):
        self.error_manage_table.verticalHeader().setDefaultSectionSize(40)
        self.error_manage_table.setStyleSheet("""QTableView::item {
                                                                    border-top: 1px solid rgb(130, 135, 144);
                                                                    color: black;
                                                                  }""")
        self.error_manage_table.model().setHorizontalHeaderLabels(["文件名称", "录制时间", "结束时间", "异常时间", "操作员", "处理结果", "备注", "操作"])
        header = self.error_manage_table.horizontalHeader()
        for i in range(self.error_manage_model.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
        # header.setStretchLastSection(True)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        result = get_record_audio_data_from_db()
        if result:
            self.add_history_data(result)
        self.setup_buttons_in_last_column()

        error_manage_table_layout = QVBoxLayout()
        error_manage_table_layout.addWidget(self.error_manage_table)

        return error_manage_table_layout
    
    def add_history_data(self, audio_datas):
        for audio_data in audio_datas:
            record_audio_data_path, record_time, stop_time, _, error_time, operator, operator_result, description = audio_data
            self.add_history_data_to_table(record_audio_data_path, 
                                           record_time,
                                           stop_time,
                                           error_time,
                                           operator,
                                           operator_result,
                                           description)
    
    def add_history_data_to_table(self,
                                  record_audio_data_path: str,
                                  record_time: str,
                                  stop_time: str,
                                  error_time: str,
                                  operator: str,
                                  operator_result: str,
                                  description: str):
        audio_data_items = []
        record_audio_name = self.get_record_audio_data_name(record_audio_data_path)
        record_audio_name_item = QStandardItem(record_audio_name)
        record_time_item = QStandardItem(str(record_time))
        stop_time_item = QStandardItem(str(stop_time))
        error_item = QStandardItem(error_time)
        operator_item = QStandardItem(operator)
        operator_result_item = QStandardItem(operator_result)
        description_item = QStandardItem(description)
        audio_data_items.append(record_audio_name_item)
        audio_data_items.append(record_time_item)
        audio_data_items.append(stop_time_item)
        audio_data_items.append(error_item)
        audio_data_items.append(operator_item)
        audio_data_items.append(operator_result_item)
        audio_data_items.append(description_item)
        self.error_manage_model.appendRow(audio_data_items)
    
    def get_record_audio_data_name(self, record_audio_data_path: str):
        if record_audio_data_path:
            return record_audio_data_path.split("/")[-1].split(".")[0]
        return ""
    
    def setup_buttons_in_last_column(self):
        table = self.error_manage_table  # 修正变量名
        model = table.model()  # 获取当前模型
        last_col = model.columnCount() - 1  # 使用模型列数

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
            index = model.index(row, last_col)
            table.setIndexWidget(index, container)

    def on_deal_btn_clicked(self, row):
        print(f"处理第 {row} 行")
        
    def on_ignore_btn_clicked(self, row):
        print(f"忽略第 {row} 行")


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










        
