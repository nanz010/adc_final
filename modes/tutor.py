"""
tutor.py — Contextual Education System
=======================================
Provides live, context-aware explanations that update based on current
parameter values. Every concept, formula, and graph panel has an
explanation that a first-year student can understand.
"""

import streamlit as st
import numpy as np


# ── Shared CSS injected once ──────────────────────────────────────────────────
TUTOR_CSS = """
<style>
.tutor-box {
    background: var(--secondary-background-color);
    border: 1px solid rgba(55,138,221,0.2);
    border-left: 4px solid #378ADD;
    border-radius: 8px;
    padding: 12px 14px;
    margin: 6px 0;
    font-family: monospace;
}
.tutor-formula {
    background: var(--secondary-background-color);
    border: 1px solid rgba(186,117,23,0.3);
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0;
    font-family: monospace;
    font-size: 13px;
    color: #BA7517;
    text-align: center;
    font-weight: 600;
}
.tutor-title {
    color: #378ADD;
    font-weight: 600;
    font-size: 12px;
    margin-bottom: 5px;
    letter-spacing: 0.04em;
}
.tutor-body {
    color: var(--text-color);
    font-size: 11px;
    line-height: 1.7;
    opacity: 0.85;
}
.tutor-good  { border-left-color: #1D9E75; }
.tutor-warn  { border-left-color: #BA7517; }
.tutor-bad   { border-left-color: #E24B4A; }
.tutor-quantum { border-left-color: #7F77DD; }
.concept-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin: 8px 0;
}
.concept-card {
    background: var(--background-color);
    border: 1px solid rgba(128,128,128,0.15);
    border-radius: 6px;
    padding: 8px 10px;
}
.concept-label {
    color: var(--text-color);
    opacity: 0.45;
    font-size: 9px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 2px;
}
.concept-value {
    color: #BA7517;
    font-size: 12px;
    font-weight: 600;
    font-family: monospace;
}
.concept-desc {
    color: var(--text-color);
    opacity: 0.5;
    font-size: 9px;
    margin-top: 2px;
}
</style>
"""


def inject_css():
    st.markdown(TUTOR_CSS, unsafe_allow_html=True)


# ── Helper ────────────────────────────────────────────────────────────────────
def _box(title, body, kind="info"):
    cls = {"info": "", "good": "tutor-good",
           "warn": "tutor-warn", "bad": "tutor-bad",
           "quantum": "tutor-quantum"}.get(kind, "")
    st.markdown(f"""
<div class="tutor-box {cls}">
  <div class="tutor-title">{title}</div>
  <div class="tutor-body">{body}</div>
</div>""", unsafe_allow_html=True)


def _formula(text):
    st.markdown(f'<div class="tutor-formula">{text}</div>',
                unsafe_allow_html=True)


