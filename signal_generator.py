import numpy as np
from scipy.signal import chirp as scipy_chirp, square, sawtooth
import streamlit as st

MAX_SAMPLES = 50_000
MIN_CYCLES  = 100   # Always generate at least 100 cycles — no blank space on zoom


def _make_t(freq, duration, sample_rate):
    """Return time array: at least MIN_CYCLES, capped at MAX_SAMPLES."""
    dur = max(duration, MIN_CYCLES / freq)
    n   = min(int(sample_rate * dur), MAX_SAMPLES)
    return np.linspace(0, dur, n, endpoint=False)


@st.cache_data(max_entries=64)
def generate_sine(freq, duration, sample_rate, amplitude=1.0):
    t = _make_t(freq, duration, sample_rate)
    return t, amplitude * np.sin(2 * np.pi * freq * t)


def generate_noisy_sine(freq, duration, sample_rate, noise_std, amplitude=1.0):
    t, signal = generate_sine(freq, duration, sample_rate, amplitude)
    return t, signal + np.random.normal(0, noise_std, size=t.shape)


def generate_chirp(f_start, f_end, duration, sample_rate):
    n = min(int(sample_rate * duration), MAX_SAMPLES)
    t = np.linspace(0, duration, n, endpoint=False)
    return t, scipy_chirp(t, f0=f_start, f1=f_end, t1=duration, method="linear")


@st.cache_data(max_entries=128)
def generate_waveform(waveform, freq, duration, sample_rate, amplitude=1.0):
    """Generate Sine / Square / Triangle / Sawtooth.

    @st.cache_data: result is cached per unique (waveform, freq, duration,
    sample_rate, amplitude) combination — slider moves that repeat a previous
    value are instant, no recomputation.

    Always generates at least MIN_CYCLES so zooming out never shows blank space.
    Capped at MAX_SAMPLES for rendering performance.
    IEEE 1241 standard mandates Sine, Square, Triangle for ADC testing.
    """
    t = _make_t(freq, duration, sample_rate)
    w = 2 * np.pi * freq * t
    if waveform == "Sine":
        sig = np.sin(w)
    elif waveform == "Square":
        sig = square(w)
    elif waveform == "Triangle":
        sig = sawtooth(w, width=0.5)
    elif waveform == "Sawtooth":
        sig = sawtooth(w, width=1.0)
    else:
        sig = np.sin(w)
    return t, amplitude * sig


@st.cache_data(max_entries=128)
def compute_fft(signal, sample_rate):
    """Single-sided FFT magnitude in dBFS.
    Normalized so a full-scale sine reads 0 dBFS at its fundamental.
    Uses Hann window to reduce spectral leakage.
    """
    n      = len(signal)
    win    = np.hanning(n)
    # Correct amplitude normalization: divide by sum(window) not N
    # This ensures a full-scale sine reads 0 dBFS at its fundamental peak
    # Using 2/sum(win) for single-sided spectrum amplitude correction
    spec   = np.fft.rfft(signal * win)
    mag    = np.abs(spec) * 2 / np.sum(win)
    mag    = np.clip(mag, 1e-12, None)
    freqs  = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    return freqs, 20 * np.log10(mag)


@st.cache_data(max_entries=64)
def compute_psd(signal, sample_rate):
    """Power Spectral Density using Welch method.
    Matches MATLAB pwelch defaults: 8 segments, Hann window.
    """
    from scipy.signal import welch
    nperseg = max(len(signal) // 8, 32)
    freqs, psd = welch(signal, fs=sample_rate, nperseg=nperseg, window="hann")
    return freqs, 10 * np.log10(np.clip(psd, 1e-20, None))


@st.cache_data(max_entries=64)
def generate_iq_signal(freq, duration, sample_rate,
                       amplitude_0=0.3, amplitude_1=0.7,
                       noise_std=0.05, n_shots=200):
    """Generate IQ scatter data for qubit |0> and |1> readout blobs."""
    rng = np.random.default_rng(42)
    I_0 = rng.normal(amplitude_0, noise_std, n_shots)
    Q_0 = rng.normal(0.0,         noise_std, n_shots)
    I_1 = rng.normal(amplitude_1, noise_std, n_shots)
    Q_1 = rng.normal(0.0,         noise_std, n_shots)
    return I_0, Q_0, I_1, Q_1
