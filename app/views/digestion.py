"""Tab 2 — Digesti & Pra-desilikasi: operating map + what-if."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src import schema
from src.models import predict


@st.cache_data(show_spinner=False)
def _operating_map(comp_key: tuple, knobs_key: tuple, n: int = 25):
    comp = dict(zip(schema.INPUTS, comp_key))
    fixed = dict(zip(schema.KNOBS, knobs_key))
    b = schema.SAFE_BOUNDS
    temps = np.linspace(*b["digester_temp_c"], n)
    naohs = np.linspace(*b["naoh_conc_gl"], n)
    tt, nn = np.meshgrid(temps, naohs)
    knobs = pd.DataFrame({
        "particle_size_um": fixed["particle_size_um"],
        "digester_temp_c": tt.ravel(),
        "naoh_conc_gl": nn.ravel(),
        "precip_temp_c": fixed["precip_temp_c"],
        "seed_ratio": fixed["seed_ratio"],
    })
    z = predict.predict_frame(predict.frame(comp, knobs))["recovery_pct"]
    return temps, naohs, z.values.reshape(n, n)


def render(row: pd.Series, ctx: dict):
    comp = predict.composition_of(row)
    knobs_now = predict.knobs_of(row)
    reco = ctx["recommended_knobs"]

    st.subheader("Peta Operasi: Recovery = f(Suhu Digester × Konsentrasi NaOH)")
    st.caption(
        f"Dihitung surrogate untuk komposisi feed SAAT INI "
        f"(silika reaktif {comp['reactive_sio2_pct']:.1f}%). "
        "Knob lain ditahan pada nilai sekarang."
    )
    temps, naohs, z = _operating_map(
        tuple(comp[c] for c in schema.INPUTS),
        tuple(knobs_now[c] for c in schema.KNOBS),
    )
    fig = go.Figure(go.Heatmap(
        x=temps, y=naohs, z=z, colorscale=ui.SEQ_BLUE,
        colorbar=dict(title="Recovery %", tickfont=dict(color=ui.INK2)),
        hovertemplate="T=%{x:.1f}°C · NaOH=%{y:.0f} g/L · recovery=%{z:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[knobs_now["digester_temp_c"]], y=[knobs_now["naoh_conc_gl"]],
        mode="markers+text", text=["ANDA DI SINI"], textposition="bottom center",
        textfont=dict(color=ui.INK), name="Saat ini",
        marker=dict(color=ui.INK, size=14, symbol="x"),
    ))
    fig.add_trace(go.Scatter(
        x=[reco["digester_temp_c"]], y=[reco["naoh_conc_gl"]],
        mode="markers+text", text=["REKOMENDASI"], textposition="top center",
        textfont=dict(color=ui.STATUS["good"]), name="Rekomendasi",
        marker=dict(color=ui.STATUS["good"], size=14, symbol="star"),
    ))
    fig.update_layout(
        xaxis_title="Suhu Digester (°C)", yaxis_title="Konsentrasi NaOH (g/L)"
    )
    st.plotly_chart(ui.base_layout(fig, height=430), width="stretch")

    st.divider()
    st.subheader("What-if: geser setpoint & komposisi, lihat prediksi")
    
    with st.expander("🔬 Input Komposisi Bauksit (Bauxite Quality)"):
        st.caption("Ubah kadar bijih untuk melihat simulasi dampak terhadap parameter operasi.")
        c_comp = st.columns(4)
        what_if_comp = comp.copy()
        what_if_comp["al2o3_pct"] = c_comp[0].number_input("Al₂O₃ (%)", min_value=20.0, max_value=80.0, value=float(comp["al2o3_pct"]), step=0.5)
        what_if_comp["reactive_sio2_pct"] = c_comp[1].number_input("Silika Reaktif (%)", min_value=0.0, max_value=20.0, value=float(comp["reactive_sio2_pct"]), step=0.1)
        what_if_comp["fe2o3_pct"] = c_comp[2].number_input("Fe₂O₃ (%)", min_value=0.0, max_value=40.0, value=float(comp["fe2o3_pct"]), step=0.5)
        what_if_comp["tio2_pct"] = c_comp[3].number_input("TiO₂ (%)", min_value=0.0, max_value=10.0, value=float(comp["tio2_pct"]), step=0.1)

    cols = st.columns(5)
    what_if = {}
    for col, k in zip(cols, schema.KNOBS):
        lo, hi = schema.SAFE_BOUNDS[k]
        what_if[k] = col.slider(
            schema.label(k), float(lo), float(hi), float(knobs_now[k]),
            key=f"whatif_{k}",
        )
    p_now = ctx["predicted_now"]
    p_new = predict.predict_one(what_if_comp, what_if)
    m = st.columns(4)
    m[0].metric("Recovery", f"{p_new['recovery_pct']:.1f}%",
                f"{p_new['recovery_pct'] - p_now['recovery_pct']:+.1f}%")
    m[1].metric("OPEX/jam", f"{p_new['total_opex']:,.0f}",
                f"{p_new['total_opex'] - p_now['total_opex']:+,.0f}",
                delta_color="inverse")
    m[2].metric("Red Mud", f"{p_new['red_mud_t']:.1f} t",
                f"{p_new['red_mud_t'] - p_now['red_mud_t']:+.1f} t",
                delta_color="inverse")
    m[3].metric("Yield Presipitasi", f"{p_new.get('precip_yield_pct', 0):.1f}%",
                f"{p_new.get('precip_yield_pct', 0) - p_now.get('precip_yield_pct', 0):+.1f}%")

