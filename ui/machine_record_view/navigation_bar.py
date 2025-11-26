import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QStandardItemModel, QStandardItem,QIcon, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListView, QButtonGroup

from consts.running_consts import DEFAULT_DIR

class NavigationBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.created_buttons = []
        self.channel_check = ChannelCheck(self)
        self.channel_check.create_caheck_label(4)

        self.navition_listview = QListView()
        self.navition_listview.setIconSize(QSize(34, 34))
        self.navition_listview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.navition_listview.setEditTriggers(QListView.NoEditTriggers)
        # 禁用选择功能，取消高亮
        self.navition_listview.setSelectionMode(QListView.NoSelection)
        # 禁用焦点，避免焦点框
        self.navition_listview.setFocusPolicy(Qt.NoFocus)
        model = QStandardItemModel()
        self.navition_listview.setModel(model)
        self.swap_size_btn = QPushButton("<<")
        self.swap_size_btn.setFixedHeight(25)
        self.swap_size_btn.clicked.connect(self.on_clicked_swap_size_btn)
        # 保存 setIndexWidget 创建的控件引用，避免被垃圾回收
        self._listview_owned_widgets = []
        # 互斥按钮组（参考 wav_or_spect_graph.py 的模式按钮）
        self._nav_btn_group = QButtonGroup(self)
        self._nav_btn_group.setExclusive(True)
        # 先完成字段初始化，再添加按钮项
        self.add_item_to_nevigation_listview()

        self.initUI()

    def initUI(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)

        self.setPalette(palette)
        self.setFixedWidth(230)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        layout = QVBoxLayout()
        self.navition_listview.setMinimumHeight(500)
        # 列表项之间的间距（按钮之间距离）
        self.navition_listview.setSpacing(5)
        self.navition_listview.setStyleSheet("""
            QListView {
                border:none;
                color:rgb(255, 255, 255);
                background-color:rgb(45, 45, 45);
                padding-top: 10px;
                font-size: 15px;}
        """)
        self.swap_size_btn.setStyleSheet("border:none; color:rgb(204,204,204);")
        # btn_layout = QHBoxLayout()
        # btn_layout.addWidget(self.swap_size_btn, alignment=Qt.AlignRight)
        layout.addWidget(self.swap_size_btn, stretch=0, alignment=Qt.AlignRight)
        layout.addWidget(self.navition_listview, stretch=1,alignment=Qt.AlignTop)
        layout.addStretch()
        self.setLayout(layout)

    def add_item_to_nevigation_listview(self):  
        # 将 6 个条目改为互斥可选按钮，颜色与 wav_or_spect_graph.py 保持一致
        self.add_item("功能模块")
        entries = [
            (" 录制音频", DEFAULT_DIR + "ui/ui_pic/sequence_pic/shishijiance.png"),
            (" 历史数据", DEFAULT_DIR + "ui/ui_pic/sequence_pic/data.png"),
            (" 报警管理", DEFAULT_DIR + "ui/ui_pic/sequence_pic/jinggao.png"),
            (" 设备列表", DEFAULT_DIR + "ui/ui_pic/sequence_pic/shebei.png"),
            (" 用户设置", DEFAULT_DIR + "ui/ui_pic/sequence_pic/yonghu.png"),
        ]
        
        for text, icon_path in entries:
            btn = self.add_button_to_listview(text, on_clicked=None, icon_url=icon_path, item_height=40)
            btn.setCheckable(True)
            # 与 wav_or_spect_graph.py 中按钮样式一致（未选灰、选中蓝）
            # btn.setStyleSheet(
            #     "border:none; color:rgb(255,255,255); text-align:left; padding-left:8px; "
            #     "background-color:rgb(55,55,55);"
            # )
            # 选中态颜色
            btn.setStyleSheet(
                "QPushButton { border:none; color:rgb(255,255,255); text-align:left; padding-left:8px; background-color:rgb(55,55,55); }"
                "QPushButton:checked { background-color: rgb(24, 144, 255); }"
            )
            self._nav_btn_group.addButton(btn)
            self.created_buttons.append(btn)
        # 默认选中第一项
        if self.created_buttons:
            self.created_buttons[0].setChecked(True)

        self.add_item("传感器状态")
        self.add_widget_to_listview(self.channel_check, item_height=None)

    def add_item(self, text:str, icon_url:str = None):
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

    def add_button_to_listview(self, text: str, on_clicked=None, icon_url: str = None, row: int = None, item_height: int = None) -> QPushButton:
        """
        在 navition_listview 中插入一个 QPushButton 项。
        - text: 按钮文本
        - on_clicked: 可选的点击回调
        - icon_url: 可选的图标路径
        - row: 插入的位置，None 表示追加到末尾
        - item_height: 行高
        返回创建的按钮实例，便于外部进一步连接信号。
        """
        model: QStandardItemModel = self.navition_listview.model()
        item = QStandardItem()
        item.setEditable(False)
        item.setSelectable(False)
        item.setSizeHint(QSize(0, item_height))
        if row is None:
            model.appendRow(item)
        else:
            model.insertRow(row, item)
        index = model.indexFromItem(item)

        button = QPushButton(text, self.navition_listview)
        if icon_url:
            button.setIcon(QIcon(icon_url))
        # 与导航栏风格一致的简洁样式
        button.setStyleSheet("border:none; color:rgb(255,255,255); text-align:left; background-color:rgb(55,55,55);")
        
        if on_clicked:
            button.clicked.connect(on_clicked)
        self.navition_listview.setIndexWidget(index, button)
        self._listview_owned_widgets.append(button)
        return button

    def add_widget_to_listview(self, widget: QWidget, row: int = None, item_height: int = None) -> QWidget:
        """
        在 navition_listview 中插入任意 QWidget。
        - widget: 要嵌入的控件（已创建）
        - row: 插入的位置，None 表示追加到末尾
        - item_height: 行高
        返回传入的 widget。
        """
        model: QStandardItemModel = self.navition_listview.model()
        item = QStandardItem()
        item.setEditable(False)
        item.setSelectable(False)
        calculated_height = item_height if item_height is not None else max(36, widget.sizeHint().height())
        item.setSizeHint(QSize(0, calculated_height))
        if row is None:
            model.appendRow(item)
        else:
            model.insertRow(row, item)
        index = model.indexFromItem(item)

        self.navition_listview.setIndexWidget(index, widget)
        self._listview_owned_widgets.append(widget)
        return widget


