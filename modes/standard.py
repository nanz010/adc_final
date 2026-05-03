import numpy as np
import streamlit as st

from signal_generator import generate_waveform, compute_fft, compute_psd
from adc_processor import quantize, compute_snr, compute_enob, compute_thd, compute_sinad
from plot_renderer import PLOTLY_CONFIG, plot_standard, plot_fft_spectrum, plot_psd, plot_snr_sweep, plot_error_histogram
from modes.tutor import explain_standard, explain_graph_controls
from modes.animations import show_standard_animation

WAVEFORMS = ["Sine", "Square", "Triangle", "Sawtooth"]


def show_standard_ui():
    st.header("Standard ADC")
    st.markdown(
        "Full ADC pipeline: analog → sampling → quantization → error. "
        "Theoretical SNR = **6.02·N + 1.76 dB** (Bennett, 1948). "
        "IEEE 1241 standard uses Sine, Square, and Triangle for ADC testing."
    )

    with st.sidebar:
        st.subheader("Standard ADC Controls")
        waveform    = st.selectbox("Input Waveform", WAVEFORMS,
                                   help="Sine is standard for ADC testing (IEEE 1241). Square/Triangle reveal harmonic distortion.")
        bits        = st.slider("ADC Bits (N)", 1, 16, 8,
                                help="Number of bits = number of quantization levels = 2^N. More bits → finer resolution → less noise.")
        freq        = st.slider("Signal Frequency (Hz)", 1, 500, 50,
                                help="Frequency of the input signal. Must be less than sample_rate/2 (Nyquist limit) to avoid aliasing.")
        sample_rate = st.slider("Sampling Rate (Hz)", 100, 5000, 1000,
                                help="How many samples per second the ADC takes. Must be > 2× signal frequency.")
        amplitude   = st.slider("Amplitude", 0.1, 1.0, 1.0, step=0.05,
                                help="Peak voltage of the signal. Full scale (1.0) gives best SNR.")

    duration = max(20 / freq, 0.05)
    t_dense,  analog   = generate_waveform(waveform, freq, duration, 10000, amplitude)
    t_sampled, sampled = generate_waveform(waveform, freq, duration, sample_rate, amplitude)
    quantized  = quantize(sampled, bits)
    error      = quantized - sampled
    snr        = compute_snr(sampled, quantized)
    enob       = compute_enob(snr)
    ideal_snr  = 6.02 * bits + 1.76
    thd        = compute_thd(sampled, quantized, freq, sample_rate)
    sinad      = compute_sinad(sampled, quantized, sample_rate, freq)
    enob_sinad = compute_enob(sinad)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("SNR",          f"{snr:.1f} dB",
              help="Signal-to-Noise Ratio from quantization noise only.")
    c2.metric("Ideal SNR",    f"{ideal_snr:.1f} dB",
              help="Theoretical max: 6.02×N + 1.76 dB (Bennett 1948)")
    c3.metric("ENOB",         f"{enob:.2f} bits",
              help="Effective Number of Bits = (SNR − 1.76) / 6.02")
    c4.metric("SINAD",        f"{sinad:.1f} dB",
              help="Signal to Noise AND Distortion — includes harmonics. Always ≤ SNR.")
    c5.metric("ENOB (SINAD)", f"{enob_sinad:.2f} bits",
              help="ENOB from SINAD — more complete than SNR-based ENOB (IEEE 1241)")
    c6.metric("THD",          f"{thd:.1f} dB" if thd > -90 else "< −90 dB",
              help="Total Harmonic Distortion at 2f,3f,...8f. Lower = better. Dithering removes it.")

    # ── Two-column layout: graph left, tutor right ────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Time Domain", "FFT Spectrum", "PSD", "SNR vs Bits", "Error Histogram", "Block Diagram"
    ])

    with tab1:
        col_graph, col_tutor = st.columns([3, 1])
        with col_graph:
            fig = plot_standard(t_dense, analog, t_sampled, sampled, quantized, error, bits=bits)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        with col_tutor:
            explain_graph_controls()

    with tab2:
        col_graph, col_tutor = st.columns([3, 1])
        with col_graph:
            freqs_o, mag_o = compute_fft(sampled,   sample_rate)
            freqs_q, mag_q = compute_fft(quantized, sample_rate)
            fig = plot_fft_spectrum(freqs_o, mag_o, freqs_q, mag_q, freq, sample_rate)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        with col_tutor:
            from modes.tutor import inject_css, _box
            inject_css()
            _box("Reading the FFT",
                 f"The tall peak at <b>{freq} Hz</b> is your signal (the fundamental). "
                 f"Smaller peaks at 2f={freq*2}Hz, 3f={freq*3}Hz are harmonics — "
                 f"distortion from quantization. The flat region between peaks is the "
                 f"<b>noise floor</b> — lowering this requires more bits or oversampling. "
                 f"Y-axis is in dBFS: 0 dBFS = full scale, lower = weaker.")

    with tab3:
        col_graph, col_tutor = st.columns([3, 1])
        with col_graph:
            freqs_po, psd_o = compute_psd(sampled,   sample_rate)
            freqs_pq, psd_q = compute_psd(quantized, sample_rate)
            fig = plot_psd(freqs_po, psd_o, freqs_pq, psd_q, bits=bits, sample_rate=sample_rate)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        with col_tutor:
            from modes.tutor import inject_css, _box
            inject_css()
            _box("Reading the PSD",
                 "Power Spectral Density shows how noise power is "
                 "distributed across frequencies (Welch method, same as MATLAB pwelch). "
                 "A <b>lower and flatter floor</b> = better ADC. "
                 "The gap between the signal peak and the noise floor "
                 "is your SNR visualized in frequency space.")

    with tab4:
        col_graph, col_tutor = st.columns([3, 1])
        with col_graph:
            bits_range = list(range(1, 17))
            snr_sim  = [compute_snr(sampled, quantize(sampled, b)) for b in bits_range]
            snr_theo = [6.02 * b + 1.76 for b in bits_range]
            fig = plot_snr_sweep(bits_range, snr_sim, snr_theo)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        with col_tutor:
            from modes.tutor import inject_css, _box, _formula
            inject_css()
            _box("Reading SNR vs Bits",
                 "Dashed blue = theoretical 6.02N+1.76. "
                 "Orange dots = simulated values. "
                 "The shaded region = deviation from theory. "
                 "At low bits (1-3), simulated SNR deviates — "
                 "Bennett's white noise model breaks down when there "
                 "are very few quantization levels.")
            _formula("Each bit adds exactly +6.02 dB")

    with tab5:
        col_graph, col_tutor = st.columns([3, 1])
        with col_graph:
            fig = plot_error_histogram(error, bits)
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG)
        with col_tutor:
            from modes.tutor import inject_css, _box
            inject_css()
            _box("Reading the error histogram",
                 "Shows the distribution of quantization errors. "
                 "A <b>flat/uniform distribution</b> between ±step/2 "
                 "means the noise model holds — error is random white noise. "
                 "A <b>non-uniform or spiky</b> distribution at low bits "
                 "means distortion — the quantization noise correlates "
                 "with the signal and creates harmonics.")

    with tab6:
        st.markdown("#### ADC Internal Architecture — SAR Block Diagram")
        st.caption(
            "This shows what is physically inside a Successive Approximation Register (SAR) ADC. "
            "Every block in this diagram corresponds to a stage your simulator models. "
            "Values update live as you move the sliders."
        )
        _render_adc_block_diagram(bits, freq, sample_rate, waveform)

    # ── Full tutor panel below graphs ─────────────────────────────────────────
    with st.expander("📖 Full explanation — click to learn everything about this mode"):
        explain_standard(bits, freq, sample_rate, amplitude, snr, enob)

    show_standard_animation()


