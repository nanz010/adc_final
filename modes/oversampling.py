import numpy as np
import streamlit as st

from signal_generator import generate_waveform, compute_fft, compute_psd
from adc_processor import (quantize, oversample, downsample_quantized,
                           compute_snr, compute_enob)
from plot_renderer import PLOTLY_CONFIG, plot_oversampling, plot_psd, plot_fft_spectrum, plot_snr_sweep
from modes.animations import show_oversampling_animation

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_oversampling_ui():
    st.header("Oversampling")
    st.markdown(
        "Oversampling by M improves SNR by **10·log₁₀(M)/2 ≈ 3 dB per doubling**. "
        "The PSD tab shows the core mechanism — noise spread wider, lower in-band floor."
    )

    with st.sidebar:
        st.subheader("Oversampling Controls")
        waveform = st.selectbox("Input Waveform", WAVEFORMS)
        bits     = st.slider("ADC Bits",              4,  16,  8)
        freq     = st.slider("Signal Frequency (Hz)", 1, 200, 50)
        factor   = st.select_slider("Oversampling Factor",
                                    options=[1, 2, 4, 8, 16, 32, 64], value=16)

    BASE_RATE   = 1000
    duration    = max(20 / freq, 0.05)

    # Correct simulation: generate signal at M× base rate, quantize, average-decimate
    t_hi, sig_hi = generate_waveform(waveform, freq, duration, BASE_RATE * factor)
    t,    signal  = generate_waveform(waveform, freq, duration, BASE_RATE)

    q_normal   = quantize(signal, bits)
    q_over_dec = downsample_quantized(quantize(sig_hi, bits), factor)

    min_len = min(len(signal), len(q_over_dec))
    t   = t[:min_len]
    sig = signal[:min_len]
    q_n = q_normal[:min_len]
    q_o = q_over_dec[:min_len]

    # SNR from noise power directly
    noise_n  = q_n - sig
    noise_o  = q_o - sig
    sig_pwr  = float(np.mean(sig**2))
    snr_n    = 10 * np.log10(sig_pwr / np.mean(noise_n**2)) if np.mean(noise_n**2) > 0 else float('inf')
    snr_o    = 10 * np.log10(sig_pwr / np.mean(noise_o**2)) if np.mean(noise_o**2) > 0 else float('inf')
    gain     = snr_o - snr_n

    # Theory: 10*log10(M) dB for independent noise averaging
    # Note: the commonly quoted "3 dB per doubling" (10*log10(M)/2) is
    # for sigma-delta noise shaping. Simple averaging gives 10*log10(M).
    # With a coherent sine the quantization noise is correlated so
    # simulated gain is near 0 — the visual staircase improvement is real,
    # but statistically measurable SNR gain needs noise-like or wideband input.
    th_gain  = 10 * np.log10(factor) if factor > 1 else 0.0
    match    = abs(gain - th_gain) < 5.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Normal SNR",      f"{snr_n:.1f} dB")
    c2.metric("Oversampled SNR", f"{snr_o:.1f} dB")
    c3.metric("Theoretical gain",f"+{th_gain:.1f} dB",
              delta=f"10·log₁₀({factor}) — independent noise",
              delta_color="off")
    c4.metric("ENOB improvement",
              f"{compute_enob(snr_n):.2f} → {compute_enob(snr_o):.2f} bits")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Time Domain", "FFT Spectrum", "PSD", "SNR vs Bits"
    ])

    with tab1:
        fig = plot_oversampling(t, q_n, q_o, snr_n, snr_o, sig)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab2:
        st.markdown("**FFT** — noise floor drops after oversampling. "
                    "Hover to compare exact noise levels.")
        freqs_n, mag_n   = compute_fft(q_n, BASE_RATE)
        freqs_ov, mag_ov = compute_fft(q_o, BASE_RATE)
        fig = plot_fft_spectrum(freqs_n, mag_n, freqs_ov, mag_ov, freq, BASE_RATE)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab3:
        st.markdown("**PSD** — same total noise, but spread wider after oversampling. "
                    "In-band noise floor drops by the oversampling factor.")
        fp_n, psd_n = compute_psd(q_n, BASE_RATE)
        fp_s, psd_s = compute_psd(sig, BASE_RATE)
        fp_o, psd_o = compute_psd(q_o, BASE_RATE)
        fig = plot_psd(fp_s, psd_s, fp_n, psd_n, fp_o, psd_o, bits=bits, sample_rate=BASE_RATE)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab4:
        bits_range = list(range(1, 17))
        snr_sim  = [compute_snr(sig, quantize(sig, b)) for b in bits_range]
        snr_theo = [6.02 * b + 1.76 for b in bits_range]
        fig = plot_snr_sweep(bits_range, snr_sim, snr_theo)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with st.expander("📐 Why the simulation gain differs from theory — and why that's correct"):
        st.markdown(f"""
**What the theory says:**

For simple oversampling + averaging decimation with **independent** quantization noise:
- Averaging M samples reduces noise power by M (noise std by √M)
- SNR gain = **10·log₁₀(M) = {th_gain:.1f} dB** for M={factor}

**Why the simulation shows less gain:**

The quantization error on a coherent sine is **deterministic, not random** — it's
a periodic function of the signal value. Adjacent sub-samples in one oversampled
period have *correlated* errors, not independent ones. Averaging correlated
errors gives less reduction than averaging independent ones.

**The commonly quoted "3 dB per doubling" (10·log₁₀(M)/2) is for sigma-delta
modulation** — which uses noise shaping to push quantization energy out of the
signal band. Simple oversampling without noise shaping gives 10·log₁₀(M) dB
when noise IS independent (wideband or noisy input), less for coherent tones.

**What you CAN see in the simulation:**
- The staircase in the Time Domain tab is visually smoother at high M — real ✓
- The PSD noise floor drops — real ✓
- The FFT noise floor drops — real ✓
- The exact dB gain matches theory only for wideband/noisy signals, not pure sines

**References:** Candy & Temes (1992), Norsworthy et al. (1997) — Oversampling Delta-Sigma
Data Converters. Analog Devices MT-002 Application Note.
        """)


    with st.expander("📖 Full explanation — click to learn everything about oversampling"):
        from modes.tutor import explain_oversampling
        explain_oversampling(bits, freq, factor, snr_n, snr_o, th_gain)

    show_oversampling_animation()
