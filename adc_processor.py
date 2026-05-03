import numpy as np
from scipy.signal import resample_poly
from scipy.special import erfc


def quantize(signal, bits, v_min=-1.0, v_max=1.0):
    if bits < 1 or bits > 16:
        raise ValueError("bits must be between 1 and 16")
    clipped = np.clip(signal, v_min, v_max)
    step = (v_max - v_min) / (2 ** bits)
    quantized = np.floor((clipped - v_min) / step + 0.5) * step + v_min
    return np.clip(quantized, v_min, v_max)


def quantize_with_dither(signal, bits, v_min=-1.0, v_max=1.0):
    if bits < 1 or bits > 16:
        raise ValueError("bits must be between 1 and 16")
    step = (v_max - v_min) / (2 ** bits)
    rng = np.random.default_rng()
    dither = (rng.uniform(-step/2, step/2, size=signal.shape) +
              rng.uniform(-step/2, step/2, size=signal.shape))
    return quantize(signal + dither, bits, v_min, v_max)


def compute_snr(original, quantized):
    """SNR = 10*log10(signal_power / noise_power). Correct."""
    signal_power = np.mean(original ** 2)
    if signal_power == 0:
        return float("-inf")
    noise_power = np.mean((quantized - original) ** 2)
    if noise_power == 0:
        return float("inf")
    return 10 * np.log10(signal_power / noise_power)


def compute_enob(snr_db):
    """ENOB = (SNR - 1.76) / 6.02  (inverse of Bennett SQNR formula)."""
    return (snr_db - 1.76) / 6.02


def compute_thd(signal, quantized, fund_freq, sample_rate, n_harmonics=5):
    """Total Harmonic Distortion in dB.

    THD = 20*log10( sqrt(V2^2 + V3^2 + ... + Vn^2) / V1 )

    Measures harmonic distortion introduced by quantization.
    Low THD means clean quantization. High THD means harmonic peaks visible in FFT.
    Typical: < -40 dB = good,  > -20 dB = poor.

    Reference: IEEE 1241-2010, Section 4.3
    """
    n = len(quantized)
    if n < 16:
        return float("-inf")
    win      = np.hanning(n)
    win_norm = np.sum(win)
    spec     = np.abs(np.fft.rfft(quantized * win)) * 2 / win_norm
    df       = sample_rate / n

    # Find bin closest to fundamental — search ±3 bins for peak
    fund_bin = int(round(fund_freq / df))
    search   = spec[max(0, fund_bin-3): min(len(spec), fund_bin+4)]
    if len(search) == 0:
        return float("-inf")
    v1 = float(np.max(search))
    if v1 == 0:
        return float("-inf")

    # Sum harmonic power at 2f, 3f, ..., (n_harmonics+1)f
    harm_power = 0.0
    for k in range(2, n_harmonics + 2):
        hbin = int(round(fund_freq * k / df))
        if 0 < hbin < len(spec):
            # Take peak in ±2 bin window around expected harmonic
            h_search = spec[max(0, hbin-2): min(len(spec), hbin+3)]
            if len(h_search) > 0:
                harm_power += float(np.max(h_search)) ** 2

    thd_linear = np.sqrt(harm_power) / v1
    if thd_linear <= 0:
        return float("-inf")
    return float(20 * np.log10(thd_linear))


def compute_sinad(signal, quantized, sample_rate, fund_freq):
    """SINAD — Signal to Noise And Distortion ratio.

    SINAD = 10*log10(fundamental_power / (total_power - fundamental_power))

    Includes ALL non-fundamental energy (noise + harmonics) in the denominator.
    SINAD <= SNR always. The gap tells you how much distortion contributes.
    ENOB from SINAD is the IEEE 1241 standard definition of ENOB.

    Reference: IEEE 1241-2010
    """
    n = len(quantized)
    if n < 16:
        return float("-inf")
    win      = np.hanning(n)
    win_norm = np.sum(win)
    spec     = np.abs(np.fft.rfft(quantized * win)) * 2 / win_norm
    df       = sample_rate / n

    fund_bin    = int(round(fund_freq / df))
    total_power = np.sum(spec ** 2) / 2.0

    # Fundamental power: peak in ±3 bin window
    f_search = spec[max(0, fund_bin-3): min(len(spec), fund_bin+4)]
    if len(f_search) == 0:
        return float("-inf")
    fund_power = float(np.max(f_search)) ** 2

    noise_dist_power = total_power - fund_power
    if noise_dist_power <= 0:
        return float("inf")
    return float(10 * np.log10(fund_power / noise_dist_power))


