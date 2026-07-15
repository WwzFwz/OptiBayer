"""Tab 2 — Digesti & Pra-desilikasi: operating map + what-if."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src import schema
from src.models import predict
from src.optimize import pareto


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

    # ---- radar: setpoint sekarang vs rekomendasi (semua 5 knob sekali pandang)
    with st.expander(":material/radar: Radar setpoint — apa yang perlu diubah & seberapa jauh"):
        st.caption(
            "Tiap sumbu = satu parameter, dinormalkan 0–1 pada rentang amannya. "
            "Selisih bentuk biru vs hijau = perubahan yang diminta advisory."
        )

        def _norm(k: str, v: float) -> float:
            lo, hi = schema.SAFE_BOUNDS[k]
            return (v - lo) / max(hi - lo, 1e-9)

        axes = [schema.label(k) for k in schema.KNOBS]
        cur = [_norm(k, knobs_now[k]) for k in schema.KNOBS]
        rec = [_norm(k, reco[k]) for k in schema.KNOBS]
        rfig = go.Figure()
        rfig.add_trace(go.Scatterpolar(
            r=cur + cur[:1], theta=axes + axes[:1], name="Saat ini",
            fill="toself", line=dict(color=ui.SERIES[0], width=2),
            fillcolor="rgba(57,135,229,0.15)",
        ))
        rfig.add_trace(go.Scatterpolar(
            r=rec + rec[:1], theta=axes + axes[:1], name="Rekomendasi",
            fill="toself", line=dict(color=ui.STATUS["good"], width=2, dash="dash"),
            fillcolor="rgba(12,163,12,0.12)",
        ))
        rfig.update_layout(
            polar=dict(
                bgcolor=ui.SURFACE,
                radialaxis=dict(range=[0, 1], showticklabels=False,
                                gridcolor=ui.GRID),
                angularaxis=dict(gridcolor=ui.GRID,
                                 tickfont=dict(color=ui.INK2, size=11)),
            ),
        )
        st.plotly_chart(ui.base_layout(rfig, height=340), width="stretch",
                        key="dig_radar")

    # ---- Pareto explorer: scatter trade-off + parallel coordinates
    with st.expander(":material/multiline_chart: Kurva Pareto — eksplorasi trade-off (carbon-aware)"):
        st.caption(
            "Tiap garis/titik = satu setpoint optimal versi NSGA-II; tidak ada "
            "yang unggul di semua objektif. Net OPEX sudah dikurangi nilai CO₂ "
            "karbonasi red mud. Parallel coordinates: SERET pada sumbu untuk "
            "memfilter solusi (mis. hanya recovery > 88%)."
        )
        if st.button("Hitung Pareto untuk feed saat ini", key="dig_pareto_btn"):
            with st.spinner("Menjalankan NSGA-II..."):
                st.session_state["_dig_pareto"] = pareto.pareto(comp)
        pf = st.session_state.get("_dig_pareto")
        if pf is not None:
            best = pareto.pick(pf)
            v_scatter, v_par = st.tabs(["Scatter trade-off", "Parallel coordinates"])
            with v_scatter:
                figp = go.Figure()
                figp.add_trace(go.Scatter(
                    x=pf["net_opex"], y=pf["recovery_pct"], mode="markers",
                    name="Solusi Pareto",
                    marker=dict(size=9, color=pf["red_mud_t"],
                                colorscale=ui.SEQ_BLUE,
                                colorbar=dict(title="Red mud (t)",
                                              tickfont=dict(color=ui.INK2))),
                    customdata=pf[["digester_temp_c", "naoh_conc_gl"]].values,
                    hovertemplate=("net OPEX %{x:,.0f} · recovery %{y:.1f}%<br>"
                                   "T %{customdata[0]:.1f}°C · NaOH "
                                   "%{customdata[1]:.0f} g/L<extra></extra>"),
                ))
                figp.add_trace(go.Scatter(
                    x=[best["net_opex"]], y=[best["recovery_pct"]],
                    mode="markers+text", text=["PILIHAN"],
                    textposition="top center",
                    textfont=dict(color=ui.STATUS["good"]), name="Bobot seimbang",
                    marker=dict(symbol="star", size=17, color=ui.STATUS["good"]),
                ))
                figp.update_layout(
                    xaxis_title="Net OPEX (/jam, setelah kredit CO₂)",
                    yaxis_title="Recovery Al (%)",
                )
                st.plotly_chart(ui.base_layout(figp, height=380),
                                width="stretch", key="dig_pareto_scatter")
            with v_par:
                dims = [
                    dict(label=schema.label(k), values=pf[k])
                    for k in schema.KNOBS
                ] + [
                    dict(label="Recovery (%)", values=pf["recovery_pct"]),
                    dict(label="Net OPEX", values=pf["net_opex"]),
                    dict(label="Red Mud (t)", values=pf["red_mud_t"]),
                ]
                pcfig = go.Figure(go.Parcoords(
                    line=dict(color=pf["recovery_pct"], colorscale=ui.SEQ_BLUE,
                              showscale=True,
                              colorbar=dict(title="Recovery %",
                                            tickfont=dict(color=ui.INK2))),
                    dimensions=dims,
                    labelfont=dict(color=ui.INK2, size=11),
                    tickfont=dict(color=ui.MUTED, size=9),
                ))
                pcfig.update_layout(
                    paper_bgcolor=ui.SURFACE, height=380,
                    margin=dict(l=60, r=60, t=50, b=30),
                    font=dict(color=ui.INK2),
                )
                st.plotly_chart(pcfig, width="stretch", key="dig_pareto_par")

    st.divider()
    st.subheader("What-if: geser setpoint, lihat prediksi")
    cols = st.columns(5)
    what_if = {}
    for col, k in zip(cols, schema.KNOBS):
        lo, hi = schema.SAFE_BOUNDS[k]
        what_if[k] = col.slider(
            schema.label(k), float(lo), float(hi), float(knobs_now[k]),
            key=f"whatif_{k}",
        )
    p_now = ctx["predicted_now"]
    p_new = predict.predict_one(comp, what_if)
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
