from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel
from consts.running_consts import DEFAULT_DIR


class HealthEvaluateWidget(QWidget):
    """
    健康评估组件（可折叠）
    - 可以指定数量生成标签
    - 标签垂直排列
    - 可以修改每个标签的内容
    - 有折叠和展开两种状态
    - 折叠状态只显示第一行标签
    - 展开状态显示所有标签，使用Frame将第一行和其余行做区分
    """
    
    # 定义信号：当展开/折叠状态改变时发出
    height_changed = pyqtSignal()
    
    def __init__(self, label_count: int = 4, parent=None):
        super().__init__(parent)
        
        self._label_count = label_count
        self._is_expanded = True
        self._labels = []
        
        # 图标路径
        self._up_arrow_path = DEFAULT_DIR + "ui/ui_pic/sequence_pic/uparrow.png"
        self._down_arrow_path = DEFAULT_DIR + "ui/ui_pic/sequence_pic/downarrow.png"
        
        # 创建折叠/展开按钮
        self._toggle_btn = QPushButton()
        self._toggle_btn.setFixedSize(24, 24)
        self._toggle_btn.setIcon(QIcon(self._up_arrow_path))
        self._toggle_btn.setIconSize(QSize(16, 16))
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self._toggle_expand)
        
        # 分隔线（展开时显示）
        self._separator_frame = QFrame()
        self._separator_frame.setFrameShape(QFrame.HLine)
        self._separator_frame.setFixedHeight(1)
        self._separator_frame.setStyleSheet("background-color: rgb(100,100,100); border: none;")
        # self._separator_frame.hide()
        
        self._init_labels()
        self._init_ui()
    
    def _init_labels(self):
        """初始化标签列表"""
        self._labels.clear()
        for i in range(self._label_count):
            # 创建容器widget包含左右两个标签
            container = QWidget()
            container.setStyleSheet("""
                QWidget {
                    background-color: rgb(45, 45, 45);
                    border: none;
                    border-radius: 6px;
                }
            """)
            container.setMinimumHeight(36)
            
            # 创建水平布局
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(12, 8, 12, 8)
            h_layout.setSpacing(8)
            
            # 左侧标签（名称）
            name_label = QLabel(f"评估项 {i + 1}")
            name_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    color: rgb(200, 200, 200);
                    border: none;
                    font-size: 14px;
                }
            """)
            
            # 右侧标签（值）
            value_label = QLabel("0")
            value_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    color: rgb(255, 255, 255);
                    border: none;
                    font-size: 14px;
                }
            """)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # 添加到布局
            h_layout.addWidget(name_label)
            h_layout.addStretch()  # 中间空白区域
            h_layout.addWidget(value_label)
            
            # 存储容器和两个标签的引用
            container.name_label = name_label
            container.value_label = value_label
            
            self._labels.append(container)
    
    def _init_ui(self):
        """初始化UI布局"""
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 第一行：折叠按钮 + 第一个标签
        first_row_layout = QHBoxLayout()
        first_row_layout.setSpacing(8)
        if self._labels:
            first_row_layout.addWidget(self._labels[0], 1)  # 第一个标签占据剩余空间
        first_row_layout.addStretch()
        first_row_layout.addWidget(self._toggle_btn)
        
        main_layout.addLayout(first_row_layout)
        
        # 分隔线（展开时显示）
        main_layout.addWidget(self._separator_frame)
        
        # 其余标签容器（展开时显示）
        self._other_labels_widget = QWidget()
        self._other_labels_layout = QVBoxLayout()
        self._other_labels_layout.setContentsMargins(0, 0, 0, 0)
        self._other_labels_layout.setSpacing(8)
        
        # 添加其余标签
        for i in range(1, len(self._labels)):
            self._other_labels_layout.addWidget(self._labels[i])
        
        self._other_labels_widget.setLayout(self._other_labels_layout)
        
        main_layout.addWidget(self._other_labels_widget)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        
        # 设置样式
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
    
    def _toggle_expand(self):
        """切换展开/折叠状态"""
        self._is_expanded = not self._is_expanded
        
        if self._is_expanded:
            # 展开：显示其余标签和分隔线
            self._toggle_btn.setIcon(QIcon(self._up_arrow_path))
            self._separator_frame.show()
            self._other_labels_widget.show()
        else:
            # 折叠：隐藏其余标签和分隔线
            self._toggle_btn.setIcon(QIcon(self._down_arrow_path))
            self._separator_frame.hide()
            self._other_labels_widget.hide()
        
        # 发出高度变化信号
        self.height_changed.emit()
    
    def set_label_count(self, count: int):
        """设置标签数量（会重新创建所有标签）"""
        if count < 1:
            count = 1
        
        self._label_count = count
        self._init_labels()
        
        # 重新构建UI
        # 清除旧的其余标签布局
        while self._other_labels_layout.count():
            item = self._other_labels_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 更新第一个标签（在主布局中）
        if self._labels:
            # 移除旧的第一个标签
            first_row_layout = self.layout().itemAt(0).layout()
            for i in range(first_row_layout.count()):
                item = first_row_layout.itemAt(i)
                if item and item.widget() and isinstance(item.widget(), QLabel):
                    first_row_layout.removeWidget(item.widget())
                    item.widget().deleteLater()
            
            # 添加新的第一个标签
            first_row_layout.insertWidget(1, self._labels[0], 1)
        
        # 添加其余标签
        for i in range(1, len(self._labels)):
            self._other_labels_layout.addWidget(self._labels[i])
    
    def set_label_text(self, index: int, name: str = None, value: str = None):
        """设置指定索引标签的文本
        
        Args:
            index: 标签索引
            name: 左侧名称文本（可选）
            value: 右侧值文本（可选）
        """
        if 0 <= index < len(self._labels):
            container = self._labels[index]
            
            if name is not None:
                # 确保转换为字符串
                if isinstance(name, (int, float)):
                    name = str(name)
                container.name_label.setText(name)
            
            if value is not None:
                # 确保转换为字符串
                if isinstance(value, (int, float)):
                    value = str(value)
                container.value_label.setText(value)
    
    def get_label(self, index: int) -> QWidget:
        """获取指定索引的标签容器对象（用于直接操作）
        
        返回的容器有 name_label 和 value_label 两个属性
        """
        if 0 <= index < len(self._labels):
            return self._labels[index]
        return None
    
    def get_name_label(self, index: int) -> QLabel:
        """获取指定索引的名称标签"""
        if 0 <= index < len(self._labels):
            return self._labels[index].name_label
        return None
    
    def get_value_label(self, index: int) -> QLabel:
        """获取指定索引的值标签"""
        if 0 <= index < len(self._labels):
            return self._labels[index].value_label
        return None
    
    def set_value(self, index: int, value: str):
        """设置指定索引标签的右侧值
        
        Args:
            index: 标签索引
            value: 右侧值文本
        """
        if 0 <= index < len(self._labels):
            # 确保转换为字符串
            if isinstance(value, (int, float)):
                value = str(value)
            self._labels[index].value_label.setText(value)
    
    def set_name(self, index: int, name: str):
        """设置指定索引标签的左侧名称
        
        Args:
            index: 标签索引
            name: 左侧名称文本
        """
        if 0 <= index < len(self._labels):
            # 确保转换为字符串
            if isinstance(name, (int, float)):
                name = str(name)
            self._labels[index].name_label.setText(name)
    
    def expand(self):
        """展开"""
        self._is_expanded = False
        self._toggle_expand()
    
    def collapse(self):
        """折叠"""
        self._is_expanded = True
        self._toggle_expand()
    
    def is_expanded(self) -> bool:
        """返回当前是否展开"""
        return self._is_expanded


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = QWidget()
    window.setWindowTitle("HealthEvaluateWidget Demo")
    # window.setStyleSheet("background-color: rgb(30, 30, 30);")
    
    layout = QVBoxLayout(window)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(20)
    
    # 创建健康评估组件（4个标签）
    health_widget = HealthEvaluateWidget(label_count=4)
    health_widget.setMinimumWidth(250)
    
    # 设置标签内容
    health_widget.set_label_text(0, name="整体健康度", value="85.5")
    health_widget.set_label_text(1, name="振动评估", value="78.2")
    health_widget.set_label_text(2, name="声压评估", value="92.1")
    health_widget.set_label_text(3, name="温度评估", value="88.0")
    
    layout.addWidget(health_widget)
    layout.addStretch()
    
    window.resize(300, 500)
    window.show()
    # health_widget.show()

    
    sys.exit(app.exec_())

