"""Sistem visual dashboard (doc 10): palet, template plotly, komponen kartu.

Palet mengikuti metode dataviz: warna status KHUSUS alarm (tidak untuk seri),
seri kategorikal urutan tetap, heatmap satu-hue biru. Dark surface #1a1a19.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# --- palet dua-mode (doc 10 §2 + palet light dari referensi dataviz) ---
# Nilai module-level di bawah DIGANTI oleh apply(mode) — view membacanya saat
# render (ui.SERIES[...]), jadi toggle tema cukup memanggil apply() + rerun.
_DARK = dict(
    SURFACE="#1a1a19", PAGE="#0d0d0d", INK="#ffffff", INK2="#c3c2b7",
    MUTED="#898781", GRID="#2c2c2a",
    SERIES=["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9"],
    SEQ_BLUE=[[0.0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#3987e5"],
              [0.75, "#1c5cab"], [1.0, "#0d366b"]],
    LINK_FADE="rgba(255,255,255,0.14)",   # link Sankey
    DIV_MID="#2c2c2a",                    # titik tengah skala diverging
    READ_BG="#0c0c0b", READ_BORDER="#3a3a38", VALUE_COLOR="#ffd84d",
    UNIT_FILL="#262624", LABEL_BG="rgba(13,13,13,0.7)",
)
_LIGHT = dict(
    SURFACE="#fcfcfb", PAGE="#f9f9f7", INK="#0b0b0b", INK2="#52514e",
    MUTED="#898781", GRID="#e1e0d9",
    SERIES=["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7"],
    SEQ_BLUE=[[0.0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#2a78d6"],
              [0.75, "#1c5cab"], [1.0, "#0d366b"]],
    LINK_FADE="rgba(11,11,11,0.12)",
    DIV_MID="#f0efec",
    READ_BG="#f0efec", READ_BORDER="#c3c2b7", VALUE_COLOR="#8a5a00",
    UNIT_FILL="#f3f2ee", LABEL_BG="rgba(252,252,251,0.8)",
)
MODE = "dark"


def apply(mode: str) -> None:
    """Tukar seluruh palet chart ke 'dark'/'light' (dipanggil main.py per run)."""
    global MODE
    MODE = "light" if mode == "light" else "dark"
    globals().update(_LIGHT if MODE == "light" else _DARK)


# warna status: SAMA di kedua mode (dipasangkan ikon+label, doc 10)
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
    "info": "#3987e5",
}
SEV_ICON = {"critical": "🔴", "serious": "🟠", "warning": "🟡", "info": "🔵"}

apply("dark")  # default; main.py menimpa sesuai toggle

# label navigasi utama — dipakai main.py (render) & kartu advisory (lompat tab)
NAV_LABELS = {
    "overview": ":material/monitoring: Overview",
    "pfd": ":material/account_tree: Diagram Proses",
    "digestion": ":material/local_fire_department: Digesti",
    "liquor": ":material/science: Liquor Loop",
    "precip": ":material/ac_unit: Presipitasi",
    "redmud": ":material/recycling: Red Mud & CCUS",
    "lab": ":material/biotech: Prediction Lab",
    "knowledge": ":material/menu_book: Knowledge",
}


def goto(page: str) -> None:
    """Lompat programatik ke halaman navigasi (dipanggil tombol jembatan)."""
    st.session_state["nav"] = NAV_LABELS[page]
    st.rerun()


def inject_css(mode: str) -> None:
    """CSS global: tombol lebih jelas + light mode penuh.

    Tema inti Streamlit tidak punya API resmi utk diganti saat runtime,
    jadi light mode ditegakkan lewat CSS di sini (chart sudah ikut via apply()).
    Konvensi tombol: primary = aksi positif/utama -> HIJAU status.
    """
    base = """
    <style>
    /* tombol: lebih besar & tegas */
    .stButton button, [data-testid="stSegmentedControl"] button {
        font-size: 1rem; border-radius: 8px;
    }
    .stButton button { padding: 0.55rem 1.1rem; }
    .stButton button p { font-size: 1rem; }
    /* primary = aksi positif (Terima, Play, dsb) -> hijau status */
    .stButton button[kind="primary"] {
        background-color: #0ca30c; border: 1px solid #0ca30c; color: #ffffff;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #0b8f0b; border-color: #0b8f0b; color: #ffffff;
    }
    /* stat tile KPI: kartu rapat, nilai menonjol, tinggi seragam */
    [data-testid="stMetricValue"] { font-size: 1.75rem; font-weight: 700; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem; }
    [class*="st-key-kpi_"] { min-height: 8.2rem; text-align: center; }
    [class*="st-key-kpi_"] [data-testid="stMetricValue"] { justify-content: center; }
    [class*="st-key-kpi_"] [data-testid="stMetricValue"] > div { width: auto; }
    [class*="st-key-kpi_"] [data-testid="stMetricDelta"] { justify-content: center; }
    [class*="st-key-kpi_"] [data-testid="stMetric"] { text-align: center; }
    /* tombol Tolak (key rej_*) = destruktif -> merah outline, penuh saat hover */
    [class*="st-key-rej_"] button {
        border: 1px solid #d03b3b; color: #d03b3b;
    }
    [class*="st-key-rej_"] button p { color: inherit; }
    [class*="st-key-rej_"] button:hover {
        background-color: #d03b3b; border-color: #d03b3b; color: #ffffff;
    }
    </style>
    """
    light = """
    <style>
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #f9f9f7; color: #0b0b0b;
    }
    [data-testid="stHeader"] { background: rgba(249,249,247,0.85); }
    [data-testid="stSidebar"] { background-color: #fcfcfb; }
    [data-testid="stSidebar"] * { color: #0b0b0b; }
    h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown,
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
    [data-testid="stWidgetLabel"] p { color: #0b0b0b; }
    [data-testid="stCaptionContainer"], .stCaption, small { color: #52514e; }
    [data-testid="stExpander"] details, div[data-testid="stExpander"] {
        background-color: #fcfcfb; border-color: #e1e0d9;
    }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color: #e1e0d9; }
    </style>
    """
    st.markdown(base + (light if mode == "light" else ""), unsafe_allow_html=True)


def base_layout(fig: go.Figure, height: int = 300, title: str | None = None) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=INK2, family="system-ui, 'Segoe UI', sans-serif", size=13),
        title=dict(text=title, font=dict(color=INK, size=15)) if title else None,
        margin=dict(l=50, r=20, t=45 if title else 20, b=40),
        height=height,
        hovermode="x unified",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def trend(x, y, name: str, *, band: tuple[float, float] | None = None,
          color: str = SERIES[0], height: int = 220, title: str | None = None,
          band_label: str = "pita aman") -> go.Figure:
    """Line chart tren + pita alarm translusen (doc 10 tab Overview)."""
    fig = go.Figure()
    if band:
        fig.add_hrect(
            y0=band[0], y1=band[1], fillcolor="rgba(255,255,255,0.05)",
            line_width=0, annotation_text=band_label,
            annotation_font=dict(color=MUTED, size=11),
        )
        fig.add_hline(y=band[0], line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_hline(y=band[1], line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_trace(go.Scatter(
        x=list(x), y=list(y), name=name, mode="lines",
        line=dict(color=color, width=2),
        hovertemplate="%{y:.2f}<extra></extra>",
    ))
    return base_layout(fig, height=height, title=title)


def status_of(value: float, good: tuple[float, float],
              warn: tuple[float, float]) -> str:
    """good di dalam pita good; warning di pita warn; selain itu critical."""
    if good[0] <= value <= good[1]:
        return "good"
    if warn[0] <= value <= warn[1]:
        return "warning"
    return "critical"


def kpi(col, label: str, value: str, status: str, delta: str | None = None,
        *, invert: bool = False):
    """Stat tile ber-kartu: titik status vektor + label + nilai + delta.

    `invert=True` untuk metrik yang NAIK = BURUK (OPEX, red mud, silika):
    panah naik jadi merah, turun jadi hijau.
    """
    slug = "".join(ch if ch.isalnum() else "_" for ch in label.lower())
    with col.container(border=True, key=f"kpi_{slug}"):
        st.markdown(
            f"<span style='color:{STATUS[status]};font-size:0.7em'>●</span> "
            f"<span style='color:{MUTED};font-size:0.78em;font-weight:600;"
            f"letter-spacing:0.05em'>{label.upper()}</span>",
            unsafe_allow_html=True,
        )
        st.metric(label, value, delta=delta,
                  delta_color="inverse" if invert else "normal",
                  label_visibility="collapsed")
        if delta is None:
            # placeholder setinggi baris delta -> semua kartu KPI sama tinggi
            st.markdown(
                f"<span style='font-size:0.85rem;color:{MUTED}'>&nbsp;</span>",
                unsafe_allow_html=True,
            )


def _persist_decision(hour: int, title: str, decision: str) -> None:
    """Audit trail persisten: tiap keputusan advisory ditulis ke CSV
    (data/processed/advisory_log.csv) — bertahan lintas restart/refresh,
    melengkapi log sesi di st.session_state."""
    try:
        import csv
        from datetime import datetime
        from pathlib import Path

        p = (Path(__file__).resolve().parents[1]
             / "data" / "processed" / "advisory_log.csv")
        p.parent.mkdir(parents=True, exist_ok=True)
        is_new = not p.exists()
        with p.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(["waktu", "jam_sim", "judul", "keputusan"])
            w.writerow([datetime.now().isoformat(timespec="seconds"),
                        hour, title, decision])
    except Exception:
        pass  # audit file gagal ditulis tidak boleh mematikan dashboard


def advisory_card(card: dict, key: str):
    """Kartu APA/DAMPAK/LAKUKAN/KENAPA + tombol keputusan (human-in-the-loop)."""
    color = STATUS[card["severity"]]
    icon = SEV_ICON[card["severity"]]
    with st.container(border=True):
        st.markdown(
            f"<span style='color:{color};font-weight:700'>{icon} "
            f"{card['severity'].upper()}</span> — **{card['title']}**",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"**Dampak:** {card['impact']}  \n"
            f"**Tindakan:** {card['action']}  \n"
            f"<span style='color:{MUTED}'>Kenapa: {card['why']} · "
            f"Confidence: {card['confidence']}</span>",
            unsafe_allow_html=True,
        )
        if card["severity"] != "info":
            hour = st.session_state.get("hour", 0)
            decided = next(
                (l for l in st.session_state.advisory_log
                 if l["hour"] == hour and l["title"] == card["title"]), None,
            )
            if decided:
                # feedback tegas: keputusan terkunci, tercatat di audit trail
                badge = ("✓ DITERIMA" if decided["decision"] == "terima"
                         else "✗ DITOLAK")
                bcol = (STATUS["good"] if decided["decision"] == "terima"
                        else STATUS["critical"])
                st.markdown(
                    f"<span style='color:{bcol};font-weight:700'>{badge}</span> "
                    f"<span style='color:{MUTED}'>— tercatat di audit trail "
                    f"(jam {hour:02d}:00)</span>",
                    unsafe_allow_html=True,
                )
            else:
                c1, c2, c3, _ = st.columns([1.2, 1.2, 1.6, 2])
                if c1.button("Terima", key=f"acc_{key}", type="primary",
                             icon=":material/check_circle:", width="stretch"):
                    st.session_state.advisory_log.append(
                        {"hour": hour, "title": card["title"], "decision": "terima"}
                    )
                    _persist_decision(hour, card["title"], "terima")
                    st.rerun()
                if c2.button("Tolak", key=f"rej_{key}",
                             icon=":material/cancel:", width="stretch"):
                    st.session_state.advisory_log.append(
                        {"hour": hour, "title": card["title"], "decision": "tolak"}
                    )
                    _persist_decision(hour, card["title"], "tolak")
                    st.rerun()
                if c3.button("Lihat peta operasi", key=f"map_{key}",
                             icon=":material/map:", width="stretch",
                             help="Lompat ke tab Digesti — rekomendasi ditandai ★ di peta"):
                    goto("digestion")


def explain_chart(chart_id: str, title: str, context: dict,
                  tags: list[str] | None = None):
    """Tombol 'Analisis AI' reusable di bawah sebuah chart.

    Konteks = angka milik chart itu saja (grounding per-chart). Jawaban
    di-cache di session per (chart, pertanyaan) supaya rerun tidak
    memanggil ulang LLM.
    """
    from src.advisory import providers

    with st.expander(f":material/auto_awesome: Analisis AI — {title}"):
        q = st.text_input(
            "Pertanyaan (opsional — kosongkan untuk penjelasan umum)",
            key=f"exq_{chart_id}",
            placeholder="mis. mana kebocoran terbesar & apa tindakannya?",
        )
        if st.button("Analisis", key=f"exb_{chart_id}",
                     icon=":material/auto_awesome:"):
            with st.spinner("Menganalisis angka chart..."):
                ans, backend = providers.explain_chart(title, context, q, tags)
            st.session_state[f"exa_{chart_id}"] = (ans, backend, q)
        cached = st.session_state.get(f"exa_{chart_id}")
        if cached:
            ans, backend, prev_q = cached
            if prev_q:
                st.caption(f"Pertanyaan: {prev_q}")
            st.markdown(ans)
            st.caption(f"backend: {backend} · jawaban dihitung dari angka "
                       "chart ini saja (grounded)")


def empty_state(feature: str, reason: str):
    st.info(f"Panel **{feature}** nonaktif — {reason}", icon="ℹ️")
