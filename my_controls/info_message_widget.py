from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel


class Info_Message_Widget(QWidget):
    """
    信息消息弹窗组件
    - 顶部：严重程度图标、级别文字、时间
    - 内容：包装名、警告内容、数值等
    - 底部：确认按钮（点击关闭窗口）
    """
    
    # 严重程度配置
    SEVERITY_COLORS = {
        "严重": "#ff4d4f",
        "警告": "#faad14",
        "提示": "#52c41a",
        "info": "#1890ff",
    }
    
    def __init__(self, 
                 severity: str = "严重",
                 package_name: str = "",
                 message: str = "",
                 value: str = "",
                 parent=None):
        super().__init__(parent)
        
        self._severity = severity
        self._package_name = package_name
        self._message = message
        self._value = value
        
        self.setAttribute(Qt.WA_DeleteOnClose)
        # self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        # self.setFixedSize(300, 180)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部栏
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)
        
        # 内容区域
        content_area = self._create_content_area()
        main_layout.addWidget(content_area)
        
        # 底部按钮容器（用于居中按钮，避免 alignment 导致的溢出问题）
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 8, 0, 8)
        confirm_btn = self._create_confirm_button()
        btn_layout.addStretch()
        btn_layout.addWidget(confirm_btn)
        btn_layout.addStretch()
        main_layout.addWidget(btn_container)
        
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(65, 65, 65);
                color: rgb(255, 255, 255);
                border-radius: 5px;
                
            }
            QPushButton {
                background-color: rgb(40, 40, 40);
                color: rgb(255, 255, 255);
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgb(24, 144, 255);
            }
        """)
    
    def _create_top_bar(self) -> QWidget:
        """创建顶部栏：图标 + 严重程度 + 时间"""
        top_bar = QWidget()
        top_bar.setFixedHeight(40)
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 严重程度图标和文字
        severity_color = self.SEVERITY_COLORS.get(self._severity, "#ff4d4f")
        
        # 图标（使用圆圈表示）
        icon_label = QLabel("⊗")  # 使用符号代替图标
        icon_label.setStyleSheet(f"color: {severity_color}; font-size: 20px")
        layout.addWidget(icon_label)
        
        # 严重程度文字
        severity_label = QLabel(self._severity)
        severity_label.setStyleSheet(f"color: {severity_color}; font-size: 14px")
        layout.addWidget(severity_label)
        
        layout.addStretch()
        
        # 时间
        current_time = QTime.currentTime().toString("hh:mm:ss")
        time_label = QLabel(current_time)
        time_label.setStyleSheet("color: rgb(160, 160, 160); font-size: 12px;")
        layout.addWidget(time_label)
        
        return top_bar
    
    def _create_content_area(self) -> QWidget:
        """创建内容区域：包装名 + 消息 + 数值"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)
        
        # 包装名标签（蓝色小字）
        if self._package_name:
            package_label = QLabel(self._package_name)
            package_label.setStyleSheet("color: rgb(24, 144, 255); font-size: 12px")
            layout.addWidget(package_label)
        
        # 主要消息（白色，较大字体）
        message_label = QLabel(self._message)
        message_label.setWordWrap(True)
        message_font = QFont()
        message_font.setPixelSize(15)
        message_label.setFont(message_font)
        message_label.setStyleSheet("color: rgb(255, 255, 255);")
        layout.addWidget(message_label)
        
        # 数值（白色，略小字体）
        if self._value:
            value_label = QLabel(self._value)
            value_label.setStyleSheet("color: rgb(220, 220, 220); font-size: 14px")
            layout.addWidget(value_label)
        
        layout.addStretch()
        
        return content
    
    def _create_confirm_button(self) -> QPushButton:
        """创建确认按钮"""
        confirm_btn = QPushButton("确  认")
        confirm_btn.setFixedSize(100, 36)
        confirm_btn.clicked.connect(self.close)
    
        return confirm_btn


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 示例：严重警告
    widget = Info_Message_Widget(
        severity="严重",
        package_name="包装名：AI密度",
        message="振动传感器2异常",
        value="3.8mm/s"
    )
    widget.show()
    
    sys.exit(app.exec_())