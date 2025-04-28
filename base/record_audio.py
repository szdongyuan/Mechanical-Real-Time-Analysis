import time
import sounddevice as sd

from PyQt5.QtCore import pyqtSignal, QThread

class AudioDataManager(QThread):
    signal_for_update = pyqtSignal(object)  # 使用 object 类型传递 ndarray

    def __init__(self):
        super().__init__()
        self.stream = None
        self.audio_data = None
        self.sampling_rate = 44100
        self.channels = 2

    def start_recording(self,
                       ctx,
                       selected_channels,
                       audio_data,
                       sampling_rate,
                       channels):
        self.ctx = ctx
        self.selected_channels = selected_channels
        self.audio_data = audio_data
        self.sampling_rate = sampling_rate
        self.channels = channels

        def audio_callback(in_data, frames, t, status):
            if status:
                print(f"Audio error: {status}")
                print(time.strftime("%Y%m%d_%H%M%S", time.localtime()))
            # # 更新音频数据
            data = in_data.T
            for i, ch in enumerate(selected_channels):
                self.audio_data[i, :-frames] = self.audio_data[i, frames:]
                self.audio_data[i, -frames:] = data[ch]

            self.signal_for_update.emit(self.audio_data)

        try:
            self.ctx.start_stream(sd.InputStream,
                                  self.sampling_rate,
                                  self.channels,
                                  self.ctx.input_dtype,
                                  audio_callback,
                                  False,
                                  blocksize=2048)
        except Exception as e:
            print(f"Failed to start audio stream: {e}")

    def stop_recording(self):
        if self.stream and self.stream.active:
            self.ctx.stream.stop()
            self.ctx = None
        self.quit()
        self.wait()
        