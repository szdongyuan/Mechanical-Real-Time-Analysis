import numpy as np
import librosa
from scipy.signal import convolve2d


class CustomPipelines:

    @classmethod
    def fix_length(cls, signal, sr, **kwargs):
        seconds = kwargs.get("seconds")
        if not seconds:
            return signal

        target_len = int(seconds * sr)
        return librosa.util.fix_length(signal, size=target_len, mode='constant')

    @classmethod
    def vibration_guided_separation(cls, signal_dict, sr, **kwargs):
        mic_signal = signal_dict.get('mic')
        vib_signals = signal_dict.get('vib')
        if mic_signal is None or not vib_signals:
            raise ValueError("vibration_guided_separation 需要 {'mic':..., 'vib':...} 格式的输入")

        n_fft = kwargs.get("n_fft", 2048)
        hop_length = kwargs.get("hop_length", 512)
        center = kwargs.get("center", False)

        vib_stfts = [
            librosa.stft(y=vib, n_fft=n_fft, hop_length=hop_length, center=center)
            for vib in vib_signals
        ]
        vib_mags = [np.abs(stft) for stft in vib_stfts]

        strategy = kwargs.get("vib_combine_strategy", "first")

        if strategy == "first" or len(vib_mags) == 1:
            combined = vib_mags[0]
        elif strategy == "average":
            combined = np.mean(vib_mags, axis=0)
        elif strategy == "weighted_average":
            weights = kwargs.get("vib_weights")
            if weights is None or len(weights) != len(vib_mags):
                raise ValueError(f"vib_combine_strategy='weighted_average' 需要 'vib_weights' 列表")
            weights_arr = np.array(weights)[:, np.newaxis, np.newaxis]
            combined = np.sum(np.array(vib_mags) * weights_arr, axis=0)
        else:
            raise ValueError(f"未知的 vib_combine_strategy: {strategy}")

        mic_stft = librosa.stft(y=mic_signal, n_fft=n_fft, hop_length=hop_length, center=center)
        mic_mag, mic_phase = librosa.magphase(mic_stft)

        norm = combined / (np.max(combined) + 1e-8)
        mask_threshold = kwargs.get("mask_threshold", 0.1)
        mask = (norm > mask_threshold).astype(np.float32)

        kernel = np.ones((3, 3), dtype=np.float32) / 9.0
        mask_smooth = convolve2d(mask, kernel, mode='same', boundary='wrap')

        mask_floor = kwargs.get("mask_floor", 0.1)
        enhanced_mag = mic_mag * (mask_smooth + mask_floor)
        enhanced_stft = enhanced_mag * mic_phase

        return librosa.istft(enhanced_stft, hop_length=hop_length, n_fft=n_fft, center=center)

    @classmethod
    def custom_spectrogram(cls, signal, sr, **kwargs):
        extraction_kwargs = kwargs.get("extraction_kwargs", {})
        if 'center' not in extraction_kwargs:
            extraction_kwargs['center'] = False
        n_fft = extraction_kwargs.get("n_fft", 2048)
        hop_length = extraction_kwargs.get("hop_length", 512)

        spec_type = kwargs.get("spec_type", "log_power")
        norm_type = kwargs.get("norm_type", "sample_min_max")
        time_series_first = kwargs.get("time_series_first", True)

        stft = librosa.stft(y=signal, **extraction_kwargs)

        if spec_type == "linear_amplitude":
            spec = np.abs(stft)
        elif spec_type == "power":
            spec = np.abs(stft) ** 2
        elif spec_type == "log_power":
            mag2 = np.abs(stft) ** 2
            spec = 10.0 * np.log(mag2 + 1e-10)
        else:
            raise ValueError(f"未知的 spec_type: {spec_type}")

        if norm_type == "sample_min_max":
            s_min = np.min(spec)
            s_max = np.max(spec)
            spec = (spec - s_min) / (s_max - s_min + 1e-6)
            spec = np.clip(spec, 0.0, 1.0)
        elif norm_type == "none":
            pass
        else:
            raise ValueError(f"未知的 norm_type: {norm_type}")

        if time_series_first:
            spec = spec.T

        return spec.astype(np.float32)


    @classmethod
    def fusion_autoencoder_preprocess(cls, signal, sr, **kwargs):
        """
        Args:
        - signal: (N, C) NumPy array representing the raw audio signal.
        - sr: int, The sampling rate (e.g., 44100).
        - **kwargs: (Nested dictionary from YML)
            - channel_config: (dict) Defines which channels to use (vib_idxs, mic_idx).
            - fix_len_params: (dict) Parameters passed to the "fix_length" function.
            - separation_params: (dict) Parameters passed to the "vibration_guided_separation" function.
            - spec_params: (dict) Parameters passed to the "custom_spectrogram" function.

        Returns:
        - [vib_spec, mic_spec]: A list containing two spectrograms, each with shape (H, W, C).
        """
        channel_config = kwargs.get("channel_config", {})
        fix_len_params = kwargs.get("fix_len_params", {})
        separation_params = kwargs.get("separation_params", {})
        spec_params = kwargs.get("spec_params", {})
        num_channels = signal.shape[1]
        if num_channels == 4 and 'case4' in channel_config:
            vib_idxs, mic_idx = channel_config['case4']
        elif num_channels == 2 and 'case2' in channel_config:
            vib_idxs, mic_idx = channel_config['case2']
        else:
            vib_idxs = channel_config.get('vib_idxs', [0])
            mic_idx = channel_config.get('mic_idx', 1)
        if not isinstance(vib_idxs, (list, tuple)): vib_idxs = [vib_idxs]

        vib_fixed_list = [
            cls.fix_length(signal[:, idx], sr, **fix_len_params) for idx in vib_idxs
        ]
        mic_fixed = cls.fix_length(signal[:, mic_idx], sr, **fix_len_params)

        mic_separated = cls.vibration_guided_separation(
            {'mic': mic_fixed, 'vib': vib_fixed_list},
            sr,
            **separation_params
        )

        vib_specs = [
            cls.custom_spectrogram(vib_sig, sr, **spec_params)
            for vib_sig in vib_fixed_list
        ]
        mic_spec = cls.custom_spectrogram(
            mic_separated, sr, **spec_params
        )

        vib_spec_stacked = np.stack(vib_specs, axis=-1)
        if mic_spec.ndim == 2:
            mic_spec = mic_spec[..., np.newaxis]

        return [vib_spec_stacked, mic_spec]