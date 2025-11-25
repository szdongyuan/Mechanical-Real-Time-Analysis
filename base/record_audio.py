import time
import threading

from PyQt5.QtCore import QThread

from base.data_struct.data_deal_struct import DataDealStruct
from base.sound_device_manager import sd
from base.log_manager import LogManager


logger = LogManager.set_log_handler("core")

class AudioDataManager(QThread):
    # signal_for_update = pyqtSignal(object)  # 使用 object 类型传递 ndarray

    def __init__(self):
        super().__init__()
        self.data_struct = DataDealStruct()
        # self.stream = None
        self.sampling_rate = 44100
        self.channels = None
        self.selected_channels = None
        self.ctx = None
        self.lock = threading.Lock()
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.emit_audio_data)

    def start_recording(self, ctx, selected_channels, sampling_rate, channels):
        self.ctx = ctx
        self.selected_channels = selected_channels
        self.sampling_rate = sampling_rate
        self.channels = channels
        # self.audio_data = [[] for _ in range(len(selected_channels))]
        print(f"start_recording: {self.ctx}, {self.selected_channels}, {self.sampling_rate}, {self.channels}")

        def audio_callback(in_data, frames, t, status):
            # 开始一轮写入：epoch 置为奇数（写入中），并限制不超过 10000
            try:
                if self.data_struct.epoch >= 10000:
                    self.data_struct.epoch = 1
                else:
                    self.data_struct.epoch += 1
            except Exception as e:
                logger.error(f"audio_callback failed: {e}")
            if status:
                print(f"Audio error: {status}")
                print(time.strftime("%Y%m%d_%H%M%S", time.localtime()))
            # 更新音频数据
            # print(frames)
            data = in_data.T

            for i, ch in enumerate(self.selected_channels):
                # 获取当前通道的环形缓冲与长度
                ring_buffer = self.data_struct.audio_data_arr[i]
                buffer_len = int(ring_buffer.shape[0])
                if buffer_len <= 0:
                    continue
                # 读取并规范写入位置（确保落在 [0, buffer_len)）
                write_idx = int(self.data_struct.write_index[i]) % buffer_len

                # 将新数据按两段写入（末尾段 + 开头段）
                tail_space = buffer_len - write_idx
                if frames <= tail_space:
                    # 全部写入尾段
                    ring_buffer[write_idx:write_idx + frames] = data[ch]
                    write_idx = (write_idx + frames) % buffer_len
                else:
                    # 分段写入
                    first_len = tail_space
                    second_len = frames - first_len
                    ring_buffer[write_idx:buffer_len] = data[ch][:first_len]
                    ring_buffer[0:second_len] = data[ch][first_len:]
                    write_idx = second_len % buffer_len

                # 回写更新后的写入位置
                self.data_struct.write_index[i] = write_idx
            
            # 本轮写入完成：epoch 置为偶数（稳定态），并限制不超过 10000
            try:
                if self.data_struct.epoch >= 10000:
                    self.data_struct.epoch = 0
                else:
                    self.data_struct.epoch += 1
            except Exception as e:
                logger.error(f"audio_callback failed: {e}")

        try:
            self.ctx.start_stream(
                sd.InputStream,
                self.sampling_rate,
                self.channels,
                self.ctx.input_dtype,
                audio_callback,
                False,
                blocksize=2048,
            )
            # self.timer.start(200)
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            print(f"Failed to start audio stream: {e}")

    def stop_recording(self):
        if self.ctx and self.ctx.stream.active:
            self.ctx.stream.stop()
            self.ctx = None
        self.quit()
        self.wait()
        # self.timer.stop()

    # def emit_audio_data(self):
    #     if self.audio_data[0]:
    #         self.signal_for_update.emit(self.audio_data)
