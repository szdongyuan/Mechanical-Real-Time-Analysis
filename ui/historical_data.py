import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QTableView, QHeaderView

from base.audio_data_manager import get_record_audio_data_from_db


class HistoryDataWindow(QDialog):
    def __init__(self):
        super().__init__()

        self.history_data_table = QTableView()
        self.history_data_table.setIconSize(QSize(25, 25)) 
        self.history_data_model = CustomStandardItemModel(10, 7, [5])
        self.history_data_table.setModel(self.history_data_model)

        self.play_icon = QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/play.png")
        self.pause_icon = QIcon("D:/gqgit/new_project/ui/ui_pic/sequence_pic/pause.png")
        self.history_data_table.clicked.connect(self.on_cell_clicked)

        result = get_record_audio_data_from_db()
        print(result)

        self.init_ui()

    def init_ui(self):
        history_data_table_layout = self.create_history_data_table_layout()

        self.setLayout(history_data_table_layout)

    def create_history_data_table_layout(self):
        self.history_data_table.setColumnWidth(4, 100)  # 设置操作列宽度为 100 像素
        self.history_data_table.verticalHeader().setDefaultSectionSize(40)
        self.history_data_table.setStyleSheet("""QTableView::item {
                                                                    border-top: 1px solid rgb(130, 135, 144);
                                                                    color: black;
                                                                  }""")
        self.history_data_table.model().setHorizontalHeaderLabels(["文件名称", "录制时间", "结束时间", "异常", "操作员", "备注", "操作"])
        self.history_data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row in range(self.history_data_model.rowCount()):
            item = self.history_data_model.item(row, 5)
            if not item:
                item = CustomStandardItem("111", "ui/ui_pic/sequence_pic/play.png")
                self.history_data_model.setItem(row, 5, item)
            item.setIcon(self.play_icon)
        self.history_data_table.viewport().update()

        history_data_table_layout = QVBoxLayout()
        history_data_table_layout.addWidget(self.history_data_table)

        return history_data_table_layout
    
    def on_cell_clicked(self, index):
        if index.column() == 5:  # 操作列（列索引4）
            item = self.history_data_model.item(index.row(), index.column())
            if item.icon() == self.play_icon:
                item.setIcon(self.pause_icon)
            else:
                item.setIcon(self.play_icon)
            # 通知视图更新图标
            self.history_data_model.dataChanged.emit(index, index, [Qt.DecorationRole])


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
    window = HistoryDataWindow()
    window.setWindowTitle("历史数据")
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())
    