import numpy as np
import streamlit as st

from signal_generator import generate_waveform, compute_fft
from adc_processor import quantize, oversample, downsample_quantized, compute_snr
from plot_renderer import PLOTLY_CONFIG, plot_comparison, plot_fft_spectrum, plot_snr_sweep

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_comparison_ui():
    st.header("Comparison Mode")
    st.markdown("Side-by-side comparison of bit depth or oversampling configurations.")

    with st.sidebar:
        st.subheader("Comparison Controls")
        compare_type = st.radio("Compare by", ["Bit Depth", "Oversampling"])
        waveform     = st.selectbox("Input Waveform", WAVEFORMS)
        freq         = st.slider("Signal Frequency (Hz)", 1, 200, 50)
        amplitude    = st.slider("Amplitude", 0.1, 1.0, 1.0, step=0.05)

    duration = max(20 / freq, 0.05)
    t, signal = generate_waveform(waveform, freq, duration, 1000, amplitude)

    if compare_type == "Bit Depth":
        signals = {
            "Original":   signal,
            "4-bit ADC":  quantize(signal, 4),
            "8-bit ADC":  quantize(signal, 8),
            "12-bit ADC": quantize(signal, 12),
            "16-bit ADC": quantize(signal, 16),
        }
        tab1, tab2, tab3 = st.tabs(["Time Domain", "FFT Spectrum", "SNR vs Bits"])

        with tab1:
            fig = plot_comparison(t, signals, mode="bit_depth")
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            st.markdown("**Theoretical SNR per bit depth:**")
            cols = st.columns(4)
            for i, b in enumerate([4, 8, 12, 16]):
                cols[i].metric(f"{b}-bit", f"{6.02*b + 1.76:.1f} dB")

        with tab2:
            st.markdown("Select two bit depths to compare FFT spectra.")
            col1, col2 = st.columns(2)
            with col1:
                b1 = st.selectbox("Bit depth A", [4, 8, 12, 16], index=0)
            with col2:
                b2 = st.selectbox("Bit depth B", [4, 8, 12, 16], index=1)
            fa, ma = compute_fft(quantize(signal, b1), 1000)
            fb, mb = compute_fft(quantize(signal, b2), 1000)
            fig = plot_fft_spectrum(fa, ma, fb, mb, freq, 1000)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

        with tab3:
            bits_range = list(range(1, 17))
            from adc_processor import compute_snr
            snr_sim  = [compute_snr(signal, quantize(signal, b)) for b in bits_range]
            snr_theo = [6.02 * b + 1.76 for b in bits_range]
            fig = plot_snr_sweep(bits_range, snr_sim, snr_theo)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    else:
        signals = {"Original": signal, "1x": quantize(signal, 8)}
        for m in [4, 16, 64]:
            os_sig, actual_m = oversample(signal, m)
            dec = downsample_quantized(quantize(os_sig, 8), actual_m)
            min_len = min(len(signal), len(dec))
            signals[f"{m}x"] = dec[:min_len]
        min_len = min(len(s) for s in signals.values())
        signals = {k: v[:min_len] for k, v in signals.items()}
        t_trim = t[:min_len]

        tab1, tab2 = st.tabs(["Time Domain", "FFT Spectrum"])

        with tab1:
            fig = plot_comparison(t_trim, signals, mode="oversampling")
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
            st.markdown("**Theoretical SNR gain per factor:**")
            cols = st.columns(4)
            for i, m in enumerate([1, 4, 16, 64]):
                gain = 10 * np.log10(m) / 2 if m > 1 else 0
                cols[i].metric(f"{m}x", f"+{gain:.1f} dB")

        with tab2:
            fa, ma = compute_fft(signals["1x"],  1000)
            fb, mb = compute_fft(signals["16x"], 1000)
            fig = plot_fft_spectrum(fa, ma, fb, mb, freq, 1000)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
