import streamlit as st

from signal_generator import generate_waveform, compute_fft, compute_psd
from adc_processor import quantize, quantize_with_dither, compute_snr, compute_enob, compute_thd, compute_sinad
from plot_renderer import PLOTLY_CONFIG, plot_dithering, plot_fft_spectrum, plot_psd, plot_error_histogram
from modes.animations import show_dithering_animation

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_dithering_ui():
    st.header("Dithering")
    st.markdown(
        "Adds ~0.5 LSB noise **before** quantization to remove harmonic distortion. "
        "Used in LIGO gravitational wave detectors. "
        "**The FFT tab is the key view** — harmonic peaks disappear after dithering."
    )

    with st.sidebar:
        st.subheader("Dithering Controls")
        waveform    = st.selectbox("Input Waveform", WAVEFORMS)
        bits        = st.slider("ADC Bits (low = more visible)", 2, 8,    4)
        freq        = st.slider("Signal Frequency (Hz)",         1, 200,  50)
        sample_rate = st.slider("Sampling Rate (Hz)",          500, 5000, 1000)
        amplitude   = st.slider("Amplitude (low = more visible)", 0.1, 1.0, 0.4, step=0.05)

    duration = max(20 / freq, 0.05)
    t, signal = generate_waveform(waveform, freq, duration, sample_rate, amplitude)
    q_no      = quantize(signal, bits)
    q_di      = quantize_with_dither(signal, bits)
    snr_no    = compute_snr(signal, q_no)
    snr_di    = compute_snr(signal, q_di)
    thd_no    = compute_thd(signal, q_no, freq, sample_rate)
    thd_di    = compute_thd(signal, q_di, freq, sample_rate)
    sinad_no  = compute_sinad(signal, q_no, sample_rate, freq)
    sinad_di  = compute_sinad(signal, q_di, sample_rate, freq)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("SNR (no dither)",   f"{snr_no:.1f} dB",
              help="Quantization noise only — does not capture harmonic distortion")
    c2.metric("SNR (dithered)",    f"{snr_di:.1f} dB")
    c3.metric("THD (no dither)",   f"{thd_no:.1f} dB" if thd_no > -90 else "< −90 dB",
              help="Total Harmonic Distortion — harmonics at 2f,3f,4f... High = bad")
    c4.metric("THD (dithered)",    f"{thd_di:.1f} dB" if thd_di > -90 else "< −90 dB",
              help="Dithering drives THD toward noise floor — should be much lower")
    c5.metric("SINAD (no dither)", f"{sinad_no:.1f} dB",
              help="Includes harmonics — better metric than SNR for distorted signals")
    c6.metric("SINAD (dithered)",  f"{sinad_di:.1f} dB",
              help="After dithering SINAD ≈ SNR — harmonics gone, only white noise remains")

    st.info("Dithering trades correlated harmonic distortion for flat white noise. "
            "Check the FFT tab — harmonic peaks vanish, noise floor flattens.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Time Domain", "FFT Spectrum", "PSD", "Error Histogram"
    ])

    with tab1:
        fig = plot_dithering(t, signal, q_no, q_di, snr_no, snr_di)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab2:
        st.markdown("**This is the key dithering view.** Without dither: harmonic peaks visible. "
                    "With dither: peaks gone, noise floor raised but flat (white).")
        freqs_n, mag_n = compute_fft(q_no, sample_rate)
        freqs_d, mag_d = compute_fft(q_di, sample_rate)
        fig = plot_fft_spectrum(freqs_n, mag_n, freqs_d, mag_d, freq, sample_rate)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab3:
        fp_s, psd_s = compute_psd(signal, sample_rate)
        fp_n, psd_n = compute_psd(q_no,   sample_rate)
        fp_d, psd_d = compute_psd(q_di,   sample_rate)
        fig = plot_psd(fp_s, psd_s, fp_n, psd_n, fp_d, psd_d, bits=bits, sample_rate=sample_rate)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab4:
        st.markdown("No dither → non-uniform error (correlated). "
                    "With dither → uniform (white noise).")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Without dithering")
            fig = plot_error_histogram(q_no - signal, bits)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        with col2:
            st.caption("With dithering")
            fig = plot_error_histogram(q_di - signal, bits)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with st.expander("References"):
        st.markdown(
            "- Lyons (2005) — *Reducing ADC Quantization Noise*\n"
            "- TI Application Note AN-804\n"
            "- LIGO O4 (2024) — 3× noise improvement with dithering"
        )

    with st.expander("📖 Full explanation — click to learn everything about dithering"):
        from modes.tutor import explain_dithering
        explain_dithering(bits, snr_no, snr_di, amplitude)

    show_dithering_animation()
