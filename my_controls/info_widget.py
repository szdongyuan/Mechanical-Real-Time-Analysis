from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QPushButton, QHBoxLayout, QLabel
from my_controls.info_message_widget import Info_Message_Widget
from consts.running_consts import DEFAULT_DIR


class MessageQueueWidget(QWidget):
    """
    系统通知窗口
    - 分为三个部分
    - 第一部分：系统通知汇总（标题行，始终显示）
    - 第二部分：各等级统计标签（严重 / 警告 / 通知）
    - 第三部分：通知明细列表（消息队列滚动区域）
    """

    height_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("系统通知")
        # 作为侧边栏子控件使用时，不需要强制最小高度，否则会影响折叠后的高度
        # 这里只限制宽度，具体高度由外层布局和折叠/展开状态共同决定
        self.setMinimumWidth(220)
        self.resize(320, 400)
        
        # 图标路径
        self._up_arrow_path = DEFAULT_DIR + "ui/ui_pic/sequence_pic/uparrow.png"
        self._down_arrow_path = DEFAULT_DIR + "ui/ui_pic/sequence_pic/downarrow.png"
        
        # 折叠状态
        self._is_expanded = True

        # 计数
        self._total_count = 0          # 系统通知总数
        self._severe_count = 0         # 严重
        self._warning_count = 0        # 警告
        self._notice_count = 0         # 通知（提示/info）
        
        self._init_ui()
        # 初始化计数显示
        self._refresh_counters()
    
    def _init_ui(self):
        """初始化 UI"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # ========== 第一部分：标题行（始终显示）==========
        self._init_first_row(main_layout)
        
        # ========== 分隔线（展开时显示）==========
        self._separator_frame = QFrame()
        self._separator_frame.setFrameShape(QFrame.HLine)
        self._separator_frame.setFixedHeight(1)
        self._separator_frame.setStyleSheet("background-color: rgb(100, 100, 100); border: none;")
        main_layout.addWidget(self._separator_frame)
        
        # ========== 可展开内容容器（第二部分 + 第三部分）==========
        self._expandable_content = QWidget()
        expandable_layout = QVBoxLayout()
        expandable_layout.setContentsMargins(0, 0, 0, 0)
        expandable_layout.setSpacing(8)
        
        # 第二部分：可折叠内容区域
        self._init_second_section(expandable_layout)
        
        # 分隔线（第二部分和第三部分之间）
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFixedHeight(1)
        separator2.setStyleSheet("background-color: rgb(100, 100, 100); border: none;")
        expandable_layout.addWidget(separator2)
        
        # 第三部分：消息队列滚动区域
        self._init_third_section(expandable_layout)
        
        self._expandable_content.setLayout(expandable_layout)
        main_layout.addWidget(self._expandable_content, 1)
        
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # 设置样式
        self.setStyleSheet("""
            MessageQueueWidget {
                background-color: rgb(60, 60, 60);
                border-radius: 6px;
            }
        """)
    
    def _init_first_row(self, parent_layout):
        """初始化第一部分（标题行，与HealthEvaluateWidget的第一行保持一致）"""
        # 创建第一行容器（与 health_evaluate_widget 中的标签容器一致）
        first_row_container = QWidget()
        first_row_container.setStyleSheet("""
            QWidget {
                background-color: rgb(45, 45, 45);
                border: none;
                border-radius: 6px;
            }
        """)
        first_row_container.setMinimumHeight(36)
        
        # 第一行内部布局
        container_layout = QHBoxLayout(first_row_container)
        container_layout.setContentsMargins(12, 8, 12, 8)
        container_layout.setSpacing(8)
        
        # 左侧标签（名称）
        self._name_label = QLabel("系统通知")
        self._name_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: rgb(200, 200, 200);
                border: none;
                font-size: 14px;
            }
        """)
        
        # 右侧标签（值）
        self._value_label = QLabel("0")
        self._value_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: rgb(255, 255, 255);
                border: none;
                font-size: 14px;
            }
        """)
        self._value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # 添加标签到容器
        container_layout.addWidget(self._name_label)
        container_layout.addStretch()
        container_layout.addWidget(self._value_label)
        
        # 折叠/展开按钮
        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.setIcon(QIcon(self._up_arrow_path))
        self._toggle_btn.setIconSize(QSize(16, 16))
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: rgb(55, 55, 55);
                border-radius: 4px;
            }
        """)
        self._toggle_btn.clicked.connect(self._toggle_expand)
        
        # 第一行布局（与 health_evaluate_widget 的 first_row_layout 一致）
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(8)
        first_row_layout.addWidget(first_row_container, 1)  # 第一行容器占据剩余空间
        first_row_layout.addStretch()
        first_row_layout.addWidget(self._toggle_btn)
        
        parent_layout.addLayout(first_row_layout)
    
    def _init_second_section(self, parent_layout):
        """初始化第二部分（严重 / 警告 / 通知 统计标签）"""
        # 创建第二部分容器
        second_section_container = QWidget()
        second_section_layout = QVBoxLayout()
        second_section_layout.setContentsMargins(0, 0, 0, 0)
        second_section_layout.setSpacing(8)

        # 配色
        severe_color = "rgb(255, 77, 79)"   # 红色
        warning_color = "rgb(250, 173, 20)" # 黄色
        notice_color = "rgb(255, 255, 255)" # 白色

        def create_row(title: str, value_label_ref_name: str, color: str):
            """创建一行统计标签，并把 value_label 保存到成员变量"""
            row_container = QWidget()
            row_container.setStyleSheet(f"""
                QWidget {{
                    background-color: rgb(45, 45, 45);
                    border: none;
                    border-radius: 6px;
                }}
            """)
            row_container.setMinimumHeight(36)

            row_layout = QHBoxLayout(row_container)
            row_layout.setContentsMargins(12, 8, 12, 8)
            row_layout.setSpacing(8)

            name_label = QLabel(title)
            name_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {color};
                    border: none;
                    font-size: 14px;
                }}
            """)

            value_label = QLabel("0")
            value_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {color};
                    border: none;
                    font-size: 14px;
                }}
            """)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row_layout.addWidget(name_label)
            row_layout.addStretch()
            row_layout.addWidget(value_label)

            # 保存引用，便于后续更新数值
            setattr(self, value_label_ref_name, value_label)

            second_section_layout.addWidget(row_container)

        # 第一行：严重（红色）
        create_row("严重", "_severe_value_label", severe_color)
        # 第二行：警告（黄色）
        create_row("警告", "_warning_value_label", warning_color)
        # 第三行：通知（白色，保持不变）
        create_row("通知", "_notice_value_label", notice_color)

        second_section_container.setLayout(second_section_layout)
        parent_layout.addWidget(second_section_container)
    
    def _init_third_section(self, parent_layout):
        """初始化第三部分（消息队列滚动区域）"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(200)
        
        # 设置滚动条样式
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgb(50, 50, 50);
            }
            QScrollBar:vertical {
                background-color: rgb(30, 30, 30);
                width: 8px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: rgb(80, 80, 80);
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgb(100, 100, 100);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # 创建容器 widget 用于放置消息
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignCenter)
        self.container_layout.setContentsMargins(0, 10, 0, 20)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch()  # 底部弹簧，确保消息从顶部开始排列
        self.container.setStyleSheet("background-color: transparent;")
        
        scroll_area.setWidget(self.container)
        parent_layout.addWidget(scroll_area)
    
    def _toggle_expand(self):
        """切换展开/折叠状态"""
        self._is_expanded = not self._is_expanded
        
        if self._is_expanded:
            # 展开：显示第二和第三部分
            self._toggle_btn.setIcon(QIcon(self._up_arrow_path))
            self._separator_frame.show()
            self._expandable_content.show()
        else:
            # 折叠：隐藏第二和第三部分
            self._toggle_btn.setIcon(QIcon(self._down_arrow_path))
            self._separator_frame.hide()
            self._expandable_content.hide()

        # 展开 / 折叠时刷新一次计数显示（颜色可能变化）
        self._refresh_counters()
        self.height_changed.emit()

    def is_expanded(self) -> bool:
        """当前是否处于展开态，供外层布局按需调整高度"""
        return self._is_expanded
    
    def set_first_row_labels(self, name: str = None, value: str = None):
        """设置第一行的标签文本
        
        Args:
            name: 左侧名称文本
            value: 右侧值文本
        """
        if name is not None:
            self._name_label.setText(str(name))
        if value is not None:
            self._value_label.setText(str(value))

    def _refresh_counters(self):
        """刷新各等级计数和系统通知汇总颜色"""
        # 文本
        self._value_label.setText(str(self._total_count))
        self._severe_value_label.setText(str(self._severe_count))
        self._warning_value_label.setText(str(self._warning_count))
        self._notice_value_label.setText(str(self._notice_count))

        # 刷新颜色
        self._refresh_color()
    
    def _refresh_color(self):
        """根据当前可见的消息窗口刷新系统通知汇总的颜色"""
        # 统计当前可见的各等级消息数量
        visible_severe = 0
        visible_warning = 0
        visible_notice = 0
        
        # 遍历容器中的所有消息窗口
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, Info_Message_Widget) and widget.isVisible():
                    severity = getattr(widget, "_severity", None)
                    if severity == "严重":
                        visible_severe += 1
                    elif severity == "警告":
                        visible_warning += 1
                    else:
                        visible_notice += 1
        
        # 系统通知计数颜色逻辑：有严重 -> 红色；否则有警告 -> 黄色；否则白色
        if visible_severe > 0:
            overall_color = "rgb(255, 77, 79)"
        elif visible_warning > 0:
            overall_color = "rgb(250, 173, 20)"
        else:
            overall_color = "rgb(255, 255, 255)"

        self._value_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {overall_color};
                border: none;
                font-size: 14px;
            }}
        """)
    
    def add_message(self, 
                    severity: str = "严重",
                    message: str = "") -> Info_Message_Widget:
        """
        添加一个消息窗口
        
        Args:
            severity: 严重程度（严重/警告/提示/info）
            package_name: 包装名
            message: 消息内容
            value: 数值
            
        Returns:
            创建的消息窗口实例
        """
        # 创建消息窗口
        msg_widget = Info_Message_Widget(
            severity=severity,
            message=message,
            parent=self.container
        )

        # 设置为普通 widget（不是独立窗口）
        msg_widget.setWindowFlags(Qt.Widget)
        # 固定大小很重要！避免按钮溢出
        msg_widget.setFixedSize(280, 170)

        # 插入到布局中（在弹簧之前）
        insert_index = self.container_layout.count() - 1
        self.container_layout.insertWidget(insert_index, msg_widget)

        # 根据严重级别更新计数
        if severity == "严重":
            self._severe_count += 1
        elif severity == "警告":
            self._warning_count += 1
        else:
            # 其余（如“提示”、“info”等）视为通知
            self._notice_count += 1
        self._total_count = self._severe_count + self._warning_count + self._notice_count
        self._refresh_counters()

        # 连接关闭信号，当窗口关闭时从布局和计数中移除
        msg_widget.destroyed.connect(lambda _, w=msg_widget: self._on_message_closed(w))

        return msg_widget
    
    def _on_message_closed(self, widget):
        """消息窗口关闭时的回调，仅更新颜色，不修改计数"""
        # 仅刷新颜色，不修改计数
        self._refresh_color()
    
    def clear_all_messages(self):
        """清除所有消息"""
        # 移除所有消息窗口（除了弹簧）
        while self.container_layout.count() > 1:
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重置计数
        self._total_count = 0
        self._severe_count = 0
        self._warning_count = 0
        self._notice_count = 0
        self._refresh_counters()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QPushButton, QHBoxLayout
    
    app = QApplication(sys.argv)
    
    # 创建队列窗口
    queue_window = MessageQueueWidget()
    
    # 创建测试按钮窗口
    test_window = QWidget()
    test_window.setWindowTitle("测试按钮")
    test_layout = QVBoxLayout(test_window)
    
    # 添加不同类型消息的按钮
    btn_severe = QPushButton("添加严重消息")
    btn_severe.clicked.connect(lambda: queue_window.add_message(
        severity="严重",
        message="振动传感器2异常",
    ))
    test_layout.addWidget(btn_severe)
    
    btn_warning = QPushButton("添加警告消息")
    btn_warning.clicked.connect(lambda: queue_window.add_message(
        severity="警告",
        message="温度超过阈值",
    ))
    test_layout.addWidget(btn_warning)
    
    btn_info = QPushButton("添加提示消息")
    btn_info.clicked.connect(lambda: queue_window.add_message(
        severity="提示",
        message="设备运行正常",
    ))
    test_layout.addWidget(btn_info)
    
    btn_clear = QPushButton("清除所有消息")
    btn_clear.clicked.connect(queue_window.clear_all_messages)
    test_layout.addWidget(btn_clear)
    
    queue_window.show()
    test_window.show()
    
    sys.exit(app.exec_())
