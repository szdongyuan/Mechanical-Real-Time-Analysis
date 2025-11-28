import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import get_window, stft


@dataclass
class KnockDetectionResult:
    """Container for per-channel peak detection results."""

    channels: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def any_threshold_exceeded(self) -> bool:
        return any(ch.get("exceed_threshold") for ch in self.channels)


class KnockDetector:
    """
    Perform band-limited spectral-energy based peak detection.
    Config structure (JSON):
    {
      "sampling_rate": 44100,
      "channels": ["good_motor", "bad_motor"],
      "stft": {"window": "hann", "frame_size": 1024, "hop_size": 512},
      "bandpass_hz": [2000, 8000],
      "energy_metric": "power_sum",
      "flux": {"method": "positive_diff", "smooth_window": 5},
      "peak_detection": {"zscore_threshold": 4.0}
    }
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}
        self.sampling_rate = int(self.config.get("sampling_rate") or 44100)
        self.channel_names: List[str] = []
        self.channel_thresholds: Dict[str, float] = {}
        channels_cfg = self.config.get("channels") or []
        for item in channels_cfg:
            if isinstance(item, str):
                self.channel_names.append(item)
            elif isinstance(item, dict):
                name = item.get("name")
                if name:
                    self.channel_names.append(name)
                    if "zscore_threshold" in item:
                        try:
                            self.channel_thresholds[name] = item["zscore_threshold"]
                        except (TypeError, ValueError):
                            pass
        if not self.channel_names and isinstance(channels_cfg, Sequence):
            self.channel_names = list(channels_cfg)

        stft_cfg = self.config.get("stft") or {}
        self.window_name = stft_cfg.get("window", "hann")
        self.frame_size = int(stft_cfg.get("frame_size") or 1024)
        self.hop_size = int(stft_cfg.get("hop_size") or self.frame_size // 2)
        self.window = get_window(self.window_name, self.frame_size, fftbins=True)

        band = self.config.get("bandpass_hz") or [0, self.sampling_rate / 2]
        self.band_low = float(band[0]) if len(band) > 0 else 0.0
        self.band_high = float(band[1]) if len(band) > 1 else self.sampling_rate / 2

        flux_cfg = self.config.get("flux") or {}
        self.flux_method = str(flux_cfg.get("method", "positive_diff")).lower()
        self.flux_smooth = max(1, int(flux_cfg.get("smooth_window") or 1))

        peak_cfg = self.config.get("peak_detection") or {}
        self.zscore_threshold = float(peak_cfg.get("zscore_threshold") or 4.0)

    # ------------------------------------------------------------------ #
    def run(self, signals: np.ndarray, sampling_rate: Optional[int] = None) -> KnockDetectionResult:
        sr = int(sampling_rate or self.sampling_rate)
        data = np.asarray(signals)
        if data.ndim == 1:
            data = data[None, :]

        results: List[Dict[str, Any]] = []
        for idx in range(data.shape[0]):
            channel_name = self._resolve_channel_name(idx)
            ch_signal = np.array(data[idx], copy=False)
            ch_result = self._analyze_channel(ch_signal, sr, channel_name)
            results.append(ch_result)
        return KnockDetectionResult(channels=results)

    # ------------------------------------------------------------------ #
    def _resolve_channel_name(self, idx: int) -> str:
        if idx < len(self.channel_names):
            return str(self.channel_names[idx])
        return f"channel_{idx}"

    def _analyze_channel(self, signal: np.ndarray, sr: int, channel: str) -> Dict[str, Any]:
        if not np.any(signal):
            return {
                "channel": channel,
                "max_flux": 0.0,
                "max_zscore": 0.0,
                "threshold": self.zscore_threshold,
            }

        freqs, _, Zxx = stft(
            signal,
            fs=sr,
            window=self.window,
            nperseg=self.frame_size,
            noverlap=self.frame_size - self.hop_size,
            boundary=None,
        )
        band_energy = self._compute_band_energy(freqs, Zxx)
        flux = self._compute_flux(band_energy)
        max_flux = float(flux.max()) if flux.size else 0.0
        max_zscore = self._max_zscore(flux)
        threshold = self.channel_thresholds.get(channel, self.zscore_threshold)

        return {
            "channel": channel,
            "max_flux": max_flux,
            "max_zscore": max_zscore,
            "threshold": threshold,
        }

    # ------------------------------------------------------------------ #
    def _compute_band_energy(self, freqs: np.ndarray, Zxx: np.ndarray) -> np.ndarray:
        if freqs.size == 0 or Zxx.size == 0:
            return np.zeros(1, dtype=np.float32)
        mask = (freqs >= self.band_low) & (freqs <= self.band_high)
        if not np.any(mask):
            mask = np.ones_like(freqs, dtype=bool)
        band = Zxx[mask, :]
        energy = np.abs(band) ** 2  # power
        return energy.sum(axis=0)

    def _compute_flux(self, energy: np.ndarray) -> np.ndarray:
        if energy.size == 0:
            return np.zeros(1, dtype=np.float32)
        diff = np.diff(energy, prepend=energy[0])
        if self.flux_method == "positive_diff":
            diff = np.maximum(diff, 0.0)
        elif self.flux_method == "abs_diff":
            diff = np.abs(diff)

        if self.flux_smooth > 1:
            diff = uniform_filter1d(diff, size=self.flux_smooth, mode="nearest")
        return diff.astype(np.float32, copy=False)

    def _max_zscore(self, flux: np.ndarray) -> float:
        if flux.size == 0:
            return 0.0
        mean = float(np.mean(flux))
        std = float(np.std(flux))
        if std < 1e-9:
            return 0.0
        z = (flux - mean) / std
        return float(np.max(z))

