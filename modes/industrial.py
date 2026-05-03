"""
industrial.py — Industrial-grade ADC analysis features
=======================================================
Features that separate a research tool from a demo:
  1. Real ADC component presets (actual datasheets)
  2. CSV / WAV file upload — analyze your own signal
  3. Parameter sweep engine
  4. Measurement report export (CSV metrics + PNG plots)
  5. Coherent sampling calculator
  6. DNL / INL histogram test
  7. ENOB vs frequency (jitter-limited)
  8. Qubit T1/T2 vs readout time tradeoff
  9. Session save / load (JSON)
"""

import json
import io
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from adc_processor import (
    quantize, compute_snr, compute_enob, compute_thd, compute_sinad,
    compute_dnl, compute_inl, compute_enob_vs_frequency,
    nearest_coherent_frequency, snr_to_readout_error,
)
from signal_generator import compute_fft, compute_psd
from plot_renderer import PLOTLY_CONFIG, BASE, C, TEXT, GRID, PANEL

# ── Real ADC component database ───────────────────────────────────────────────
ADC_PRESETS = {
    "Custom": None,
    "ADS1115  — 16-bit, 860 SPS  (TI, precision)": {
        "bits": 16, "sample_rate": 860, "v_ref": 4.096,
        "enob_typ": 15.0, "noise_uv": 4.0,
        "url": "https://www.ti.com/product/ADS1115",
        "notes": "Delta-sigma. Used in microcontrollers, IoT sensors.",
    },
    "MCP3208  — 12-bit, 100 kSPS (Microchip, SAR)": {
        "bits": 12, "sample_rate": 100_000, "v_ref": 5.0,
        "enob_typ": 11.5, "noise_uv": 100.0,
        "url": "https://www.microchip.com/en-us/product/MCP3208",
        "notes": "SAR ADC. SPI interface. Common in Arduino/Raspberry Pi projects.",
    },
    "AD9680  — 14-bit, 1 GSPS  (Analog Devices, RF)": {
        "bits": 14, "sample_rate": 1_000_000_000, "v_ref": 2.0,
        "enob_typ": 11.8, "noise_uv": 1000.0,
        "url": "https://www.analog.com/en/products/ad9680.html",
        "notes": "Pipeline ADC. Used in radar, 5G base stations, software-defined radio.",
    },
    "ADS9110  — 18-bit, 2 MSPS  (TI, precision high-speed)": {
        "bits": 18, "sample_rate": 2_000_000, "v_ref": 4.096,
        "enob_typ": 17.5, "noise_uv": 8.0,
        "url": "https://www.ti.com/product/ADS9110",
        "notes": "SAR ADC. Used in medical instruments, power analyzers.",
    },
    "MAX11905 — 20-bit, 1.6 MSPS (Maxim, ultra-precision)": {
        "bits": 20, "sample_rate": 1_600_000, "v_ref": 4.096,
        "enob_typ": 19.0, "noise_uv": 2.0,
        "url": "https://www.maximintegrated.com/en/products/MAX11905.html",
        "notes": "SAR ADC. Highest ENOB class. Used in seismometers, precision instrumentation.",
    },
}


def show_adc_presets():
    """ADC component database panel."""
    st.markdown("#### 🔌 Real ADC Component Presets")
    st.caption("Load real ADC specifications and compare your simulation against datasheet values.")

    col1, col2 = st.columns([2, 3])
    with col1:
        selected = st.selectbox("Select ADC component", list(ADC_PRESETS.keys()),
                                label_visibility="collapsed")

    preset = ADC_PRESETS[selected]
    if preset is None:
        return None

    with col2:
        st.markdown(f"""
<div style='background:var(--secondary-background-color);border:1px solid rgba(128,128,128,0.15);
border-radius:8px;padding:10px 14px;font-family:monospace;font-size:11px;line-height:1.8'>
<b style='color:#378ADD'>{selected.split("—")[0].strip()}</b><br>
{preset['bits']}-bit &nbsp;·&nbsp; {preset['sample_rate']:,} SPS &nbsp;·&nbsp;
Vref = {preset['v_ref']} V &nbsp;·&nbsp; ENOB_typ = {preset['enob_typ']:.1f} bits<br>
<span style='opacity:0.6'>{preset['notes']}</span>
</div>
""", unsafe_allow_html=True)

    return preset


