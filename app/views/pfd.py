"""Tab — Diagram Proses (HMI panel): sirkuit Bayer gaya SCADA dengan nilai live.

Gambaran besar 6 line (input tim proses):
1. feed + recycled spent liquor + NaOH + CaO -> pre-desilication
2. pre-desilication -> digestion
3. digestion -> filtration -> overflow Bayer liquor / underflow red mud
4. overflow -> precipitation -> Al(OH)3 + remaining spent liquor
5. spent liquor -> conditioning -> recycle ke sirkuit
6. underflow -> red mud washing (+air) -> tailing; recovered liquor -> conditioning

Gaya HMI: pipa ortogonal tebal (warna per jenis aliran), kotak readout digital
per stream, lampu status per stasiun. Nilai dari baris replay saat ini
Satuan: ton/jam (skala pabrik, dry feed dari data).
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import ui
from src.advisory import knowledge

_UNIT_W, _UNIT_H = 1.9, 0.9
_TERM_W, _TERM_H = 1.5, 0.6


def _pipe_color(kind: str) -> str:
    """Warna pipa per jenis aliran — dibaca saat render agar ikut mode tema."""
    return {
        "liquor": ui.SERIES[0],       # Bayer liquor / kaustik
        "slurry": "#b08968",          # slurry bauksit
        "redmud": ui.STATUS["serious"],
        "product": ui.STATUS["good"],
        "water": ui.SERIES[1],
        "recycle": ui.SERIES[1],
    }[kind]


def _lamp(fig, x, y, status: str):
    fig.add_trace(go.Scatter(
        x=[x], y=[y], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(size=11, color=ui.STATUS[status],
                    line=dict(color="#000000", width=1)),
    ))


def _unit(fig, x, y, label, *, status="good", hover=""):
    """Vessel/tank stasiun: kotak ber-bingkai status + lampu indikator."""
    fig.add_shape(
        type="rect", x0=x - _UNIT_W / 2, x1=x + _UNIT_W / 2,
        y0=y - _UNIT_H / 2, y1=y + _UNIT_H / 2,
        line=dict(color=ui.STATUS[status], width=2.5),
        fillcolor=ui.UNIT_FILL, layer="below",
    )
    # "level" dekoratif ala tangki
    fig.add_shape(
        type="rect", x0=x - _UNIT_W / 2 + 0.08, x1=x + _UNIT_W / 2 - 0.08,
        y0=y - _UNIT_H / 2 + 0.08, y1=y - _UNIT_H / 2 + 0.3,
        line_width=0, fillcolor="rgba(57,135,229,0.25)", layer="below",
    )
    fig.add_annotation(x=x, y=y + 0.08, text=f"<b>{label}</b>", showarrow=False,
                       font=dict(color=ui.INK, size=12))
    _lamp(fig, x + _UNIT_W / 2 - 0.16, y + _UNIT_H / 2 - 0.16, status)
    if hover:
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers",
            marker=dict(size=46, color="rgba(0,0,0,0)"),
            hovertemplate=hover + "<extra></extra>", showlegend=False,
        ))


def _terminal(fig, x, y, label, *, hover=""):
    fig.add_shape(
        type="rect", x0=x - _TERM_W / 2, x1=x + _TERM_W / 2,
        y0=y - _TERM_H / 2, y1=y + _TERM_H / 2,
        line=dict(color=ui.MUTED, width=1), fillcolor=ui.SURFACE, layer="below",
    )
    fig.add_annotation(x=x, y=y, text=label, showarrow=False,
                       font=dict(color=ui.INK2, size=11))
    if hover:
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers",
            marker=dict(size=36, color="rgba(0,0,0,0)"),
            hovertemplate=hover + "<extra></extra>", showlegend=False,
        ))


def _pipe(fig, pts: list[tuple], kind: str | None = None, *,
          color: str | None = None, width: float = 5,
          dash: str | None = None):
    """Pipa ortogonal: polyline tebal + arrowhead di ujung.

    `color`/`width` override dipakai lapisan analitik (highlight vs redup).
    """
    color = color or _pipe_color(kind)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1,
                      line=dict(color=color, width=width, dash=dash),
                      layer="below")
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    fig.add_annotation(x=xb, y=yb, ax=xa, ay=ya, axref="x", ayref="y",
                       showarrow=True, arrowhead=2, arrowsize=0.9,
                       arrowwidth=max(width - 1, 2), arrowcolor=color, text="")


def _readout(fig, x, y, label, value, *, color=None):
    """Kotak readout digital ala HMI: label kecil + angka terang."""
    color = color or ui.VALUE_COLOR
    w, h = 1.45, 0.52
    fig.add_shape(type="rect", x0=x - w / 2, x1=x + w / 2,
                  y0=y - h / 2, y1=y + h / 2,
                  line=dict(color=ui.READ_BORDER, width=1),
                  fillcolor=ui.READ_BG)
    fig.add_annotation(x=x, y=y + h / 2 + 0.14, text=label, showarrow=False,
                       font=dict(color=ui.MUTED, size=9))
    fig.add_annotation(x=x, y=y, text=f"<b>{value}</b>", showarrow=False,
                       font=dict(color=color, size=12, family="Consolas, monospace"))


def _spark(col, series, title: str, color: str, fmt: str = "{:.1f}") -> None:
    """Sparkline mini (sub-chart konteks 12 jam) di atas diagram."""
    figs = go.Figure(go.Scatter(
        y=list(series), mode="lines",
        line=dict(color=color, width=2), hoverinfo="skip",
    ))
    figs.update_xaxes(visible=False)
    figs.update_yaxes(visible=False)
    figs.update_layout(
        paper_bgcolor=ui.SURFACE, plot_bgcolor=ui.SURFACE, height=72,
        margin=dict(l=6, r=6, t=22, b=4), showlegend=False,
        title=dict(text=f"{title} · {fmt.format(series.iloc[-1])}",
                   font=dict(size=11, color=ui.INK2)),
    )
    col.plotly_chart(figs, width="stretch", key=f"pfd_spark_{title}")


def render(row: pd.Series, ctx: dict, hist: pd.DataFrame | None = None):
    st.subheader("Diagram Proses — Sirkuit Bayer (HMI live)")

    # lapisan analitik: satu peta, tiga cerita (overlay analytics)
    layer = st.radio(
        "Lapisan analitik",
        ["Operasi", "Kebocoran NaOH", "Jalur Karbon (CCUS)"],
        horizontal=True, key="pfd_layer",
    )

    if hist is not None and len(hist) > 2:
        h12 = hist.tail(12)
        s1, s2, s3 = st.columns(3)
        _spark(s1, h12["recovery_pct"], "Recovery 12 jam (%)", ui.SERIES[0])
        _spark(s2, h12["reactive_sio2_pct"], "SiO₂ feed 12 jam (%)", ui.SERIES[4])
        _spark(s3, h12["red_mud_t"], "Red mud 12 jam (t)", ui.SERIES[1],
               fmt="{:.0f}")

    nb = ctx["na_balance"]
    sio2 = float(row["reactive_sio2_pct"])
    dig_eff = float(row["digestion_eff_pct"])
    yield_pct = float(row["precip_yield_pct"])

    feed_status = ("critical" if ctx["silika_level"] == "critical"
                   else "warning" if ctx["silika_level"] == "warning" else "good")
    dig_status = "good" if dig_eff >= 95 else "warning" if dig_eff >= 90 else "critical"
    prec_status = "good" if yield_pct >= 79 else "warning" if yield_pct >= 76 else "critical"
    cao_status = {"sesuai": "good", "over-dosing": "warning",
                  "under-dosing": "warning"}.get(ctx["cao_advisory"]["status"], "good")

    fig = go.Figure()

    # ================= PIPA (digambar dulu, di bawah node) =================
    # (tag, titik, jenis aliran, dash) — 6 line proses dari tim
    pipes = [
        ("feed",      [(1.75, 8.8), (3.3, 8.8), (3.3, 7.8)], "slurry", None),
        ("naoh",      [(1.75, 7.3), (2.35, 7.3)], "liquor", None),
        ("cao",       [(1.75, 5.9), (3.3, 5.9), (3.3, 6.8)], "water", None),
        ("recycle",   [(4.45, 4.3), (2.05, 4.3), (2.05, 7.3), (2.35, 7.3)],
         "recycle", "dash"),
        ("slurry2",   [(4.25, 7.3), (5.9, 7.3), (5.9, 8.35)], "slurry", None),
        ("dig2filt",  [(6.85, 8.8), (7.75, 8.8)], "liquor", None),
        ("overflow",  [(8.7, 8.35), (8.7, 5.95)], "liquor", None),
        ("underflow", [(9.65, 8.8), (11.5, 8.8), (11.5, 7.35)], "redmud", None),
        ("product",   [(8.7, 5.05), (8.7, 3.35)], "product", None),
        ("spent",     [(7.75, 5.5), (5.35, 5.5), (5.35, 4.75)], "liquor", None),
        ("water_in",  [(13.3, 8.8), (13.3, 6.9), (12.45, 6.9)], "water", None),
        ("tailing",   [(11.5, 6.45), (11.5, 5.0)], "redmud", None),
        ("recovered", [(10.55, 6.9), (10.0, 6.9), (10.0, 4.3), (6.3, 4.3)],
         "recycle", "dash"),
    ]
    # lapisan analitik: pipa yang relevan MENYALA (warna cerita), sisanya redup
    highlight = {
        "Kebocoran NaOH": {
            "naoh": ui.STATUS["info"],        # NaOH segar masuk
            "recycle": ui.STATUS["warning"],  # soda mati berputar via conditioning
            "underflow": ui.STATUS["critical"],  # Na terikut red mud
            "tailing": ui.STATUS["critical"],
            "recovered": ui.STATUS["good"],   # yang berhasil diselamatkan washing
        },
        "Jalur Karbon (CCUS)": {
            "underflow": ui.STATUS["good"],
            "tailing": ui.STATUS["good"],
        },
    }.get(layer)

    for tag, pts, kind, dash_ in pipes:
        if highlight is None:
            _pipe(fig, pts, kind, dash=dash_)
        else:
            hl = highlight.get(tag)
            _pipe(fig, pts, kind, color=hl or ui.GRID,
                  width=6.5 if hl else 3, dash=dash_)

    # ================= STASIUN & TERMINAL =================
    feed_dry = float(row.get("feed_rate_t", 100.0) or 100.0)
    _terminal(fig, 1.0, 8.8, "Washed<br>Bauxite",
              hover=f"Feed {feed_dry:,.0f} t/jam kering<br>"
                    f"Al₂O₃ {row['al2o3_pct']:.1f}% · SiO₂ reaktif {sio2:.1f}%")
    _terminal(fig, 1.0, 7.3, "NaOH",
              hover=f"Make-up {nb['makeup_t']:.2f} t")
    _terminal(fig, 1.0, 5.9, "CaO",
              hover=f"Dosis {row['cao_addition_t']:.2f} t "
                    f"({ctx['cao_advisory']['status']})")
    _terminal(fig, 13.3, 9.15, "Air Cuci",
              hover=f"{row['wash_water_ratio']:.1f} t / t red mud")
    _terminal(fig, 8.7, 3.0, "Produk Al(OH)₃",
              hover=f"{row['hydrate_t']:.1f} t hidrat · recovery "
                    f"{row['recovery_pct']:.1f}%")
    _terminal(fig, 11.5, 4.65, "Tailing → CCUS",
              hover=f"{row['red_mud_t']:.1f} t basah · Al terikut "
                    f"{row['al_lost_redmud_t']:.2f} t<br>potensi karbonasi "
                    f"{row['red_mud_t'] * 0.023:.2f} t CO₂")

    _unit(fig, 3.3, 7.3, "Pre-Desilication", status=feed_status,
          hover=f"SiO₂ reaktif {sio2:.1f}%<br>Ca/Si {row['ca_si_ratio']:.1f} · "
                f"eff {row['predesil_eff']:.0%}")
    _unit(fig, 5.9, 8.8, "Digestion", status=dig_status,
          hover=f"Efisiensi {dig_eff:.1f}%<br>T {row['digester_temp_c']:.1f} °C · "
                f"NaOH {row['naoh_conc_gl']:.0f} g/L · L/S {row['ls_ratio']:.0f}")
    _unit(fig, 8.7, 8.8, "Filtration", status="good",
          hover=f"Klarifikasi eff {row['clarif_eff']:.0%}<br>"
                "overflow: Bayer liquor · underflow: red mud")
    _unit(fig, 8.7, 5.5, "Precipitation", status=prec_status,
          hover=f"Yield {yield_pct:.1f}%<br>T {row['precip_temp_c']:.1f} °C · "
                f"seed {row['seed_ratio']:.2f}")
    _unit(fig, 5.35, 4.3, "Conditioning", status=cao_status,
          hover=f"Causticity {row['causticity']:.2f}<br>Soda mati net "
                f"{nb['dead_soda_net_t']:.2f} t · CaO advisory "
                f"{ctx['cao_advisory']['cao_recommended_t']:.2f} t")
    _unit(fig, 11.5, 6.9, "RM Washing", status="good",
          hover=f"Air {row['wash_water_ratio']:.1f} t/t · eff {row['wash_eff']:.0%}"
                f"<br>NaOH loss fisik {nb['physical_loss_t']:.2f} t")

    # ================= READOUT DIGITAL (per lapisan) =================
    if layer == "Kebocoran NaOH":
        mk = max(nb["makeup_t"], 1e-9)
        _readout(fig, 4.9, 6.55, "NaOH make-up",
                 f"{nb['makeup_t']:.1f} t", color=ui.STATUS["info"])
        _readout(fig, 7.35, 9.35, "Terkunci DSP (silika)",
                 f"{nb['dsp_loss_t']:.1f} t · {nb['dsp_loss_t'] / mk:.0%}",
                 color=ui.STATUS["warning"])
        _readout(fig, 3.2, 3.7, "Soda mati (net)",
                 f"{nb['dead_soda_net_t']:.1f} t · {nb['dead_soda_net_t'] / mk:.0%}",
                 color=ui.STATUS["serious"])
        _readout(fig, 12.65, 5.6, "Loss fisik (red mud)",
                 f"{nb['physical_loss_t']:.1f} t · {nb['physical_loss_t'] / mk:.0%}",
                 color=ui.STATUS["critical"])
        _readout(fig, 9.75, 7.15, "NaOH recycle",
                 f"{nb['recycled_t']:.0f} t", color=ui.STATUS["good"])
        legend_items = [("NaOH masuk", ui.STATUS["info"]),
                        ("Terkunci DSP", ui.STATUS["warning"]),
                        ("Soda mati", ui.STATUS["serious"]),
                        ("Hilang fisik", ui.STATUS["critical"]),
                        ("Terselamatkan", ui.STATUS["good"])]
    elif layer == "Jalur Karbon (CCUS)":
        cb = ctx["carbonation"]
        _readout(fig, 12.6, 8.35, "Red mud (feedstock)",
                 f"{row['red_mud_t']:.0f} t", color=ui.STATUS["good"])
        _readout(fig, 12.65, 5.6, "Potensi CO₂",
                 f"{cb['co2_sequestered_t']:.1f} t/jam", color=ui.STATUS["good"])
        _readout(fig, 9.85, 3.6, "Nilai karbon",
                 f"Rp{cb['carbon_value_idr']:,.0f}", color=ui.STATUS["good"])
        _readout(fig, 9.75, 7.15, "Air karbonasi (L/S 2:1)",
                 f"{cb['water_needed_t']:.0f} t", color=ui.SERIES[1])
        legend_items = [("Jalur karbonasi (paper 2026: 23 kg CO₂/t RM)",
                         ui.STATUS["good"])]
    else:
        sio2_color = (ui.STATUS[feed_status] if feed_status != "good"
                      else ui.VALUE_COLOR)
        _readout(fig, 2.5, 9.35, "SiO₂ reaktif", f"{sio2:.1f} %", color=sio2_color)
        _readout(fig, 4.9, 6.55, "NaOH make-up", f"{nb['makeup_t']:.2f} t")
        _readout(fig, 7.35, 9.35, "Digestion eff", f"{dig_eff:.1f} %",
                 color=ui.STATUS[dig_status] if dig_status != "good" else ui.VALUE_COLOR)
        _readout(fig, 9.75, 7.15, "Bayer liquor", "overflow", color=ui.SERIES[0])
        _readout(fig, 12.6, 8.35, "Underflow", "red mud", color=ui.STATUS["serious"])
        _readout(fig, 7.55, 4.65, "Precip yield", f"{yield_pct:.1f} %",
                 color=ui.STATUS[prec_status] if prec_status != "good" else ui.VALUE_COLOR)
        _readout(fig, 9.85, 3.6, "Al(OH)₃", f"{row['hydrate_t']:.0f} t",
                 color=ui.STATUS["good"])
        _readout(fig, 12.65, 5.6, "Red mud", f"{row['red_mud_t']:.1f} t",
                 color=ui.STATUS["serious"])
        _readout(fig, 3.2, 3.7, "Recycle liquor (Al)",
                 f"{row['al_recycled_t']:.1f} t", color=ui.SERIES[1])
        _readout(fig, 8.15, 3.95, "Recovered liquor",
                 f"{row['water_wash_t']:.0f} t", color=ui.SERIES[1])
        legend_items = [("Bayer liquor / kaustik", _pipe_color("liquor")),
                        ("Slurry bauksit", _pipe_color("slurry")),
                        ("Red mud", _pipe_color("redmud")),
                        ("Produk", _pipe_color("product")),
                        ("Air / recycle (putus-putus)", _pipe_color("water"))]

    for i, (name, lcolor) in enumerate(legend_items):
        x0 = 0.5 + i * 2.75
        fig.add_shape(type="line", x0=x0, y0=2.35, x1=x0 + 0.4, y1=2.35,
                      line=dict(color=lcolor, width=5))
        fig.add_annotation(x=x0 + 0.52, y=2.35, text=name, showarrow=False,
                           xanchor="left", font=dict(color=ui.MUTED, size=10))

    fig.update_xaxes(visible=False, range=[0, 14.2])
    fig.update_yaxes(visible=False, range=[2.0, 9.9])
    ui.base_layout(fig, height=620)
    fig.update_layout(hovermode="closest", margin=dict(l=6, r=6, t=6, b=6))
    st.plotly_chart(fig, width="stretch")

    _ex_ctx = {
        "lapisan_aktif": layer,
        "silika_reaktif_pct": sio2,
        "digestion_eff_pct": dig_eff,
        "precip_yield_pct": yield_pct,
        "recovery_pct": float(row["recovery_pct"]),
        "red_mud_t": float(row["red_mud_t"]),
        "kebocoran_naoh": {
            "makeup_t": nb["makeup_t"], "dsp_t": nb["dsp_loss_t"],
            "soda_mati_net_t": nb["dead_soda_net_t"],
            "fisik_t": nb["physical_loss_t"],
        },
        "karbonasi": {
            "co2_t_per_jam": ctx["carbonation"]["co2_sequestered_t"],
            "nilai_rp": ctx["carbonation"]["carbon_value_idr"],
        },
    }
    _layer_tags = {"Operasi": knowledge.CHART_TAGS["pfd_operasi"]["tags"], "Kebocoran NaOH": knowledge.CHART_TAGS["pfd_kebocoran"]["tags"], "Jalur Karbon (CCUS)": knowledge.CHART_TAGS["pfd_karbon"]["tags"]}
    ui.explain_chart("pfd", f"Diagram Proses (lapisan: {layer})", _ex_ctx, tags=_layer_tags.get(layer))

    # ================= gauge ala panel SCADA =================
    g1, g2, g3 = st.columns(3)

    def _gauge(col, title, value, unit, good_from, warn_from, vmax=100.0):
        gfig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            number=dict(suffix=unit, font=dict(size=26, color=ui.INK)),
            title=dict(text=title, font=dict(size=13, color=ui.INK2)),
            gauge=dict(
                axis=dict(range=[0, vmax], tickfont=dict(color=ui.MUTED, size=9)),
                bar=dict(color=ui.SERIES[0], thickness=0.35),
                bgcolor=ui.SURFACE,
                steps=[
                    dict(range=[0, warn_from], color="rgba(208,59,59,0.35)"),
                    dict(range=[warn_from, good_from], color="rgba(250,178,25,0.35)"),
                    dict(range=[good_from, vmax], color="rgba(12,163,12,0.30)"),
                ],
            ),
        ))
        gfig.update_layout(paper_bgcolor=ui.SURFACE, height=180,
                           margin=dict(l=25, r=25, t=40, b=10),
                           font=dict(color=ui.INK2))
        col.plotly_chart(gfig, width="stretch")

    _gauge(g1, "Efisiensi Digesti", dig_eff, " %", 95, 90)
    _gauge(g2, "Yield Presipitasi", yield_pct, " %", 79, 76)
    _gauge(g3, "Recovery Al", float(row["recovery_pct"]), " %", 85, 82)

    st.caption(
        "PFD gambaran besar (bukan P&ID detail) · satuan ton/jam (skala pabrik) · "
        "hover stasiun/terminal untuk detail · lampu = status stasiun. Roadmap: "
        "klik stasiun → lompat ke tab-nya; layout mengikuti P&ID pabrik asli "
        "saat integrasi tahap 2."
    )
