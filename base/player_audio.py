import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from base.sound_device_manager import sd
from base.log_manager import LogManager


logger = LogManager.set_log_handler("core")

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
        # 标准化数据类型与形状：float32，二维 (frames, channels)
        audio_np = np.asarray(audio_data, dtype=np.float32)
        if audio_np.ndim == 1:
            audio_np = audio_np.reshape(-1, 1)
        elif audio_np.ndim != 2:
            raise ValueError("不支持的音频格式：期望 1D 或 2D 数组")

        self.audio_data = audio_np  # 原始数据（规范化后）
        self._play_view = audio_np  # 可能根据设备通道能力调整后的视图
        self.sample_rate = sample_rate
        self.stream = None
        self.current_frame = 0
        self.total_frames = int(self._play_view.shape[0])
        self.is_paused = False
        self.is_playing = False

    @staticmethod
    def _downmix_to_stereo(data: np.ndarray) -> np.ndarray:
        """
        将多通道数据降混为立体声：
        - 左声道：偶数索引通道均值 (0,2,4,...)
        - 右声道：奇数索引通道均值 (1,3,5,...；若不存在则与左声道相同)
        返回 (frames, 2) 的 float32 数组
        """
        if data.ndim != 2:
            raise ValueError("downmix 期望二维数组")
        # 左声道 = 偶数索引通道的均值
        # 选取数据的偶数通道（第0、2、4...列），用于左声道混音
        left_group = data[:, 0::2]
        left = left_group.mean(axis=1) if left_group.shape[1] > 0 else np.zeros(data.shape[0], dtype=np.float32)
        # 右声道 = 奇数索引通道的均值；若无奇数通道，则复制左声道
        right_group = data[:, 1::2]
        if right_group.shape[1] > 0:
            right = right_group.mean(axis=1)
        else:
            right = left
        stereo = np.stack((left.astype(np.float32), right.astype(np.float32)), axis=1)
        return stereo

    def start(self):
        """开始播放"""
        if self.is_playing:
            return

        try:
            # 基于设备能力调整通道数（必要时降混）
            try:
                out_id = sd.default.device[1]
                dev_info = sd.query_devices(out_id)
                max_out = int(dev_info.get("max_output_channels", 2))
            except Exception:
                max_out = 2
            desired = int(self.audio_data.shape[1])
            max_out = max(1, max_out)
            if desired > max_out:
                if max_out >= 2:
                    # 超出设备通道能力时，优先降混为立体声
                    self._play_view = self._downmix_to_stereo(self.audio_data)
                else:
                    # 仅支持单声道，混为单声道
                    self._play_view = np.mean(self.audio_data, axis=1, keepdims=True).astype(np.float32)
            else:
                self._play_view = self.audio_data
            # 若设备支持 >=2 声道，但 _play_view 超过 max_out（极端情况），仍限制在设备能力内
            play_channels = min(int(self._play_view.shape[1]), max_out)
            if self._play_view.shape[1] != play_channels:
                # 退化为前 play_channels 个通道（极端设备限制）
                self._play_view = self._play_view[:, :play_channels]
            self.total_frames = int(self._play_view.shape[0])

            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=play_channels,
                dtype="float32",
                blocksize=1024,
                callback=self._callback,
            )
            self.stream.start()
            self.is_playing = True
            self.is_paused = False
        except Exception as e:
            logger.error(f"播放失败: {e}")

    def _callback(self, outdata, frames, time_info, status):
        """音频回调函数"""
        if status:
            logger.error(f"音频输出错误: {status}")

        if self.is_paused or self.current_frame >= self.total_frames:
            outdata[:] = 0
            return

        end_frame = self.current_frame + frames
        data = self._play_view
        if end_frame > self.total_frames:
            remaining = self.total_frames - self.current_frame
            if remaining > 0:
                outdata[:remaining, :] = data[self.current_frame : self.current_frame + remaining, :]
            if end_frame - self.total_frames > 0:
                outdata[remaining:, :] = 0
            self.current_frame = self.total_frames
        else:
            outdata[:] = data[self.current_frame : end_frame, :]
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
