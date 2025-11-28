"""
独立音频播放器控件 - 支持单个音频文件的播放控制
特点：
- 独立线程播放，不阻塞主进程
- 不影响主进程的录音功能
- 包含播放/暂停按钮和进度显示
"""

import os
import librosa
import numpy as np

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QSlider, QStyle
)

from base.player_audio import AudioPlayer
from consts.running_consts import DEFAULT_DIR


class AudioPlayerWidget(QWidget):
    """
    独立的音频播放器控件
    - 支持播放单个音频文件
    - 播放在独立线程中进行，不会阻塞主线程或影响录音
    """
    
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    
    def __init__(self, title: str = "音频", parent=None):
        super().__init__(parent)
        self._title = title
        self._audio_file_path = None
        self._wave_data = None
        self._player: AudioPlayer = None
        self._is_playing = False
        self._duration_seconds = 0.0
        self._sample_rate = 44100
        
        # 进度更新定时器
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(100)  # 100ms 更新一次
        self._progress_timer.timeout.connect(self._update_progress)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)
        
        # 标题行
        title_label = QLabel(self._title)
        title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        main_layout.addWidget(title_label)
        
        # 控制行：播放按钮 + 进度条 + 时间
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        # 播放/暂停按钮
        self._play_btn = QPushButton()
        self._play_btn.setFixedSize(36, 36)
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._play_btn.setStyleSheet("""
            QPushButton {
                background-color: #1890ff;
                border: none;
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """)
        self._play_btn.clicked.connect(self._on_play_clicked)
        control_layout.addWidget(self._play_btn)
        
        # 进度滑块
        self._progress_slider = QSlider(Qt.Horizontal)
        self._progress_slider.setRange(0, 1000)
        self._progress_slider.setValue(0)
        self._progress_slider.setEnabled(False)
        self._progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #3a3a3a;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1890ff;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #1890ff;
                border-radius: 3px;
            }
        """)
        self._progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self._progress_slider.sliderReleased.connect(self._on_slider_released)
        control_layout.addWidget(self._progress_slider, 1)
        
        # 时间标签
        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        self._time_label.setMinimumWidth(90)
        control_layout.addWidget(self._time_label)
        
        main_layout.addLayout(control_layout)
        
        # 文件名标签（隐藏，但保留用于内部状态）
        self._file_label = QLabel("")
        self._file_label.setVisible(False)
        
        # 整体样式
        self.setStyleSheet("""
            AudioPlayerWidget {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
            }
        """)
    
    def set_audio_file(self, file_path: str):
        """设置音频文件路径"""
        self._audio_file_path = file_path
        
        if file_path and os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            self._file_label.setText(file_name)
            self._file_label.setToolTip(file_path)
            self._play_btn.setEnabled(True)
            self._load_audio()
        else:
            self._file_label.setText("文件不存在")
            self._play_btn.setEnabled(False)
            self._wave_data = None
            self._duration_seconds = 0.0
            self._update_time_label(0, 0)
    
    def _load_audio(self):
        """加载音频数据"""
        try:
            wave_data, sr = librosa.load(
                self._audio_file_path, 
                sr=None,  # 保持原始采样率
                mono=False, 
                dtype=np.float32
            )
            self._sample_rate = sr
            
            # 转换为 (samples, channels) 格式
            if len(wave_data.shape) == 1:
                wave_data = wave_data.reshape(-1, 1)
            elif len(wave_data.shape) == 2 and wave_data.shape[0] < wave_data.shape[1]:
                # librosa 返回 (channels, samples)，需要转置
                wave_data = wave_data.T
            
            self._wave_data = wave_data
            self._duration_seconds = len(wave_data) / sr
            self._update_time_label(0, self._duration_seconds)
            self._progress_slider.setEnabled(True)
            
        except Exception as e:
            print(f"加载音频失败: {e}")
            self._file_label.setText(f"加载失败: {str(e)[:30]}")
            self._play_btn.setEnabled(False)
            self._wave_data = None
    
    def _on_play_clicked(self):
        """播放/暂停按钮点击"""
        if self._is_playing:
            self._stop_playback()
        else:
            self._start_playback()
    
    def _start_playback(self):
        """开始播放"""
        if self._wave_data is None:
            return
        
        # 停止之前的播放
        if self._player is not None:
            try:
                self._player.playback_finished.disconnect(self._on_playback_finished)
            except:
                pass
            self._player.stop()
        
        # 创建新的播放器
        self._player = AudioPlayer(self._wave_data, sample_rate=self._sample_rate)
        self._player.playback_finished.connect(self._on_playback_finished)
        self._player.start()
        
        self._is_playing = True
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self._progress_timer.start()
        self.playback_started.emit()
    
    def _stop_playback(self):
        """停止播放"""
        if self._player is not None:
            self._player.stop()
        
        self._is_playing = False
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._progress_timer.stop()
        self._progress_slider.setValue(0)
        self._update_time_label(0, self._duration_seconds)
        self.playback_stopped.emit()
    
    def _on_playback_finished(self):
        """播放完成回调"""
        self._is_playing = False
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._progress_timer.stop()
        self._progress_slider.setValue(0)
        self._update_time_label(0, self._duration_seconds)
        self.playback_stopped.emit()
    
    def _update_progress(self):
        """更新进度"""
        if self._player is None or not self._is_playing:
            return
        
        current_frame = self._player.current_frame
        total_frames = self._player.total_frames
        
        if total_frames > 0:
            progress = int((current_frame / total_frames) * 1000)
            self._progress_slider.setValue(progress)
            
            current_time = current_frame / self._sample_rate
            self._update_time_label(current_time, self._duration_seconds)
    
    def _update_time_label(self, current: float, total: float):
        """更新时间标签"""
        def format_time(seconds):
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        
        self._time_label.setText(f"{format_time(current)} / {format_time(total)}")
    
    def _on_slider_pressed(self):
        """滑块按下时暂停进度更新"""
        self._progress_timer.stop()
    
    def _on_slider_released(self):
        """滑块释放时跳转到指定位置（暂不支持seek，仅显示）"""
        if self._is_playing:
            self._progress_timer.start()
    
    def stop(self):
        """外部调用停止播放"""
        self._stop_playback()
    
    def is_playing(self) -> bool:
        """返回是否正在播放"""
        return self._is_playing
    
    def closeEvent(self, event):
        """关闭时停止播放"""
        self._stop_playback()
        super().closeEvent(event)

