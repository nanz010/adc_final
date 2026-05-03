import streamlit as st
from modes import show_classical_ui, show_quantum_ui, show_comparison_ui

st.set_page_config(
    page_title="ADC Analyzer Pro — QtHack04",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

for key, val in [("page", "home"), ("visited", set()), ("show_formulas", True)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── CSS — identical instrument theme ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

:root {
  --bg0:#0b0d0f; --bg1:#111418; --bg2:#161b20; --bg3:#1c2228;
  --border:#252d35; --border2:#2e3840;
  --text0:#e8eaec; --text1:#9aa5b0; --text2:#5c6a75;
  --amber:#ffb020; --green:#3ddc84; --blue:#4da8da;
  --red:#f04747;   --purple:#a78bfa; --cyan:#22d3ee;
  --teal:#2dd4bf;  --orange:#fb923c;
}

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .block-container,
section[data-testid="stSidebar"] {
    background-color: var(--bg0) !important;
    color: var(--text0) !important;
}
[data-testid="stHeader"] { background: var(--bg0) !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* Status bar */
.inst-statusbar {
    display:flex; align-items:center; justify-content:space-between;
    height:28px; background:var(--bg1); border-bottom:1px solid var(--border);
    padding:0 16px; font-family:'JetBrains Mono',monospace; font-size:10px;
    color:var(--text2); letter-spacing:.06em; text-transform:uppercase;
    position:sticky; top:0; z-index:100;
}
.inst-statusbar-left  { display:flex; align-items:center; gap:20px; }
.inst-statusbar-right { display:flex; align-items:center; gap:16px; }
.sb-dot { width:6px; height:6px; border-radius:50%; display:inline-block; margin-right:5px; }
.sb-dot-on  { background:var(--green); box-shadow:0 0 6px var(--green); }
.sb-sep { width:1px; height:14px; background:var(--border2); }

.inst-body { padding: 0 20px 24px; }

/* Instrument panel */
.inst-panel {
    background:var(--bg1); border:1px solid var(--border);
    border-top:3px solid var(--amber); margin:0 0 16px; padding:0;
    font-family:'JetBrains Mono',monospace;
}
.inst-panel-header {
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 16px; border-bottom:1px solid var(--border); background:var(--bg2);
}
.inst-panel-title { font-size:11px; font-weight:700; color:var(--amber); letter-spacing:.12em; text-transform:uppercase; }
.inst-panel-sub   { font-size:10px; color:var(--text2); letter-spacing:.04em; }
.inst-panel-body  { padding:16px; }

/* Readout strip */
.readout-row {
    display:grid; grid-template-columns:repeat(5,1fr); gap:1px;
    background:var(--border); border:1px solid var(--border); margin-bottom:14px;
}
.readout-cell { background:var(--bg0); padding:10px 12px; text-align:center; }
.readout-label { font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--text2); letter-spacing:.1em; text-transform:uppercase; display:block; margin-bottom:4px; }
.readout-value { font-family:'Share Tech Mono','JetBrains Mono',monospace; font-size:18px; color:var(--amber); line-height:1; }
.readout-value.green { color:var(--green); }
.readout-value.blue  { color:var(--blue); }

/* Formula register */
.formula-reg { display:flex; align-items:stretch; border:1px solid var(--border); margin-bottom:16px; overflow:hidden; }
.formula-reg-label { background:var(--amber); color:#000; font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; padding:0 12px; display:flex; align-items:center; white-space:nowrap; flex-shrink:0; }
.formula-reg-items { display:flex; background:var(--bg0); flex:1; overflow-x:auto; scrollbar-width:none; }
.formula-reg-items::-webkit-scrollbar { display:none; }
.formula-reg-item  { padding:8px 16px; border-right:1px solid var(--border); white-space:nowrap; }
.fri-name { font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--text2); letter-spacing:.08em; text-transform:uppercase; display:block; margin-bottom:3px; }
.fri-val  { font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--cyan); }

/* 3-card grid */
.mode-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1px; background:var(--border); border:1px solid var(--border); margin-bottom:1px; }
.mode-card { background:var(--bg1); padding:0; cursor:pointer; position:relative; overflow:hidden; }
.mode-card:hover { background:var(--bg2); }
.mode-card-accent { position:absolute; left:0; top:0; bottom:0; width:4px; }
.mode-card-body   { padding:20px 20px 18px 26px; }
.mode-num   { font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--text2); letter-spacing:.12em; margin-bottom:8px; }
.mode-icon  { font-size:28px; margin-bottom:8px; display:block; }
.mode-title { font-family:'JetBrains Mono',monospace; font-size:15px; font-weight:700; color:var(--text0); margin-bottom:6px; letter-spacing:.02em; }
.mode-desc  { font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--text1); line-height:1.6; margin-bottom:12px; }
.mode-tags  { display:flex; flex-wrap:wrap; gap:4px; margin-bottom:4px; }
.mode-tag   { font-family:'JetBrains Mono',monospace; font-size:8px; padding:2px 6px; background:var(--bg0); border:1px solid var(--border2); color:var(--text2); letter-spacing:.04em; }
.mode-visited { color:var(--green); font-size:9px; font-family:'JetBrains Mono',monospace; }

