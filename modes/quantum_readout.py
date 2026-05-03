import numpy as np
import streamlit as st

from signal_generator import generate_sine, generate_iq_signal
from adc_processor import (quantize, compute_snr, compute_enob,
                           snr_to_readout_error,
                           compute_shot_noise_snr, combined_readout_snr)
from plot_renderer import PLOTLY_CONFIG, plot_quantum

try:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, ReadoutError
    QISKIT_OK = True
except ImportError:
    QISKIT_OK = False


@st.cache_data(show_spinner=False)
def _run_qiskit(error_prob, shots=1024):
    if not QISKIT_OK:
        return {}
    p = error_prob
    qc = QuantumCircuit(1, 1)
    qc.measure(0, 0)
    nm = NoiseModel()
    nm.add_all_qubit_readout_error(ReadoutError([[1 - p, p], [p, 1 - p]]))
    result = AerSimulator(noise_model=nm).run(qc, shots=shots).result()
    return result.get_counts()



def _render_quantum_circuit(bits, adc_snr, shot_snr_db, total_snr_db,
                             readout_error, fidelity, bottleneck, n_photons):
    """SVG circuit diagram of the quantum readout chain."""
    import streamlit.components.v1 as components

    fid_color  = "#3DDC84" if fidelity > 0.99 else "#F04747"
    bot_color  = "#4DA8DA" if "ADC" in bottleneck else "#F04747"
    err_pct    = readout_error * 100

    svg = f"""
<svg width="820" height="500" viewBox="0 0 820 500" xmlns="http://www.w3.org/2000/svg"
     style="font-family:'JetBrains Mono',monospace;background:#0b0d0f;display:block">
  <defs>
    <marker id="qa" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#A78BFA"
            stroke-width="1.5" stroke-linecap="round"/>
    </marker>
    <marker id="gb" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#3DDC84"
            stroke-width="1.5" stroke-linecap="round"/>
    </marker>
    <marker id="ab" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#FFB020"
            stroke-width="1.5" stroke-linecap="round"/>
    </marker>
    <marker id="bb" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#4DA8DA"
            stroke-width="1.5" stroke-linecap="round"/>
    </marker>
  </defs>

  <!-- Title -->
  <rect x="0" y="0" width="820" height="32" fill="#1C2228"/>
  <text x="14" y="21" fill="#A78BFA" font-size="11" font-weight="700"
        letter-spacing="3">QUANTUM READOUT CIRCUIT — FROM QUBIT TO DIGITAL RESULT</text>
  <text x="720" y="21" fill="#5C6A75" font-size="10">{bits}-bit ADC</text>

  <!-- Live metrics strip -->
  <rect x="0" y="32" width="820" height="26" fill="#111418"/>
  <text x="14"  y="50" fill="#9AA5B0" font-size="9">ADC SNR: {adc_snr:.1f} dB</text>
  <text x="140" y="50" fill="#9AA5B0" font-size="9">Shot SNR: {shot_snr_db:.1f} dB</text>
  <text x="270" y="50" fill="#A78BFA" font-size="9">Total SNR: {total_snr_db:.1f} dB</text>
  <text x="400" y="50" fill="#9AA5B0" font-size="9">Error: {err_pct:.2f}%</text>
  <text x="490" y="50" fill="{fid_color}" font-size="9" font-weight="700">Fidelity: {fidelity*100:.2f}%</text>
  <text x="620" y="50" fill="{bot_color}" font-size="9" font-weight="700">Bottleneck: {bottleneck}</text>

  <!-- ── TEMPERATURE ZONES ── -->
  <!-- Dilution fridge -->
  <rect x="14" y="80" width="280" height="130" fill="#0D0A1E" stroke="#534AB7" stroke-width="1.5" stroke-dasharray="6,3" rx="4"/>
  <text x="22" y="97" fill="#534AB7" font-size="9" font-weight="700">DILUTION REFRIGERATOR — 15 mK</text>

  <!-- Qubit box -->
  <rect x="24" y="105" width="90" height="90" fill="#1A0F3A" stroke="#A78BFA" stroke-width="1.5" rx="3"/>
  <rect x="24" y="105" width="90" height="5" fill="#A78BFA" rx="1"/>
  <text x="69" y="130" fill="#A78BFA" font-size="10" font-weight="700" text-anchor="middle">QUBIT</text>
  <text x="69" y="148" fill="#9AA5B0" font-size="9" text-anchor="middle">|0⟩ or |1⟩</text>
  <text x="69" y="164" fill="#9AA5B0" font-size="9" text-anchor="middle">superposition</text>
  <text x="69" y="180" fill="#534AB7" font-size="9" text-anchor="middle">∼15 mK</text>
  <line x1="114" y1="150" x2="136" y2="150" stroke="#A78BFA" stroke-width="2" marker-end="url(#qa)"/>

  <!-- Resonator -->
  <rect x="138" y="105" width="100" height="90" fill="#1A0F3A" stroke="#A78BFA" stroke-width="1.5" rx="3"/>
  <rect x="138" y="105" width="100" height="5" fill="#A78BFA" rx="1"/>
  <text x="188" y="130" fill="#A78BFA" font-size="10" font-weight="700" text-anchor="middle">RESONATOR</text>
  <text x="188" y="148" fill="#9AA5B0" font-size="9" text-anchor="middle">µwave pulse</text>
  <text x="188" y="163" fill="#9AA5B0" font-size="9" text-anchor="middle">N={n_photons} photons</text>
  <text x="188" y="178" fill="#A78BFA" font-size="9" text-anchor="middle">∼5–10 GHz</text>
  <line x1="238" y1="150" x2="296" y2="150" stroke="#A78BFA" stroke-width="2" marker-end="url(#qa)"/>

  <!-- 4K zone -->
  <rect x="298" y="80" width="130" height="130" fill="#0A1422" stroke="#4DA8DA" stroke-width="1.5" stroke-dasharray="6,3" rx="4"/>
  <text x="308" y="97" fill="#4DA8DA" font-size="9" font-weight="700">4 KELVIN</text>
  <rect x="308" y="105" width="110" height="90" fill="#081828" stroke="#4DA8DA" stroke-width="1.5" rx="3"/>
  <rect x="308" y="105" width="110" height="5" fill="#4DA8DA" rx="1"/>
  <text x="363" y="130" fill="#4DA8DA" font-size="10" font-weight="700" text-anchor="middle">CRYO AMP</text>
  <text x="363" y="148" fill="#9AA5B0" font-size="9" text-anchor="middle">HEMT amplifier</text>
  <text x="363" y="163" fill="#9AA5B0" font-size="9" text-anchor="middle">First gain stage</text>
  <text x="363" y="178" fill="#9AA5B0" font-size="9" text-anchor="middle">Adds thermal noise</text>
  <line x1="418" y1="150" x2="440" y2="150" stroke="#4DA8DA" stroke-width="2" marker-end="url(#bb)"/>

  <!-- Room temperature zone -->
  <rect x="442" y="80" width="362" height="130" fill="#0D0D0D" stroke="#2E3840" stroke-width="1" stroke-dasharray="5,3" rx="4"/>
  <text x="452" y="97" fill="#5C6A75" font-size="9" font-weight="700">ROOM TEMPERATURE</text>

  <!-- RT Amp -->
  <rect x="452" y="105" width="95" height="90" fill="#0A1A0A" stroke="#3DDC84" stroke-width="1.5" rx="3"/>
  <rect x="452" y="105" width="95" height="5" fill="#3DDC84" rx="1"/>
  <text x="499" y="128" fill="#3DDC84" font-size="10" font-weight="700" text-anchor="middle">RT AMP</text>
  <text x="499" y="145" fill="#9AA5B0" font-size="9" text-anchor="middle">Second gain</text>
  <text x="499" y="160" fill="#9AA5B0" font-size="9" text-anchor="middle">300 K noise</text>
  <text x="499" y="178" fill="#9AA5B0" font-size="9" text-anchor="middle">~40 dB gain</text>
  <line x1="547" y1="150" x2="567" y2="150" stroke="#3DDC84" stroke-width="2" marker-end="url(#gb)"/>

  <!-- IQ Mixer -->
  <rect x="569" y="105" width="85" height="90" fill="#0A1818" stroke="#2DD4BF" stroke-width="1.5" rx="3"/>
  <rect x="569" y="105" width="85" height="5" fill="#2DD4BF" rx="1"/>
  <text x="611" y="128" fill="#2DD4BF" font-size="10" font-weight="700" text-anchor="middle">IQ MIXER</text>
  <text x="611" y="145" fill="#9AA5B0" font-size="9" text-anchor="middle">Splits into</text>
  <text x="611" y="160" fill="#2DD4BF" font-size="9" text-anchor="middle">I channel</text>
  <text x="611" y="175" fill="#2DD4BF" font-size="9" text-anchor="middle">Q channel</text>
  <line x1="654" y1="150" x2="674" y2="150" stroke="#FFB020" stroke-width="2" marker-end="url(#ab)"/>

  <!-- ADC — the key box, highlighted -->
  <rect x="676" y="94" width="108" height="108" fill="#1C150A" stroke="#FFB020" stroke-width="2.5" rx="3"/>
  <rect x="676" y="94" width="108" height="7" fill="#FFB020" rx="1"/>
  <text x="730" y="122" fill="#FFB020" font-size="12" font-weight="700" text-anchor="middle">ADC</text>
  <text x="730" y="140" fill="#FFB020" font-size="9" font-weight="700" text-anchor="middle">YOUR</text>
  <text x="730" y="154" fill="#FFB020" font-size="9" font-weight="700" text-anchor="middle">SIMULATOR</text>
  <text x="730" y="170" fill="#9AA5B0" font-size="9" text-anchor="middle">{bits}-bit</text>
  <text x="730" y="184" fill="#9AA5B0" font-size="9" text-anchor="middle">SNR={adc_snr:.1f} dB</text>
  <line x1="784" y1="148" x2="806" y2="148" stroke="#FFB020" stroke-width="2" marker-end="url(#ab)"/>
  <!-- Digital out -->
  <text x="810" y="140" fill="#3DDC84" font-size="9">|0⟩</text>
  <text x="810" y="158" fill="#F04747" font-size="9">|1⟩</text>

  <!-- "models this" callout -->
  <line x1="730" y1="202" x2="730" y2="222" stroke="#FFB020" stroke-width="1" stroke-dasharray="3,2"/>
  <text x="730" y="234" fill="#FFB020" font-size="9" text-anchor="middle" font-weight="700">← your project models this</text>

  <!-- ── NOISE BUDGET TABLE ── -->
  <rect x="14" y="256" width="792" height="22" fill="#1C2228"/>
  <text x="14" y="272" fill="#5C6A75" font-size="9" letter-spacing="2">NOISE BUDGET — LIVE VALUES</text>

  <!-- ADC noise -->
  <rect x="14" y="280" width="190" height="100" fill="#1C150A" stroke="#FFB020" stroke-width="1"/>
  <text x="24" y="300" fill="#FFB020" font-size="10" font-weight="700">ADC Quantization</text>
  <text x="24" y="317" fill="#9AA5B0" font-size="9">Step size = 2 / 2^{bits}</text>
  <text x="24" y="333" fill="#9AA5B0" font-size="9">        = {2/(2**bits)*1000:.2f} mV</text>
  <text x="24" y="349" fill="#FFB020" font-size="9">SNR = {adc_snr:.1f} dB</text>
  <text x="24" y="365" fill="#9AA5B0" font-size="9">Improved by: more bits</text>
  <text x="24" y="376" fill="#9AA5B0" font-size="9">or oversampling</text>

  <!-- Shot noise -->
  <rect x="218" y="280" width="190" height="100" fill="#1A0808" stroke="#F04747" stroke-width="1"/>
  <text x="228" y="300" fill="#F04747" font-size="10" font-weight="700">Quantum Shot Noise</text>
  <text x="228" y="317" fill="#9AA5B0" font-size="9">N_photons = {n_photons}</text>
  <text x="228" y="333" fill="#9AA5B0" font-size="9">σ = amplitude / √N</text>
  <text x="228" y="349" fill="#F04747" font-size="9">SNR = {shot_snr_db:.1f} dB</text>
  <text x="228" y="365" fill="#9AA5B0" font-size="9">Improved by: more photons</text>
  <text x="228" y="376" fill="#F04747" font-size="9">NOT by ADC bits (SQL)</text>

  <!-- Combined -->
  <rect x="422" y="280" width="190" height="100" fill="#0A0A1A" stroke="#A78BFA" stroke-width="1"/>
  <text x="432" y="300" fill="#A78BFA" font-size="10" font-weight="700">Combined SNR</text>
  <text x="432" y="317" fill="#9AA5B0" font-size="9">1/total = 1/ADC + 1/shot</text>
  <text x="432" y="333" fill="#A78BFA" font-size="9">= {total_snr_db:.1f} dB</text>
  <text x="432" y="349" fill="#9AA5B0" font-size="9">error = ½·erfc(√(SNR/2))</text>
  <text x="432" y="365" fill="#9AA5B0" font-size="9">     = {err_pct:.3f}%</text>
  <text x="432" y="376" fill="{bot_color}" font-size="9" font-weight="700">Bottleneck: {bottleneck}</text>

  <!-- Fidelity -->
  <rect x="626" y="280" width="180" height="100" fill="#041A08" stroke="{fid_color}" stroke-width="2"/>
  <text x="636" y="300" fill="{fid_color}" font-size="10" font-weight="700">Fidelity</text>
  <text x="636" y="317" fill="#9AA5B0" font-size="9">= 1 − error</text>
  <text x="636" y="337" fill="{fid_color}" font-size="16" font-weight="700">{fidelity*100:.2f}%</text>
  <text x="636" y="358" fill="#9AA5B0" font-size="9">IBM target: &gt;99%</text>
  <text x="636" y="374" fill="{fid_color}" font-size="9" font-weight="700">{"✓ MEETS TARGET" if fidelity > 0.99 else "✗ BELOW TARGET"}</text>

  <!-- IQ scatter legend -->
  <rect x="14" y="392" width="792" height="22" fill="#1C2228"/>
  <text x="14" y="408" fill="#5C6A75" font-size="9" letter-spacing="2">IQ SCATTER INTERPRETATION</text>

  <rect x="14" y="416" width="398" height="70" fill="#0A0A1A" stroke="#A78BFA" stroke-width="1"/>
  <text x="24" y="434" fill="#A78BFA" font-size="10" font-weight="700">How to read the IQ plot</text>
  <text x="24" y="450" fill="#9AA5B0" font-size="9">Each dot = one qubit measurement (I, Q coordinates from ADC)</text>
  <text x="24" y="466" fill="#A78BFA" font-size="9">|0⟩ cluster: left side   |1⟩ cluster: right side</text>
  <text x="24" y="480" fill="#F04747" font-size="9">Red dots = readout errors (crossed the decision boundary)</text>

  <rect x="426" y="416" width="380" height="70" fill="#041A08" stroke="{fid_color}" stroke-width="1"/>
  <text x="436" y="434" fill="{fid_color}" font-size="10" font-weight="700">Current result</text>
  <text x="436" y="450" fill="#9AA5B0" font-size="9">Tighter clusters = more ADC bits = fewer dots cross boundary</text>
  <text x="436" y="466" fill="{bot_color}" font-size="9" font-weight="700">To improve: {"increase ADC bits →" if "ADC" in bottleneck else "increase readout photons →"} fidelity rises</text>
  <text x="436" y="480" fill="#9AA5B0" font-size="9">Ref: Krantz et al. (2019) · ICARUS-Q (2022)</text>
</svg>
"""
    html = f"""<!DOCTYPE html>
<html><head><style>body{{margin:0;padding:0;background:#0b0d0f;overflow-x:hidden}}</style></head>
<body>{svg}</body></html>"""
    components.html(html, height=520, scrolling=False)

