import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QPushButton


class ErrorManageWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.error_manage_table = QTableView()
        self.error_manage_table.setIconSize(QSize(25, 25)) 
        self.error_manage_model = CustomStandardItemModel(10, 7, [5])
        self.error_manage_table.setModel(self.error_manage_model)

        self.play_icon = QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/play.png")
        self.pause_icon = QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/pause.png")
        # self.error_manage_table.clicked.connect(self.on_cell_clicked)

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
        self.error_manage_table.model().setHorizontalHeaderLabels(["录制时间", "结束时间", "异常时间", "操作员", "处理结果", "备注", "操作"])
        self.error_manage_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        self.setup_buttons_in_last_column()

        error_manage_table_layout = QVBoxLayout()
        error_manage_table_layout.addWidget(self.error_manage_table)

        return error_manage_table_layout
    
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
    
    def on_cell_clicked(self, index):
        if index.column() == 6:  # 操作列（列索引4）
            item = self.error_manage_model.item(index.row(), index.column())
            if item.icon() == self.play_icon:
                item.setIcon(self.pause_icon)
            else:
                item.setIcon(self.play_icon)
            # 通知视图更新图标
            self.error_manage_model.dataChanged.emit(index, index, [Qt.DecorationRole])



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
    
class CustomStandardItem(QStandardItem):
    def __init__(self, text:str, icon_url:str):
        super().__init__(text)
        if icon_url:
            self.setIcon(QIcon(icon_url))
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ErrorManageWidget()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())