/* Mode top bar */
.inst-topbar { display:flex; align-items:center; height:40px; background:var(--bg1); border-bottom:1px solid var(--border); padding:0 16px; font-family:'JetBrains Mono',monospace; margin-bottom:0; }

/* Measurement table */
.meas-table { width:100%; border-collapse:collapse; border:1px solid var(--border); font-family:'JetBrains Mono',monospace; margin-bottom:14px; background:var(--bg0); }
.meas-table th { background:var(--bg2); color:var(--text2); font-size:9px; letter-spacing:.1em; text-transform:uppercase; padding:6px 10px; border:1px solid var(--border); font-weight:500; text-align:left; }
.meas-table td { padding:8px 10px; border:1px solid var(--border); font-size:12px; color:var(--amber); vertical-align:middle; }
.meas-table td.label { color:var(--text1); font-size:10px; background:var(--bg1); letter-spacing:.04em; }

/* Sidebar */
[data-testid="stSidebar"] > div { background:var(--bg1) !important; border-right:1px solid var(--border) !important; min-width:258px !important; max-width:278px !important; }
[data-testid="stSidebar"] * { color:var(--text0) !important; }
[data-testid="stSidebar"] label { font-family:'JetBrains Mono',monospace !important; font-size:10px !important; color:var(--text2) !important; letter-spacing:.06em !important; text-transform:uppercase !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background:var(--amber) !important; }

/* Metrics */
[data-testid="stMetricValue"] { font-family:'Share Tech Mono','JetBrains Mono',monospace !important; font-size:1.4rem !important; font-weight:400 !important; color:var(--amber) !important; }
[data-testid="stMetricLabel"] { font-family:'JetBrains Mono',monospace !important; font-size:0.68rem !important; color:var(--text2) !important; letter-spacing:.08em !important; text-transform:uppercase !important; }

/* Tabs */
[data-testid="stTabs"] [role="tablist"] { background:var(--bg1) !important; border-bottom:1px solid var(--border) !important; gap:0 !important; }
[data-testid="stTabs"] button { font-family:'JetBrains Mono',monospace !important; font-size:10px !important; letter-spacing:.06em !important; text-transform:uppercase !important; color:var(--text2) !important; background:var(--bg1) !important; border-right:1px solid var(--border) !important; border-radius:0 !important; padding:8px 16px !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color:var(--amber) !important; background:var(--bg0) !important; border-bottom:2px solid var(--amber) !important; }
[data-testid="stTabs"] button:hover { color:var(--text0) !important; background:var(--bg2) !important; }

/* Expanders */
[data-testid="stExpander"] { background:var(--bg1) !important; border:1px solid var(--border) !important; border-radius:0 !important; }
[data-testid="stExpander"] summary { font-family:'JetBrains Mono',monospace !important; font-size:10px !important; color:var(--text1) !important; letter-spacing:.06em !important; text-transform:uppercase !important; background:var(--bg2) !important; padding:8px 12px !important; }

/* Buttons */
[data-testid="stButton"] > button { background:var(--bg2) !important; border:1px solid var(--border2) !important; color:var(--text1) !important; border-radius:0 !important; font-family:'JetBrains Mono',monospace !important; font-size:10px !important; letter-spacing:.06em !important; text-transform:uppercase !important; padding:6px 12px !important; }
[data-testid="stButton"] > button:hover { background:var(--bg3) !important; border-color:var(--amber) !important; color:var(--amber) !important; }