def show_quantum_ui():
    st.header("Quantum Readout Simulator")
    st.markdown(
        "In real quantum computers, qubit states are read via a microwave resonator. "
        "The analog signal is amplified and digitized by an ADC. "
        "**ADC resolution directly determines qubit readout fidelity.** "
        "But beyond a certain bit depth, **quantum shot noise** — not the ADC — "
        "becomes the limiting factor."
    )

    if not QISKIT_OK:
        st.warning("Qiskit not installed. Run: `pip install qiskit qiskit-aer`  "
                   "Showing DSP simulation only.")

    with st.sidebar:
        st.subheader("Quantum Readout Controls")
        bits       = st.slider("ADC Bits", 4, 16, 8,
                               help="12+ bits needed for >99% fidelity")
        freq       = st.slider("Readout Freq (MHz)", 1, 100, 10)
        amplitude  = st.slider("Signal Amplitude", 0.05, 1.0, 0.3, step=0.05,
                               help="Qubit signals are weak: 0.1–0.4")
        noise_std  = st.slider("Amplifier Noise", 0.0, 0.2, 0.05, step=0.005)
        n_photons  = st.slider("Readout Photons (N)", 1, 200, 20,
                               help="More photons = less shot noise, but more back-action on qubit")
        shots      = st.slider("Qiskit Shots", 256, 4096, 1024, step=256)
        n_iq       = st.slider("IQ Scatter Points", 50, 500, 200)

    sample_rate = max(freq * 10, 100)
    duration    = max(20 / freq, 0.05)
    t, signal   = generate_sine(freq, duration, sample_rate, amplitude)

    # Shot noise: irreducible quantum noise from discrete photon arrivals
    # std = sqrt(N_photons) in normalized units — CANNOT be reduced by better ADC
    shot_noise_std = amplitude / np.sqrt(n_photons) if n_photons > 0 else 0
    total_noise    = np.sqrt(noise_std**2 + shot_noise_std**2)

    noisy     = signal + np.random.normal(0, total_noise, size=signal.shape)
    quantized = quantize(noisy, bits)

    # ADC SNR (quantization only)
    adc_snr        = compute_snr(signal, quantized)
    enob           = compute_enob(adc_snr)
    noise_floor    = 2.0 / (2 ** bits)

    # Shot noise SNR limit
    shot_snr_db    = compute_shot_noise_snr(n_photons)

    # Combined SNR (ADC + shot noise — noise powers add)
    total_snr_db   = combined_readout_snr(adc_snr, n_photons)

    # Readout error using physically correct erfc() formula
    readout_error  = snr_to_readout_error(total_snr_db)
    fidelity       = 1.0 - readout_error

    # Is ADC or shot noise the bottleneck?
    adc_limited  = adc_snr < shot_snr_db
    bottleneck   = "ADC quantization" if adc_limited else "Quantum shot noise"

    I_0, Q_0, I_1, Q_1 = generate_iq_signal(
        freq, duration, sample_rate,
        amplitude_0=amplitude * 0.4,
        amplitude_1=amplitude,
        noise_std=total_noise + noise_floor,
        n_shots=n_iq,
    )

    with st.spinner("Running Qiskit simulation..."):
        counts = _run_qiskit(readout_error, shots=shots)

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ADC SNR",       f"{adc_snr:.1f} dB")
    c2.metric("Shot Noise SNR", f"{shot_snr_db:.1f} dB",
              delta="Quantum limit",
              delta_color="off")
    c3.metric("Total SNR",     f"{total_snr_db:.1f} dB")
    c4.metric("Fidelity",      f"{fidelity * 100:.2f}%",
              delta="Good" if fidelity > 0.99 else "Needs improvement",
              delta_color="normal" if fidelity > 0.99 else "inverse")

    # Bottleneck banner — the key insight of this mode
    if adc_limited:
        st.info(
            f"**ADC is the bottleneck** — increasing ADC bits will improve fidelity. "
            f"Shot noise SNR ({shot_snr_db:.1f} dB) > ADC SNR ({adc_snr:.1f} dB)."
        )
    else:
        st.warning(
            f"**Shot noise is the bottleneck** — adding more ADC bits gives NO improvement. "
            f"Only increasing readout photons (N={n_photons}) can help further. "
            f"This is the Standard Quantum Limit (SQL)."
        )

    if fidelity >= 0.99:
        st.success(f"Fidelity {fidelity*100:.2f}% meets quantum computing threshold (>99%).")
    else:
        st.error(f"Fidelity {fidelity*100:.2f}% below 99%. {bottleneck} is limiting.")

    tab_plot, tab_circuit = st.tabs(["IQ Scatter + Histogram", "Circuit Diagram"])

    with tab_plot:
        fig = plot_quantum(t, quantized, noise_floor, bits,
                           readout_error, counts, I_0, Q_0, I_1, Q_1)
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)

    with tab_circuit:
        st.markdown("#### Quantum Readout Circuit — From Qubit to Digital Result")
        st.caption(
            "Shows the complete hardware chain your simulator models. "
            "Values update live as you change sliders. "
            "The ADC box (highlighted in amber) is exactly what this mode simulates."
        )
        _render_quantum_circuit(
            bits, adc_snr, shot_snr_db, total_snr_db,
            readout_error, fidelity, bottleneck, n_photons
        )

    with st.expander("Physics — shot noise and the Standard Quantum Limit"):
        st.markdown(f"""
**Quantum shot noise** arises because the readout pulse contains a finite number
of photons (N={n_photons}). Photons arrive randomly — even a perfectly steady beam
has fluctuations of σ = √N (Poisson statistics). This is irreducible quantum noise.

**Your current noise budget:**
| Source | Std Dev | SNR |
|--------|---------|-----|
| ADC quantization | `{noise_floor/2:.5f}` V | `{adc_snr:.1f}` dB |
| Amplifier thermal | `{noise_std:.5f}` V | — |
| Quantum shot noise | `{shot_noise_std:.5f}` V | `{shot_snr_db:.1f}` dB |
| **Combined** | `{total_noise:.5f}` V | **`{total_snr_db:.1f}` dB** |

**Bottleneck: {bottleneck}**

**Readout error formula (erfc-based, not heuristic):**
```
error = (1/2) × erfc(√(SNR_total / 2))
      = (1/2) × erfc(√({10**(total_snr_db/10)/2:.3f}))
      = {readout_error:.6f}
```
This is the exact Gaussian overlap integral between the |0⟩ and |1⟩ IQ blobs.

**References:** Krantz et al. (2019), ICARUS-Q (2022), HERQULES arXiv:2212.03895
        """)

    with st.expander("📖 Full explanation — click to learn everything about quantum readout"):
        from modes.tutor import explain_quantum
        explain_quantum(bits, adc_snr, readout_error, fidelity, noise_floor)
