import streamlit as st

from signal_generator import generate_waveform, compute_fft
from adc_processor import detect_aliasing, compute_alias_frequency
from plot_renderer import PLOTLY_CONFIG, plot_aliasing, plot_fft_spectrum
from modes.animations import show_aliasing_animation

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_aliasing_ui():
    st.header("Aliasing Demo")
    st.markdown("When fs < 2·f_signal the signal folds back — **aliasing**. "
                "The FFT tab shows the alias peak appearing at the wrong frequency.")

    with st.sidebar:
        st.subheader("Aliasing Controls")
        waveform    = st.selectbox("Input Waveform", WAVEFORMS)
        signal_freq = st.slider("Signal Frequency (Hz)",  1, 2000,  700)
        sample_rate = st.slider("Sampling Rate (Hz)",   100, 2000,  500)

    nyquist        = sample_rate / 2
    alias_detected = detect_aliasing(signal_freq, sample_rate)
    alias_freq     = compute_alias_frequency(signal_freq, sample_rate)

    if alias_detected:
        st.error(f"Aliasing! {signal_freq} Hz > Nyquist {nyquist:.0f} Hz. "
                 f"Alias at **{alias_freq:.1f} Hz**")
    else:
        st.success(f"No aliasing. {signal_freq} Hz < Nyquist {nyquist:.0f} Hz.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Signal",  f"{signal_freq} Hz")
    c2.metric("Nyquist", f"{nyquist:.0f} Hz")
    c3.metric("Alias",   f"{alias_freq:.1f} Hz" if alias_detected else "None")

    duration = max(20 / signal_freq, 0.05)
    t_orig,  original     = generate_waveform(waveform, signal_freq, duration, 10000)
    t_under, undersampled = generate_waveform(waveform, signal_freq, duration, sample_rate)

    tab1, tab2 = st.tabs(["Time Domain", "FFT Spectrum"])

    with tab1:
        fig = plot_aliasing(t_orig, original, t_under, undersampled,
                            alias_detected, signal_freq, sample_rate, alias_freq)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab2:
        st.markdown("**FFT of undersampled signal** — alias peak appears at "
                    f"**{alias_freq:.1f} Hz** instead of {signal_freq} Hz.")
        freqs_o, mag_o = compute_fft(original,     10000)
        freqs_u, mag_u = compute_fft(undersampled, sample_rate)
        fig = plot_fft_spectrum(freqs_o, mag_o, freqs_u, mag_u,
                                signal_freq, sample_rate)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with st.expander("📖 Full explanation — click to learn everything about aliasing"):
        from modes.tutor import explain_aliasing
        explain_aliasing(signal_freq, sample_rate, alias_detected, alias_freq)

    show_aliasing_animation()
