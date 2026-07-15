"""Tab 3 — Liquor Loop: Sankey natrium (ke mana NaOH bocor) + dosis make-up."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src.utils import converters


def render(row: pd.Series, ctx: dict):
    nb = ctx["na_balance"]
    ca = ctx["cao_advisory"]

    st.subheader("Sankey Natrium — ke mana uang NaOH mengalir")
    st.caption(
        "Satuan: ton/jam (skala pabrik, dry feed dari data). Dekomposisi "
        "kebocoran = estimasi neraca Na ber-asumsi eksplisit (doc 06 Bag. 6 — "
        "menunggu data causticity bervariasi untuk soft sensor ML)."
    )

    labels = [
        "NaOH Make-up (segar)",        # 0
        "Liquor Recycle",              # 1
        "Digesti",                     # 2
        "Loss Kimiawi (DSP/Sodalit)",  # 3
        "Soda Mati (Na₂CO₃ net)",      # 4
        "Loss Fisik (moisture red mud)",  # 5
        "Kembali ke Liquor",           # 6
    ]
    node_colors = [
        ui.SERIES[0], ui.SERIES[1], ui.SERIES[0],
        ui.STATUS["critical"], ui.STATUS["serious"], ui.STATUS["warning"],
        ui.SERIES[1],
    ]
    src = [0, 1, 2, 2, 2, 2]
    dst = [2, 2, 3, 4, 5, 6]
    val = [
        max(nb["makeup_t"], 1e-3),
        max(nb["recycled_t"], 1e-3),
        max(nb["dsp_loss_t"], 1e-3),
        max(nb["dead_soda_net_t"], 1e-3),
        max(nb["physical_loss_t"], 1e-3),
        max(nb["recycled_t"], 1e-3),
    ]
    fig = go.Figure(go.Sankey(
        node=dict(label=labels, color=node_colors, pad=24, thickness=16,
                  line=dict(color=ui.GRID, width=1)),
        link=dict(source=src, target=dst, value=val,
                  color=ui.LINK_FADE),
    ))
    st.plotly_chart(ui.base_layout(fig, height=380), width="stretch")

    total_loss = nb["dsp_loss_t"] + nb["dead_soda_net_t"] + nb["physical_loss_t"]
    c = st.columns(4)
    c[0].metric("Total kebocoran NaOH", f"{total_loss:.2f} t")
    c[1].metric("• Kimiawi (DSP)", f"{nb['dsp_loss_t']:.2f} t")
    c[2].metric("• Soda mati (net)", f"{nb['dead_soda_net_t']:.2f} t")
    c[3].metric("• Fisik (red mud)", f"{nb['physical_loss_t']:.2f} t")

    st.divider()
    st.subheader("Dosis Make-up: rekomendasi vs aktual")
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("**CaO (kaustisasi soda mati)**")
        icon = {"sesuai": "🟢", "over-dosing": "🟠", "under-dosing": "🟡"}.get(ca["status"], "⚪")
        act_l = converters.ton_to_liters(ca['cao_actual_t']) if not pd.isna(ca['cao_actual_t']) else 0
        rec_l = converters.ton_to_liters(ca['cao_recommended_t'])
        st.markdown(
            f"{icon} Status: **{ca['status']}**  \n"
            f"Aktual: {ca['cao_actual_t']:.2f} t ({act_l:,.0f} L/jam) · Stoikiometrik: "
            f"{ca['cao_recommended_t']:.2f} t ({rec_l:,.0f} L/jam)  \n"
            f"<span style='color:{ui.MUTED}'>Estimasi Na₂CO₃ terbentuk: "
            f"{ca['na2co3_est_t']:.2f} t · reaksi Na₂CO₃ + Ca(OH)₂ → 2NaOH + CaCO₃</span>",
            unsafe_allow_html=True,
        )
    with right, st.container(border=True):
        st.markdown("**NaOH segar**")
        st.markdown(
            f"Make-up aktual: {nb['makeup_t']:.2f} t per basis  \n"
            f"Terbesar dimakan: **DSP dari silika reaktif "
            f"{ctx['composition']['reactive_sio2_pct']:.1f}%**  \n"
            f"<span style='color:{ui.MUTED}'>Turunkan silika feed (blending) atau "
            f"naikkan efisiensi pra-desilikasi untuk menekan make-up.</span>",
            unsafe_allow_html=True,
        )
