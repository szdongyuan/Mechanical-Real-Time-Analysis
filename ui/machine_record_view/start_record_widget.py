import os

from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QPalette, QColor
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QFrame

from consts.running_consts import DEFAULT_DIR
from ui.show_solid_widget import ShowSolidWindow
from my_controls.peak_scatter_widget import PeakScatterWidget


class StartRecordWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.record_btn = QPushButton("启  动")
        self.stop_btn = QPushButton("停  止")
        self.audio_store_path_lineedit = QLineEdit()
        self.select_store_path_action = None
        self.peak_scatter = PeakScatterWidget()

        self.record_btn.setCheckable(True)
        self.stop_btn.setCheckable(True)

        # 设置对象名，便于样式区分
        self.record_btn.setObjectName("record_btn")
        self.stop_btn.setObjectName("stop_btn")
        # 未开始录制时禁止点击 Stop
        self.stop_btn.setEnabled(False)

        # 事件连接：点击 Record 进入选中（高亮绿），点击 Stop 取消
        self.record_btn.clicked.connect(self._on_record_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.init_ui()

    def init_ui(self):
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.init_lineedit_function()
        
        h_frame = QFrame()
        h_frame.setFrameShape(QFrame.HLine)
        h_frame.setFixedHeight(1)  # 设置高度为1像素
        h_frame.setStyleSheet("background-color: rgb(70, 70, 70); border: none;")

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 8, 10, 0)
        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.audio_store_path_lineedit)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(btn_layout)
        layout.addWidget(h_frame)
        layout.addWidget(self._create_solid_graph())
        self.setLayout(layout)

        self.set_widget_style()

    def set_widget_style(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                border: none;
                font-size: 14px;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgb(24, 144, 255);
            }
            QPushButton#record_btn:checked {
                background-color: rgb(3, 223, 109);
            }
        """)

    def _create_solid_graph(self):
        # 创建容器 widget 并设置背景色
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        # 默认展示 3D 模型；若加载失败则回退到占位文本
        step_widget = QLabel("STEP 模型未加载")
        step_widget.setAlignment(Qt.AlignCenter)
        step_widget.setStyleSheet("color: rgb(180, 180, 180);")
        step_path = DEFAULT_DIR + "ui/R87-Y160M.stp"
        if os.path.exists(step_path):
            try:
                show_solid_window = ShowSolidWindow(step_path)
                solid_widget = show_solid_window.get_widget()
                solid_widget.setMinimumSize(550, 150)
                solid_widget.setMaximumSize(700, 410)
                step_widget = solid_widget
            except Exception as exc:
                step_widget.setText(f"STEP 模型加载失败: {exc}")

        # 将图片放入容器布局
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(step_widget, 1)  # 添加拉伸因子
        layout.addSpacing(10)
        layout.addWidget(self.peak_scatter, 1)   # 添加拉伸因子
        
        return container

    # def init_lineedit_function(self, on_select_path):
    def init_lineedit_function(self):
        self.audio_store_path_lineedit.setReadOnly(True)
        self.audio_store_path_lineedit.setPlaceholderText("请选择音频存储路径")
        self.audio_store_path_lineedit.setStyleSheet("""
            QLineEdit {
                color: rgb(225, 225, 225);
                background-color: rgb(70, 70, 70);
                border: 1px solid rgb(70, 70, 70);
                font-size: 14px;
            }
        """)
        icon_path = DEFAULT_DIR + "ui/ui_pic/ai_window_pic/folder-s.png"
        self.select_store_path_action = self.audio_store_path_lineedit.addAction(
            QIcon(icon_path), QLineEdit.TrailingPosition
        )
        # select_store_path_action.triggered.connect(on_select_path)

    def _on_record_clicked(self):
        # 保持 Record 处于选中（绿色）
        self.record_btn.setChecked(True)
        # Stop 不维持选中态
        self.record_btn.setEnabled(False)
        # 允许停止
        self.stop_btn.setEnabled(True)

    def _on_stop_clicked(self):
        # 若当前未录制（Record 非绿色），直接忽略
        if not self.record_btn.isChecked():
            return
        # 结束录制，Record 恢复默认色
        self.record_btn.setChecked(False)
        # Stop 点击后也不保持选中
        self.stop_btn.setChecked(False)
        # 停止后禁用 Stop
        self.stop_btn.setEnabled(False)
        # 其他按钮保持默认
        self.record_btn.setEnabled(True)
        

    # 外部接口 -----------------------------------------------------------------
    def set_peak_channels(self, channels):
        try:
            self.peak_scatter.set_channels(channels)
        except Exception:
            pass

    def set_peak_threshold(self, threshold: float):
        self.peak_scatter.set_default_threshold(threshold)

    def set_peak_radius(self, radius: float):
        try:
            self.peak_scatter.set_ok_radius(radius)
        except Exception:
            pass

    def set_peak_max_radius(self, radius: float):
        try:
            self.peak_scatter.set_max_radius(radius)
        except Exception:
            pass

    def update_peak_scatter(self, result_items):
        self.peak_scatter.append_results(result_items)

    def reset_peak_scatter(self):
        self.peak_scatter.reset()


if __name__ == "__main__":

    import sys
    sys.path.append("..")
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    window = StartRecordWidget()
    window.show()
    app.exec_()

    