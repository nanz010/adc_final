import numpy as np
import streamlit as st

from signal_generator import generate_waveform, generate_noisy_sine, compute_fft, compute_psd
from adc_processor import quantize, compute_snr, compute_enob
from plot_renderer import PLOTLY_CONFIG, plot_realworld, plot_fft_spectrum, plot_psd, plot_error_histogram

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_realworld_ui():
    st.header("Real-World Noise")
    st.markdown("Combines thermal noise, jitter, and quantization noise.")

    with st.sidebar:
        st.subheader("Real-World Controls")
        waveform    = st.selectbox("Input Waveform", WAVEFORMS)
        bits        = st.slider("ADC Bits",            1,   16,    8)
        freq        = st.slider("Signal Frequency",    1,  500,   50)
        sample_rate = st.slider("Sampling Rate (Hz)", 100, 5000, 1000)
        noise_std   = st.slider("Noise Std Dev",      0.0,  0.5,  0.05, step=0.005)
        amplitude   = st.slider("Amplitude",          0.1,  1.0,  1.0,  step=0.05)

    duration = max(20 / freq, 0.05)
    t, ideal  = generate_waveform(waveform, freq, duration, sample_rate, amplitude)
    noisy     = ideal + np.random.normal(0, noise_std, size=ideal.shape)
    quantized = quantize(noisy, bits)
    snr       = compute_snr(ideal, quantized)
    enob      = compute_enob(snr)
    ideal_snr = compute_snr(ideal, quantize(ideal, bits))

    c1, c2, c3 = st.columns(3)
    c1.metric("Actual SNR",  f"{snr:.1f} dB")
    c2.metric("ENOB",        f"{enob:.2f} bits")
    c3.metric("Degradation", f"{ideal_snr - snr:.1f} dB",
              delta=f"-{ideal_snr - snr:.1f} dB", delta_color="inverse")

    metrics = {"snr": snr, "enob": enob, "noise_std": noise_std,
               "bits": bits, "ideal_snr": ideal_snr}

    tab1, tab2, tab3, tab4 = st.tabs([
        "Time Domain", "FFT Spectrum", "PSD", "Error Histogram"
    ])

    with tab1:
        fig = plot_realworld(t, ideal, noisy, quantized, metrics)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab2:
        freqs_i, mag_i = compute_fft(ideal,     sample_rate)
        freqs_q, mag_q = compute_fft(quantized, sample_rate)
        fig = plot_fft_spectrum(freqs_i, mag_i, freqs_q, mag_q, freq, sample_rate)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab3:
        fp_i, psd_i = compute_psd(ideal,     sample_rate)
        fp_q, psd_q = compute_psd(quantized, sample_rate)
        fig = plot_psd(fp_i, psd_i, fp_q, psd_q, bits=bits, sample_rate=sample_rate)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab4:
        fig = plot_error_histogram(quantized - ideal, bits)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with st.expander("📖 Full explanation — click to learn everything about real-world noise"):
        from modes.tutor import explain_realworld
        explain_realworld(bits, noise_std, snr, enob, ideal_snr)
