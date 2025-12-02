import sys
from dataclasses import dataclass
from datetime import datetime

from PyQt5.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QButtonGroup, QSizePolicy, QWIDGETSIZE_MAX

from my_controls.custom_label import CustomInfoLabel
from my_controls.health_evaluate_widget import HealthEvaluateWidget
from my_controls.info_widget import MessageQueueWidget


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

        self.health_widget = QWidget()
        # self.message_widget = QWidget()
        self._main_layout = None
        self._bottom_spacer = None
        self.is_hide_flag = False
        self.swap_size_btn = QPushButton(">>")
        self.swap_size_btn.clicked.connect(self.on_clicked_swap_size_btn)
        self._nav_btn_group = QButtonGroup(self)
        self._nav_btn_group.setExclusive(True)

        self.information_level_widget = InformationLevelWidget()
        self.health_evaluate_widget = HealthEvaluateWidget(3)
        # self.queue_info_widget = MessageQueueWidget()
        self.initUI()
        self.init_health_evaluate_widget()

    def initUI(self):
        self.swap_size_btn.setStyleSheet("border:none; color:rgb(204,204,204);font-size: 14px;")
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)

        self.setPalette(palette)
        self.setFixedWidth(300)
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.health_evaluate_widget.height_changed.connect(self._on_health_widget_height_changed)
        # self.queue_info_widget.height_changed.connect(self._on_message_widget_height_changed)

        self.set_main_layout()

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
        self.health_evaluate_widget.set_label_text(1, "系统 1 健康度 ", value=str(good_score))
        bad_score = str(score_results.get("bad_motor", "0"))
        self.health_evaluate_widget.set_label_text(2, "系统 2 健康度 ", value=str(bad_score))

    def set_main_layout(self):
        self.set_control_contain(self.health_evaluate_widget, self.health_widget)
        # self.set_control_contain(self.queue_info_widget, self.message_widget)
        self._on_health_widget_height_changed()

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        layout.addWidget(self.swap_size_btn, alignment=Qt.AlignLeft)
        layout.addWidget(self.information_level_widget, 0)
        layout.addWidget(self.health_widget, 0)
        # layout.addWidget(self.message_widget, 0)
        # 添加底部弹簧 widget，用于折叠时填充剩余空间（可动态控制 stretch factor）
        self._bottom_spacer = QWidget()
        self._bottom_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._bottom_spacer, 1)
        self._main_layout = layout
        self.setLayout(layout)
        
        # 初始化时根据当前 queue_info_widget 状态调整一次 message_widget 布局
        # self._on_message_widget_height_changed()

    def set_control_contain(self, control: QWidget, contain: QWidget):
        contain.setStyleSheet("background-color: rgb(60,60,60);border-radius: 6px;")
        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(control)
        layout.setSizeConstraint(QVBoxLayout.SetMinAndMaxSize)
        contain.setLayout(layout)

    def on_clicked_swap_size_btn(self):
        if self.is_hide_flag:
            self.information_level_widget.show()
            self.health_widget.show()
            # self.message_widget.show()
            self.swap_size_btn.setText(">>")
            self.setFixedWidth(300)
            self.is_hide_flag = False
        else:
            self.information_level_widget.hide()
            self.health_widget.hide()
            # self.message_widget.hide()
            self.swap_size_btn.setText("<<")
            self.setFixedWidth(35)
            self.is_hide_flag = True

    def _on_health_widget_height_changed(self):
        """
        当 health_evaluate_widget 展开 / 折叠时，动态调整其在 QListView 中对应行的高度，
        避免展开后显示不全。
        """
        self.health_evaluate_widget.updateGeometry()
        self.health_widget.layout().activate()
        self.health_widget.adjustSize()

        new_height = max(36, self.health_evaluate_widget.sizeHint().height())
        self.health_widget.setFixedHeight(new_height)

    # def _on_message_widget_height_changed(self):
    #     """
    #     根据 queue_info_widget 的折叠 / 展开状态动态调整 message_widget 的布局策略：
    #     - 展开时：message_widget 占用除上方控件外的所有剩余空间；
    #     - 折叠时：message_widget 高度≈ queue_info_widget 折叠高度，其余区域留空白。
    #     """
    #     # 先让内部控件根据折叠/展开重新计算尺寸
    #     self.queue_info_widget.updateGeometry()
    #     if self.message_widget.layout():
    #         self.message_widget.layout().activate()

    #     is_expanded = self.queue_info_widget.is_expanded()

    #     msg_layout = self.message_widget.layout()
    #     if not isinstance(msg_layout, QVBoxLayout):
    #         # 保护性判断，理论上不会发生
    #         return

    #     if is_expanded:
    #         # 展开：允许 message_widget 在垂直方向上自由拉伸，填充剩余空间
    #         msg_layout.setSizeConstraint(QVBoxLayout.SetDefaultConstraint)
    #         self.message_widget.setMinimumHeight(0)
    #         self.message_widget.setMaximumHeight(QWIDGETSIZE_MAX)
    #         self.message_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
    #         # 更新主布局：展开时 message_widget 占用剩余空间，底部弹簧不占用空间
    #         if self._main_layout is not None and self._bottom_spacer is not None:
    #             self._main_layout.setStretchFactor(self.message_widget, 1)
    #             self._main_layout.setStretchFactor(self._bottom_spacer, 0)
    #             self._bottom_spacer.hide()
    #     else:
    #         # 折叠：把 message_widget 的高度限制在其内容（折叠后的 queue_info_widget）范围内
    #         msg_layout.setSizeConstraint(QVBoxLayout.SetMinAndMaxSize)

    #         # 让父容器的高度尽量贴合当前内容高度
    #         collapsed_height = self.queue_info_widget.sizeHint().height()
    #         margins = msg_layout.contentsMargins()
    #         collapsed_height += margins.top() + margins.bottom()

    #         self.message_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    #         self.message_widget.setMinimumHeight(collapsed_height)
    #         self.message_widget.setMaximumHeight(collapsed_height)
            
    #         # 更新主布局：折叠时 message_widget 不占用额外空间，底部弹簧填充剩余空间
    #         if self._main_layout is not None and self._bottom_spacer is not None:
    #             self._main_layout.setStretchFactor(self.message_widget, 0)
    #             self._main_layout.setStretchFactor(self._bottom_spacer, 1)
    #             self._bottom_spacer.show()

    #     # 触发布局重新计算
    #     if self._main_layout is not None:
    #         self._main_layout.activate()
    #     self.updateGeometry()
    #     self.adjustSize()

class InformationLevelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.average_spl = CustomInfoLabel("平均声压级：", "70.0 dB", color="green")
        self.runing_time = CustomInfoLabel("运行时间：", "00:00:00", color="green")

        self._elapsed_seconds = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_running_time)
        self._timer.start(1000)

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

        hours = self._elapsed_seconds // 3600
        minutes = (self._elapsed_seconds % 3600) // 60
        seconds = self._elapsed_seconds % 60

        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InformationBar()
    # window = InformationLevelWidget()
    window.show()
    sys.exit(app.exec())

