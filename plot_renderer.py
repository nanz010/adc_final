"""
plot_renderer.py  —  ADC Analysis Platform
All Plotly figures with full LTspice-inspired interactivity.

Features included in every plot:
  1. Hover tooltip          exact time + amplitude on all traces simultaneously
  2. Zoom in/out            scroll wheel or toolbar buttons
  3. Pan                    click-drag after zooming
  4. Box-select zoom        draw a rectangle to zoom into that region
  5. Reset zoom             double-click anywhere or toolbar Home
  6. Spike lines            crosshair on ALL panels at same x-position
  7. Show/Hide traces       click any legend item to toggle
  8. PNG export             toolbar camera button at 2x resolution
  9. Dual cursors           Cursor A (amber) + Cursor B (teal) vertical lines
                            delta-time shown below the chart
  10. Annotation tool       toolbar Draw Line tool to add custom markers
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── Color theme ───────────────────────────────────────────────────────────────
BG    = "#0F1117"
PANEL = "#1a1a1a"
GRID  = "#2a2a2a"
TEXT  = "#FAFAFA"
MUTED = "#888888"

C = {
    "analog":    "#378ADD",
    "sampled":   "#1D9E75",
    "quantized": "#D85A30",
    "error":     "#BA7517",
    "dither":    "#7F77DD",
    "alias":     "#E24B4A",
    "cursor_a":  "#FAC775",
    "cursor_b":  "#9FE1CB",
}

# ── Base layout applied to every figure ──────────────────────────────────────
BASE = dict(
    paper_bgcolor=BG,
    plot_bgcolor=PANEL,
    font=dict(color=TEXT, family="monospace", size=12),
    hovermode="x unified",
    margin=dict(l=65, r=45, t=55, b=65),
    legend=dict(
        bgcolor="rgba(26,26,26,0.92)",
        bordercolor="#444",
        borderwidth=1,
        font=dict(size=11),
    ),
)

# ── Smooth rendering — prevents choppy curves when zoomed out ─────────────────
def _smooth(x, y, max_pts=2000, staircase=False):
    """Downsample large arrays for smooth rendering at all zoom levels.

    staircase=True  → used for quantized signals: keep ALL unique level transitions,
                      never drop step edges. Show up to max_pts points but always
                      preserve every level-change point so steps stay visible at
                      ALL bit depths (1-bit coarse staircase through 16-bit fine steps).
    staircase=False → min-max decimation for analog/continuous signals.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    n = len(x)
    if n <= max_pts:
        return x, y

    if staircase:
        # Keep every point where the quantized value changes — those are the stair edges.
        # Plus first/last, plus evenly spaced fill to max_pts.
        changes = np.where(np.diff(y) != 0)[0] + 1
        keep    = set([0, n - 1])
        for c in changes:
            keep.add(max(0, c - 1))   # just before the step
            keep.add(c)               # the step itself
        if len(keep) < max_pts:
            fill_n   = max_pts - len(keep)
            fill_idx = np.linspace(0, n - 1, fill_n + 2, dtype=int)[1:-1]
            keep.update(fill_idx.tolist())
        idx = np.array(sorted(keep), dtype=int)
        return x[idx], y[idx]

    bucket      = max(1, n // (max_pts // 2))
    sig_range   = float(np.ptp(y)) if len(y) > 0 else 1.0
    edge_thresh = 0.8 * sig_range

    new_x, new_y = [], []

    for i in range(0, n - bucket, bucket):
        chunk_y = y[i:i + bucket]
        chunk_x = x[i:i + bucket]
        imin = int(np.argmin(chunk_y))
        imax = int(np.argmax(chunk_y))
        chunk_range = float(chunk_y[imax] - chunk_y[imin])

        if sig_range > 0 and chunk_range > edge_thresh:
            # Edge bucket — keep first, min, max, last in time order
            pts = sorted({0, imin, imax, len(chunk_y) - 1})
            for p in pts:
                new_x.append(chunk_x[p])
                new_y.append(chunk_y[p])
        else:
            # Smooth region — normal min-max decimation
            if imin < imax:
                new_x += [chunk_x[imin], chunk_x[imax]]
                new_y += [chunk_y[imin], chunk_y[imax]]
            else:
                new_x += [chunk_x[imax], chunk_x[imin]]
                new_y += [chunk_y[imax], chunk_y[imin]]

    return np.array(new_x), np.array(new_y)


# ── Config dict passed to st.plotly_chart ─────────────────────────────────────
PLOTLY_CONFIG = dict(
    scrollZoom=True,
    displayModeBar=True,
    modeBarButtonsToAdd=["drawline", "eraseshape"],
    modeBarButtonsToRemove=["lasso2d"],
    toImageButtonOptions=dict(
        format="png",
        filename="adc_waveform",
        height=900, width=1500, scale=2,
    ),
)


def _apply_axes(fig, n_rows):
    """Apply grid + spike lines to every axis panel."""
    style = dict(
        gridcolor=GRID,
        zerolinecolor=GRID,
        zerolinewidth=1,
        showspikes=True,        # spike line = crosshair on hover
        spikecolor="#555555",
        spikethickness=1,
        spikedash="dot",
        spikemode="across",     # spans across ALL panels
    )
    for i in range(1, n_rows + 1):
        xk = "xaxis" if i == 1 else f"xaxis{i}"
        yk = "yaxis" if i == 1 else f"yaxis{i}"
        fig.update_layout(**{xk: style, yk: style})
    return fig


def _cursor_shapes(x_min, x_max):
    """Two vertical cursor lines: Cursor A (amber) and Cursor B (teal)."""
    span = x_max - x_min
    ca   = x_min + span * 0.25
    cb   = x_min + span * 0.75
    return [
        dict(type="line", x0=ca, x1=ca, y0=0, y1=1, yref="paper",
             line=dict(color=C["cursor_a"], width=1.5, dash="dash")),
        dict(type="line", x0=cb, x1=cb, y0=0, y1=1, yref="paper",
             line=dict(color=C["cursor_b"], width=1.5, dash="dash")),
    ]


def _cursor_label(x_min, x_max):
    """Delta-time annotation shown below the chart."""
    span  = x_max - x_min
    ca    = x_min + span * 0.25
    cb    = x_min + span * 0.75
    delta = cb - ca
    return dict(
        text=(f"<b style='color:{C['cursor_a']}'>Cursor A</b>: {ca:.5f} s  |  "
              f"<b style='color:{C['cursor_b']}'>Cursor B</b>: {cb:.5f} s  |  "
              f"<b>ΔT</b>: {delta:.5f} s  "
              f"<span style='color:{MUTED}'>"
              f"(use toolbar Draw Line to reposition cursors)</span>"),
        xref="paper", yref="paper",
        x=0.0, y=-0.08,
        showarrow=False,
        font=dict(size=10, color=TEXT),
        align="left",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1.  STANDARD ADC  — 4-panel time domain
# ─────────────────────────────────────────────────────────────────────────────
def plot_standard(t, analog, sampled_t, sampled, quantized, error, bits=8):
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "① Analog signal (continuous)",
            "② Sampled signal",
            "③ Quantized output (staircase)",
            "④ Quantization error",
        ],
        vertical_spacing=0.06,
    )

    # Panel 1 — smooth analog signal
    t_s, a_s = _smooth(t, analog)
    fig.add_trace(go.Scatter(
        x=t_s, y=a_s, mode="lines", name="Analog", connectgaps=True,
        line=dict(color=C["analog"], width=1.5),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>amp</b>=%{y:.6f}<extra>Analog</extra>",
    ), row=1, col=1)

    # Panel 2 — sampled stems + dots. Max 300 stems for visual clarity.
    max_stems = 300
    if len(sampled_t) > max_stems:
        idx   = np.linspace(0, len(sampled_t) - 1, max_stems, dtype=int)
        st_t  = sampled_t[idx]
        st_v  = sampled[idx]
    else:
        st_t = sampled_t
        st_v = sampled

    stem_x, stem_y = [], []
    for xi, yi in zip(st_t, st_v):
        stem_x += [xi, xi, None]
        stem_y += [0,  yi, None]

    fig.add_trace(go.Scatter(
        x=stem_x, y=stem_y, mode="lines",
        line=dict(color=C["sampled"], width=0.8),
        name="Stems", showlegend=False, hoverinfo="skip",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=st_t, y=st_v, mode="markers", name="Sampled",
        marker=dict(color=C["sampled"], size=4),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>amp</b>=%{y:.6f}<extra>Sampled</extra>",
    ), row=2, col=1)

    # Panel 3 — quantized staircase.
    # Use staircase=True so every level transition is preserved at ALL bit depths.
    # This fixes the "flat line at high bits" bug — fine steps are never decimated away.
    t_s2, samp_s = _smooth(sampled_t, sampled)
    t_s3, quan_s = _smooth(sampled_t, quantized, staircase=True)
    fig.add_trace(go.Scatter(
        x=t_s2, y=samp_s, mode="lines", name="Sampled (ref)",
        line=dict(color=C["sampled"], width=1, dash="dot"),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>sampled</b>=%{y:.6f}<extra>Sampled ref</extra>",
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=t_s3, y=quan_s, mode="lines", name="Quantized", connectgaps=True,
        line=dict(color=C["quantized"], width=2, shape="hv"),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>quantized</b>=%{y:.6f}<extra>Quantized</extra>",
    ), row=3, col=1)

    # Panel 4 — quantization error.
    # Use staircase=True to preserve the step structure of the error signal.
    t_s4, err_s = _smooth(sampled_t, error, staircase=True)
    fig.add_trace(go.Scatter(
        x=t_s4, y=err_s, mode="lines", name="Q-Error",
        fill="tozeroy", fillcolor="rgba(186,117,23,0.25)",
        line=dict(color=C["error"], width=1),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>error</b>=%{y:.8f}<extra>Q-Error</extra>",
    ), row=4, col=1)
    fig.add_hline(y=0, line_color=TEXT, line_width=0.5, row=4, col=1)

    amp = float(np.max(np.abs(analog))) * 1.2

    # Error Y-axis: always ±(step/2)*1.5 so scale is readable at ALL bit depths.
    # At 16-bit, step = 0.0000305V — without this floor the panel looks like a flat line.
    step    = 2.0 / (2 ** bits)
    err_amp = max(float(np.max(np.abs(error))) * 1.8, step * 0.75)

    x_min, x_max = float(t[0]), float(t[-1])
    for s in _cursor_shapes(x_min, x_max):
        fig.add_shape(**s, row="all", col=1)

    fig.update_layout(
        height=880,
        annotations=[_cursor_label(x_min, x_max)],
        **BASE,
    )
    _apply_axes(fig, 4)
    fig.update_xaxes(title_text="Time (s)", row=4, col=1)
    for r, lbl in enumerate(["Amplitude (V)", "Amplitude (V)",
                              "Amplitude (V)", "Error (V)"], 1):
        fig.update_yaxes(title_text=lbl, row=r, col=1)

    # Lock Y ranges to signal amplitude — prevents wild auto-scaling
    fig.update_yaxes(range=[-amp, amp], row=1, col=1)
    fig.update_yaxes(range=[-amp, amp], row=2, col=1)
    fig.update_yaxes(range=[-amp, amp], row=3, col=1)
    fig.update_yaxes(range=[-err_amp, err_amp], row=4, col=1)

    # Lock X range to data bounds — prevents blank space on left/right
    for r in range(1, 5):
        fig.update_xaxes(range=[x_min, x_max], row=r, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 2.  OVERSAMPLING  — 2-panel comparison
# ─────────────────────────────────────────────────────────────────────────────
def plot_oversampling(t, normal, oversampled_dec, snr_normal, snr_over, original):
    gain = snr_over - snr_normal
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=[
            f"① Normal quantization — SNR = {snr_normal:.1f} dB",
            f"② Oversampled + decimated — SNR = {snr_over:.1f} dB   (+{gain:.1f} dB gain)",
        ],
        vertical_spacing=0.10,
    )

    for row, (sig, label, color) in enumerate([
        (normal,          "Normal",      C["quantized"]),
        (oversampled_dec, "Oversampled", C["sampled"]),
    ], start=1):
        t_s, o_s = _smooth(t, original)
        fig.add_trace(go.Scatter(
            x=t_s, y=o_s, mode="lines",
            name=f"Original {'(1)' if row==1 else '(2)'}",
            line=dict(color=C["analog"], width=1, dash="dot"),
            hovertemplate="<b>t</b>=%{x:.6f} s<br><b>orig</b>=%{y:.6f}<extra>Original</extra>",
        ), row=row, col=1)
        t_s2, sig_s = _smooth(t, sig, staircase=True)
        fig.add_trace(go.Scatter(
            x=t_s2, y=sig_s, mode="lines", name=label,
            line=dict(color=color, width=2, shape="hv"),
            hovertemplate=f"<b>t</b>=%{{x:.6f}} s<br><b>amp</b>=%{{y:.6f}}<extra>{label}</extra>",
        ), row=row, col=1)

    x_min, x_max = float(t[0]), float(t[-1])
    for s in _cursor_shapes(x_min, x_max):
        fig.add_shape(**s, row="all", col=1)

    fig.update_layout(
        height=580,
        annotations=[_cursor_label(x_min, x_max)],
        **BASE,
    )
    _apply_axes(fig, 2)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    fig.update_yaxes(title_text="Amplitude (V)", row=1, col=1)
    fig.update_yaxes(title_text="Amplitude (V)", row=2, col=1)
    for r in range(1, 3):
        fig.update_xaxes(range=[x_min, x_max], row=r, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3.  ALIASING  — 2-panel with warning box
# ─────────────────────────────────────────────────────────────────────────────
def plot_aliasing(t_orig, original, t_under, undersampled,
                  alias_detected, signal_freq, sample_rate, alias_freq):
    color  = C["alias"] if alias_detected else C["sampled"]
    title2 = (f"② Undersampled at {sample_rate:.0f} Hz  →  alias at {alias_freq:.1f} Hz"
              if alias_detected
              else f"② Sampled at {sample_rate:.0f} Hz  —  no aliasing")

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[f"① Original  {signal_freq:.0f} Hz", title2],
        vertical_spacing=0.15,
    )

    t_os, orig_s = _smooth(t_orig, original)
    fig.add_trace(go.Scatter(
        x=t_os, y=orig_s, mode="lines", name="Original", connectgaps=True,
        line=dict(color=C["analog"], width=1.5),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>amp</b>=%{y:.6f}<extra>Original</extra>",
    ), row=1, col=1)

    t_us, under_s = _smooth(t_under, undersampled)
    fig.add_trace(go.Scatter(
        x=t_us, y=under_s, mode="lines+markers",
        name="Undersampled" if alias_detected else "Sampled",
        line=dict(color=color, width=2),
        marker=dict(size=5, color=color),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>amp</b>=%{y:.6f}<extra>Sampled</extra>",
    ), row=2, col=1)

    ann = []
    if alias_detected:
        ann.append(dict(
            text=(f"  ⚠  ALIASING DETECTED  |  "
                  f"Signal = {signal_freq:.0f} Hz  >  "
                  f"Nyquist = {sample_rate/2:.0f} Hz  |  "
                  f"Alias = {alias_freq:.1f} Hz  "),
            xref="paper", yref="paper", x=0.5, y=-0.10,
            showarrow=False,
            font=dict(color=C["alias"], size=11),
            bgcolor="#2a0606", bordercolor=C["alias"], borderwidth=1,
            align="center",
        ))

    fig.update_layout(
        height=580,
        margin=dict(l=65, r=45, t=55, b=90),
        annotations=ann,
        **{k: v for k, v in BASE.items() if k != "margin"},
    )
    _apply_axes(fig, 2)
    fig.update_xaxes(title_text="Time (s)", row=1, col=1)
    fig.update_xaxes(title_text="Time (s)", row=2, col=1)
    fig.update_yaxes(title_text="Amplitude (V)", row=1, col=1)
    fig.update_yaxes(title_text="Amplitude (V)", row=2, col=1)
    t_min = float(min(t_orig[0], t_under[0]))
    t_max = float(max(t_orig[-1], t_under[-1]))
    for r in range(1, 3):
        fig.update_xaxes(range=[t_min, t_max], row=r, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 4.  REAL-WORLD NOISE  — 3-panel
# ─────────────────────────────────────────────────────────────────────────────
def plot_realworld(t, ideal, noisy, quantized, metrics):
    snr       = metrics.get("snr", 0)
    enob      = metrics.get("enob", 0)
    noise_std = metrics.get("noise_std", 0)

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "① Ideal signal",
            f"② With real-world noise  (σ = {noise_std:.4f} V)",
            f"③ After ADC quantization  |  SNR = {snr:.1f} dB  |  ENOB = {enob:.2f} bits",
        ],
        vertical_spacing=0.08,
    )

    for row, (sig, label, color, shape, is_staircase) in enumerate([
        (ideal,     "Ideal",     C["analog"],    "linear", False),
        (noisy,     "Noisy",     C["sampled"],   "linear", False),
        (quantized, "Quantized", C["quantized"], "hv",     True),
    ], start=1):
        t_s, sig_s = _smooth(t, sig, staircase=is_staircase)
        fig.add_trace(go.Scatter(
            x=t_s, y=sig_s, mode="lines", name=label,
            line=dict(color=color, width=1.5, shape=shape),
            hovertemplate=(f"<b>t</b>=%{{x:.6f}} s<br>"
                           f"<b>{label.lower()}</b>=%{{y:.6f}}<extra>{label}</extra>"),
        ), row=row, col=1)

    x_min, x_max = float(t[0]), float(t[-1])
    for s in _cursor_shapes(x_min, x_max):
        fig.add_shape(**s, row="all", col=1)

    fig.update_layout(
        height=700,
        annotations=[_cursor_label(x_min, x_max)],
        **BASE,
    )
    _apply_axes(fig, 3)
    fig.update_xaxes(title_text="Time (s)", row=3, col=1)
    for r in range(1, 4):
        fig.update_yaxes(title_text="Amplitude (V)", row=r, col=1)
        fig.update_xaxes(range=[x_min, x_max], row=r, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5.  DITHERING  — 3-panel
# ─────────────────────────────────────────────────────────────────────────────
def plot_dithering(t, original, q_no, q_di, snr_no, snr_di):
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "① Original signal",
            f"② Without dithering  —  SNR = {snr_no:.1f} dB  (harmonic distortion visible)",
            f"③ With triangular dithering  —  SNR = {snr_di:.1f} dB  (flat noise floor)",
        ],
        vertical_spacing=0.08,
    )

    for row, (sig, label, color, shape, is_staircase) in enumerate([
        (original, "Original",  C["analog"],    "linear", False),
        (q_no,     "No dither", C["quantized"], "hv",     True),
        (q_di,     "Dithered",  C["dither"],    "hv",     True),
    ], start=1):
        t_s, sig_s = _smooth(t, sig, staircase=is_staircase)
        fig.add_trace(go.Scatter(
            x=t_s, y=sig_s, mode="lines", name=label,
            line=dict(color=color, width=1.8, shape=shape),
            hovertemplate=f"<b>t</b>=%{{x:.6f}} s<br><b>amp</b>=%{{y:.6f}}<extra>{label}</extra>",
        ), row=row, col=1)

    x_min, x_max = float(t[0]), float(t[-1])
    for s in _cursor_shapes(x_min, x_max):
        fig.add_shape(**s, row="all", col=1)

    fig.update_layout(
        height=700,
        annotations=[_cursor_label(x_min, x_max)],
        **BASE,
    )
    _apply_axes(fig, 3)
    fig.update_xaxes(title_text="Time (s)", row=3, col=1)
    for r in range(1, 4):
        fig.update_yaxes(title_text="Amplitude (V)", row=r, col=1)
        fig.update_xaxes(range=[x_min, x_max], row=r, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 6.  QUANTUM READOUT  — 2×2 grid
# ─────────────────────────────────────────────────────────────────────────────
def plot_quantum(t, signal, noise_floor, bits, readout_error,
                 counts, I_0, Q_0, I_1, Q_1):
    fidelity = 1.0 - readout_error

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            f"① Qubit readout pulse — {bits}-bit ADC",
            "② IQ scatter — state discrimination",
            "③ Qiskit measurement histogram",
            f"④ Performance metrics",
        ],
        column_widths=[0.55, 0.45],
        vertical_spacing=0.14,
        horizontal_spacing=0.10,
    )

    # Panel 1 — readout pulse + noise floor band
    fig.add_trace(go.Scatter(
        x=t, y=signal, mode="lines", name="Readout pulse", connectgaps=True,
        line=dict(color=C["analog"], width=1.5),
        hovertemplate="<b>t</b>=%{x:.6f} s<br><b>amp</b>=%{y:.6f}<extra>Readout</extra>",
    ), row=1, col=1)

    fig.add_hline(y= noise_floor, line_color=C["alias"], line_width=1,
                  line_dash="dash", row=1, col=1,
                  annotation_text=f"+1 LSB={noise_floor:.5f}",
                  annotation_font_color=C["alias"], annotation_font_size=9)
    fig.add_hline(y=-noise_floor, line_color=C["alias"], line_width=1,
                  line_dash="dash", row=1, col=1,
                  annotation_text=f"-1 LSB={-noise_floor:.5f}",
                  annotation_font_color=C["alias"], annotation_font_size=9)
    fig.add_trace(go.Scatter(
        x=list(t) + list(t[::-1]),
        y=[noise_floor]*len(t) + [-noise_floor]*len(t),
        fill="toself", fillcolor="rgba(226,75,74,0.07)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Noise band", hoverinfo="skip",
    ), row=1, col=1)

    # Panel 2 — IQ scatter
    fig.add_trace(go.Scatter(
        x=I_0, y=Q_0, mode="markers", name="|0⟩ state",
        marker=dict(color=C["sampled"], size=5, opacity=0.6),
        hovertemplate="I=%{x:.4f}<br>Q=%{y:.4f}<extra>|0⟩</extra>",
    ), row=1, col=2)
    fig.add_trace(go.Scatter(
        x=I_1, y=Q_1, mode="markers", name="|1⟩ state",
        marker=dict(color=C["quantized"], size=5, opacity=0.6),
        hovertemplate="I=%{x:.4f}<br>Q=%{y:.4f}<extra>|1⟩</extra>",
    ), row=1, col=2)
    decision_x = (float(np.mean(I_0)) + float(np.mean(I_1))) / 2
    fig.add_vline(x=decision_x, line_color=TEXT, line_width=1, line_dash="dash",
                  row=1, col=2,
                  annotation_text="Decision", annotation_font_color=TEXT,
                  annotation_font_size=10)

    # Panel 3 — Qiskit histogram
    if counts:
        states = sorted(counts.keys())
        vals   = [counts[s] for s in states]
        colors = [C["sampled"] if s == "0" else C["quantized"] for s in states]
        fig.add_trace(go.Bar(
            x=states, y=vals, name="Qiskit counts",
            marker_color=colors,
            hovertemplate="State=%{x}<br>Count=%{y}<extra>Qiskit</extra>",
        ), row=2, col=1)
    else:
        fig.add_annotation(
            text="Qiskit not installed<br>pip install qiskit qiskit-aer",
            xref="paper", yref="paper", x=0.25, y=0.25,
            showarrow=False, font=dict(color=MUTED, size=11),
        )

    # Panel 4 — Metrics
    lines = [
        f"<b>ADC bits:</b>       {bits}",
        f"<b>Noise floor:</b>    {noise_floor:.5f} V",
        f"<b>Readout error:</b>  {readout_error:.4f}",
        f"<b>Fidelity:</b>       {fidelity*100:.2f}%",
        " ",
        "<b>IBM target:</b>    >99% fidelity",
        "<b>Requirement:</b>   12+ bit ADC @ GHz",
        " ",
        "<i>Ref: ICARUS-Q (2022)</i>",
        "<i>HERQULES arXiv:2212.03895</i>",
    ]
    fig.add_annotation(
        text="<br>".join(lines),
        xref="paper", yref="paper",
        x=0.62, y=0.36,
        xanchor="left", yanchor="top",
        showarrow=False,
        font=dict(size=11, color=TEXT, family="monospace"),
        bgcolor=PANEL, bordercolor="#555", borderwidth=1,
        align="left",
    )

    fig.update_layout(height=740, **BASE)
    # Apply spike lines to all 4 panels of 2x2 grid
    spike_style = dict(gridcolor=GRID, zerolinecolor=GRID, zerolinewidth=1,
                       showspikes=True, spikecolor="#555555", spikethickness=1,
                       spikedash="dot", spikemode="across")
    for ax in ["xaxis","yaxis","xaxis2","yaxis2","xaxis3","yaxis3","xaxis4","yaxis4"]:
        fig.update_layout(**{ax: spike_style})
    fig.update_xaxes(title_text="Time (s)",      row=1, col=1)
    fig.update_xaxes(title_text="I (in-phase)",  row=1, col=2)
    fig.update_xaxes(title_text="State",         row=2, col=1)
    fig.update_yaxes(title_text="Amplitude (V)", row=1, col=1)
    fig.update_yaxes(title_text="Q (quadrature)",row=1, col=2)
    fig.update_yaxes(title_text="Counts",        row=2, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 7.  COMPARISON  — N-panel stacked
# ─────────────────────────────────────────────────────────────────────────────
def plot_comparison(t, signals, mode):
    colors = [C["analog"], C["sampled"], C["quantized"],
              C["dither"], C["alias"], C["cursor_a"], C["cursor_b"]]
    n        = len(signals)
    original = list(signals.values())[0]

    titles = []
    for i, (label, sig) in enumerate(signals.items()):
        if i == 0:
            titles.append(f"① {label}  (reference)")
        else:
            from adc_processor import compute_snr
            snr = compute_snr(original, sig)
            num = "②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯"[min(i - 1, 15)]
            titles.append(f"{num} {label}  —  SNR = {snr:.1f} dB")

    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        subplot_titles=titles,
        vertical_spacing=0.06,
    )

    for i, (label, sig) in enumerate(signals.items()):
        shape        = "linear" if i == 0 else "hv"
        is_staircase = (i > 0)
        t_s, sig_s   = _smooth(t, sig, staircase=is_staircase)
        fig.add_trace(go.Scatter(
            x=t_s, y=sig_s, mode="lines", name=label,
            line=dict(color=colors[i % len(colors)], width=1.8, shape=shape),
            hovertemplate=f"<b>t</b>=%{{x:.6f}} s<br><b>amp</b>=%{{y:.6f}}<extra>{label}</extra>",
        ), row=i + 1, col=1)

    x_min, x_max = float(t[0]), float(t[-1])
    for s in _cursor_shapes(x_min, x_max):
        fig.add_shape(**s, row="all", col=1)

    title_text = (
        "Bit Depth Comparison — same signal, different ADC resolution"
        if mode == "bit_depth"
        else "Oversampling Comparison — same ADC, different oversampling factor"
    )
    fig.update_layout(
        height=max(270 * n, 500),
        title=dict(text=title_text, font=dict(color=TEXT, size=13)),
        annotations=[_cursor_label(x_min, x_max)],
        **BASE,
    )
    _apply_axes(fig, n)
    fig.update_xaxes(title_text="Time (s)", row=n, col=1)
    for r in range(1, n + 1):
        fig.update_yaxes(title_text="Amplitude (V)", row=r, col=1)
        fig.update_xaxes(range=[x_min, x_max], row=r, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 8.  FFT SPECTRUM  — LTspice FFT window equivalent
# ─────────────────────────────────────────────────────────────────────────────
def plot_fft_spectrum(freqs_orig, mag_orig, freqs_q, mag_q,
                      signal_freq, sample_rate):
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=[
            "① FFT — original signal  (dBFS vs Hz)",
            "② FFT — after quantization  (noise floor + harmonic distortion)",
        ],
        vertical_spacing=0.10,
    )

    fig.add_trace(go.Scatter(
        x=freqs_orig, y=mag_orig, mode="lines", name="Original FFT", connectgaps=True,
        line=dict(color=C["analog"], width=1.2),
        hovertemplate="<b>f</b>=%{x:.2f} Hz<br><b>mag</b>=%{y:.2f} dBFS<extra>Original</extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=freqs_q, y=mag_q, mode="lines", name="Quantized FFT", connectgaps=True,
        line=dict(color=C["quantized"], width=1.2),
        fill="tozeroy", fillcolor="rgba(216,90,48,0.06)",
        hovertemplate="<b>f</b>=%{x:.2f} Hz<br><b>mag</b>=%{y:.2f} dBFS<extra>Quantized</extra>",
    ), row=2, col=1)

    # Harmonic markers (like LTspice vertical cursor lines at nf)
    nyquist = sample_rate / 2
    labels  = ["f", "2f", "3f", "4f", "5f", "6f", "7f"]
    for k in range(1, 8):
        hf = signal_freq * k
        if hf > nyquist:
            break
        fig.add_vline(
            x=hf,
            line_color=C["cursor_a"] if k == 1 else "#555",
            line_width=1.0 if k == 1 else 0.7,
            line_dash="solid" if k == 1 else "dot",
            row=2, col=1,
            annotation_text=labels[k - 1],
            annotation_font_color=C["cursor_a"] if k == 1 else "#777",
            annotation_font_size=10,
        )

    fig.update_layout(height=580, **BASE)
    _apply_axes(fig, 2)
    fig.update_xaxes(title_text="Frequency (Hz)", row=2, col=1)
    fig.update_yaxes(title_text="Magnitude (dBFS)", row=1, col=1)
    fig.update_yaxes(title_text="Magnitude (dBFS)", row=2, col=1)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 9.  PSD  — Power Spectral Density
