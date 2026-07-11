"""Sistem visual dashboard (doc 10): palet, template plotly, komponen kartu.

Palet mengikuti metode dataviz: warna status KHUSUS alarm (tidak untuk seri),
seri kategorikal urutan tetap, heatmap satu-hue biru. Dark surface #1a1a19.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# --- palet (dark mode, doc 10 §2) ---
SURFACE = "#1a1a19"
PAGE = "#0d0d0d"
INK = "#ffffff"
INK2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"

SERIES = ["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9"]  # urutan TETAP
STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
    "info": "#3987e5",
}
SEQ_BLUE = [
    [0.0, "#cde2fb"], [0.25, "#86b6ef"], [0.5, "#3987e5"],
    [0.75, "#1c5cab"], [1.0, "#0d366b"],
]

SEV_ICON = {"critical": "🔴", "serious": "🟠", "warning": "🟡", "info": "🔵"}


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


def kpi(col, label: str, value: str, status: str, delta: str | None = None):
    icon = {"good": "🟢", "warning": "🟡", "serious": "🟠", "critical": "🔴"}[status]
    col.metric(f"{icon} {label}", value, delta=delta)


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
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("✔ Terima", key=f"acc_{key}"):
                st.session_state.advisory_log.append(
                    {"hour": st.session_state.hour, "title": card["title"], "decision": "terima"}
                )
                st.toast("Advisory diterima — dicatat di audit trail")
            if c2.button("✘ Tolak", key=f"rej_{key}"):
                st.session_state.advisory_log.append(
                    {"hour": st.session_state.hour, "title": card["title"], "decision": "tolak"}
                )
                st.toast("Advisory ditolak — dicatat di audit trail")


def empty_state(feature: str, reason: str):
    st.info(f"Panel **{feature}** nonaktif — {reason}", icon="ℹ️")
