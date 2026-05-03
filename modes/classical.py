"""
classical.py — Unified Classical ADC Mode
All classical sub-modes in one page with a pill navigator.

Sub-modes:
  ⚡ Standard ADC      — full pipeline, SNR/ENOB/THD/SINAD
  📈 Oversampling      — M× oversample, averaging decimation
  🌊 Aliasing          — Nyquist violation demo
  🔧 Real-World Noise  — thermal + jitter + quantization
  🎛️ Dithering         — TPDF, harmonics disappear
  🎬 Live Animation    — frame-by-frame canvas
  🏭 Industrial        — presets, sweep, DNL/INL, ENOB(f), T1/T2
"""
import streamlit as st

# Sub-mode registry — ordered list
SUB_MODES = [
    {"id": "standard",   "icon": "⚡", "label": "Standard ADC"},
    {"id": "oversampling","icon": "📈", "label": "Oversampling"},
    {"id": "aliasing",   "icon": "🌊", "label": "Aliasing"},
    {"id": "realworld",  "icon": "🔧", "label": "Real-World Noise"},
    {"id": "dithering",  "icon": "🎛️", "label": "Dithering"},
    {"id": "animation",  "icon": "🎬", "label": "Live Animation"},
    {"id": "industrial", "icon": "🏭", "label": "Industrial"},
]

SUB_FN = {
    "standard":    lambda: _lazy("modes.standard",       "show_standard_ui"),
    "oversampling": lambda: _lazy("modes.oversampling",  "show_oversampling_ui"),
    "aliasing":    lambda: _lazy("modes.aliasing",       "show_aliasing_ui"),
    "realworld":   lambda: _lazy("modes.realworld",      "show_realworld_ui"),
    "dithering":   lambda: _lazy("modes.dithering",      "show_dithering_ui"),
    "animation":   lambda: _lazy("modes.animation",      "show_animation_ui"),
    "industrial":  lambda: _lazy("modes.industrial_mode","show_industrial_ui"),
}


def _lazy(module: str, fn: str):
    """Import and call a sub-mode function lazily (avoid circular imports)."""
    import importlib
    mod = importlib.import_module(module)
    getattr(mod, fn)()


def show_classical_ui():
    # ── Session state: which sub-mode is active ──────────────────────────
    if "classical_tab" not in st.session_state:
        st.session_state.classical_tab = "standard"

    active = st.session_state.classical_tab

    # ── Pill navigator ────────────────────────────────────────────────────
    st.markdown("""
<style>
.pill-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 10px 0 12px;
    border-bottom: 1px solid var(--border, #252d35);
    margin-bottom: 16px;
}
.pill-nav-item {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: .06em;
    text-transform: uppercase;
    padding: 5px 12px;
    border: 1px solid #252d35;
    background: #111418;
    color: #9aa5b0;
    cursor: pointer;
    white-space: nowrap;
    transition: all .1s;
}
.pill-nav-item.active {
    background: #0b0d0f;
    color: #ffb020;
    border-color: #ffb020;
    border-bottom: 2px solid #ffb020;
}
.pill-nav-item:hover { color: #e8eaec; background: #161b20; }
</style>
""", unsafe_allow_html=True)

    # Render pill buttons as a horizontal row using columns
    cols = st.columns(len(SUB_MODES))
    for col, sub in zip(cols, SUB_MODES):
        with col:
            is_active = active == sub["id"]
            label = f"{sub['icon']} {sub['label']}"
            # Highlight active button with native Streamlit styling trick
            if is_active:
                st.markdown(
                    f'<div style="font-family:JetBrains Mono,monospace;'
                    f'font-size:10px;letter-spacing:.05em;text-transform:uppercase;'
                    f'padding:6px 8px;background:#0b0d0f;color:#ffb020;'
                    f'border:1px solid #ffb020;border-bottom:2px solid #ffb020;'
                    f'text-align:center;margin-bottom:4px">{label}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(label, key=f"pill_{sub['id']}", use_container_width=True):
                    st.session_state.classical_tab = sub["id"]
                    st.rerun()

    # ── Render active sub-mode ────────────────────────────────────────────
    st.markdown(
        f'<div style="height:2px;background:#4da8da;margin:0 0 12px;opacity:0.6"></div>',
        unsafe_allow_html=True,
    )

    SUB_FN[active]()