# ─────────────────────────────────────────────────────────────────────────────
def plot_psd(freqs_orig, psd_orig, freqs_q, psd_q,
             freqs_over=None, psd_over=None, bits=None, sample_rate=None):
    """PSD plot. Optional bits+sample_rate adds theoretical noise floor line."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=freqs_orig, y=psd_orig, mode="lines", name="Original", connectgaps=True,
        line=dict(color=C["analog"], width=1.5),
        hovertemplate="<b>f</b>=%{x:.2f} Hz<br><b>PSD</b>=%{y:.2f} dB/Hz<extra>Original</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=freqs_q, y=psd_q, mode="lines", name="Quantized", connectgaps=True,
        line=dict(color=C["quantized"], width=1.5),
        hovertemplate="<b>f</b>=%{x:.2f} Hz<br><b>PSD</b>=%{y:.2f} dB/Hz<extra>Quantized</extra>",
    ))
    if freqs_over is not None:
        fig.add_trace(go.Scatter(
            x=freqs_over, y=psd_over, mode="lines", name="Oversampled", connectgaps=True,
            line=dict(color=C["sampled"], width=1.5),
            hovertemplate="<b>f</b>=%{x:.2f} Hz<br><b>PSD</b>=%{y:.2f} dB/Hz<extra>Oversampled</extra>",
        ))

    # Theoretical quantization noise floor:
    # Total quantization noise power = step^2 / 12 = (2/2^N)^2 / 12
    # Spread uniformly over bandwidth 0..fs/2, so PSD = noise_power / (fs/2)
    # In dB/Hz: 10*log10(noise_power / (fs/2))
    if bits is not None and sample_rate is not None and len(freqs_q) > 1:
        step          = 2.0 / (2 ** bits)
        noise_power   = (step ** 2) / 12.0
        noise_floor   = 10 * np.log10(noise_power / (sample_rate / 2.0))
        fig.add_hline(
            y=noise_floor,
            line_color=C["error"],
            line_width=1.0,
            line_dash="dot",
            annotation_text=f"Theoretical noise floor ({bits}-bit): {noise_floor:.1f} dB/Hz",
            annotation_font_color=C["error"],
            annotation_font_size=10,
            annotation_position="bottom right",
        )

    fig.update_layout(
        height=420,
        title=dict(
            text="Power Spectral Density — Welch method  (lower floor = better ADC)",
            font=dict(color=TEXT, size=13),
        ),
        xaxis=dict(title="Frequency (Hz)", gridcolor=GRID,
                   showspikes=True, spikecolor="#555",
                   spikethickness=1, spikedash="dot"),
        yaxis=dict(title="Power/Freq (dB/Hz)", gridcolor=GRID),
        **BASE,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 10.  SNR SWEEP  — Simulated vs Theoretical
# ─────────────────────────────────────────────────────────────────────────────
def plot_snr_sweep(bits_range, snr_simulated, snr_theoretical):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=bits_range, y=snr_theoretical,
        mode="lines", name="Theoretical  6.02·N + 1.76",
        line=dict(color=C["analog"], width=2, dash="dash"),
        hovertemplate="<b>N</b>=%{x}<br><b>Theoretical</b>=%{y:.2f} dB<extra>Theory</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=bits_range, y=snr_simulated,
        mode="lines+markers", name="Simulated",
        line=dict(color=C["quantized"], width=2),
        marker=dict(size=7, color=C["quantized"]),
        hovertemplate="<b>N</b>=%{x}<br><b>Simulated</b>=%{y:.2f} dB<extra>Simulated</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=bits_range + bits_range[::-1],
        y=snr_theoretical + snr_simulated[::-1],
        fill="toself", fillcolor="rgba(216,90,48,0.10)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Deviation", hoverinfo="skip",
    ))

    fig.update_layout(
        height=420,
        title=dict(
            text="SNR vs Bit Depth — Simulated vs Theoretical",
            font=dict(color=TEXT, size=13),
        ),
        xaxis=dict(title="Bit Depth (N)", tickmode="linear", tick0=1, dtick=1,
                   gridcolor=GRID, showspikes=True,
                   spikecolor="#555", spikethickness=1, spikedash="dot"),
        yaxis=dict(title="SNR (dB)", gridcolor=GRID),
        **BASE,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 11.  ERROR HISTOGRAM  — Quantization error distribution
# ─────────────────────────────────────────────────────────────────────────────
def plot_error_histogram(error, bits):
    step = 2.0 / (2 ** bits)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=error, nbinsx=80,
        name="Q-Error distribution",
        marker_color=C["error"], opacity=0.85,
        hovertemplate="<b>error</b>=%{x:.6f}<br><b>count</b>=%{y}<extra>Q-Error</extra>",
    ))
    for x_val, lbl in [(step/2,  "+step/2  (max error)"),
                       (-step/2, "-step/2  (min error)")]:
        fig.add_vline(
            x=x_val, line_color=TEXT, line_width=1.2, line_dash="dash",
            annotation_text=lbl,
            annotation_font_color=TEXT, annotation_font_size=10,
        )

    fig.update_layout(
        height=380,
        title=dict(
            text=(f"Quantization error histogram — {bits}-bit  "
                  f"(uniform distribution = white noise model holds)"),
            font=dict(color=TEXT, size=13),
        ),
        xaxis=dict(title="Quantization Error (V)", gridcolor=GRID,
                   showspikes=True, spikecolor="#555",
                   spikethickness=1, spikedash="dot"),
        yaxis=dict(title="Count", gridcolor=GRID),
        **BASE,
    )
    return fig