# ── Block diagram tab — added for hardware context ─────────────────────────
def _render_adc_block_diagram(bits, freq, sample_rate, waveform):
    """Render an interactive SVG block diagram of the SAR ADC internals."""
    import streamlit.components.v1 as components

    step_v  = f"{2.0 / (2**bits) * 1000:.2f} mV"
    levels  = 2 ** bits
    nyquist = sample_rate / 2
    alias_warn  = "⚠ ALIASING" if freq >= nyquist else "✓ OK"
    alias_color = "#F04747"    if freq >= nyquist else "#3DDC84"

    svg = f"""
<svg width="820" height="480" viewBox="0 0 820 480"
     xmlns="http://www.w3.org/2000/svg"
     style="font-family:'JetBrains Mono',monospace;background:#0b0d0f;display:block">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#FFB020"
            stroke-width="1.5" stroke-linecap="round"/>
    </marker>
    <marker id="arr-g" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#3DDC84"
            stroke-width="1.5" stroke-linecap="round"/>
    </marker>
  </defs>

  <!-- Title strip -->
  <rect x="0" y="0" width="820" height="32" fill="#1C2228"/>
  <text x="14" y="21" fill="#FFB020" font-size="11" font-weight="700"
        letter-spacing="3">ADC BLOCK DIAGRAM — SUCCESSIVE APPROXIMATION (SAR) TYPE</text>
  <text x="700" y="21" fill="#5C6A75" font-size="10">{bits}-bit · {sample_rate} Hz · {waveform}</text>

  <!-- Live status strip -->
  <rect x="0" y="32" width="820" height="26" fill="#111418"/>
  <text x="14"  y="50" fill="#9AA5B0" font-size="9">Signal: {freq} Hz</text>
  <text x="120" y="50" fill="#9AA5B0" font-size="9">Nyquist: {nyquist:.0f} Hz</text>
  <text x="240" y="50" fill="{alias_color}" font-size="9" font-weight="700">{alias_warn}</text>
  <text x="340" y="50" fill="#9AA5B0" font-size="9">Levels: {levels:,}</text>
  <text x="430" y="50" fill="#9AA5B0" font-size="9">Step: {step_v}</text>
  <text x="520" y="50" fill="#FFB020" font-size="9">SQNR: {6.02*bits+1.76:.1f} dB</text>
  <text x="640" y="50" fill="#9AA5B0" font-size="9">ENOB: {bits:.1f} bits (theory)</text>

  <!-- Analog input -->
  <rect x="14" y="100" width="90" height="90" fill="#161B20" stroke="#5C6A75" stroke-width="1"/>
  <text x="59" y="136" fill="#9AA5B0" font-size="10" text-anchor="middle">ANALOG</text>
  <text x="59" y="152" fill="#9AA5B0" font-size="10" text-anchor="middle">INPUT</text>
  <text x="59" y="170" fill="#4DA8DA" font-size="9" text-anchor="middle">{freq} Hz</text>
  <line x1="104" y1="145" x2="128" y2="145" stroke="#FFB020" stroke-width="2" marker-end="url(#arr)"/>

  <!-- Anti-alias filter -->
  <rect x="130" y="88" width="130" height="114" fill="#0C1A2E" stroke="#4DA8DA" stroke-width="1.5"/>
  <rect x="130" y="88" width="130" height="5"   fill="#4DA8DA"/>
  <text x="195" y="111" fill="#4DA8DA" font-size="10" font-weight="700" text-anchor="middle">ANTI-ALIAS</text>
  <text x="195" y="125" fill="#4DA8DA" font-size="10" font-weight="700" text-anchor="middle">FILTER</text>
  <text x="195" y="143" fill="#9AA5B0" font-size="9" text-anchor="middle">Low-pass at</text>
  <text x="195" y="156" fill="#FFB020" font-size="9" text-anchor="middle">f_cut = {nyquist:.0f} Hz</text>
  <text x="195" y="169" fill="#9AA5B0" font-size="9" text-anchor="middle">Blocks aliasing</text>
  <text x="195" y="183" fill="{alias_color}" font-size="9" text-anchor="middle" font-weight="700">{alias_warn}</text>
  <line x1="260" y1="145" x2="284" y2="145" stroke="#FFB020" stroke-width="2" marker-end="url(#arr)"/>

  <!-- Sample and hold -->
  <rect x="286" y="88" width="130" height="114" fill="#0A2218" stroke="#3DDC84" stroke-width="1.5"/>
  <rect x="286" y="88" width="130" height="5"   fill="#3DDC84"/>
  <text x="351" y="111" fill="#3DDC84" font-size="10" font-weight="700" text-anchor="middle">SAMPLE</text>
  <text x="351" y="125" fill="#3DDC84" font-size="10" font-weight="700" text-anchor="middle">&amp; HOLD</text>
  <text x="351" y="143" fill="#9AA5B0" font-size="9" text-anchor="middle">Capacitor charges</text>
  <text x="351" y="156" fill="#9AA5B0" font-size="9" text-anchor="middle">Switch opens</text>
  <text x="351" y="169" fill="#FFB020" font-size="9" text-anchor="middle">fs = {sample_rate} Hz</text>
  <text x="351" y="183" fill="#9AA5B0" font-size="9" text-anchor="middle">Aperture jitter here</text>
  <line x1="416" y1="145" x2="440" y2="145" stroke="#FFB020" stroke-width="2" marker-end="url(#arr)"/>

  <!-- Clock into S&H -->
  <line x1="351" y1="72" x2="351" y2="88" stroke="#5C6A75" stroke-width="1.5"
        stroke-dasharray="4,3" marker-end="url(#arr-g)"/>
  <text x="351" y="66" fill="#5C6A75" font-size="9" text-anchor="middle">Clock (fs)</text>

  <!-- Comparator + SAR -->
  <rect x="442" y="88" width="140" height="114" fill="#1C150A" stroke="#FFB020" stroke-width="2"/>
  <rect x="442" y="88" width="140" height="5"   fill="#FFB020"/>
  <text x="512" y="111" fill="#FFB020" font-size="10" font-weight="700" text-anchor="middle">COMPARATOR</text>
  <text x="512" y="125" fill="#FFB020" font-size="10" font-weight="700" text-anchor="middle">&amp; SAR LOGIC</text>
  <text x="512" y="143" fill="#9AA5B0" font-size="9" text-anchor="middle">V_in vs V_DAC</text>
  <text x="512" y="156" fill="#9AA5B0" font-size="9" text-anchor="middle">Binary search</text>
  <text x="512" y="169" fill="#FFB020" font-size="9" text-anchor="middle">{bits} steps per sample</text>
  <text x="512" y="183" fill="#9AA5B0" font-size="9" text-anchor="middle">Quantization noise here</text>
  <line x1="582" y1="145" x2="606" y2="145" stroke="#FFB020" stroke-width="2" marker-end="url(#arr)"/>

  <!-- DAC feedback -->
  <rect x="442" y="230" width="140" height="60" fill="#1C150A" stroke="#FFB020"
        stroke-width="1" stroke-dasharray="5,3"/>
  <text x="512" y="256" fill="#FFB020" font-size="10" font-weight="700" text-anchor="middle">DAC FEEDBACK</text>
  <text x="512" y="272" fill="#9AA5B0" font-size="9" text-anchor="middle">Generates V_ref</text>
  <text x="512" y="284" fill="#9AA5B0" font-size="9" text-anchor="middle">for each bit decision</text>
  <line x1="512" y1="202" x2="512" y2="230" stroke="#FFB020" stroke-width="1.5"
        stroke-dasharray="4,3" marker-end="url(#arr)"/>
  <line x1="442" y1="260" x2="360" y2="260" stroke="#FFB020" stroke-width="1.5"
        stroke-dasharray="4,3"/>
  <line x1="360" y1="202" x2="360" y2="260" stroke="#FFB020" stroke-width="1.5"
        stroke-dasharray="4,3" marker-end="url(#arr)"/>

  <!-- Output register -->
  <rect x="608" y="88" width="130" height="114" fill="#04221A" stroke="#22D3EE" stroke-width="1.5"/>
  <rect x="608" y="88" width="130" height="5"   fill="#22D3EE"/>
  <text x="673" y="111" fill="#22D3EE" font-size="10" font-weight="700" text-anchor="middle">OUTPUT</text>
  <text x="673" y="125" fill="#22D3EE" font-size="10" font-weight="700" text-anchor="middle">REGISTER</text>
  <text x="673" y="143" fill="#9AA5B0" font-size="9" text-anchor="middle">Stores {bits} bits</text>
  <text x="673" y="156" fill="#FFB020" font-size="9" text-anchor="middle">{levels:,} possible values</text>
  <text x="673" y="169" fill="#9AA5B0" font-size="9" text-anchor="middle">SNR = {6.02*bits+1.76:.1f} dB</text>
  <text x="673" y="183" fill="#9AA5B0" font-size="9" text-anchor="middle">Output to CPU/DSP</text>
  <line x1="738" y1="145" x2="760" y2="145" stroke="#22D3EE" stroke-width="2"
        marker-end="url(#arr-g)"/>
  <text x="772" y="149" fill="#22D3EE" font-size="10">OUT</text>

  <!-- What your simulator models section -->
  <rect x="14" y="318" width="792" height="22" fill="#1C2228"/>
  <text x="20" y="334" fill="#5C6A75" font-size="9" letter-spacing="2">WHAT YOUR SIMULATOR MODELS AT EACH STAGE</text>

  <rect x="14"  y="342" width="238" height="124" fill="#0C1A2E" stroke="#4DA8DA" stroke-width="1"/>
  <text x="24"  y="361" fill="#4DA8DA" font-size="10" font-weight="700">Anti-alias filter</text>
  <text x="24"  y="378" fill="#9AA5B0" font-size="9">→ Aliasing Demo sub-mode</text>
  <text x="24"  y="394" fill="#9AA5B0" font-size="9">Shows what happens when fs &lt; 2f</text>
  <text x="24"  y="410" fill="#9AA5B0" font-size="9">f_alias = f mod fs, fold at Nyquist</text>
  <text x="24"  y="426" fill="{alias_color}" font-size="9" font-weight="700">{alias_warn}</text>
  <text x="24"  y="442" fill="#9AA5B0" font-size="9">Sample &amp; Hold → Live Animation</text>
  <text x="24"  y="458" fill="#9AA5B0" font-size="9">Step-by-step sampling visible</text>

  <rect x="266" y="342" width="270" height="124" fill="#1C150A" stroke="#FFB020" stroke-width="1"/>
  <text x="276" y="361" fill="#FFB020" font-size="10" font-weight="700">Comparator &amp; SAR</text>
  <text x="276" y="378" fill="#9AA5B0" font-size="9">→ Standard ADC (this sub-mode)</text>
  <text x="276" y="394" fill="#FFB020" font-size="9">SQNR = 6.02×{bits} + 1.76 = {6.02*bits+1.76:.1f} dB</text>
  <text x="276" y="410" fill="#9AA5B0" font-size="9">Step = 2/2^{bits} = {2/(2**bits)*1000:.3f} mV</text>
  <text x="276" y="426" fill="#9AA5B0" font-size="9">Quantization error: ±step/2</text>
  <text x="276" y="442" fill="#9AA5B0" font-size="9">→ Dithering sub-mode (noise before comparator)</text>
  <text x="276" y="458" fill="#9AA5B0" font-size="9">→ Oversampling (multiple samples/step)</text>

  <rect x="550" y="342" width="256" height="124" fill="#04221A" stroke="#22D3EE" stroke-width="1"/>
  <text x="560" y="361" fill="#22D3EE" font-size="10" font-weight="700">Output register → Metrics</text>
  <text x="560" y="378" fill="#9AA5B0" font-size="9">SNR  = {6.02*bits+1.76:.1f} dB</text>
  <text x="560" y="394" fill="#9AA5B0" font-size="9">ENOB = {(6.02*bits+1.76-1.76)/6.02:.2f} bits</text>
  <text x="560" y="410" fill="#9AA5B0" font-size="9">THD  = harmonics at 2f, 3f, 4f...</text>
  <text x="560" y="426" fill="#9AA5B0" font-size="9">SINAD = noise + distortion combined</text>
  <text x="560" y="442" fill="#9AA5B0" font-size="9">DNL/INL = linearity (Industrial sub-mode)</text>
  <text x="560" y="458" fill="#22D3EE" font-size="9">IEEE 1241-2010 standard compliant</text>
</svg>
"""
    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ margin:0; padding:0; background:#0b0d0f; overflow-x:hidden; }}
</style>
</head>
<body>
{svg}
</body>
</html>
"""
    components.html(html, height=500, scrolling=False)
