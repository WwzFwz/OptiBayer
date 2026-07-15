"""Tab Overview (doc 10 §3) — pusat analisis tren & neraca material.

render(df, seq, hour):
    df   : seluruh histori bersih (995 baris) — dasar analisis korelasi
           komposisi/parameter vs target (statistik lebih kuat drpd hanya
           jendela replay).
    seq  : urutan replay yang sedang diputar dashboard (lihat src/data/replay.py)
    hour : jam simulasi yang sedang aktif (indeks di `seq`)

Tiga sub-tab:
1. "Tren Historis"      — time-series recovery/OPEX/red mud/silika + pita alarm
                           + jam sekarang bertanda + log kejadian.
2. "Korelasi & Scatter"  — heatmap korelasi FEATURES x TARGETS (fitur #1: input
                           vs target) + scatter interaktif + grid kecil semua fitur.
3. "Neraca Material"     — Sankey Al & Na (material masuk vs keluar, fitur #1)
                           + regret meter & laporan serah-terima (doc 10/13).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app import ui
from src import capability, schema
from src.models import predict as mpredict
from src.advisory import providers
from src.optimize import regret
from src.physics import na_balance

BANDS = {
    "recovery_pct": (85.0, 100.0),
    "total_opex": (0.0, 2500.0),
    "red_mud_t": (0.0, 75.0),
    "reactive_sio2_pct": (0.0, 5.5),
}
TREND_TITLES = {
    "recovery_pct": "Recovery Al (%)",
    "total_opex": "Total OPEX (/jam)",
    "red_mud_t": "Red Mud Basah (ton)",
    "reactive_sio2_pct": "Silika Reaktif Masuk (%)",
}

def _diverging() -> list:
    """Skala diverging merah↔biru; titik tengah netral ikut mode tema."""
    return [
        [0.0, "#d03b3b"], [0.25, "#c98c7a"], [0.5, ui.DIV_MID],
        [0.75, "#5a9fd6"], [1.0, ui.SERIES[0]],
    ]


# --------------------------------------------------------------------------
# 1) Tren historis
# --------------------------------------------------------------------------
def _events(seq: pd.DataFrame) -> list[dict]:
    ev = []
    for h in range(len(seq)):
        r = seq.iloc[h]
        if r["reactive_sio2_pct"] > BANDS["reactive_sio2_pct"][1] + 0.8:
            ev.append({"jam": h, "level": "critical",
                       "pesan": f"Silika reaktif {r['reactive_sio2_pct']:.1f}% — jauh di atas ambang"})
        elif r["reactive_sio2_pct"] > BANDS["reactive_sio2_pct"][1]:
            ev.append({"jam": h, "level": "warning",
                       "pesan": f"Silika reaktif {r['reactive_sio2_pct']:.1f}% — di atas ambang"})
        if r["recovery_pct"] < BANDS["recovery_pct"][0] - 3:
            ev.append({"jam": h, "level": "critical",
                       "pesan": f"Recovery jatuh ke {r['recovery_pct']:.1f}%"})
        if r["red_mud_t"] > BANDS["red_mud_t"][1] + 10:
            ev.append({"jam": h, "level": "warning",
                       "pesan": f"Red mud naik ke {r['red_mud_t']:.1f} t"})
    return ev


def _trend_section(seq: pd.DataFrame, hour: int) -> None:
    st.caption(
        "Tren " + str(len(seq)) + " jam simulasi terakhir — garis putus-putus "
        "menandai jam yang sedang aktif. Pita transparan = zona operasi aman."
    )
    cols = ["recovery_pct", "total_opex", "red_mud_t", "reactive_sio2_pct"]
    grid = st.columns(2)

    # overlay khusus recovery: garis prediksi model + penanda anomali residual
    pred_rec, resid_std = None, 0.0
    try:
        pred_rec = mpredict.predict_frame(seq[list(schema.FEATURES)])["recovery_pct"]
        resid_std = float(
            mpredict.meta("recovery_pct")["metrics"]["cv_resid_std"]
        )
    except FileNotFoundError:
        pass

    for i, col in enumerate(cols):
        fig = ui.trend(
            seq.index, seq[col], TREND_TITLES[col],
            band=BANDS[col], color=ui.SERIES[i % len(ui.SERIES)],
            height=230, title=TREND_TITLES[col],
        )
        if col == "recovery_pct" and pred_rec is not None:
            fig.add_trace(go.Scatter(
                x=list(seq.index), y=list(pred_rec), name="Prediksi model",
                mode="lines", line=dict(color=ui.INK2, width=1.5, dash="dot"),
                hovertemplate="%{y:.2f}<extra>prediksi</extra>",
            ))
            if resid_std > 0:
                resid = (seq[col] - pred_rec).abs()
                anom = seq.index[resid > 3 * resid_std]
                if len(anom):
                    fig.add_trace(go.Scatter(
                        x=list(anom), y=list(seq.loc[anom, col]),
                        name="Anomali", mode="markers",
                        marker=dict(color=ui.STATUS["critical"], size=9,
                                    symbol="diamond-open"),
                        hovertemplate="anomali: %{y:.2f}<extra></extra>",
                    ))
        fig.add_vline(x=hour, line=dict(color=ui.INK, width=1.5, dash="dash"))
        fig.add_trace(go.Scatter(
            x=[hour], y=[seq[col].iloc[hour]], mode="markers",
            marker=dict(color=ui.INK, size=9, symbol="diamond"),
            showlegend=False, hovertemplate="jam sekarang: %{y:.2f}<extra></extra>",
        ))
        grid[i % 2].plotly_chart(fig, width="stretch", key=f"trend_{col}")

    events = _events(seq)
    with st.expander(f"Log kejadian ({len(events)} tercatat)", expanded=False):
        if not events:
            st.caption("Tidak ada kejadian di luar ambang pada jendela ini.")
        else:
            ev_df = pd.DataFrame(events).sort_values("jam", ascending=False)
            st.dataframe(
                ev_df.rename(columns={"jam": "Jam", "level": "Level", "pesan": "Kejadian"}),
                width="stretch", hide_index=True, height=min(280, 40 + 35 * len(ev_df)),
            )


# --------------------------------------------------------------------------
# 2) Korelasi & scatter — input (komposisi+parameter) vs target
# --------------------------------------------------------------------------
def _correlation_heatmap(df: pd.DataFrame, target: str) -> go.Figure:
    corr = {f: float(np.corrcoef(df[f], df[target])[0, 1]) for f in schema.FEATURES}
    order = sorted(corr, key=lambda f: abs(corr[f]), reverse=True)
    vals = [corr[f] for f in order]
    labels = [schema.label(f) for f in order]

    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h",
        marker=dict(
            color=vals, colorscale=_diverging(), cmin=-1, cmax=1,
            line=dict(width=0),
        ),
        hovertemplate="%{y}: r=%{x:.3f}<extra></extra>",
    ))
    fig.add_vline(x=0, line=dict(color=ui.GRID, width=1))
    fig = ui.base_layout(fig, height=430,
                          title=f"Korelasi fitur vs {schema.label(target)}")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(range=[-1, 1], title="koefisien korelasi (r)")
    return fig


def _scatter_grid(df: pd.DataFrame, target: str) -> go.Figure:
    feats = schema.FEATURES
    n_cols = 3
    n_rows = int(np.ceil(len(feats) / n_cols))
    fig = make_subplots(
        rows=n_rows, cols=n_cols,
        subplot_titles=[schema.label(f) for f in feats],
        horizontal_spacing=0.06, vertical_spacing=0.09,
    )
    x_t = df[target].to_numpy(dtype=float)
    for i, feat in enumerate(feats):
        r, c = divmod(i, n_cols)
        x = df[feat].to_numpy(dtype=float)
        fig.add_trace(
            go.Scatter(
                x=x, y=x_t, mode="markers",
                marker=dict(size=4, color=ui.SERIES[0], opacity=0.45),
                hovertemplate=f"{schema.label(feat)}: %{{x:.2f}}<br>"
                              f"{schema.label(target)}: %{{y:.2f}}<extra></extra>",
                showlegend=False,
            ),
            row=r + 1, col=c + 1,
        )
        if np.std(x) > 1e-9:
            z = np.polyfit(x, x_t, 1)
            xs = np.linspace(x.min(), x.max(), 20)
            fig.add_trace(
                go.Scatter(x=xs, y=np.polyval(z, xs), mode="lines",
                           line=dict(color=ui.STATUS["warning"], width=1.5),
                           showlegend=False, hoverinfo="skip"),
                row=r + 1, col=c + 1,
            )
    fig = ui.base_layout(fig, height=235 * n_rows,
                          title=f"Semua fitur vs {schema.label(target)}")
    fig.update_annotations(font=dict(color=ui.INK2, size=11))
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    return fig


def _correlation_section(df: pd.DataFrame) -> None:
    st.caption(
        "Analisis historis penuh (" + str(len(df)) + " baris) — bagaimana "
        "komposisi bauksit & parameter proses berhubungan dengan target."
    )
    target = st.selectbox(
        "Target", schema.TARGETS, format_func=schema.label, key="ov_corr_target",
    )
    c1, c2 = st.columns([1, 1])
    with c1:
        st.plotly_chart(_correlation_heatmap(df, target), width="stretch",
                         key="ov_corr_bar")
    with c2:
        feat = st.selectbox(
            "Bandingkan satu fitur", schema.FEATURES, format_func=schema.label,
            index=schema.FEATURES.index("reactive_sio2_pct"), key="ov_scatter_feat",
        )
        xv = df[feat].to_numpy(dtype=float)
        yv = df[target].to_numpy(dtype=float)
        fig = go.Figure(go.Scatter(
            x=xv, y=yv, mode="markers",
            marker=dict(color=ui.SERIES[0], size=5, opacity=0.5),
            hovertemplate=f"{schema.label(feat)}: %{{x:.2f}}<br>"
                          f"{schema.label(target)}: %{{y:.2f}}<extra></extra>",
            showlegend=False,
        ))
        if np.std(xv) > 1e-9:
            z = np.polyfit(xv, yv, 1)
            xs = np.linspace(xv.min(), xv.max(), 30)
            r = float(np.corrcoef(xv, yv)[0, 1])
            fig.add_trace(go.Scatter(
                x=xs, y=np.polyval(z, xs), mode="lines",
                line=dict(color=ui.STATUS["warning"], width=2),
                name=f"tren (r={r:.2f})", hoverinfo="skip",
            ))
        st.plotly_chart(ui.base_layout(fig, height=380,
                                        title=f"{schema.label(feat)} vs {schema.label(target)}"),
                         width="stretch", key="ov_scatter_single")

    with st.expander("Lihat scatter SEMUA fitur sekaligus (grid kecil)"):
        st.plotly_chart(_scatter_grid(df, target), width="stretch", key="ov_scatter_grid")


# --------------------------------------------------------------------------
# 3) Neraca material masuk-keluar (Sankey) + regret/handover
# --------------------------------------------------------------------------
def _sankey_al(row: pd.Series) -> go.Figure:
    feed = max(float(row["al_feed_t"]), 0.0)
    recyc = max(float(row["al_recycled_t"]), 0.0)
    prod = max(float(row["hydrate_t"]), 0.0)
    lost = max(float(row["al_lost_redmud_t"]), 0.0)
    sisa = max(feed + recyc - prod - lost, 0.0)

    labels = ["Bauxite Segar (Al)", "Recycle Spent Liquor (Al)",
              "Digesti + Presipitasi", "Produk Al(OH)₃", "Red Mud (hilang)",
              "Kembali ke Liquor"]
    idx = dict(bauxite=0, recycle=1, proc=2, prod=3, lost=4, back=5)
    colors = [ui.SERIES[0], ui.SERIES[4], ui.MUTED, ui.STATUS["good"],
              ui.STATUS["critical"], ui.SERIES[1]]
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=18, thickness=16,
                  line=dict(color=ui.GRID, width=0.5)),
        link=dict(
            source=[idx["bauxite"], idx["recycle"], idx["proc"], idx["proc"], idx["proc"]],
            target=[idx["proc"], idx["proc"], idx["prod"], idx["lost"], idx["back"]],
            value=[feed, recyc, prod, lost, sisa],
            color=["rgba(57,135,229,0.35)", "rgba(144,133,233,0.35)",
                   "rgba(12,163,12,0.35)", "rgba(208,59,59,0.35)",
                   "rgba(137,135,129,0.30)"],
        ),
    ))
    return ui.base_layout(fig, height=340, title="Neraca Aluminium (ton/jam)")


def _sankey_na(row: pd.Series) -> go.Figure:
    nb = na_balance.breakdown(row)
    makeup, recycled = nb["makeup_t"], nb["recycled_t"]
    dsp, dead, phys = nb["dsp_loss_t"], nb["dead_soda_net_t"], nb["physical_loss_t"]
    back = max(nb["consumed_t"] - dsp - dead - phys, 0.0)

    labels = ["NaOH Make-up (segar)", "NaOH Recycle (liquor)", "Total NaOH Terpakai",
              "Terkunci di DSP (silika)", "Soda Mati (karbonasi net)",
              "Hilang Fisik (RM, dll)", "Kembali ke Liquor"]
    idx = dict(makeup=0, recyc=1, used=2, dsp=3, dead=4, phys=5, back=6)
    colors = [ui.SERIES[0], ui.SERIES[4], ui.MUTED, ui.STATUS["warning"],
              ui.STATUS["serious"], ui.STATUS["critical"], ui.STATUS["good"]]
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=labels, color=colors, pad=18, thickness=16,
                  line=dict(color=ui.GRID, width=0.5)),
        link=dict(
            source=[idx["makeup"], idx["recyc"], idx["used"], idx["used"], idx["used"], idx["used"]],
            target=[idx["used"], idx["used"], idx["dsp"], idx["dead"], idx["phys"], idx["back"]],
            value=[makeup, recycled, dsp, dead, phys, back],
            color=["rgba(57,135,229,0.35)", "rgba(144,133,233,0.35)",
                   "rgba(250,178,25,0.35)", "rgba(236,131,90,0.35)",
                   "rgba(208,59,59,0.35)", "rgba(12,163,12,0.30)"],
        ),
    ))
    return ui.base_layout(fig, height=340, title="Neraca NaOH (ton/jam)")


def _regret_handover_section(df: pd.DataFrame, seq: pd.DataFrame, hour: int) -> None:
    st.caption(
        "Berapa banyak recovery/OPEX yang 'tertinggal di meja' bila parameter "
        "8 jam terakhir mengikuti rekomendasi optimizer, plus draf laporan "
        "serah-terima shift."
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hitung regret 8 jam terakhir", width="stretch"):
            lo = max(0, hour - 7)
            window = seq.iloc[lo:hour + 1]
            with st.spinner("Menjalankan optimizer pada 8 jam terakhir..."):
                rg = regret.shift_regret(window)
                series = regret.shift_series(window)
            st.session_state["_ov_regret"] = rg
            st.session_state["_ov_regret_series"] = series
        rg = st.session_state.get("_ov_regret")
        if rg:
            a, cf = rg["actual"], rg["counterfactual"]
            st.metric("Recovery aktual vs optimal",
                      f"{a['recovery_pct']:.1f}%", f"{cf['recovery_pct']-a['recovery_pct']:+.1f} pt vs optimal")
            st.metric("OPEX aktual vs optimal (kumulatif)",
                      f"{a['total_opex']:,.0f}", f"{cf['total_opex']-a['total_opex']:+,.0f} vs optimal",
                      delta_color="inverse")
            st.metric("Red mud aktual vs optimal (kumulatif)",
                      f"{a['red_mud_t']:,.1f} t", f"{cf['red_mud_t']-a['red_mud_t']:+,.1f} t vs optimal",
                      delta_color="inverse")
            series = st.session_state.get("_ov_regret_series")
            if series is not None and len(series):
                fig_cf = go.Figure()
                fig_cf.add_trace(go.Scatter(
                    x=series["sim_hour"], y=series["actual"], name="Aktual",
                    mode="lines", line=dict(color=ui.SERIES[0], width=2),
                    hovertemplate="%{y:.2f}%<extra>aktual</extra>",
                ))
                fig_cf.add_trace(go.Scatter(
                    x=series["sim_hour"], y=series["counterfactual"],
                    name="Jika advisory diikuti", mode="lines",
                    line=dict(color=ui.STATUS["good"], width=2, dash="dash"),
                    fill="tonexty", fillcolor="rgba(12,163,12,0.15)",
                    hovertemplate="%{y:.2f}%<extra>counterfactual</extra>",
                ))
                ui.base_layout(
                    fig_cf, height=230,
                    title="Recovery: aktual vs counterfactual (area = regret)",
                )
                st.plotly_chart(fig_cf, width="stretch", key="ov_regret_chart")
            ui.explain_chart("regret", "Regret Meter (counterfactual 8 jam)", {
                "aktual": rg["actual"],
                "seandainya_advisory_diikuti": rg["counterfactual"],
                "selisih": rg["delta"],
                "jumlah_jam": rg["n_rows"],
            })

    with c2:
        if st.button("Buat draf laporan serah-terima shift", width="stretch"):
            lo = max(0, hour - 7)
            window = seq.iloc[lo:hour + 1]
            stats = {
                "hour_start": int(lo), "hour_end": int(hour),
                "recovery_mean": float(window["recovery_pct"].mean()),
                "opex_sum": float(window["total_opex"].sum()),
                "red_mud_sum": float(window["red_mud_t"].sum()),
                "co2_t": float(window["red_mud_t"].sum() * 0.023),
                "silika_last": float(window["reactive_sio2_pct"].iloc[-1]),
                "silika_trend": "naik" if window["reactive_sio2_pct"].iloc[-1] > window["reactive_sio2_pct"].iloc[0] else "turun/stabil",
                "n_advisories": len(st.session_state.get("advisory_log", [])),
                "n_critical": sum(1 for e in _events(window) if e["level"] == "critical"),
            }
            text, backend = providers.handover_report(stats)
            st.session_state["_ov_handover"] = (text, backend)
        ho = st.session_state.get("_ov_handover")
        if ho:
            text, backend = ho
            st.text_area("Laporan (siap salin)", text, height=220, key="ov_handover_text")
            st.caption(f"dibuat via backend: {backend}")


def _material_flow_section(df: pd.DataFrame, row: pd.Series) -> None:
    caps = capability.detect(df)
    c1, c2 = st.columns(2)
    with c1:
        if caps.get("sankey_al"):
            st.plotly_chart(_sankey_al(row), width="stretch", key="ov_sankey_al")
        else:
            ui.empty_state("Sankey Aluminium", "kolom neraca aluminium tidak tersedia")
    with c2:
        if caps.get("sankey_na"):
            st.plotly_chart(_sankey_na(row), width="stretch", key="ov_sankey_na")
        else:
            ui.empty_state("Sankey NaOH", "kolom neraca natrium tidak tersedia")
    st.divider()
    _regret_handover_section(df, st.session_state.get("_seq_ref", df), int(row.name) if row.name is not None else 0)
    st.divider()
    _audit_trail_section()


def _audit_trail_section() -> None:
    """Audit trail keputusan advisory: log sesi + file persisten (lintas restart)."""
    from pathlib import Path

    st.subheader("Audit Trail Keputusan Advisory")
    log_path = (Path(__file__).resolve().parents[2]
                / "data" / "processed" / "advisory_log.csv")
    shown = False
    if log_path.exists():
        try:
            log_df = pd.read_csv(log_path).tail(50).iloc[::-1]
            st.dataframe(log_df.rename(columns={
                "waktu": "Waktu", "jam_sim": "Jam Sim",
                "judul": "Advisory", "keputusan": "Keputusan",
            }), width="stretch", hide_index=True,
                height=min(280, 40 + 35 * len(log_df)))
            st.caption(
                f"Persisten (lintas restart): `{log_path.name}` — "
                f"{len(pd.read_csv(log_path))} keputusan tercatat total."
            )
            shown = True
        except Exception:
            pass
    if not shown:
        sess = st.session_state.get("advisory_log", [])
        if sess:
            st.dataframe(pd.DataFrame(sess), width="stretch", hide_index=True)
        else:
            st.caption(
                "Belum ada keputusan advisory. Klik Terima/Tolak pada kartu "
                "advisory — setiap keputusan tercatat di sini + file CSV persisten."
            )


# --------------------------------------------------------------------------
def render(df: pd.DataFrame, seq: pd.DataFrame, hour: int) -> None:
    st.session_state["_seq_ref"] = seq  # dipakai _material_flow_section
    row = seq.iloc[hour]

    t1, t2, t3 = st.tabs([
        ":material/show_chart: Tren Historis", ":material/scatter_plot: Korelasi & Scatter",
        ":material/balance: Neraca Material",
    ])
    with t1:
        _trend_section(seq, hour)
    with t2:
        _correlation_section(df)
    with t3:
        _material_flow_section(df, row)
