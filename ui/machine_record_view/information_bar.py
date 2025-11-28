import sys
from dataclasses import dataclass
from datetime import datetime

from PyQt5.QtCore import Qt, QSize, QObject, pyqtSignal, QEvent, QTimer
from PyQt5.QtGui import QStandardItemModel, QStandardItem,QIcon, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QListView, QButtonGroup, QTextEdit

from my_controls.custom_label import CustomInfoLabel
from my_controls.health_evaluate_widget import HealthEvaluateWidget


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
        self.widget = QWidget()
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
        self._nav_btn_group = QButtonGroup(self)
        self._nav_btn_group.setExclusive(True)

        self.information_level_widget = InformationLevelWidget()
        self.health_evaluate_widget = HealthEvaluateWidget(3)
        # self.health_evaluate_widget.setStyleSheet("background-color: rgb(60,60,60);")
        self.add_item_to_nevigation_listview()
        self.initUI()
        self.navition_listview.viewport().installEventFilter(self)
        self.init_health_evaluate_widget()

    def initUI(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)

        self.setPalette(palette)
        self.setFixedWidth(300)
        # self.setWindowFlags(Qt.FramelessWindowHint)
        layout = QVBoxLayout()
        self.navition_listview.setMinimumHeight(500)
        self.navition_listview.setStyleSheet("""
            QListView {
                border:none;
                color:rgb(255, 255, 255);
                background-color:rgb(45, 45, 45);
                padding-top: 10px;
				font-size: 14px;
            }
        """)
        self.swap_size_btn.setStyleSheet("border:none; color:rgb(204,204,204);font-size: 14px;")
        layout.addWidget(self.swap_size_btn, stretch=0, alignment=Qt.AlignLeft)
        layout.addWidget(self.navition_listview, stretch=1, alignment=Qt.AlignTop)
        layout.addStretch()
        self.setLayout(layout)

    def init_health_evaluate_widget(self):
        self.health_evaluate_widget.set_label_text(0, name="整体健康度", value="0.0")
        self.health_evaluate_widget.set_label_text(1, name="系统 1 健康度", value="0.0")
        self.health_evaluate_widget.set_label_text(2, name="系统 2 健康度", value="0.0")

    def write_score(self, results: list):
        score_results = results[0].get("health_scores", {})
        overall_score = score_results.get("overall", "0")
        overall_score = str(overall_score)
        self.health_evaluate_widget.set_value(0, overall_score)

        good_score = str(score_results.get("good_motor", "0"))
        self.health_evaluate_widget.set_label_text(1, "系统 1 健康度: " + good_score)
        bad_score = str(score_results.get("bad_motor", "0"))
        self.health_evaluate_widget.set_label_text(2, "系统 2 健康度: " + bad_score)

    def add_item_to_nevigation_listview(self):
        self.add_widget_to_listview(self.information_level_widget)
        
        self.widget.setStyleSheet("background-color: rgb(60,60,60);border-radius: 6px;")
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.health_evaluate_widget)
        # 设置布局约束，使容器大小跟随内容变化
        layout.setSizeConstraint(QVBoxLayout.SetMinAndMaxSize)
        self.widget.setLayout(layout)
        self.add_widget_to_listview(self.widget)
        # 监听 health_evaluate_widget 的高度变化信号
        self.health_evaluate_widget.height_changed.connect(self._on_health_widget_height_changed)
        # self.add_widget_to_listview(self.queue_widget)

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

    def _on_health_widget_height_changed(self):
        """
        当 health_evaluate_widget 展开 / 折叠时，动态调整其在 QListView 中对应行的高度，
        避免展开后显示不全。
        """
        item = self._widget_to_item.get(self.widget)
        if item is None:
            return

        # 强制更新布局，使容器高度跟随内容变化
        self.health_evaluate_widget.updateGeometry()
        self.widget.layout().activate()  # 激活布局，强制重新计算
        self.widget.adjustSize()  # 调整容器大小以适应内容
        
        # 重新根据控件当前的 sizeHint 计算高度
        new_height = max(36, self.widget.sizeHint().height())
        item.setSizeHint(QSize(0, new_height))

        # 通知 QListView 重新布局
        self.navition_listview.updateGeometries()
        self.navition_listview.viewport().update()

    # def _update_text_edit_row_height(self):
    #     """让 text_edit 这一行铺满剩余空间。"""
    #     text_item = self._widget_to_item.get(self.queue_widget)
    #     if text_item is None:
    #         return
    #     view_h = self.navition_listview.viewport().height()
    #     if view_h <= 0:
    #         return
    #     model: QStandardItemModel = self.navition_listview.model()
    #     other_h = 0
    #     for r in range(model.rowCount()):
    #         it = model.item(r)
    #         if it is text_item:
    #             continue
    #         h = it.sizeHint().height()
    #         if h <= 0:
    #             h = 20
    #         other_h += h
    #     remaining = max(60, view_h - other_h - 6)
    #     text_item.setSizeHint(QSize(0, remaining))
    #     self.navition_listview.updateGeometries()
    #     self.navition_listview.viewport().update()

    # def eventFilter(self, obj, event):
    #     # if obj is self.navition_listview.viewport() and event.type() == QEvent.Resize:
    #     #     self._update_text_edit_row_height()
    #     return super().eventFilter(obj, event)

    # def resizeEvent(self, e):
    #     super().resizeEvent(e)
    #     # self._update_text_edit_row_height()


class InformationLevelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # self.evaluate_health = CustomInfoLabel("健康评估：", "0", color="green")
        # self.warning_count = CustomInfoLabel("警 告 数：", "0", color="yellow")
        self.average_spl = CustomInfoLabel("平均声压级：", "70.0 dB", color="green")
        self.runing_time = CustomInfoLabel("运行时间：", "00:00:00", color="green")
        
        # 初始化运行时间计数器（秒）
        self._elapsed_seconds = 0
        
        # 创建定时器，每秒更新一次
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_running_time)
        self._timer.start(1000)  # 1000毫秒 = 1秒
        
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(100)
        
        h_layout_bottom = QHBoxLayout()
        h_layout_bottom.setContentsMargins(0, 0, 0, 10)
        h_layout_bottom.addWidget(self.average_spl)
        h_layout_bottom.addStretch()
        h_layout_bottom.addWidget(self.runing_time)
        self.setLayout(h_layout_bottom)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgb(45,45,45); border-radius: 6px;")
    
    def _update_running_time(self):
        """每秒更新一次运行时间"""
        self._elapsed_seconds += 1
        
        # 计算时分秒
        hours = self._elapsed_seconds // 3600
        minutes = (self._elapsed_seconds % 3600) // 60
        seconds = self._elapsed_seconds % 60
        
        # 格式化为 HH:MM:SS
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # 更新显示
        self.runing_time.set_second_line(time_str)
    
    def reset_timer(self):
        """重置计时器"""
        self._elapsed_seconds = 0
        self.runing_time.set_second_line("00:00:00")
    
    def stop_timer(self):
        """停止计时器"""
        self._timer.stop()
    
    def start_timer(self):
        """启动计时器"""
        self._timer.start(1000)

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