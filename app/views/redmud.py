"""Tab 5 — Red Mud & CCUS: Sankey aluminium + panel karbonasi (paper 2026)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src.physics import carbonation


def render(row: pd.Series, ctx: dict):
    st.subheader("Sankey Aluminium — dari feed ke produk (dan yang bocor)")
    al_feed = float(row["al_feed_t"])
    al_lost = float(row["al_lost_redmud_t"])
    al_recycled = float(row["al_recycled_t"])
    al_product = max(al_feed - al_lost, 1e-3)

    labels = ["Al dari Bauksit", "Liquor (recycle)", "Digesti+Presipitasi",
              "Produk Al(OH)₃", "Hilang ke Red Mud"]
    node_colors = [ui.SERIES[0], ui.SERIES[1], ui.SERIES[0],
                   ui.STATUS["good"], ui.STATUS["critical"]]
    fig = go.Figure(go.Sankey(
        node=dict(label=labels, color=node_colors, pad=24, thickness=16,
                  line=dict(color=ui.GRID, width=1)),
        link=dict(
            source=[0, 1, 2, 2, 2],
            target=[2, 2, 3, 4, 1],
            value=[al_feed, al_recycled, al_product, al_lost, al_recycled],
            color="rgba(255,255,255,0.14)",
        ),
    ))
    st.plotly_chart(ui.base_layout(fig, height=340), use_container_width=True)
    st.caption(
        f"Ton Al per basis ~100 t bauksit. Hilang ke red mud: "
        f"**{al_lost:.1f} t Al** ({al_lost / al_feed * 100:.1f}% feed) — "
        "setiap ton ini juga menaikkan alkalinitas & volume tailing."
    )

    st.divider()
    st.subheader("♻️ Karbonasi Akuatik Langsung — red mud sebagai sink CO₂")
    st.caption(
        "Kalkulator deterministik dari paper ScienceDirect 2026 "
        "(2.3 g CO₂/100 g RM · L/S 2:1 · mass loss 14.19% vs 10.74%)."
    )
    price = st.number_input(
        "Harga karbon (Rp/ton CO₂)", min_value=0.0, value=30_000.0, step=10_000.0,
        help="Default: tarif pajak karbon RI (Rp30/kg). Coba harga EU ETS ±Rp1,4 jt/ton.",
    )
    res = carbonation.assess(float(row["red_mud_t"]), carbon_price_idr=price)

    c = st.columns(4)
    c[0].metric("Red mud jam ini", f"{res.red_mud_t:.1f} t")
    c[1].metric("CO₂ tersekuestrasi", f"{res.co2_sequestered_t:.2f} t")
    c[2].metric("Air dibutuhkan (L/S 2:1)", f"{res.water_needed_t:.0f} t")
    c[3].metric("Nilai karbon", f"Rp{res.carbon_value_idr:,.0f}")

    lo, hi = res.ph_after_est
    reg_lo, reg_hi = carbonation.PH_REG_BAND
    ok = res.compliant_est
    with st.container(border=True):
        st.markdown(
            f"**Status pH tailing (estimasi)**  \n"
            f"Sebelum karbonasi: pH {res.ph_before[0]:.0f}–{res.ph_before[1]:.0f} "
            f"(di luar baku mutu) → sesudah: **pH {lo:.1f}–{hi:.1f}**  \n"
            f"{'🟢' if ok else '🟠'} "
            f"{'MEMENUHI' if ok else 'BELUM PASTI MEMENUHI'} pita Permen LHK "
            f"No. 6/2021 (pH {reg_lo:.0f}–{reg_hi:.0f}) — "
            f"<span style='color:{ui.MUTED}'>membuka jalur pemanfaatan backfill / "
            f"produk sirkular alih-alih landfill.</span>",
            unsafe_allow_html=True,
        )
