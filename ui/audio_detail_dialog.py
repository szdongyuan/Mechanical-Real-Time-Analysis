"""
音频详情弹窗 - 显示三个音频播放器
- 原始音频
- 声源分离音频1
- 声源分离音频2
"""

import os
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QWidget

from my_controls.audio_player_widget import AudioPlayerWidget


class AudioDetailDialog(QDialog):
    """
    音频详情弹窗
    - 显示原始音频和两个声源分离后的音频
    - 每个音频都可以独立播放
    """

    def __init__(self, original_audio_path: str,
                 separated_audio1_path: str = None,
                 separated_audio2_path: str = None,
                 record_time: str = "",
                 parent=None):
        super().__init__(parent)

        self._original_path = original_audio_path
        self._separated1_path = separated_audio1_path
        self._separated2_path = separated_audio2_path
        self._record_time = record_time

        self._players = []  # 保存所有播放器引用

        self._init_ui()
        self._load_audio_files()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("音频详情")
        self.setMinimumSize(500, 450)
        self.resize(550, 500)
        self.setModal(True)

        # 深灰色主题（与主界面风格统一）
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #404040;
                color: #e0e0e0;
                border: 1px solid #505050;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #606060;
            }
            QPushButton:pressed {
                background-color: #353535;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("📊 声源分离音频")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #464646;")
        main_layout.addWidget(line)

        # 滚动区域（用于容纳三个播放器）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2d2d2d;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #2d2d2d;
            }
            QScrollBar:vertical {
                background-color: #353535;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #2d2d2d;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        scroll_layout.setSpacing(12)

        # 原始音频播放器
        self._original_player = AudioPlayerWidget("🔊 包装机原始混合音频")
        scroll_layout.addWidget(self._original_player)
        self._players.append(self._original_player)

        # 声源分离音频1
        self._separated1_player = AudioPlayerWidget("⚙️ 声源 1：机械手和拨烟杆")
        scroll_layout.addWidget(self._separated1_player)
        self._players.append(self._separated1_player)

        # 声源分离音频2
        self._separated2_player = AudioPlayerWidget("⚙️ 声源 2：叠层板")
        scroll_layout.addWidget(self._separated2_player)
        self._players.append(self._separated2_player)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # 底部按钮样式（统一样式：默认灰色，点击时蓝色）
        btn_style = """
            QPushButton {
                background-color: #404040;
                color: #e0e0e0;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #1890ff;
                color: #ffffff;
            }
        """

        # 底部按钮（靠右对齐，与声源2右边界一致）
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 15, 10, 0)  # 右边距10与滚动区域一致
        bottom_layout.addStretch()  # 左侧弹性空间，让按钮靠右

        stop_all_btn = QPushButton("全部停止")
        stop_all_btn.setFont(QFont("Microsoft YaHei", 11))
        stop_all_btn.setStyleSheet(btn_style)
        stop_all_btn.clicked.connect(self._stop_all)
        bottom_layout.addWidget(stop_all_btn)

        close_btn = QPushButton("关闭")
        close_btn.setFont(QFont("Microsoft YaHei", 11))
        close_btn.setStyleSheet(btn_style)
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)

        main_layout.addLayout(bottom_layout)

    def _load_audio_files(self):
        """加载音频文件"""
        # 加载原始音频
        if self._original_path:
            self._original_player.set_audio_file(self._original_path)

        # 加载分离音频1
        if self._separated1_path:
            self._separated1_player.set_audio_file(self._separated1_path)
        else:
            # 尝试自动推断路径：xxx.wav -> xxx_source1.wav
            inferred_path = self._infer_separated_path(self._original_path, "_source1")
            if inferred_path:
                self._separated1_player.set_audio_file(inferred_path)

        # 加载分离音频2
        if self._separated2_path:
            self._separated2_player.set_audio_file(self._separated2_path)
        else:
            # 尝试自动推断路径：xxx.wav -> xxx_source2.wav
            inferred_path = self._infer_separated_path(self._original_path, "_source2")
            if inferred_path:
                self._separated2_player.set_audio_file(inferred_path)

    def _infer_separated_path(self, original_path: str, suffix: str) -> str:
        """
        根据原始音频路径推断分离音频路径
        例如：xxx.wav -> xxx_good_motor.wav
        """
        if not original_path:
            return None

        base, ext = os.path.splitext(original_path)
        inferred = f"{base}{suffix}{ext}"

        if os.path.exists(inferred):
            return inferred
        return None

    def _stop_all(self):
        """停止所有播放"""
        for player in self._players:
            player.stop()

    def closeEvent(self, event):
        """关闭时停止所有播放"""
        self._stop_all()
        super().closeEvent(event)


def show_audio_detail(original_path: str,
                      separated1_path: str = None,
                      separated2_path: str = None,
                      record_time: str = "",
                      parent=None):
    """
    便捷函数：显示音频详情弹窗

    参数:
        original_path: 原始音频文件路径
        separated1_path: 分离音频1路径（可选，不传则自动推断）
        separated2_path: 分离音频2路径（可选，不传则自动推断）
        record_time: 录制时间字符串（用于显示）
        parent: 父窗口
    """
    dialog = AudioDetailDialog(
        original_audio_path=original_path,
        separated_audio1_path=separated1_path,
        separated_audio2_path=separated2_path,
        record_time=record_time,
        parent=parent
    )
    dialog.exec_()