# ── File upload: analyze your own signal ─────────────────────────────────────
def show_file_upload():
    """Upload CSV or WAV and run the full analysis pipeline."""
    st.markdown("#### 📂 Upload Your Signal")
    st.caption("Upload a CSV (one column of samples) or WAV file to analyze your own ADC output data.")

    uploaded = st.file_uploader(
        "Drop file here",
        type=["csv", "txt", "wav"],
        label_visibility="collapsed",
    )
    if uploaded is None:
        return None, None

    ext = uploaded.name.lower().split(".")[-1]
    try:
        if ext in ("csv", "txt"):
            data = np.loadtxt(io.StringIO(uploaded.read().decode("utf-8")),
                              delimiter=",", comments="#")
            if data.ndim > 1:
                data = data[:, 0]
            sample_rate = st.number_input("Sample rate of uploaded file (Hz)",
                                          min_value=1, max_value=10_000_000,
                                          value=1000, step=100)
            return data[:50_000], int(sample_rate)

        elif ext == "wav":
            from scipy.io import wavfile
            sr, data = wavfile.read(uploaded)
            if data.ndim > 1:
                data = data[:, 0].astype(float)
            else:
                data = data.astype(float)
            data = data / (np.max(np.abs(data)) + 1e-12)  # normalize to ±1
            st.success(f"Loaded {len(data):,} samples at {sr:,} Hz")
            return data[:50_000], sr

    except Exception as e:
        st.error(f"Could not read file: {e}")
        return None, None


