import numpy as np
from scipy.ndimage import maximum_filter


class AudioThdFrequencyResponseAnalysis(object):

    @staticmethod
    def spl_calculation(recorded_signal, reference_pressure=20e-6, window_size=1201, is_smooth=True):
        """
        Calculate the Sound Pressure Level (SPL) of the recorded signal.

        Args:
            - recorded_signal : ndarray
                The input recorded signal
            - reference_pressure : float
                The reference sound pressure, defaulting to 20 μPa (20e-6 Pa),
                used as the baseline for SPL calculation.
            - window_size: int
                The sliding window length

        Returns:
            - spl_smooth : ndarray
                The computed SPL (in dB) after smoothing.
        """
        amplitude_list = maximum_filter(np.abs(recorded_signal), size=window_size)
        spl = 20 * np.log10(np.array(amplitude_list) / reference_pressure)
        if is_smooth:
            spl_smooth = np.convolve(spl, np.ones(1102) / 1102, mode="same")
            return spl_smooth
        else:
            return spl
