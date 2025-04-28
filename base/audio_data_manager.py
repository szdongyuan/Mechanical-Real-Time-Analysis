import time
import numpy as np

from scipy.io import wavfile


def save_audio_data(record_audio_data, sameple_rate, selected_channels, record_audio_time):
    print("save_audio_data")
    channels = len(selected_channels)
    file_name = "D:/gqgit/new_project/audio/record/" + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + str(sameple_rate) + str(channels) + ".wav"
    deta = record_audio_data.copy().T.astype(np.float32)
    wavfile.write(file_name, sameple_rate, deta)