/* Selectbox */
[data-testid="stSelectbox"] > div > div { background:var(--bg0) !important; border:1px solid var(--border2) !important; border-radius:0 !important; color:var(--text0) !important; font-family:'JetBrains Mono',monospace !important; font-size:11px !important; }

/* Alerts */
[data-testid="stAlert"] { border-radius:0 !important; border-left-width:3px !important; background:var(--bg2) !important; font-family:'JetBrains Mono',monospace !important; font-size:11px !important; }

/* Markdown */
[data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li { color:var(--text1) !important; font-size:12px !important; line-height:1.6 !important; }
[data-testid="stMarkdownContainer"] code { background:var(--bg2) !important; color:var(--cyan) !important; border:1px solid var(--border) !important; border-radius:2px !important; font-size:11px !important; padding:1px 4px !important; }
[data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4 { color:var(--text0) !important; font-family:'JetBrains Mono',monospace !important; letter-spacing:.04em !important; }
hr { border-color:var(--border) !important; }
h1,h2,h3,h4 { font-family:'JetBrains Mono',monospace !important; color:var(--text0) !important; }
[data-testid="stProgress"] > div > div { background:var(--amber) !important; }
</style>
""", unsafe_allow_html=True)

# ── 3-mode registry ───────────────────────────────────────────────────────────
MODES = [
    {
        "id":     "classical",
        "num":    "MODE 01",
        "icon":   "⚡",
        "title":  "Classical ADC",
        "accent": "#4da8da",
        "desc":   (
            "All classical simulation modes in one place — "
            "Standard ADC, Oversampling, Aliasing, Real-World Noise, "
            "Dithering, Live Animation, and Industrial Analysis. "
            "Switch between sub-modes instantly using the pill navigator."
        ),
        "tags":   ["SNR","ENOB","THD","SINAD","Oversampling","Aliasing","Dithering","DNL","INL"],
        "fn":     show_classical_ui,
    },
    {
        "id":     "quantum",
        "num":    "MODE 02",
        "icon":   "⚛️",
        "title":  "Quantum Readout",
        "accent": "#a78bfa",
        "desc":   (
            "ADC resolution directly limits qubit readout fidelity. "
            "IQ scatter plot, shot noise limit, erfc readout error model, "
            "Qiskit noise simulation, and the quantum circuit diagram "
            "from qubit to digital discriminator."
        ),
        "tags":   ["Qubit","IQ scatter","erfc","Shot noise","Qiskit","T1/T2"],
        "fn":     show_quantum_ui,
    },
    {
        "id":     "comparison",
        "num":    "MODE 03",
        "icon":   "📊",
        "title":  "Comparison",
        "accent": "#2dd4bf",
        "desc":   (
            "Side-by-side quality comparison. Bit depth: 4-bit vs 8 vs 12 vs 16. "
            "Oversampling: 1× vs 4× vs 16× vs 64×. "
            "FFT and SNR sweep across all configurations simultaneously."
        ),
        "tags":   ["Bit depth","OSR","FFT","SNR sweep","Side-by-side"],
        "fn":     show_comparison_ui,
    },
]
MODE_BY_ID = {m["id"]: m for m in MODES}


# ─────────────────────────────────────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_home():
    import datetime
    now     = datetime.datetime.now().strftime("%H:%M:%S")
    visited = st.session_state.visited

    # Status bar
    st.markdown(f"""
<div class="inst-statusbar">
  <div class="inst-statusbar-left">
    <span><span class="sb-dot sb-dot-on"></span>SYSTEM READY</span>
    <div class="sb-sep"></div>
    <span>ADC-ANALYZER-PRO v25.0</span>
    <div class="sb-sep"></div>
    <span>QTHACK04 · SRMIST · TRACK-04 · PROB-19</span>
  </div>
  <div class="inst-statusbar-right">
    <span>{len(visited)}/3 MODES VISITED</span>
    <div class="sb-sep"></div>
    <span>{now}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="inst-body">', unsafe_allow_html=True)

    # Instrument panel
    st.markdown("""
<div class="inst-panel">
  <div class="inst-panel-header">
    <div>
      <div class="inst-panel-title">⚡ ADC Resolution &amp; Noise Simulator</div>
      <div class="inst-panel-sub">SRMIST Kattankulathur · QtHack04 · Track 04: Quantum Systems · Problem #19 · March 30–31 2026</div>
    </div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#5c6a75;text-align:right;line-height:1.8">
      Bennett (1948) · IEEE 1241-2010<br>
      ICARUS-Q (2022) · LIGO O4 (2024)<br>
      Krantz et al. (2019)
    </div>
  </div>
  <div class="inst-panel-body" style="padding:12px 16px 0">
""", unsafe_allow_html=True)

    # Readout strip
    st.markdown("""
<div class="readout-row">
  <div class="readout-cell">
    <span class="readout-label">Modes</span>
    <span class="readout-value">3</span>
  </div>
  <div class="readout-cell">
    <span class="readout-label">SQNR formula</span>
    <span class="readout-value" style="font-size:13px">6.02N+1.76</span>
  </div>
  <div class="readout-cell">
    <span class="readout-label">OSR gain / 2×M</span>
    <span class="readout-value green">+3.01 dB</span>
  </div>
  <div class="readout-cell">
    <span class="readout-label">Readout model</span>
    <span class="readout-value blue" style="font-size:13px">½·erfc</span>
  </div>
  <div class="readout-cell">
    <span class="readout-label">Dither type</span>
    <span class="readout-value" style="font-size:13px">TPDF</span>
  </div>
</div>
""", unsafe_allow_html=True)
    st.markdown('  </div>\n</div>', unsafe_allow_html=True)

    # Formula register toggle
    show_f = st.toggle("Show formula register", value=st.session_state.show_formulas,
                       key="formula_toggle")
    st.session_state.show_formulas = show_f
    if show_f:
        st.markdown("""
<div class="formula-reg">
  <div class="formula-reg-label">REGISTERS</div>
  <div class="formula-reg-items">
    <div class="formula-reg-item"><span class="fri-name">SQNR</span><span class="fri-val">6.02·N + 1.76 dB</span></div>
    <div class="formula-reg-item"><span class="fri-name">ENOB</span><span class="fri-val">(SNR − 1.76) / 6.02</span></div>
    <div class="formula-reg-item"><span class="fri-name">OSR gain</span><span class="fri-val">10·log₁₀(M) / 2 dB</span></div>
    <div class="formula-reg-item"><span class="fri-name">Nyquist</span><span class="fri-val">f_s &gt; 2·f_signal</span></div>
    <div class="formula-reg-item"><span class="fri-name">Readout err</span><span class="fri-val">½·erfc(√(SNR/2))</span></div>
    <div class="formula-reg-item"><span class="fri-name">Step (1 LSB)</span><span class="fri-val">(V_max − V_min) / 2^N</span></div>
    <div class="formula-reg-item"><span class="fri-name">Q-noise rms</span><span class="fri-val">Δ / √12</span></div>
    <div class="formula-reg-item"><span class="fri-name">Shot SNR</span><span class="fri-val">5·log₁₀(N_photons)</span></div>
    <div class="formula-reg-item"><span class="fri-name">THD</span><span class="fri-val">20·log₁₀(√ΣVₙ² / V₁)</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 3 mode cards ─────────────────────────────────────────────────────
    cols = st.columns(3, gap="small")
    for col, mode in zip(cols, MODES):
        with col:
            visited_mark = (
                ' <span class="mode-visited">■ VISITED</span>'
                if mode["id"] in visited else ""
            )
            tags_html = "".join(
                f'<span class="mode-tag">{t}</span>' for t in mode["tags"]
            )
            st.markdown(f"""
<div class="mode-card">
  <div class="mode-card-accent" style="background:{mode['accent']}"></div>
  <div class="mode-card-body">
    <div class="mode-num">{mode['num']}</div>
    <span class="mode-icon">{mode['icon']}</span>
    <div class="mode-title">{mode['title']}{visited_mark}</div>
    <div class="mode-desc">{mode['desc']}</div>
    <div class="mode-tags">{tags_html}</div>
  </div>
</div>""", unsafe_allow_html=True)
            if st.button("OPEN →", key=f"btn_{mode['id']}", use_container_width=True):
                st.session_state.visited.add(mode["id"])
                st.session_state.page = mode["id"]
                st.rerun()

    # Footer table
    st.markdown("""
<table class="meas-table" style="margin-top:16px">
  <tr>
    <th>Parameter</th><th>Value</th>
    <th>Parameter</th><th>Value</th>
    <th>Parameter</th><th>Value</th>
  </tr>
  <tr>
    <td class="label">Test standard</td><td>IEEE 1241-2010</td>
    <td class="label">Quantization model</td><td>Mid-tread uniform</td>
    <td class="label">FFT window</td><td>Hann (sum-normalized)</td>
  </tr>
  <tr>
    <td class="label">PSD method</td><td>Welch (8 seg)</td>
    <td class="label">Dither</td><td>TPDF (2× uniform)</td>
    <td class="label">Quantum noise</td><td>erfc Gaussian overlap</td>
  </tr>
  <tr>
    <td class="label">Oversampling</td><td>Avg decimation (CIC)</td>
    <td class="label">Jitter model</td><td>Analog Devices MT-008</td>
    <td class="label">T1/T2 model</td><td>Krantz et al. (2019)</td>
  </tr>
</table>
""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MODE PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_mode(mode_id: str):
    mode   = MODE_BY_ID[mode_id]
    accent = mode["accent"]

    # Status bar
    st.markdown(f"""
<div class="inst-statusbar">
  <div class="inst-statusbar-left">
    <span><span class="sb-dot sb-dot-on"></span>ACQUIRING</span>
    <div class="sb-sep"></div>
    <span>{mode['num']} · {mode['title'].upper()}</span>
  </div>
  <div class="inst-statusbar-right">
    <span>ADC-ANALYZER-PRO</span>
  </div>
</div>
""", unsafe_allow_html=True)

    # Nav bar
    mode_ids = [m["id"] for m in MODES]
    cur_idx  = mode_ids.index(mode_id)

    col_home, col_prev, col_next, col_title = st.columns([1, 1, 1, 7])
    with col_home:
        if st.button("⌂ HOME", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()
    with col_prev:
        if cur_idx > 0:
            p = MODES[cur_idx - 1]
            if st.button(f"◀ {p['num']}", use_container_width=True, help=p["title"]):
                st.session_state.visited.add(p["id"])
                st.session_state.page = p["id"]
                st.rerun()
    with col_next:
        if cur_idx < len(MODES) - 1:
            n = MODES[cur_idx + 1]
            if st.button(f"{n['num']} ▶", use_container_width=True, help=n["title"]):
                st.session_state.visited.add(n["id"])
                st.session_state.page = n["id"]
                st.rerun()
    with col_title:
        tags_html = " ".join(
            f'<span style="font-size:9px;padding:1px 5px;background:#161b20;'
            f'border:1px solid #2e3840;color:#5c6a75;margin-right:3px;'
            f'font-family:monospace">{t}</span>'
            for t in mode["tags"]
        )
        st.markdown(
            f'<div style="padding-top:6px;font-family:JetBrains Mono,monospace">'
            f'<span style="color:{accent};font-size:14px;font-weight:600">'
            f'{mode["icon"]} {mode["title"]}</span> '
            f'<span style="color:#5c6a75;font-size:10px">·</span> '
            f'{tags_html}</div>',
            unsafe_allow_html=True,
        )

    # Accent line
    st.markdown(
        f'<div style="height:2px;background:{accent};margin:0 0 8px;opacity:0.8"></div>',
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace;font-size:9px;'
            f'letter-spacing:.1em;text-transform:uppercase;color:{accent};'
            f'padding:10px 8px 8px;border-bottom:1px solid #252d35">'
            f'{mode["num"]} · {mode["title"]}</div>',
            unsafe_allow_html=True,
        )
        if st.button("⌂ HOME", use_container_width=True, key="sb_home"):
            st.session_state.page = "home"
            st.rerun()
        with st.expander("SWITCH MODE"):
            for m in MODES:
                if m["id"] != mode_id:
                    vis = "■ " if m["id"] in st.session_state.visited else "  "
                    if st.button(
                        f"{vis}{m['num']} {m['title']}",
                        key=f"sw_{m['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.visited.add(m["id"])
                        st.session_state.page = m["id"]
                        st.rerun()
        with st.expander("FORMULAS", expanded=False):
            st.markdown("""
`SQNR = 6.02·N + 1.76 dB`

`ENOB = (SNR − 1.76) / 6.02`

`OSR = 10·log₁₀(M) / 2 dB`

`f_s > 2·f_signal`

`err = ½·erfc(√(SNR/2))`

`THD = 20·log₁₀(√ΣVₙ²/V₁)`
""")

    mode["fn"]()


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
page = st.session_state.page
if page == "home":
    show_home()
elif page in MODE_BY_ID:
    show_mode(page)
else:
    st.session_state.page = "home"
    st.rerun()
