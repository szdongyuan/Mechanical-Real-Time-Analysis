from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QDesktopServices, QFont, QPixmap, QPalette, QColor
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QFrame

from consts.running_consts import DEFAULT_DIR
from ui.show_solid_widget import ShowSolidWindow


class StartRecordWidget(QWidget):

    def __init__(self):
        super().__init__()

        self.record_btn = QPushButton("启  动")
        self.stop_btn = QPushButton("停  止")
        self.audio_store_path_lineedit = QLineEdit()
        self.about_dy_btn = QPushButton("关于东原")
        self.select_store_path_action = None

        self.record_btn.setCheckable(True)
        self.stop_btn.setCheckable(True)

        # 设置对象名，便于样式区分
        self.record_btn.setObjectName("record_btn")
        self.stop_btn.setObjectName("stop_btn")
        self.about_dy_btn.setObjectName("about_dy_btn")
        # 未开始录制时禁止点击 Stop
        self.stop_btn.setEnabled(False)

        # 事件连接：点击 Record 进入选中（高亮绿），点击 Stop 取消
        self.record_btn.clicked.connect(self._on_record_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.about_dy_btn.clicked.connect(self._on_about_dy_clicked)
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
        btn_layout.addWidget(self.about_dy_btn)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(btn_layout)
        layout.addWidget(h_frame)
        layout.addWidget(self._create_solid_graph(), alignment=Qt.AlignCenter)
        self.setLayout(layout)

        self.set_widget_style()

    def set_widget_style(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: rgb(70, 70, 70);
                color: rgb(255, 255, 255);
                border: none;
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
        container.setStyleSheet("background-color: rgb(25, 25, 25);")

        step_path = DEFAULT_DIR + "ui/R87-Y160M.stp"
        show_solid_window = ShowSolidWindow(step_path)
        solid_widget = show_solid_window.get_widget()
        solid_widget.setMinimumSize(550, 350)
        solid_widget.setMaximumSize(700, 410)
        
        # 创建图片标签
        # solid_graph = QLabel()
        # # solid_graph.setPixmap(QPixmap(DEFAULT_DIR + "ui/ui_pic/solid_graph.png"))
        # solid_graph.setPixmap(QPixmap(DEFAULT_DIR + "ui/ui_pic/sequence_pic/dianji.png"))
        # solid_graph.setMaximumSize(700, 410)
        # solid_graph.setScaledContents(True)
        # solid_graph.setAlignment(Qt.AlignCenter)

        scatter_plot = QLabel()
        scatter_plot.setPixmap(QPixmap(DEFAULT_DIR + "ui/ui_pic/sequence_pic/scatter_plot.png"))
        scatter_plot.setMaximumSize(700, 410)
        scatter_plot.setScaledContents(True)
        scatter_plot.setAlignment(Qt.AlignCenter)

        # 将图片放入容器布局
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(solid_widget, 1)  # 添加拉伸因子
        layout.addWidget(scatter_plot, 1)   # 添加拉伸因子
        
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

    @staticmethod
    def _on_about_dy_clicked():
        browser = QDesktopServices()
        browser.openUrl(QUrl("https://suzhoudongyuan.com/"))


if __name__ == "__main__":

    import sys
    sys.path.append("..")
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    window = StartRecordWidget()
    window.show()
    app.exec_()

    