def _concept_grid(items):
    """items = list of (label, value, desc) tuples"""
    cards = ""
    for label, value, desc in items:
        cards += f"""
        <div class="concept-card">
          <div class="concept-label">{label}</div>
          <div class="concept-value">{value}</div>
          <div class="concept-desc">{desc}</div>
        </div>"""
    st.markdown(f'<div class="concept-grid">{cards}</div>',
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MODE 1 — STANDARD ADC
# ─────────────────────────────────────────────────────────────────────────────
def explain_standard(bits, freq, sample_rate, amplitude, snr, enob):
    """Full contextual explanation for Standard ADC mode."""

    inject_css()
    st.markdown("### 📖 What you are looking at")

    # ── What is an ADC ────────────────────────────────────────────────────────
    _box("What is an ADC?",
         "An <b>Analog-to-Digital Converter (ADC)</b> takes a smooth, "
         "continuous signal from the real world (like sound, temperature, "
         "or a sensor reading) and converts it into a sequence of numbers "
         "a computer can understand. It does this in two steps: "
         "<b>sampling</b> (taking snapshots at regular intervals) and "
         "<b>quantization</b> (rounding each snapshot to the nearest "
         "allowed level).")

    # ── The 4 panels explained ────────────────────────────────────────────────
    st.markdown("#### The 4 graph panels")

    _box("① Analog signal — the real world",
         f"The smooth blue sine wave is the <b>ideal continuous signal</b> "
         f"at {freq} Hz. In reality this could be a voice recording, a "
         f"sensor reading, or in quantum computing — a microwave pulse from "
         f"a qubit. This signal has infinite precision — every point in time "
         f"has an exact value.")

    _box("② Sampled signal — taking snapshots",
         f"The green dots show where the ADC takes a measurement. "
         f"At {sample_rate} Hz sample rate, it takes <b>{sample_rate} "
         f"snapshots every second</b>. The vertical stems show each "
         f"measurement moment. Between snapshots, all information is lost — "
         f"this is why sample rate matters.",
         kind="good")

    _box("③ Quantized output — rounding to allowed levels",
         f"The orange staircase is what the ADC actually outputs. "
         f"With <b>{bits} bits</b>, there are only <b>{2**bits} allowed "
         f"levels</b>. Every sample gets rounded to the nearest level. "
         f"The step size between levels is "
         f"<b>{2.0/(2**bits):.5f} V</b> (called 1 LSB — Least Significant "
         f"Bit). More bits = smaller steps = smoother staircase = "
         f"better accuracy.",
         kind="warn")

    _box("④ Quantization error — the rounding mistake",
         "The difference between the real sample value and the rounded "
         "quantized value. This is unavoidable noise — every ADC introduces "
         "it. The goal is to make it as small as possible. "
         "For a good ADC this should look random (white noise). "
         "If it looks periodic or structured, the ADC has distortion.",
         kind="bad")

    # ── Key formulas ──────────────────────────────────────────────────────────
    st.markdown("#### Key formulas")

    _formula(f"SNR = 6.02 × N + 1.76 dB = 6.02 × {bits} + 1.76 = {6.02*bits+1.76:.1f} dB")

    _box("Why 6.02 per bit?",
         "Every extra bit <b>doubles the number of levels</b>, which "
         "<b>halves the step size</b>, which reduces noise power by 4×. "
         "In decibels: 10 × log₁₀(4) = <b>6.02 dB</b>. "
         "The 1.76 is a fixed constant from the math of uniform "
         "random rounding error (Bennett, 1948).")

    _formula("ENOB = (SNR − 1.76) / 6.02")

    _box("What is ENOB?",
         "<b>Effective Number of Bits</b> — given the measured SNR, how many "
         "bits is this ADC actually performing like? A perfect 8-bit ADC has "
         f"ENOB = 8. Your current ENOB = <b>{enob:.2f} bits</b>. "
         f"If ENOB < {bits}, the ADC is not reaching its theoretical limit "
         "due to noise or distortion.")

    # ── Live computed values ───────────────────────────────────────────────────
    st.markdown("#### Your current ADC parameters")

    ideal_snr = 6.02 * bits + 1.76
    step = 2.0 / (2 ** bits)
    nyquist = sample_rate / 2

    snr_quality = "good" if snr > 40 else "warn" if snr > 20 else "bad"
    _box(f"SNR = {snr:.1f} dB  (ideal = {ideal_snr:.1f} dB)",
         f"Your signal is <b>{10**(snr/10):.0f}× stronger</b> than the "
         f"quantization noise. "
         + ("This is good — the ADC is working near its theoretical limit."
            if snr > ideal_snr - 2
            else f"Degradation of {ideal_snr - snr:.1f} dB from ideal — "
                 "real-world noise is reducing quality."),
         kind=snr_quality)

    _concept_grid([
        ("Bit depth", f"{bits} bits", f"2^{bits} = {2**bits} levels"),
        ("Step size (1 LSB)", f"{step:.5f} V", "smallest measurable change"),
        ("Sample rate", f"{sample_rate} Hz", f"{sample_rate} samples/sec"),
        ("Nyquist limit", f"{nyquist} Hz", "max signal freq without aliasing"),
        ("Signal freq", f"{freq} Hz",
         "✓ safe" if freq < nyquist else "⚠ aliasing!"),
        ("Amplitude", f"{amplitude:.2f} V", "signal peak voltage"),
    ])

    # ── What to try ───────────────────────────────────────────────────────────
    st.markdown("#### Try this to learn")
    st.markdown(f"""
- **Reduce bits to 2 or 3** — watch the staircase become very coarse and SNR drop below 15 dB
- **Set bits to 16** — the staircase disappears, SNR reaches {6.02*16+1.76:.0f} dB
- **Increase sample rate above {freq*10}** — more dots on panel ②, same signal quality
- **Set freq near {sample_rate//2} Hz** — approaching Nyquist limit, signal still OK
- **Set freq above {sample_rate//2} Hz** — aliasing! (switch to Aliasing Demo mode to see this)
""")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 2 — OVERSAMPLING
# ─────────────────────────────────────────────────────────────────────────────
def explain_oversampling(bits, freq, factor, snr_n, snr_o, th_gain):
    inject_css()
    st.markdown("### 📖 What you are looking at")

    _box("What is oversampling?",
         f"Instead of sampling at exactly the minimum required rate, you "
         f"sample <b>{factor}× faster</b> than needed, then filter and "
         f"reduce back to the original rate. The quantization noise is the "
         f"same total amount — but it gets <b>spread across a {factor}× "
         f"wider frequency range</b>. After filtering, only the narrow "
         f"band containing your signal is kept, along with only 1/{factor} "
         f"of the noise. Result: better SNR for free.")

    _formula(f"SNR gain = 10 × log₁₀(M) / 2 = 10 × log₁₀({factor}) / 2 = +{th_gain:.1f} dB")

    _box("The bucket analogy",
         f"Imagine quantization noise as 1 litre of water. "
         f"Normal sampling: 1 bucket, fills high. "
         f"Oversampling {factor}×: {factor} buckets, same water spread thin. "
         f"You keep only the buckets where your signal lives (1/{factor} of them), "
         f"and throw away the rest — taking only 1/{factor} of the noise with it. "
         f"Signal is untouched. SNR improves by {th_gain:.1f} dB.")

    gain = snr_o - snr_n
    kind = "good" if abs(gain - th_gain) < 2 else "warn"
    _box(f"Your result: +{gain:.1f} dB gain (theory predicts +{th_gain:.1f} dB)",
         f"Normal SNR: <b>{snr_n:.1f} dB</b> → "
         f"Oversampled SNR: <b>{snr_o:.1f} dB</b>. "
         + ("Matches theory well — the simulation is physically correct."
            if kind == "good"
            else "Some deviation from theory — expected for short signals "
                 "where the noise statistics are not fully averaged."),
         kind=kind)

    _formula(f"Each doubling of M → +3 dB SNR → +0.5 effective bit")

    _concept_grid([
        ("Oversampling factor M", f"{factor}×", "sampling rate multiplier"),
        ("Normal SNR", f"{snr_n:.1f} dB", "without oversampling"),
        ("Oversampled SNR", f"{snr_o:.1f} dB", "after averaging decimation"),
        ("Theoretical gain", f"+{th_gain:.1f} dB", "10·log₁₀(M)/2"),
        ("Actual gain", f"+{gain:.1f} dB", "measured from simulation"),
        ("Effective extra bits", f"+{th_gain/6.02:.2f} bits",
         "gain / 6.02 per bit"),
    ])

    st.markdown("#### Try this to learn")
    st.markdown(f"""
- **Change M from 1 to 64** — watch SNR climb by {10*np.log10(64)/2:.0f} dB total
- **Switch to PSD tab** — see the noise floor physically drop after oversampling
- **Switch to FFT tab** — noise floor is lower, signal peak stays the same height
- **Try M=4 then M=16** — each 4× gives +6 dB (same as adding 1 bit)
""")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 3 — ALIASING
# ─────────────────────────────────────────────────────────────────────────────
def explain_aliasing(signal_freq, sample_rate, alias_detected, alias_freq):
    inject_css()
    st.markdown("### 📖 What you are looking at")

    nyquist = sample_rate / 2

    if alias_detected:
        _box("ALIASING IS HAPPENING",
             f"Your signal at <b>{signal_freq} Hz</b> is faster than the "
             f"ADC can track (Nyquist limit = {nyquist:.0f} Hz). "
             f"The ADC misidentifies it as a <b>{alias_freq:.1f} Hz</b> signal. "
             f"This is completely wrong data — the ADC is lying to you. "
             f"In quantum computing, aliased readout signals mean you're "
             f"recording the wrong qubit state.",
             kind="bad")
    else:
        _box("No aliasing — sampling is valid",
             f"Signal ({signal_freq} Hz) is below Nyquist limit "
             f"({nyquist:.0f} Hz). The ADC correctly captures the signal. "
             f"You are {nyquist - signal_freq:.0f} Hz below the safety limit.",
             kind="good")

    _box("What is the Nyquist theorem?",
         "To correctly record a signal, you must sample at <b>more than "
         "twice the signal frequency</b>. If you sample too slowly, the "
         "signal 'wraps around' and appears at the wrong frequency — "
         "this is called aliasing. Named after Harry Nyquist (1928).")

    _formula(f"Nyquist rule: sample_rate > 2 × signal_freq → {sample_rate} > 2 × {signal_freq} ?  "
             f"{'✓ YES' if not alias_detected else '✗ NO — ALIASING'}")

    _formula(f"Alias frequency = |f_signal mod f_sample| folded at Nyquist = {alias_freq:.1f} Hz")

    _box("Real world example",
         "Old movies show car wheels appearing to spin <b>backwards</b>. "
         "The camera samples at 24 frames/sec. If the wheel spins at "
         "25 rotations/sec, aliasing makes it look like 1 rotation/sec "
         "in reverse. Same math, same physics as ADC aliasing.")

    _concept_grid([
        ("Signal frequency", f"{signal_freq} Hz", "what you're trying to measure"),
        ("Sample rate", f"{sample_rate} Hz", "ADC speed"),
        ("Nyquist limit", f"{nyquist:.0f} Hz", "sample_rate / 2"),
        ("Alias frequency", f"{alias_freq:.1f} Hz",
         "apparent freq after aliasing" if alias_detected else "no alias"),
        ("Status", "ALIASED ⚠" if alias_detected else "SAFE ✓",
         "is ADC capturing correctly?"),
        ("Fix", f"Set sample rate > {signal_freq*2} Hz",
         "to avoid aliasing"),
    ])

    st.markdown("#### Try this to learn")
    st.markdown(f"""
- **Set signal to {int(sample_rate*0.4)} Hz, sample rate {sample_rate}** — safe, below Nyquist
- **Increase signal above {int(nyquist)} Hz** — aliasing starts immediately
- **Set signal to exactly {int(nyquist)} Hz** — right at the edge (still ok, barely)
- **Double the sample rate** — same signal now safe again
""")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 4 — REAL-WORLD NOISE
# ─────────────────────────────────────────────────────────────────────────────
def explain_realworld(bits, noise_std, snr, enob, ideal_snr):
    inject_css()
    st.markdown("### 📖 What you are looking at")

    _box("Real ADCs have more noise than theory predicts",
         "The formula SNR = 6.02N + 1.76 dB assumes <b>only quantization "
         "noise</b>. Real ADCs also have: thermal noise (from resistors), "
         "clock jitter (timing errors), reference voltage noise, and "
         "amplifier noise. This mode adds all of these together so you "
         "can see the real degradation.")

    step = 2.0 / (2 ** bits)
    q_noise = step / (12 ** 0.5)

    _box("Types of noise in your simulation",
         f"<b>Quantization noise:</b> ≈{q_noise:.5f} V rms (from {bits}-bit rounding)<br>"
         f"<b>Additive noise (σ={noise_std:.4f} V):</b> models thermal noise, "
         f"jitter, reference noise — all lumped together.<br>"
         f"<b>Total:</b> RSS combination = √(quantization² + additive²) "
         f"= {np.sqrt(q_noise**2 + noise_std**2):.5f} V rms")

    kind = "good" if snr > ideal_snr - 3 else "warn" if snr > ideal_snr - 10 else "bad"
    _box(f"SNR degradation: {ideal_snr - snr:.1f} dB below ideal",
         f"Ideal {bits}-bit SNR = {ideal_snr:.1f} dB. "
         f"Your actual SNR = {snr:.1f} dB. "
         f"The {ideal_snr - snr:.1f} dB gap is caused by the "
         f"σ={noise_std:.4f} V additive noise. "
         + ("Very small degradation — ADC is near ideal." if kind == "good"
            else "Significant degradation — noise is dominating." if kind == "warn"
            else "Severe degradation — signal is buried in noise."),
         kind=kind)

    _formula(f"Total noise power = Q_noise² + Additive_noise²")
    _formula(f"SNR = 10 × log₁₀(signal_power / total_noise_power) = {snr:.1f} dB")

    _concept_grid([
        ("Ideal SNR", f"{ideal_snr:.1f} dB", f"6.02×{bits}+1.76"),
        ("Actual SNR", f"{snr:.1f} dB", "with real-world noise"),
        ("Degradation", f"{ideal_snr-snr:.1f} dB", "gap from ideal"),
        ("Additive noise σ", f"{noise_std:.4f} V", "thermal + jitter + ref"),
        ("Q-noise rms", f"{q_noise:.5f} V", f"step/{np.sqrt(12):.2f}"),
        ("ENOB", f"{enob:.2f} bits", "effective performance"),
    ])

    st.markdown("#### Try this to learn")
    st.markdown("""
- **Set noise to 0** — see ideal quantization only, SNR matches formula exactly
- **Increase noise gradually** — watch SNR fall and ENOB drop
- **High bits + high noise** — extra bits don't help if noise dominates
- **Low bits + low noise** — quantization noise is the limit, not thermal
""")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 5 — DITHERING
# ─────────────────────────────────────────────────────────────────────────────
def explain_dithering(bits, snr_no, snr_di, amplitude):
    inject_css()
    st.markdown("### 📖 What you are looking at")

    step = 2.0 / (2 ** bits)

    _box("What is dithering?",
         f"Without dithering, quantization noise is <b>correlated</b> with "
         f"the signal — it creates fake tones at 2f, 3f, 4f... called "
         f"harmonic distortion. Dithering adds ≈{step/2:.5f} V of random "
         f"noise <b>before</b> quantization. This breaks the correlation. "
         f"The result: no harmonics, just flat white noise. "
         f"Total noise power may increase slightly, but it's perceptually "
         f"much cleaner.")

    _box("Where is dithering used in the real world?",
         "<b>LIGO (2024):</b> gravitational wave detector improved "
         "digitization noise 3× with dithering.<br>"
         "<b>Professional audio:</b> CD recording (16-bit) uses TPDF dither "
         "to eliminate harmonic distortion at low volumes.<br>"
         "<b>Scientific instruments:</b> any precision ADC measuring a "
         "periodic signal uses dithering.")

    _formula(f"Triangular dither (TPDF) = Uniform(−step/2, +step/2) + Uniform(−step/2, +step/2)")
    _formula(f"Step size = (v_max − v_min) / 2^N = 2.0 / {2**bits} = {step:.5f} V")

    gain = snr_di - snr_no
    _box(f"Dither effect on SNR: {'+' if gain >= 0 else ''}{gain:.1f} dB",
         f"Without dither SNR = {snr_no:.1f} dB — but this includes "
         f"harmonic peaks that pollute the spectrum.<br>"
         f"With dither SNR = {snr_di:.1f} dB — slightly different total "
         f"noise power, but now it is <b>white and uncorrelated</b>. "
         f"Switch to FFT tab to see the harmonic peaks disappear.",
         kind="good" if gain >= -3 else "warn")

    _box("Look at the FFT tab — this is the key view",
         "Without dithering: you will see sharp peaks at 2f, 3f, 4f "
         "(harmonic distortion).<br>"
         "With dithering: those peaks vanish. The noise floor rises "
         "slightly but is completely flat. This is the correct behavior "
         "for precision measurement applications.")

    st.markdown("#### Try this to learn")
    st.markdown(f"""
- **Set bits to 2 or 3** — makes the effect very dramatic and visible
- **Set amplitude to 0.3** — low amplitude makes harmonics more obvious
- **Switch to FFT tab** — see harmonic peaks appear/disappear with dithering
- **Switch to Error Histogram** — no dither = non-uniform; with dither = uniform (white noise)
""")


# ─────────────────────────────────────────────────────────────────────────────
# MODE 6 — QUANTUM READOUT
# ─────────────────────────────────────────────────────────────────────────────
def explain_quantum(bits, snr, readout_error, fidelity, noise_floor):
    inject_css()
    st.markdown("### 📖 What you are looking at")

    _box("Why does ADC matter in quantum computing?",
         "A qubit produces a tiny microwave pulse when measured. "
         "This pulse is amplified and then <b>digitized by an ADC</b>. "
         "The ADC must distinguish between a |0⟩ pulse and a |1⟩ pulse "
         "that differ by only microvolts. If the ADC's quantization noise "
         "is larger than the difference between the pulses, the qubit "
         "state is misread. This is called <b>readout error</b>.",
         kind="quantum")

    _box("The quantum measurement chain",
         "Qubit → Microwave resonator → Cryogenic amplifier (4K) → "
         "Room-temperature amplifier → IQ mixer → "
         f"<b>ADC ({bits}-bit) ← you are here</b> → "
         "Digital discriminator → Recorded state (0 or 1)",
         kind="quantum")

    _box("What is the IQ scatter plot?",
         "Real qubit readout uses <b>two ADC channels</b> — "
         "I (in-phase) and Q (quadrature), 90° apart. "
         "Each measurement appears as a dot in 2D space. "
         "|0⟩ measurements cluster in one region, "
         "|1⟩ measurements cluster in another. "
         "The <b>decision boundary</b> (dashed line) separates them. "
         "Dots on the wrong side = readout errors. "
         "More ADC bits = tighter clusters = fewer errors.",
         kind="quantum")

    _formula("Fidelity = 1 − readout_error_probability")
    _formula(f"ADC SNR = {snr:.1f} dB → readout error ≈ {readout_error:.3f} → fidelity = {fidelity*100:.1f}%")

    fid_kind = "good" if fidelity > 0.99 else "warn" if fidelity > 0.95 else "bad"
    _box(f"Your fidelity: {fidelity*100:.1f}%",
         f"IBM Quantum target: >99% fidelity. "
         + (f"You meet this with {bits}-bit ADC." if fidelity > 0.99
            else f"You need more bits — try 12+ bit ADC. "
                 f"Current {bits}-bit gives only {fidelity*100:.1f}%."),
         kind=fid_kind)

    _box("What is the noise floor?",
         f"The noise floor ({noise_floor:.5f} V) is the size of 1 LSB — "
         f"the smallest voltage the ADC can distinguish. "
         f"If the difference between |0⟩ and |1⟩ pulses is smaller than "
         f"this, the ADC cannot tell them apart. "
         f"Quantum readout signals are typically 0.1–0.5 V after "
         f"amplification, so {bits}-bit resolution matters critically.",
         kind="quantum")

    _concept_grid([
        ("ADC bits", f"{bits}", f"2^{bits} = {2**bits} levels"),
        ("ADC SNR", f"{snr:.1f} dB", "signal vs quantization noise"),
        ("Noise floor (1 LSB)", f"{noise_floor:.5f} V", "smallest detectable change"),
        ("Readout error", f"{readout_error:.3f}", "P(wrong state recorded)"),
        ("Fidelity", f"{fidelity*100:.1f}%", "P(correct state recorded)"),
        ("IBM target", ">99%", "needs 12+ bit ADC @ GHz"),
    ])

    st.markdown("#### Try this to learn")
    st.markdown(f"""
- **Drag bits from 4 to 16** — watch fidelity climb toward 99%
- **Watch IQ scatter** — clusters tighten as bits increase, fewer dots cross the boundary
- **Increase amplifier noise** — simulates real cryogenic amplifier noise at 4K
- **Look at Qiskit histogram** — at low bits, the |1⟩ bar grows (misclassified |0⟩ states)
""")


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH LEGEND — shown beside any graph on demand
# ─────────────────────────────────────────────────────────────────────────────
def explain_graph_controls():
    inject_css()
    _box("How to use the interactive graphs",
         "<b>Hover:</b> move mouse over any line — tooltip shows exact time and amplitude<br>"
         "<b>Zoom in:</b> scroll wheel up, or drag a box to zoom into that region<br>"
         "<b>Zoom out:</b> scroll wheel down<br>"
         "<b>Pan:</b> click and drag after zooming<br>"
         "<b>Reset:</b> double-click anywhere to return to full view<br>"
         "<b>Hide/show trace:</b> click any item in the legend (top right)<br>"
         "<b>Download PNG:</b> camera icon in top-right toolbar<br>"
         "<b>Cursors A & B:</b> amber and teal dashed lines — the ΔT between them is shown below the graph<br>"
         "<b>Draw custom line:</b> pencil icon in toolbar — annotate any point")
