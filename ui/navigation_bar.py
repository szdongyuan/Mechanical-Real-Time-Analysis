import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QIcon, QStandardItem
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListView

from consts.running_consts import DEFAULT_DIR

class NavigationBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.navition_listview = QListView()
        self.navition_listview.setIconSize(QSize(34, 34))
        self.navition_listview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        model = QStandardItemModel()
        self.navition_listview.setModel(model)
        self.swap_size_btn = QPushButton("<<")
        self.swap_size_btn.clicked.connect(self.on_clicked_swap_size_btn)
        self.add_item_to_nevigation_listview()

        self.initUI()

    def initUI(self):
        self.setFixedWidth(230)
        self.setWindowFlags(Qt.FramelessWindowHint)
        layout = QVBoxLayout()
        self.navition_listview.setMinimumHeight(500)
        self.navition_listview.setStyleSheet("""QListView {
                                                            border:none;
                                                            background-color:rgb(240, 240, 240);
                                                            font-size: 28px;}
                                                QListView::item {
                                                                height: 80px;
                                                            }""")
        self.swap_size_btn.setStyleSheet("border:none;")
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.swap_size_btn, alignment=Qt.AlignRight)
        layout.addLayout(btn_layout)
        layout.addWidget(self.navition_listview, alignment=Qt.AlignTop)
        layout.addStretch()
        self.setLayout(layout)

    def add_item_to_nevigation_listview(self):  
        self.add_item(" 实时监测", DEFAULT_DIR + "ui/ui_pic/sequence_pic/shishijiance.png")
        self.add_item(" 历史数据", DEFAULT_DIR + "ui/ui_pic/sequence_pic/data.png")
        self.add_item(" 报警管理", DEFAULT_DIR + "ui/ui_pic/sequence_pic/jinggao.png")
        self.add_item(" 设备列表", DEFAULT_DIR + "ui/ui_pic/sequence_pic/shebei.png")
        self.add_item(" 用户设置", DEFAULT_DIR + "ui/ui_pic/sequence_pic/yonghu.png")
        self.navition_listview.setCurrentIndex(self.navition_listview.model().index(0, 0))

    def add_item(self, text:str, icon_url:str):
        item = NavigationBarItem(text, icon_url)
        self.navition_listview.model().appendRow(item)

    def on_clicked_swap_size_btn(self):
        if self.navition_listview.isVisible():
            self.navition_listview.hide()
            self.swap_size_btn.setText(">>")
            self.setFixedWidth(35)
        else:
            self.navition_listview.show()
            self.swap_size_btn.setText("<<")
            self.setFixedWidth(230)


class NavigationBarItem(QStandardItem):
    def __init__(self, text:str, icon_url:str = None):
        super().__init__(text)
        if icon_url:
            self.setIcon(QIcon(icon_url))
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NavigationBar()
    window.show()
    sys.exit(app.exec())