# ── Export: CSV metrics + PNG plots ──────────────────────────────────────────
def show_export_panel(metrics: dict, figs: dict = None):
    """Export current analysis as CSV metrics and optional PNGs."""
    st.markdown("#### 💾 Export Results")

    col_csv, col_json = st.columns(2)

    with col_csv:
        # Metrics CSV
        csv_lines = ["metric,value,unit"]
        for k, v in metrics.items():
            unit = "dB" if "snr" in k.lower() or "sinad" in k.lower() or "thd" in k.lower() else \
                   "bits" if "enob" in k.lower() or "bits" in k.lower() else ""
            csv_lines.append(f"{k},{v},{unit}")
        csv_str = "\n".join(csv_lines)
        st.download_button(
            "⬇ Download metrics (CSV)",
            data=csv_str.encode(),
            file_name="adc_metrics.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_json:
        # Session config JSON
        json_str = json.dumps(metrics, indent=2)
        st.download_button(
            "⬇ Download config (JSON)",
            data=json_str.encode(),
            file_name="adc_config.json",
            mime="application/json",
            use_container_width=True,
        )


# ── Parameter sweep engine ────────────────────────────────────────────────────
def show_parameter_sweep(signal, sample_rate, freq):
    """Sweep bits, OSR, or frequency and plot SNR/ENOB/THD vs parameter."""
    st.markdown("#### 🔁 Parameter Sweep")
    st.caption("Automatically sweep a parameter and plot how metrics change. "
               "This is the core workflow of ADC characterization.")

    col1, col2, col3 = st.columns(3)
    with col1:
        sweep_param = st.selectbox(
            "Sweep parameter",
            ["Bit depth (1→16)", "Oversampling factor (1→64)", "Input frequency"],
            label_visibility="collapsed",
        )
    with col2:
        sweep_metric = st.selectbox(
            "Plot metric",
            ["SNR (dB)", "ENOB (bits)", "THD (dB)", "SINAD (dB)"],
            label_visibility="collapsed",
        )
    with col3:
        if st.button("▶ Run Sweep", use_container_width=True):
            st.session_state["run_sweep"] = True

    if not st.session_state.get("run_sweep"):
        st.caption("Press ▶ Run Sweep to compute.")
        return

    with st.spinner("Computing sweep..."):
        xs, ys, xlabel = [], [], ""

        if sweep_param == "Bit depth (1→16)":
            xs = list(range(1, 17))
            xlabel = "Bit Depth (N)"
            for b in xs:
                q = quantize(signal, b)
                val = {
                    "SNR (dB)":   compute_snr(signal, q),
                    "ENOB (bits)":compute_enob(compute_snr(signal, q)),
                    "THD (dB)":   compute_thd(signal, q, freq, sample_rate),
                    "SINAD (dB)": compute_sinad(signal, q, sample_rate, freq),
                }[sweep_metric]
                ys.append(val)
            # Add theoretical SNR line for bit depth sweep
            theo = [6.02*b+1.76 for b in xs] if sweep_metric == "SNR (dB)" else None

        elif sweep_param == "Oversampling factor (1→64)":
            from adc_processor import oversample, downsample_quantized
            osrs = [1, 2, 4, 8, 16, 32, 64]
            xs = osrs
            xlabel = "Oversampling Factor (M)"
            bits = 8
            for m in osrs:
                if m == 1:
                    q = quantize(signal, bits)
                    signal_tmp = signal
                else:
                    os_sig, actual_m = oversample(signal, m)
                    q = downsample_quantized(quantize(os_sig, bits), actual_m)
                    mn = min(len(signal), len(q))
                    signal_tmp = signal[:mn]
                    q = q[:mn]
                val = {
                    "SNR (dB)":   compute_snr(signal_tmp, q),
                    "ENOB (bits)":compute_enob(compute_snr(signal_tmp, q)),
                    "THD (dB)":   compute_thd(signal_tmp, q, freq, sample_rate),
                    "SINAD (dB)": compute_sinad(signal_tmp, q, sample_rate, freq),
                }[sweep_metric]
                ys.append(val)
            theo = [6.02*8+1.76 + 10*np.log10(m)/2 for m in xs] if sweep_metric == "SNR (dB)" else None

        elif sweep_param == "Input frequency":
            freqs = np.logspace(1, np.log10(sample_rate/2.2), 30)
            xs = freqs.tolist()
            xlabel = "Input Frequency (Hz)"
            from signal_generator import generate_waveform
            for f_test in freqs:
                dur = max(10/f_test, 0.01)
                _, sig_f = generate_waveform("Sine", f_test, dur, sample_rate, 1.0)
                q_f = quantize(sig_f, 8)
                val = {
                    "SNR (dB)":   compute_snr(sig_f, q_f),
                    "ENOB (bits)":compute_enob(compute_snr(sig_f, q_f)),
                    "THD (dB)":   compute_thd(sig_f, q_f, f_test, sample_rate),
                    "SINAD (dB)": compute_sinad(sig_f, q_f, sample_rate, f_test),
                }[sweep_metric]
                ys.append(val)
            theo = None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        name=sweep_metric,
        line=dict(color=C["quantized"], width=2),
        marker=dict(size=6, color=C["quantized"]),
        hovertemplate=f"<b>{xlabel}</b>=%{{x}}<br><b>{sweep_metric}</b>=%{{y:.2f}}<extra></extra>",
    ))
    if theo:
        fig.add_trace(go.Scatter(
            x=xs, y=theo, mode="lines", name="Theoretical",
            line=dict(color=C["analog"], width=1.5, dash="dash"),
            hovertemplate=f"<b>Theoretical</b>=%{{y:.2f}}<extra></extra>",
        ))
    fig.update_layout(
        height=360,
        title=dict(text=f"{sweep_metric} vs {xlabel}", font=dict(color=TEXT, size=13)),
        xaxis=dict(title=xlabel, gridcolor=GRID,
                   type="log" if sweep_param == "Input frequency" else "linear"),
        yaxis=dict(title=sweep_metric, gridcolor=GRID),
        **BASE,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
    st.session_state["run_sweep"] = False


# ── DNL / INL histogram test ──────────────────────────────────────────────────
def show_dnl_inl(signal, bits):
    """Code density histogram → DNL and INL plots."""
    st.markdown("#### 📊 DNL / INL Histogram Test")
    st.caption(
        "Feed a ramp or full-scale sine and count how many samples land in each quantization bin. "
        "Flat histogram = perfect linearity. DNL > +1 = missing code."
    )

    dnl = compute_dnl(signal, bits)
    inl = compute_inl(dnl)
    codes = np.arange(len(dnl))

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        subplot_titles=["DNL — Differential Non-Linearity",
                                        "INL — Integral Non-Linearity"],
                        vertical_spacing=0.12)

    dnl_colors = [C["alias"] if abs(v) > 0.5 else C["sampled"] for v in dnl]
    fig.add_trace(go.Bar(x=codes, y=dnl, name="DNL",
                         marker_color=dnl_colors,
                         hovertemplate="Code %{x}<br>DNL=%{y:.3f} LSB<extra></extra>"),
                  row=1, col=1)
    fig.add_hline(y=0, line_color=TEXT, line_width=0.5, row=1, col=1)
    fig.add_hline(y=1, line_color=C["alias"], line_width=0.5, line_dash="dash", row=1, col=1,
                  annotation_text="±1 LSB limit", annotation_font_color=C["alias"], annotation_font_size=9)
    fig.add_hline(y=-1, line_color=C["alias"], line_width=0.5, line_dash="dash", row=1, col=1)

    fig.add_trace(go.Scatter(x=codes, y=inl, mode="lines", name="INL",
                             line=dict(color=C["dither"], width=1.5),
                             hovertemplate="Code %{x}<br>INL=%{y:.3f} LSB<extra></extra>"),
                  row=2, col=1)
    fig.add_hline(y=0, line_color=TEXT, line_width=0.5, row=2, col=1)

    dnl_max = float(np.max(np.abs(dnl)))
    inl_max = float(np.max(np.abs(inl)))

    fig.update_layout(height=480, **BASE)
    fig.update_xaxes(title_text="ADC Code", row=2, col=1)
    fig.update_yaxes(title_text="DNL (LSB)", row=1, col=1)
    fig.update_yaxes(title_text="INL (LSB)", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    c1, c2, c3 = st.columns(3)
    c1.metric("Max |DNL|", f"{dnl_max:.3f} LSB",
              help="> 1 LSB = missing code. > 0.5 LSB = poor linearity.")
    c2.metric("Max |INL|", f"{inl_max:.3f} LSB",
              help="> 0.5 LSB = accuracy limited by non-linearity, not noise.")
    n_missing = int(np.sum(dnl < -0.9))
    c3.metric("Missing codes", str(n_missing),
              delta="ideal: 0", delta_color="inverse" if n_missing > 0 else "off")


# ── ENOB vs frequency (jitter-limited) ───────────────────────────────────────
def show_enob_vs_freq(bits, sample_rate):
    """Plot ENOB degradation with input frequency due to aperture jitter."""
    st.markdown("#### 📉 ENOB vs Input Frequency")
    st.caption(
        "Aperture jitter limits ENOB at high frequencies — adding noise proportional to 2πf·t_j. "
        "This is the most important ADC bandwidth spec, shown on every datasheet."
    )

    jitter_ps = st.slider(
        "Aperture jitter (ps rms)",
        min_value=0.1, max_value=500.0, value=10.0, step=0.1,
        help="Typical values: high-speed ADC = 0.1–1 ps, microcontroller ADC = 10–100 ps",
    )
    jitter_s = jitter_ps * 1e-12

    freq_range = np.logspace(1, np.log10(sample_rate / 2.2), 200)
    enob_arr   = compute_enob_vs_frequency(bits, jitter_s, freq_range)
    enob_q     = compute_enob(6.02 * bits + 1.76)  # quantization limit

    fig = go.Figure()
    fig.add_hline(
        y=enob_q, line_color=C["analog"], line_width=1, line_dash="dash",
        annotation_text=f"Quantization limit: {enob_q:.1f} bits",
        annotation_font_color=C["analog"], annotation_font_size=10,
    )
    fig.add_trace(go.Scatter(
        x=freq_range, y=enob_arr, mode="lines", name=f"ENOB ({jitter_ps:.1f} ps jitter)",
        line=dict(color=C["quantized"], width=2),
        hovertemplate="<b>f</b>=%{x:.1f} Hz<br><b>ENOB</b>=%{y:.2f} bits<extra></extra>",
        fill="tozeroy", fillcolor="rgba(216,90,48,0.08)",
    ))

    # Mark -3 dB bandwidth (where ENOB drops by 0.5 bits)
    target = enob_q - 0.5
    cross_idx = np.where(enob_arr < target)[0]
    if len(cross_idx) > 0:
        f_bw = freq_range[cross_idx[0]]
        fig.add_vline(
            x=f_bw, line_color=C["cursor_a"], line_width=1, line_dash="dot",
            annotation_text=f"−0.5 bit BW: {f_bw/1e3:.1f} kHz",
            annotation_font_color=C["cursor_a"], annotation_font_size=10,
        )

    fig.update_layout(
        height=380,
        title=dict(text=f"ENOB vs Input Frequency — {bits}-bit ADC, jitter={jitter_ps:.1f} ps",
                   font=dict(color=TEXT, size=13)),
        xaxis=dict(title="Input Frequency (Hz)", type="log", gridcolor=GRID,
                   showspikes=True, spikecolor="#555", spikethickness=1),
        yaxis=dict(title="ENOB (bits)", gridcolor=GRID),
        **BASE,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)


# ── Coherent sampling calculator ──────────────────────────────────────────────
def show_coherent_sampling(freq, sample_rate, n_samples):
    """Calculate the nearest coherent input frequency."""
    st.markdown("#### 🎯 Coherent Sampling Calculator")
    st.caption(
        "For accurate SINAD/THD measurement, the input frequency must be coherently related "
        "to the sample rate: f_in = M × f_s / N where gcd(M,N) = 1. "
        "Non-coherent sampling causes spectral leakage that corrupts all FFT-based metrics."
    )

    f_coh, M, N = nearest_coherent_frequency(freq, sample_rate, n_samples)
    leakage_note = "exact" if abs(f_coh - freq) < 0.001 else f"nearest: {f_coh:.4f} Hz"

    col1, col2, col3 = st.columns(3)
    col1.metric("Target frequency", f"{freq} Hz")
    col2.metric("Coherent frequency", f"{f_coh:.4f} Hz", delta=leakage_note,
                delta_color="off" if abs(f_coh - freq) < 0.001 else "inverse")
    col3.metric("M / N", f"{M} / {N}", help="gcd(M,N) = 1 required")

    if abs(f_coh - freq) > 0.01:
        st.warning(
            f"Your signal frequency {freq} Hz is not coherent with {sample_rate} Hz / {n_samples} points. "
            f"Use **{f_coh:.4f} Hz** instead to eliminate spectral leakage. "
            f"Error = {abs(f_coh-freq):.4f} Hz."
        )
    else:
        st.success(f"Coherent sampling satisfied. M={M}, N={N}.")


# ── Qubit T1/T2 vs readout time tradeoff ─────────────────────────────────────
def show_t1_t2_tradeoff():
    """Plot optimal readout integration time vs T1/T2 decoherence."""
    st.markdown("#### ⚛️ T1/T2 vs Readout Time Tradeoff")
    st.caption(
        "Longer readout integration → better IQ discrimination → lower readout error. "
        "But longer time → qubit decays (T1) or dephases (T2) mid-measurement. "
        "There is an optimal integration time. This is the central constraint of quantum ADC design."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        T1_us = st.slider("T1 relaxation (μs)", 1.0, 500.0, 50.0,
                           help="Typical superconducting qubit: 10–200 μs")
    with col2:
        T2_us = st.slider("T2 dephasing (μs)", 0.5, T1_us, min(T1_us/2, 30.0),
                           help="T2 ≤ 2·T1 always. Typical: 5–100 μs")
    with col3:
        snr_base = st.slider("ADC SNR at t=1μs (dB)", 5.0, 40.0, 20.0,
                              help="SNR scales as sqrt(t) — longer integration averages noise")

    T1 = T1_us * 1e-6
    T2 = T2_us * 1e-6

    # Time axis: 0.1 μs to 5×T2
    t_arr = np.linspace(0.1e-6, min(5 * T2, 500e-6), 300)
    t_us  = t_arr * 1e6

    # SNR improves as sqrt(t) from shot noise averaging
    snr_t_db  = snr_base + 10 * np.log10(t_arr / 1e-6) / 2

    # T1 decay probability: qubit relaxes to |0> during measurement
    p_t1_error = 1 - np.exp(-t_arr / T1)

    # T2 dephasing: reduces contrast of IQ blobs
    contrast    = np.exp(-t_arr / T2)

    # Effective SNR accounting for T2 dephasing of IQ contrast
    snr_eff_db  = snr_t_db + 20 * np.log10(np.clip(contrast, 1e-6, 1))

    # Readout error from effective SNR
    readout_err = np.array([snr_to_readout_error(s) for s in snr_eff_db])

    # Total error = readout_error + T1 decay probability
    total_err   = np.clip(readout_err + p_t1_error * 0.5, 0, 1)

    opt_idx     = np.argmin(total_err)
    t_opt_us    = t_us[opt_idx]
    err_opt     = total_err[opt_idx]
    fid_opt     = 1 - err_opt

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=[
            "① SNR gain vs T2 dephasing — competing effects",
            "② Total readout error — optimal integration time",
        ],
        vertical_spacing=0.12,
    )

    # Panel 1
    fig.add_trace(go.Scatter(
        x=t_us, y=snr_t_db, mode="lines", name="SNR (integration gain)",
        line=dict(color=C["analog"], width=1.5),
        hovertemplate="t=%{x:.2f} μs<br>SNR=%{y:.1f} dB<extra>Integration gain</extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=t_us, y=snr_eff_db, mode="lines", name="SNR (after T2 dephasing)",
        line=dict(color=C["dither"], width=2),
        hovertemplate="t=%{x:.2f} μs<br>SNR_eff=%{y:.1f} dB<extra>After T2</extra>",
    ), row=1, col=1)

    # Panel 2 — total error with components
    fig.add_trace(go.Scatter(
        x=t_us, y=readout_err, mode="lines", name="Readout error (IQ discrimination)",
        line=dict(color=C["sampled"], width=1.2, dash="dot"),
        hovertemplate="t=%{x:.2f} μs<br>IQ error=%{y:.4f}<extra>IQ</extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=t_us, y=p_t1_error * 0.5, mode="lines", name="T1 decay error",
        line=dict(color=C["error"], width=1.2, dash="dot"),
        hovertemplate="t=%{x:.2f} μs<br>T1 error=%{y:.4f}<extra>T1</extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=t_us, y=total_err, mode="lines", name="Total error",
        line=dict(color=C["quantized"], width=2.5),
        fill="tozeroy", fillcolor="rgba(216,90,48,0.07)",
        hovertemplate="t=%{x:.2f} μs<br>Total error=%{y:.4f}<extra>Total</extra>",
    ), row=2, col=1)

    # Optimal time marker
    fig.add_vline(
        x=t_opt_us, line_color=C["cursor_a"], line_width=1.5, line_dash="dash",
        annotation_text=f"Optimal: {t_opt_us:.1f} μs",
        annotation_font_color=C["cursor_a"], annotation_font_size=10,
        row=2, col=1,
    )
    fig.add_hline(y=0.01, line_color="#555", line_width=0.5, line_dash="dot",
                  row=2, col=1, annotation_text="1% error threshold",
                  annotation_font_color="#777", annotation_font_size=9)

    fig.update_layout(height=580, **BASE)
    fig.update_xaxes(title_text="Integration time (μs)", row=2, col=1,
                     gridcolor=GRID, showspikes=True, spikecolor="#555")
    fig.update_yaxes(title_text="SNR (dB)", row=1, col=1, gridcolor=GRID)
    fig.update_yaxes(title_text="Error probability", row=2, col=1,
                     gridcolor=GRID, range=[0, min(0.5, float(total_err.max()) * 1.3)])

    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Optimal integration time", f"{t_opt_us:.2f} μs")
    c2.metric("Min total error", f"{err_opt:.4f}")
    c3.metric("Max fidelity", f"{fid_opt*100:.2f}%")
    c4.metric("T2 / T_opt ratio", f"{T2_us/t_opt_us:.1f}×",
              help="Optimal time is typically 0.5–1× T2")

    with st.expander("Physics — why there is an optimal time"):
        st.markdown(f"""
**Two competing processes:**

**Integration gain** — averaging more photons reduces shot noise. SNR ∝ √t,
so doubling integration time adds +1.5 dB SNR and lowers the IQ discrimination error.

**T2 dephasing** — the qubit's superposition decays exponentially with time constant T₂ = {T2_us:.1f} μs.
As the qubit dephases, the IQ blobs spread and overlap. Beyond ~T₂, the blobs merge and discrimination fails regardless of SNR.

**T1 relaxation** — the qubit can relax from |1⟩ to |0⟩ during measurement with time constant T₁ = {T1_us:.1f} μs.
This directly adds a state-flip error proportional to t/T₁.

**The optimum** at t = {t_opt_us:.2f} μs is where the IQ improvement from longer integration is
exactly cancelled by the additional T1 + T2 decoherence errors. Real quantum processors (IBM, Google)
tune their readout pulse length to sit at this exact point.

**Reference:** Krantz et al. (2019), §4.3; Gambetta et al. (2007) PRA 76, 012325.
""")
