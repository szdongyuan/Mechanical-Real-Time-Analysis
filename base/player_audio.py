import sounddevice as sd
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread


class AudioPlayer(QObject):
    playback_finished = pyqtSignal()

    def __init__(self, audio_data, sample_rate=44100):
        """
        初始化播放器

        参数:
            audio_data (np.ndarray): 要播放的音频数据，形状为 (n_samples,) 或 (n_samples, n_channels)
            sample_rate (int): 采样率
        """
        super().__init__()
        self.audio_data = audio_data
        self.sample_rate = sample_rate
        self.stream = None
        self.current_frame = 0
        self.total_frames = audio_data.shape[0]
        self.is_paused = False
        self.is_playing = False

    def start(self):
        """开始播放"""
        if self.is_playing:
            return

        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self._get_channels(),
                dtype=self.audio_data.dtype,
                blocksize=1024,
                callback=self._callback,
            )
            self.stream.start()
            self.is_playing = True
            self.is_paused = False
        except Exception as e:
            print(f"播放失败: {e}")

    def _callback(self, outdata, frames, time_info, status):
        """音频回调函数"""
        if status:
            print(f"音频输出错误: {status}")

        if self.is_paused or self.current_frame >= self.total_frames:
            outdata[:] = 0
            return

        end_frame = self.current_frame + frames

        if end_frame > self.total_frames:
            pad_size = end_frame - self.total_frames
            real_data = self.audio_data[self.current_frame :]
            # 创建与 outdata 形状一致的零数组
            padding = np.zeros((pad_size, outdata.shape[1]), dtype=real_data.dtype)
            outdata[: self.total_frames - self.current_frame] = real_data
            outdata[self.total_frames - self.current_frame :] = padding
            self.current_frame = self.total_frames
        else:
            outdata[:] = self.audio_data[self.current_frame : end_frame]
            self.current_frame = end_frame

        if self.current_frame >= self.total_frames:
            self.stop()

    def stop(self):
        """停止播放"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.is_playing = False
        self.is_paused = False
        self.current_frame = 0
        self.playback_finished.emit()

    def pause(self):
        """暂停播放"""
        self.is_paused = not self.is_paused

    def is_active(self):
        """检查是否正在播放"""
        return self.is_playing and not self.is_paused

    def _get_channels(self):
        """自动识别通道数"""
        if len(self.audio_data.shape) == 1:
            return 1
        elif len(self.audio_data.shape) == 2:
            return self.audio_data.shape[1]
        else:
            raise ValueError("不支持的音频格式")
