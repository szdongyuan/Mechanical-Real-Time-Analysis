import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QButtonGroup

from consts.running_consts import DEFAULT_DIR

class NavigationBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.created_buttons = []
        self.is_hide_flag = False
        self.section_labels = []
        self._main_layout = None
        
        # 互斥按钮组
        self._nav_btn_group = QButtonGroup(self)
        self._nav_btn_group.setExclusive(True)
        
        # 折叠按钮
        self.swap_size_btn = QPushButton("<<")
        self.swap_size_btn.setFixedHeight(25)
        self.swap_size_btn.clicked.connect(self.on_clicked_swap_size_btn)
        
        # 通道检查控件
        self.channel_check = ChannelCheck(self)
        self.channel_check.create_check_label(4)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        
        self.initUI()

    def initUI(self):
        # 设置背景色
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.setFixedWidth(250)
        
        # 按钮样式
        self.swap_size_btn.setStyleSheet("border:none; color:rgb(204,204,204);font-size: 14px;")
        
        # 构建内容布局
        self.content_layout.setContentsMargins(0, 10, 0, 0)
        self.content_layout.setSpacing(10)
        
        # 添加导航项
        self.add_navigation_items()
        
        self.content_layout.addStretch()
        self.content_widget.setLayout(self.content_layout)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 0, 10, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.swap_size_btn, 0, Qt.AlignRight)
        main_layout.addWidget(self.content_widget, 1)
        main_layout.addStretch()
        
        self._main_layout = main_layout
        self.setLayout(main_layout)

    def add_navigation_items(self):  
        """添加导航项"""
        # 功能模块标题
        self.add_section_label("功能模块")
        
        # 功能按钮
        entries = [
            (" 实时监测", DEFAULT_DIR + "ui/ui_pic/sequence_pic/shishijiance.png"),
            (" 历史数据", DEFAULT_DIR + "ui/ui_pic/sequence_pic/data.png"),
            (" 报警管理", DEFAULT_DIR + "ui/ui_pic/sequence_pic/jinggao.png"),
            (" 设备列表", DEFAULT_DIR + "ui/ui_pic/sequence_pic/shebei.png"),
            (" 用户设置", DEFAULT_DIR + "ui/ui_pic/sequence_pic/yonghu.png"),
        ]
        
        for text, icon_path in entries:
            btn = self.add_navigation_button(text, icon_path)
            self.created_buttons.append(btn)
        
        # 默认选中第一项
        if self.created_buttons:
            self.created_buttons[0].setChecked(True)
        
        # 传感器状态标题
        self.add_section_label("传感器状态")
        
        # 通道检查控件
        self.content_layout.addWidget(self.channel_check)

    def add_section_label(self, text: str):
        """添加节标题标签"""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: rgb(255, 255, 255);
                font-size: 14px;
                padding: 5px 0px;
                background-color: transparent;
            }
        """)
        self.content_layout.addWidget(label)
        self.section_labels.append(label)
    
    def add_navigation_button(self, text: str, icon_path: str = None) -> QPushButton:
        """添加导航按钮"""
        btn = QPushButton(text)
        btn.setFixedHeight(40)
        btn.setMinimumWidth(40)
        btn.setCheckable(True)
        
        if icon_path:
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(34, 34))
        
        # 选中态颜色
        btn.setStyleSheet(
            "QPushButton { border:none; color:rgb(255,255,255); text-align:left; padding-left:8px; background-color:rgb(55,55,55); font-size: 15px; border-radius: 5px;}"
            "QPushButton:checked { background-color: rgb(24, 144, 255); }"
        )
        
        self._nav_btn_group.addButton(btn)
        self.content_layout.addWidget(btn)
        
        return btn

    def on_clicked_swap_size_btn(self):
        """折叠/展开按钮点击事件"""
        if self.is_hide_flag:
            # 展开
            self._set_collapsed(False)
            self.swap_size_btn.setText("<<")
            self.setFixedWidth(250)
            self.is_hide_flag = False
        else:
            # 折叠
            self._set_collapsed(True)
            self.swap_size_btn.setText(">>")
            # 预留给图标的宽度，类似 VS Code 侧边栏
            self.setFixedWidth(60)
            self.is_hide_flag = True

    def _set_collapsed(self, collapsed: bool):
        """
        切换折叠 / 展开样式：
        - 折叠：只显示图标，隐藏标题和通道状态区域
        - 展开：显示文字、标题和通道状态
        """
        # 标题标签与通道检查区
        for label in self.section_labels:
            label.setVisible(not collapsed)
        self.channel_check.setVisible(not collapsed)

        # 导航按钮文本与样式
        for btn in self.created_buttons:
            if collapsed:
                # 记录原始文本
                if not hasattr(btn, "_full_text"):
                    btn._full_text = btn.text()
                btn.setText("")
                # 居中显示图标，类似 VS Code 左侧栏
                btn.setStyleSheet(
                    "QPushButton { border:none; color:rgb(255,255,255); border-radius: 5px;"
                    "text-align:center; background-color:rgb(55,55,55); font-size: 15px;}"
                    "QPushButton:checked { background-color: rgb(24, 144, 255); }"
                )
                btn.setIconSize(QSize(24, 24))
            else:
                # 恢复文本
                if hasattr(btn, "_full_text"):
                    btn.setText(btn._full_text)
                btn.setStyleSheet(
                    "QPushButton { border:none; color:rgb(255,255,255); text-align:left; border-radius: 5px;"
                    "padding-left:8px; background-color:rgb(55,55,55); font-size: 15px;}"
                    "QPushButton:checked { background-color: rgb(24, 144, 255); }"
                )
                btn.setIconSize(QSize(34, 34))


class ChannelCheck(QWidget):

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.channels:int = 0

        self.check_result_labels = list()
        
        # 设置背景色和最小高度，确保在深色导航栏中可见
        self.setStyleSheet("color: rgb(255, 255, 255); font-size: 15px;")

    def create_check_label(self, channel:int):
        # 如果已经存在布局，先移除旧布局，避免叠加
        if self.layout() is not None:
            old_layout = self.layout()
            QWidget().setLayout(old_layout)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.check_result_labels.clear()
        sensor_type = ["声纹传感器", "振动传感器"]
        for i in range(channel):
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"通道{i + 1}： {sensor_type[int(i<2)]}"))
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