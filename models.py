from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class SignalParams:
    freq: float
    duration: float
    sample_rate: int
    bits: int
    amplitude: float
    noise_std: float
    oversample_factor: int

    def __post_init__(self) -> None:
        if not (1 <= self.bits <= 16):
            raise ValueError(f"bits must be in [1, 16], got {self.bits}")
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be > 0, got {self.sample_rate}")
        if self.freq <= 0:
            raise ValueError(f"freq must be > 0, got {self.freq}")
        if self.oversample_factor < 1:
            raise ValueError(f"oversample_factor must be >= 1, got {self.oversample_factor}")
        if not (0 < self.amplitude <= 1):
            raise ValueError(f"amplitude must be in (0, 1], got {self.amplitude}")


@dataclass
class ProcessedSignals:
    t: np.ndarray
    analog: np.ndarray
    sampled: np.ndarray
    quantized: np.ndarray
    error: np.ndarray
    snr_db: float
    enob: float
    alias_detected: bool
    oversampled: Optional[np.ndarray] = None


@dataclass
class ModeConfig:
    name: str
    default_bits: int
    default_freq: float
    default_sample_rate: int
    show_noise_control: bool
    show_oversample_control: bool
    show_aliasing_warning: bool
