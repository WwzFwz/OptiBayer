"""Tab 4 — Presipitasi: kurva Ceq + gap supersaturasi (uang yang belum diambil)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src.advisory import knowledge
from src.physics import precipitation


def render(row: pd.Series, ctx: dict):
    st.subheader("Kurva Ekuilibrium Gibbsite — gap supersaturasi", help="Persamaan Misra & Pearl (1981): log(Al₂O₃) = 6.2106 - 2486.7/T(K) + 1.0875 * log10(NaOH g/L). Lihat docs/equilibrium_constants.json")
    st.caption(
        "Overlay fisika (korelasi Misra, belum terkalibrasi pabrik). Gap antara "
        "alumina terlarut (A) dan garis Ceq = driving force presipitasi = "
        "yield yang masih bisa diambil."
    )

    c1, c2 = st.columns([1, 3])
    with c1:
        a_gl = st.slider("Alumina terlarut A (g/L)", 80.0, 180.0, 130.0, 5.0)
        caustic = float(row["naoh_conc_gl"])
        t_now = float(row["precip_temp_c"])
        st.metric("Kaustik (dari digesti)", f"{caustic:.0f} g/L")
        st.metric("Suhu presipitasi", f"{t_now:.1f} °C")
        gap = precipitation.supersaturation_gap(a_gl, t_now, caustic)
        st.metric("Gap supersaturasi", f"{gap:.1f} g/L",
                  help="A − Ceq(T, kaustik): makin besar, makin banyak yang bisa diendapkan")

    with c2:
        temps, ceqs = precipitation.ceq_curve(caustic)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temps, y=ceqs, name="Ceq (ekuilibrium)", mode="lines",
            line=dict(color=ui.SERIES[0], width=2),
            hovertemplate="T=%{x:.0f}°C · Ceq=%{y:.1f} g/L<extra></extra>",
        ))
        fig.add_hline(y=a_gl, line=dict(color=ui.SERIES[2], width=2, dash="dash"),
                      annotation_text=f"A saat ini ≈ {a_gl:.0f} g/L",
                      annotation_font=dict(color=ui.SERIES[2]))
        fig.add_trace(go.Scatter(
            x=[t_now], y=[float(precipitation.ceq(t_now, caustic))],
            mode="markers+text", text=["titik operasi"], textposition="top center",
            textfont=dict(color=ui.INK), name="Operasi",
            marker=dict(color=ui.INK, size=12, symbol="x"),
        ))
        fig.update_layout(xaxis_title="Suhu (°C)", yaxis_title="Al₂O₃ terlarut (g/L)")
        st.plotly_chart(ui.base_layout(fig, height=380), width="stretch")

    ui.explain_chart("ceq", "Kurva Ceq — Gap Supersaturasi",
                     tags=knowledge.CHART_TAGS["ceq"]["tags"], context={
                         "alumina_terlarut_a_gl": a_gl,
                         "ceq_pada_suhu_operasi_gl": float(
                             precipitation.ceq(t_now, caustic)),
                         "gap_supersaturasi_gl": gap,
                         "suhu_presipitasi_c": t_now,
                         "kaustik_gl": caustic,
                         "yield_sekarang_pct": ctx["predicted_now"].get(
                             "precip_yield_pct"),
                         "yield_jika_rekomendasi_pct": ctx[
                             "predicted_if_followed"].get("precip_yield_pct"),
                     })

    st.divider()
    d = ctx["delta_if_followed"]
    reco = ctx["recommended_knobs"]
    with st.container(border=True):
        st.markdown(
            f"**Rekomendasi stasiun presipitasi** — suhu "
            f"**{reco['precip_temp_c']:.1f} °C**, rasio seed **{reco['seed_ratio']:.2f}** "
            f"→ prediksi yield {ctx['predicted_if_followed'].get('precip_yield_pct', 0):.1f}% "
            f"({d.get('precip_yield_pct', 0):+.1f}%)  \n"
            f"<span style='color:{ui.MUTED}'>Suhu lebih rendah menurunkan Ceq "
            f"(gap membesar → yield naik) tapi memperlambat kinetika — optimizer "
            f"menyeimbangkan keduanya lewat data.</span>",
            unsafe_allow_html=True,
        )