class NavigationBarItem(QStandardItem):
    def __init__(self, text:str, icon_url:str = None):
        super().__init__(text)
        if icon_url:
            self.setIcon(QIcon(icon_url))


class ChannelCheck(QWidget):

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.channels:int = 0

        self.check_result_labels = list()
        
        # 设置背景色和最小高度，确保在深色导航栏中可见
        self.setStyleSheet("color: rgb(255, 255, 255); font-size: 15px;")

    def create_caheck_label(self, channel:int):
        # 如果已经存在布局，先移除旧布局，避免叠加
        if self.layout() is not None:
            old_layout = self.layout()
            QWidget().setLayout(old_layout)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.check_result_labels.clear()
        for i in range(channel):
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"通道{i + 1}： 声压传感器"))
            h_layout.addStretch()

            channel_result_label = QLabel()
            self.check_result_labels.append(channel_result_label)
            h_layout.addWidget(channel_result_label)

            widget = QWidget()
            widget.setLayout(h_layout)
            widget.setStyleSheet("background-color: rgb(55, 55, 55);")

            layout.addWidget(widget)
        for i in range(channel):
            self.set_label_text(i, "已连接", "green")
        self.setLayout(layout)
    
    def set_label_text(self, channel:int, text:str, color:str):
        color_dict = {
            "red": "#ff4d4f",
            "yellow": "#faad14",
            "green": "#52c41a",
            "white": "#ffffff",
        }
        color = color_dict.get(color, color_dict["white"])
        self.check_result_labels[channel].setText(f"<span style='color:{color};'>{text}</span>")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NavigationBar()
    window.show()
    sys.exit(app.exec())