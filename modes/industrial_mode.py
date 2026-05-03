"""
industrial_mode.py — Industrial ADC Analysis Mode
All advanced features in one unified mode.
"""
import numpy as np
import streamlit as st

from signal_generator import generate_waveform, compute_fft
from adc_processor import quantize, compute_snr, compute_enob, compute_thd, compute_sinad
from plot_renderer import PLOTLY_CONFIG
from modes.industrial import (
    ADC_PRESETS, show_adc_presets, show_file_upload, show_export_panel,
    show_parameter_sweep, show_dnl_inl, show_enob_vs_freq,
    show_coherent_sampling, show_t1_t2_tradeoff,
)

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_industrial_ui():
    st.header("Industrial ADC Analysis")
    st.markdown(
        "Professional-grade ADC characterization tools: real component presets, "
        "file upload, parameter sweeps, DNL/INL linearity tests, "
        "jitter analysis, coherent sampling, and quantum T1/T2 tradeoffs."
    )

    # ── ADC Preset selector ─────────────────────────────────────────────
    preset = show_adc_presets()

    # ── Sidebar controls — override with preset if selected ─────────────
    with st.sidebar:
        st.subheader("Signal Controls")

        if preset:
            bits        = preset["bits"] if preset["bits"] <= 16 else 16
            sample_rate = min(int(preset["sample_rate"]), 100_000)
            st.info(f"Preset loaded: {bits}-bit, {sample_rate:,} SPS")
        else:
            bits        = st.slider("ADC Bits", 1, 16, 8)
            sample_rate = st.slider("Sample Rate (Hz)", 100, 100_000, 10_000, step=100)

        waveform  = st.selectbox("Waveform", WAVEFORMS)
        freq      = st.slider("Signal Frequency (Hz)", 1,
                              min(sample_rate // 3, 5000), min(100, sample_rate // 10))
        amplitude = st.slider("Amplitude", 0.1, 1.0, 1.0, step=0.05)

    # ── File upload (overrides synthetic signal) ─────────────────────────
    with st.expander("📂 Upload your own signal file"):
        uploaded_signal, uploaded_sr = show_file_upload()

    # ── Signal source selection ──────────────────────────────────────────
    if uploaded_signal is not None:
        signal      = uploaded_signal
        sample_rate = uploaded_sr
        t           = np.linspace(0, len(signal) / sample_rate, len(signal))
        st.info(f"Using uploaded signal: {len(signal):,} samples at {sample_rate:,} Hz")
    else:
        duration   = max(20 / freq, 0.05)
        t, signal  = generate_waveform(waveform, freq, duration, sample_rate, amplitude)

    # ── Compute all metrics ──────────────────────────────────────────────
    quantized = quantize(signal, bits)
    snr       = compute_snr(signal, quantized)
    enob      = compute_enob(snr)
    thd       = compute_thd(signal, quantized, freq, sample_rate)
    sinad     = compute_sinad(signal, quantized, sample_rate, freq)
    ideal_snr = 6.02 * bits + 1.76
    step      = 2.0 / (2 ** bits)

    # ── Metrics row ──────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("SNR",        f"{snr:.2f} dB",  help="Measured signal-to-noise ratio")
    c2.metric("Ideal SNR",  f"{ideal_snr:.1f} dB", help="6.02×N + 1.76 dB")
    c3.metric("ENOB",       f"{enob:.3f} bits", help="(SNR − 1.76) / 6.02")
    c4.metric("SINAD",      f"{sinad:.2f} dB", help="Includes harmonic distortion")
    c5.metric("THD",        f"{thd:.1f} dB" if thd > -90 else "< −90 dB",
              help="Total harmonic distortion at 2f…8f")
    c6.metric("1 LSB",      f"{step*1000:.3f} mV", help="Smallest measurable step")

    # ── Preset comparison ────────────────────────────────────────────────
    if preset:
        enob_gap = preset["enob_typ"] - enob
        if enob_gap > 1:
            st.warning(
                f"⚠ Simulated ENOB ({enob:.2f} bits) is {enob_gap:.1f} bits below "
                f"this ADC's typical datasheet ENOB ({preset['enob_typ']:.1f} bits). "
                f"Real ADC has additional noise sources not in pure quantization model."
            )
        else:
            st.success(
                f"✓ Simulated ENOB ({enob:.2f} bits) matches "
                f"datasheet typical ({preset['enob_typ']:.1f} bits) within 1 bit."
            )

    # ── Tabbed analysis ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Parameter Sweep", "DNL / INL", "ENOB vs Frequency",
        "Coherent Sampling", "Quantum T1/T2"
    ])

    with tab1:
        show_parameter_sweep(signal, sample_rate, freq)

    with tab2:
        show_dnl_inl(signal, bits)

    with tab3:
        show_enob_vs_freq(bits, sample_rate)

    with tab4:
        n_samples = len(signal)
        show_coherent_sampling(freq, sample_rate, n_samples)

    with tab5:
        show_t1_t2_tradeoff()

    # ── Export ──────────────────────────────────────────────────────────
    metrics = {
        "bits": bits, "sample_rate": sample_rate, "freq": freq,
        "snr_db": round(snr, 4), "ideal_snr_db": round(ideal_snr, 2),
        "enob_bits": round(enob, 4), "sinad_db": round(sinad, 4),
        "thd_db": round(thd, 2) if thd > -90 else -90,
        "step_v": round(step, 8), "n_samples": len(signal),
    }
    with st.expander("💾 Export results"):
        show_export_panel(metrics)
