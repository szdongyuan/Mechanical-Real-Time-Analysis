import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import get_window, stft


class MotorState(IntEnum):
    """电机状态枚举"""
    SLEEPING = 0   # 停机状态
    RUNNING = 1    # 正常运行
    KNOCKED = 2    # 被敲击


@dataclass
class KnockDetectionResult:
    """Container for per-channel peak detection results."""

    channels: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def any_threshold_exceeded(self) -> bool:
        return any(ch.get("is_knocked") for ch in self.channels)

    @property
    def any_sleeping(self) -> bool:
        return any(not ch.get("is_running") for ch in self.channels)


class KnockDetector:
    """
    Perform band-limited spectral-energy based peak detection.
    
    检测逻辑:
    1. 使用能量级别判断电机是否在运行（停机/运行）
    2. 使用 flux + zscore 检测电机是否被敲击
    
    状态判断优先级:
    - 如果 zscore >= zscore_threshold -> KNOCKED（被敲击）
    - 如果 energy < energy_threshold -> SLEEPING（停机）
    - 否则 -> RUNNING（正常运行）
    
    Config structure (JSON):
    {
      "sampling_rate": 44100,
      "channels": [
        {
          "name": "good_motor",
          "zscore_threshold": 4.0,
          "energy_threshold": 1e-6
        }
      ],
      "stft": {"window": "hann", "frame_size": 1024, "hop_size": 512},
      "bandpass_hz": [2000, 8000],
      "energy_metric": "power_sum",
      "flux": {"method": "positive_diff", "smooth_window": 5},
      "defaults": {
        "zscore_threshold": 4.0,
        "energy_threshold": 1e-6
      }
    }
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config or {}
        self.sampling_rate = int(self.config.get("sampling_rate") or 44100)
        
        # 通道配置
        self.channel_names: List[str] = []
        self.channel_zscore_thresholds: Dict[str, float] = {}
        self.channel_energy_thresholds: Dict[str, float] = {}
        
        # 默认阈值
        defaults = self.config.get("defaults") or {}
        self.default_zscore_threshold = float(defaults.get("zscore_threshold") or 4.0)
        self.default_energy_threshold = float(defaults.get("energy_threshold") or 1e-6)
        
        channels_cfg = self.config.get("channels") or []
        for item in channels_cfg:
            if isinstance(item, str):
                self.channel_names.append(item)
            elif isinstance(item, dict):
                name = item.get("name")
                if name:
                    self.channel_names.append(name)
                    # zscore 阈值（用于敲击检测）
                    if "zscore_threshold" in item:
                        try:
                            val = item["zscore_threshold"]
                            # 兼容旧格式 [min, max]，取 max 作为敲击阈值
                            if isinstance(val, (list, tuple)) and len(val) >= 2:
                                self.channel_zscore_thresholds[name] = float(val[1])
                            else:
                                self.channel_zscore_thresholds[name] = float(val)
                        except (TypeError, ValueError):
                            pass
                    # 能量阈值（用于停机检测）
                    if "energy_threshold" in item:
                        try:
                            self.channel_energy_thresholds[name] = float(item["energy_threshold"])
                        except (TypeError, ValueError):
                            pass

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

        # 标准差最小阈值，用于避免除零错误
        self.std_min_threshold = float(self.config.get("std_min_threshold") or 1e-11)

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

    def _get_zscore_threshold(self, channel: str) -> float:
        return self.channel_zscore_thresholds.get(channel, self.default_zscore_threshold)

    def _get_energy_threshold(self, channel: str) -> float:
        return self.channel_energy_thresholds.get(channel, self.default_energy_threshold)

    def _analyze_channel(self, signal: np.ndarray, sr: int, channel: str) -> Dict[str, Any]:
        zscore_threshold = self._get_zscore_threshold(channel)
        energy_threshold = self._get_energy_threshold(channel)
        
        if not np.any(signal):
            return {
                "channel": channel,
                "energy_level": 0.0,
                "is_running": False,
                "max_flux": 0.0,
                "max_zscore": 0.0,
                "is_knocked": False,
                "motor_state": MotorState.SLEEPING,
                "zscore_threshold": zscore_threshold,
                "energy_threshold": energy_threshold,
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
        
        # 计算平均能量级别（用于判断是否运行）
        energy_level = float(np.mean(band_energy)) if band_energy.size else 0.0
        is_running = energy_level >= energy_threshold
        
        # 计算 flux 和 zscore（用于判断是否被敲击）
        flux = self._compute_flux(band_energy)
        max_flux = float(flux.max()) if flux.size else 0.0
        max_zscore = self._max_zscore(flux)
        is_knocked = max_zscore >= zscore_threshold
        
        # 判断最终电机状态
        if is_knocked:
            motor_state = MotorState.KNOCKED
        elif not is_running:
            motor_state = MotorState.SLEEPING
        else:
            motor_state = MotorState.RUNNING
        
        return {
            "channel": channel,
            "energy_level": energy_level,
            "is_running": is_running,
            "max_flux": max_flux,
            "max_zscore": max_zscore,
            "is_knocked": is_knocked,
            "motor_state": motor_state,
            "zscore_threshold": zscore_threshold,
            "energy_threshold": energy_threshold,
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
        if std < self.std_min_threshold:
            return 0.0
        z = (flux - mean) / std
        return float(np.max(z))
