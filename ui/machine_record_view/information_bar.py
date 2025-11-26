import sys
from dataclasses import dataclass
from datetime import datetime

from PyQt5.QtCore import Qt, QSize, QObject, pyqtSignal, QEvent
from PyQt5.QtGui import QStandardItemModel, QStandardItem,QIcon, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListView, QButtonGroup, QTextEdit

from consts.running_consts import DEFAULT_DIR
from my_controls.custom_button import CustomInfoButton


@dataclass
class LogEntry:
    level: str
    timestamp: datetime
    message: str


class LogModel(QObject):
    logs_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._entries = []

    def add_log(self, level: str, message: str):
        entry = LogEntry(level=level, timestamp=datetime.now(), message=message)
        self._entries.append(entry)
        self.logs_changed.emit()

    @property
    def entries(self):
        return list(self._entries)


class LogController:
    def __init__(self, model: LogModel):
        self.model = model

    def info(self, message: str):
        self.model.add_log("INFO", message)

    def warning(self, message: str):
        self.model.add_log("WARNING", message)

    def error(self, message: str):
        self.model.add_log("ERROR", message)


class InformationBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.navition_listview = QListView()
        self.navition_listview.setIconSize(QSize(34, 34))
        self.navition_listview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 禁止编辑列表内容
        self.navition_listview.setEditTriggers(QListView.NoEditTriggers)
        # 禁用选择功能，取消高亮
        self.navition_listview.setSelectionMode(QListView.NoSelection)
        # 禁用焦点，避免焦点框
        self.navition_listview.setFocusPolicy(Qt.NoFocus)
        model = QStandardItemModel()
        self.navition_listview.setModel(model)
        self.swap_size_btn = QPushButton(">>")
        self.swap_size_btn.clicked.connect(self.on_clicked_swap_size_btn)
        # 保存 setIndexWidget 创建的控件引用，避免被垃圾回收
        self._listview_owned_widgets = []
        # 记录 widget -> item，用于动态拉伸最后一项
        self._widget_to_item = {}
        # 互斥按钮组（参考 wav_or_spect_graph.py 的模式按钮）
        self._nav_btn_group = QButtonGroup(self)
        self._nav_btn_group.setExclusive(True)

        self.information_level_widget = InformationLevelWidget()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
		# 深色主题：避免白底
        self.text_edit.setStyleSheet("background: rgb(65,65,65); color: rgb(220,220,220); border: 1px solid rgb(70,70,70);")
        # 先完成字段初始化，再添加按钮项
        self.add_item_to_nevigation_listview()

        self.initUI()
        # 监听 viewport 尺寸变化，动态让 text_edit 铺满剩余空间
        self.navition_listview.viewport().installEventFilter(self)
        self._update_text_edit_row_height()

    def initUI(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)

        self.setPalette(palette)
        self.setFixedWidth(300)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        layout = QVBoxLayout()
        self.navition_listview.setMinimumHeight(500)
        # 列表项之间的间距（按钮之间距离）
        # self.navition_listview.setSpacing(5)
        self.navition_listview.setStyleSheet("""
            QListView {
                border:none;
                color:rgb(255, 255, 255);
                background-color:rgb(45, 45, 45);
                padding-top: 10px;
				font-size: 15px;
            }
        """)
        self.swap_size_btn.setStyleSheet("border:none; color:rgb(204,204,204);")
        # btn_layout = QHBoxLayout()
        # btn_layout.addWidget(self.swap_size_btn, alignment=Qt.AlignLeft)
        # layout.addLayout(btn_layout)
        layout.addWidget(self.swap_size_btn, stretch=0, alignment=Qt.AlignLeft)
        layout.addWidget(self.navition_listview, stretch=1, alignment=Qt.AlignTop)
        layout.addStretch()
        # layout.addStretch()
        self.setLayout(layout)

    def add_item_to_nevigation_listview(self):
        self.add_item(" 信息等级")
        self.add_widget_to_listview(self.information_level_widget)
        self.add_item(" 系统信息")
        self.add_widget_to_listview(self.text_edit)

    def add_item(self, text:str, icon_url:str = None):
        item = NavigationBarItem(text, icon_url)
        self.navition_listview.model().appendRow(item)

    def on_clicked_swap_size_btn(self):
        if self.navition_listview.isVisible():
            self.navition_listview.hide()
            self.swap_size_btn.setText("<<")
            self.setFixedWidth(35)
        else:
            self.navition_listview.show()
            self.swap_size_btn.setText(">>")
            self.setFixedWidth(300)

    def add_button_to_listview(self, text: str, on_clicked=None, icon_url: str = None, row: int = None, item_height: int = 36) -> QPushButton:
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
		# 若未指定高度，使用控件自身的 sizeHint，避免被压扁出现白条
        calculated_height = item_height if item_height is not None else max(36, widget.sizeHint().height())
        item.setSizeHint(QSize(0, calculated_height))
        if row is None:
            model.appendRow(item)
        else:
            model.insertRow(row, item)
        index = model.indexFromItem(item)

        self.navition_listview.setIndexWidget(index, widget)
        self._listview_owned_widgets.append(widget)
        # 保存映射，便于后续调整该项高度
        self._widget_to_item[widget] = item
        return widget

    def _update_text_edit_row_height(self):
        """让 text_edit 这一行铺满剩余空间。"""
        text_item = self._widget_to_item.get(self.text_edit)
        if text_item is None:
            return
        view_h = self.navition_listview.viewport().height()
        if view_h <= 0:
            return
        model: QStandardItemModel = self.navition_listview.model()
        other_h = 0
        for r in range(model.rowCount()):
            it = model.item(r)
            if it is text_item:
                continue
            h = it.sizeHint().height()
            if h <= 0:
                h = 20
            other_h += h
        remaining = max(60, view_h - other_h - 6)
        text_item.setSizeHint(QSize(0, remaining))
        self.navition_listview.updateGeometries()
        self.navition_listview.viewport().update()

    def eventFilter(self, obj, event):
        if obj is self.navition_listview.viewport() and event.type() == QEvent.Resize:
            self._update_text_edit_row_height()
        return super().eventFilter(obj, event)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_text_edit_row_height()


class InformationLevelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.warning_btn = CustomInfoButton("警告：", "0", color="yellow")
        self.error_btn = CustomInfoButton("错误：", "0", color="red")
        self.info_btn = CustomInfoButton("通知：", "0", color="green")
        self.all_btn = CustomInfoButton("全部：", "0", color="white")

        # 互斥选择（参考 wav_or_spect_graph.py）
        self._level_group = QButtonGroup(self)
        self._level_group.setExclusive(True)
        for btn in (self.error_btn, self.warning_btn, self.info_btn, self.all_btn):
            btn.setCheckable(True)
            # 未选：深灰；选中：高亮蓝
            btn.setStyleSheet(
                "QPushButton { background-color: rgb(55,55,55); color: rgb(255,255,255); border:none;border-radius: 6px; }"
                "QPushButton:checked { background-color: rgb(24,144,255); }"
            )
            self._level_group.addButton(btn)
        # 默认选中“全部”
        self.all_btn.setChecked(True)

        self.init_ui()

    def init_ui(self):
        self.setFixedSize(270, 150)

        h_layout_top = QHBoxLayout()
        h_layout_top.addWidget(self.error_btn)
        h_layout_top.addWidget(self.warning_btn)
        h_layout_bottom = QHBoxLayout()
        h_layout_bottom.addWidget(self.info_btn)
        h_layout_bottom.addWidget(self.all_btn)
        v_layout = QVBoxLayout()
        v_layout.addLayout(h_layout_top)
        v_layout.addLayout(h_layout_bottom)
        self.setLayout(v_layout)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgb(45,45,45); border-radius: 6px;")

class NavigationBarItem(QStandardItem):
    def __init__(self, text:str, icon_url:str = None):
        super().__init__(text)
        # 设置为不可编辑
        self.setEditable(False)
        if icon_url:
            self.setIcon(QIcon(icon_url))
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InformationBar()
    # window = InformationLevelWidget()
    window.show()
    sys.exit(app.exec())