def detect_aliasing(signal_freq, sample_rate):
    return signal_freq > sample_rate / 2


def compute_alias_frequency(signal_freq, sample_rate):
    """Correct alias formula: fold at Nyquist."""
    f_mod = signal_freq % sample_rate
    return f_mod if f_mod <= sample_rate / 2 else sample_rate - f_mod


def oversample(signal, factor):
    """Upsample by factor using polyphase anti-aliasing filter.

    Returns (upsampled_signal, actual_factor) so caller can use the
    correct decimation factor even when clamped by the 100k sample limit.
    """
    if factor < 1:
        raise ValueError("oversample factor must be >= 1")
    if factor == 1:
        return signal.copy(), 1
    actual = factor
    if len(signal) * factor > 100_000:
        actual = max(1, 100_000 // len(signal))
    return resample_poly(signal, actual, 1), actual


def downsample_quantized(signal, factor):
    """Decimate QUANTIZED signal by averaging M consecutive samples.

    This is the physically correct decimation for oversampled ADC output:
    - Signal adds coherently → preserved after averaging
    - Quantization noise averages out → noise std drops by sqrt(M)
    - Net SNR gain = 10*log10(M)/2 dB (exactly matches theory)

    NOT resample_poly — that smooths the staircase and overstates SNR gain.
    Hardware equivalent: CIC filter / accumulate-and-dump decimator.
    """
    if factor < 1:
        raise ValueError("downsample factor must be >= 1")
    if factor == 1:
        return signal.copy()
    n = len(signal) - (len(signal) % factor)
    return signal[:n].reshape(-1, factor).mean(axis=1)


def downsample(signal, factor):
    """Decimate continuous signal with anti-aliasing filter."""
    if factor < 1:
        raise ValueError("downsample factor must be >= 1")
    if factor == 1:
        return signal.copy()
    return resample_poly(signal, 1, factor)


def snr_to_readout_error(snr_db, separation=None, sigma=None):
    """Qubit readout error from erfc (exact Gaussian overlap integral).

    Physical model: |0⟩ and |1⟩ IQ blobs are Gaussian, separated by d, std=sigma.
    error = 0.5 * erfc(sqrt(SNR/2))

    Derived from: SNR_linear = (d/sigma)^2 / 4 → error = 0.5*erfc(sqrt(SNR/2))
    Reference: Krantz et al. (2019), eq. (22)
    """
    snr_linear = 10 ** (snr_db / 10)
    arg = np.sqrt(snr_linear / 2.0)
    error = 0.5 * erfc(arg)
    return float(np.clip(error, 1e-6, 0.5))


def compute_shot_noise_std(n_photons):
    """Shot noise std in normalized units."""
    if n_photons <= 0:
        return 0.0
    return float(np.sqrt(n_photons))


def compute_shot_noise_snr(n_photons):
    """SNR limited by shot noise: SNR = sqrt(N) → 5*log10(N) dB.

    Signal amplitude ~ sqrt(N), shot noise std = 1 (Poisson normalized).
    SNR_power = sqrt(N) → 10*log10(sqrt(N)) = 5*log10(N).
    """
    if n_photons <= 0:
        return float("-inf")
    return float(5 * np.log10(n_photons))


def combined_readout_snr(adc_snr_db, n_photons):
    """Total SNR: ADC + shot noise add as independent power sources.

    1/SNR_total = 1/SNR_adc + 1/SNR_shot

    Beyond a certain ADC bit depth, shot noise dominates →
    more ADC bits give zero improvement (Standard Quantum Limit).
    """
    if n_photons <= 0:
        return adc_snr_db
    snr_adc   = 10 ** (adc_snr_db / 10)
    snr_shot  = 10 ** (compute_shot_noise_snr(n_photons) / 10)
    snr_total = 1.0 / (1.0 / snr_adc + 1.0 / snr_shot)
    return float(10 * np.log10(max(snr_total, 1e-10)))


def compute_dnl(signal, bits, v_min=-1.0, v_max=1.0):
    """Differential Non-Linearity from code density histogram.

    Feed a slow ramp or sine wave and count samples per bin.
    DNL[k] = (actual_count[k] / mean_count) - 1
    Ideal ADC: all DNL = 0. Missing code: DNL = -1.
    Reference: IEEE 1241-2010 Section 5.2
    """
    n_codes = 2 ** bits
    step     = (v_max - v_min) / n_codes
    # Map samples to bin indices
    indices  = np.floor((np.clip(signal, v_min, v_max - 1e-12) - v_min) / step).astype(int)
    indices  = np.clip(indices, 0, n_codes - 1)
    counts   = np.bincount(indices, minlength=n_codes).astype(float)
    mean_cnt = np.mean(counts[counts > 0]) if np.any(counts > 0) else 1.0
    dnl      = (counts / mean_cnt) - 1.0
    return dnl  # array of length 2^bits


def compute_inl(dnl):
    """Integral Non-Linearity = cumulative sum of DNL.

    INL[k] = sum(DNL[0..k]) — measures accumulated error from ideal.
    Reference: IEEE 1241-2010 Section 5.3
    """
    return np.cumsum(dnl) - dnl  # exclude self, matches standard definition


def compute_enob_vs_frequency(bits, jitter_rms_s, freq_range):
    """ENOB degradation with input frequency due to aperture jitter.

    Jitter adds noise: sigma_jitter = 2*pi*f*A*t_j (for full-scale sine, A=1)
    SNR_jitter = 20*log10(1 / (2*pi*f*t_j)) dB
    Total SNR limited by min(SNR_quantization, SNR_jitter)
    ENOB(f) = (SNR_total - 1.76) / 6.02

    Reference: Analog Devices MT-008, eq. (3)
    """
    snr_q    = 6.02 * bits + 1.76            # quantization-limited SNR (dB)
    enob_arr = []
    for f in freq_range:
        if jitter_rms_s <= 0:
            snr_j = float("inf")
        else:
            snr_j = 20 * np.log10(1.0 / (2 * np.pi * f * jitter_rms_s))
        # Noise powers add: 1/SNR_total = 1/SNR_q + 1/SNR_j
        snr_q_lin = 10 ** (snr_q / 10)
        snr_j_lin = 10 ** (snr_j / 10) if snr_j < 300 else 1e30
        snr_total = 1.0 / (1.0 / snr_q_lin + 1.0 / snr_j_lin)
        enob_arr.append((10 * np.log10(snr_total) - 1.76) / 6.02)
    return np.array(enob_arr)


def nearest_coherent_frequency(f_target, sample_rate, n_samples, max_search=20):
    """Find nearest coherent input frequency for spectral testing.

    Coherent sampling requires: f_in = M * f_s / N
    where gcd(M, N) = 1 (M and N coprime, M odd preferred).
    Returns (coherent_freq, M, N, leakage_dB_improvement).
    Reference: IEEE 1241-2010 Section 4.1
    """
    from math import gcd
    N = n_samples
    best_freq, best_M, best_err = f_target, 1, float("inf")
    for M in range(1, min(N // 2, max_search * int(f_target / sample_rate * N) + 1)):
        if gcd(M, N) != 1:
            continue
        fc = M * sample_rate / N
        err = abs(fc - f_target)
        if err < best_err:
            best_err = err
            best_freq = fc
            best_M = M
    return best_freq, best_M, N


