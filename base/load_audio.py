import os

import numpy as np
import librosa

from consts import error_code


def get_audio_files_and_labels(signal_path, sr=None, with_labels=-1, **kwargs):
    """
    Function to retrieve audio files and their corresponding labels from a directory.

    Args:
    - signal_dir (str): Directory containing audio files.
    - sr (int or None): Sampling rate for audio files. If None, uses default sampling rate.
    - with_labels (int): Label to assign to the audio files. Default is -1.

    Returns:
    - audio_signals (list): List containing audio signals loaded from files.
    - audio_file_names (list): List containing names of audio files.
    - fs (list): List containing sampling rates of audio files.
    - labels (list): List containing labels assigned to audio files.

    """
    audio_signals = []
    audio_file_names = []
    fs = []
    labels = []
    signal_path = signal_path.replace("\\", "/")
    if os.path.isfile(signal_path):
        signal_files = [os.path.basename(signal_path)]
        signal_path = os.path.dirname(signal_path)
    elif os.path.isdir(signal_path):
        signal_files = os.listdir(signal_path)
    else:
        return error_code.INVALID_PATH, "invalid path [%s]" % signal_path

    max_size = kwargs.get("max_size", len(signal_files))
    replace = True if max_size > len(signal_files) else False
    selected_files = np.random.choice(signal_files, size=max_size, replace=replace)
    for signal_file in selected_files:
        single_audio_path = os.path.join(signal_path, signal_file).replace("\\", "/")

        try:
            y, sr = librosa.load(single_audio_path, sr=sr, mono=False)
            y = y.T
            if fs and sr != fs[-1]:
                pass
            else:
                audio_signals.append(y)
                audio_file_names.append(signal_file)
                labels.append(with_labels)
                fs.append(sr)
        except Exception as e:
            print("something wrong")

    return error_code.OK, (audio_signals, audio_file_names, fs, labels)
