"""Tab baru — Prediction Lab: What-If Simulator + Prediction Analysis + Parameter
Simulation (fitur 2, 3, 4 permintaan hackathon).

Operator memasukkan komposisi bauksit (9 oksida, "Lain-lain" otomatis = sisa
ke 100%, sama seperti konvensi generator data — lihat VBA macro kalkulator)
dan 5 parameter proses, lalu:

- Prediksi REAL-TIME direview dua "mesin" berdampingan:
    1. Model ML (LightGBM surrogate) — "Machine Learning NYATA" dari data histori.
    2. Kalkulator neraca massa (`src/physics/mass_balance.py`) — port Python
       dari `data/calculator/Bayer_Process_Mass_Water_Balance.xlsm`, tervalidasi
       terhadap 995 baris data.csv (rerata error <0.11% pada tiap target).
  Kedua nilai ditampilkan bersisian sebagai cross-check ("digital twin").
- Peringatan bila komposisi/parameter yang dimasukkan di luar rentang data
  latih model (ekstrapolasi, doc 14 item C3).
- Simulasi What-If Parameter: kurva sensitivitas tiap parameter (yang lain
  ditahan pada nilai + komposisi SEKARANG) + ringkasan tornado chart.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app import ui
from src import schema
from src.models import predict, train
from src.physics import mass_balance

OXIDES_9 = [c for c in schema.INPUTS if c != "others_pct"]

# Basis data latih ML = data.csv v2: Dashboard!C6=1000 t/jam basah, C7=20%
# -> dry 800 t/jam. Target massa/OPEX model ML dilatih pada basis ini;
# what-if feed rate menskalakannya linear (identik dgn formula xlsm).
ML_TRAIN_WET_FEED = 1000.0
ML_TRAIN_MOISTURE = 0.2
ML_TRAIN_DRY_FEED = ML_TRAIN_WET_FEED * (1.0 - ML_TRAIN_MOISTURE)
SCALED_TARGETS = ("total_opex", "red_mud_t")  # target persen bebas skala


def _feed_inputs() -> tuple[float, float]:
    """What-if laju umpan & moisture bauksit (Dashboard!C6/C7 di xlsm)."""
    st.markdown("##### Laju Umpan Bauksit (what-if skala pabrik)")
    c = st.columns(3)
    wet = c[0].number_input(
        "Wet Feed Rate (t/jam)", min_value=100.0, max_value=5000.0,
        value=ML_TRAIN_WET_FEED, step=50.0, key="pl_wet_feed",
        help="Dashboard!C6 pada kalkulator xlsm — basis data latih: 1000 t/jam",
    )
    moist_pct = c[1].number_input(
        "Moisture bauksit (%)", min_value=0.0, max_value=40.0,
        value=ML_TRAIN_MOISTURE * 100.0, step=1.0, key="pl_moisture",
        help="Dashboard!C7 — basis data latih: 20%",
    )
    mf = moist_pct / 100.0
    dry = wet * (1.0 - mf)
    c[2].metric(
        "Dry Feed Rate", f"{dry:,.0f} t/jam",
        delta=f"{dry / ML_TRAIN_DRY_FEED:.2f}× basis latih",
        help="= wet × (1 − moisture). Seluruh neraca massa linear terhadap ini.",
    )
    return wet, mf


def _bounds_widened(feat: str, frac: float = 0.25, cap: float = 100.0) -> tuple[float, float]:
    """Rentang slider komposisi: rentang data latih dilebarkan (bauksit baru
    bisa saja di luar 995 sampel sintesis), tapi tetap fisis masuk akal."""
    try:
        lo, hi = predict.meta()["bounds"][feat]
    except Exception:
        lo, hi = 0.0, cap
    span = max(hi - lo, 1e-6)
    return max(0.0, lo - frac * span), min(cap, hi + frac * span)


def _init_state(df: pd.DataFrame) -> None:
    if st.session_state.get("_pl_init"):
        return
    for k in OXIDES_9:
        st.session_state.setdefault(f"pl_{k}", round(float(df[k].mean()), 3))
    for k in schema.KNOBS:
        st.session_state.setdefault(f"pl_{k}", round(float(df[k].mean()), 3))
    st.session_state["_pl_init"] = True


def _apply_row(row: pd.Series) -> None:
    for k in OXIDES_9:
        st.session_state[f"pl_{k}"] = round(float(row[k]), 3)
    for k in schema.KNOBS:
        st.session_state[f"pl_{k}"] = round(float(row[k]), 3)


def _composition_inputs(df: pd.DataFrame) -> tuple[dict[str, float], float]:
    st.markdown("##### Komposisi Bauksit Masuk")
    st.caption(
        "9 oksida di bawah bisa diatur bebas; **Lain-lain/LOI otomatis "
        "= sisa hingga 100%** — konvensi yang sama dipakai kalkulator Excel "
        "asli saat membangun data latih."
    )
    b1, b2, b3 = st.columns(3)
    if b1.button("Sampel acak dari histori", width="stretch"):
        _apply_row(df.sample(1).iloc[0])
    if b2.button("Reset ke rata-rata historis", width="stretch"):
        _apply_row(df[list(schema.INPUTS) + list(schema.KNOBS)].mean())
    show_grid = b3.toggle("Tampilkan grid 3×3", value=True)

    comp: dict[str, float] = {}
    if show_grid:
        cols = st.columns(3)
        for i, feat in enumerate(OXIDES_9):
            lo, hi = _bounds_widened(feat)
            comp[feat] = cols[i % 3].slider(
                schema.label(feat), float(lo), float(hi),
                key=f"pl_{feat}", step=0.01,
            )
    else:
        for feat in OXIDES_9:
            lo, hi = _bounds_widened(feat)
            comp[feat] = st.slider(
                schema.label(feat), float(lo), float(hi),
                key=f"pl_{feat}", step=0.01,
            )

    total9 = sum(comp.values())
    others = 100.0 - total9
    c1, c2 = st.columns([3, 1])
    with c2:
        if others < 0:
            st.metric("Lain-lain/LOI", f"{others:.2f}%", "melebihi 100%!")
        else:
            st.metric("Lain-lain/LOI (otomatis)", f"{others:.2f}%")
    with c1:
        frac_used = min(total9 / 100.0, 1.0)
        st.progress(frac_used, text=f"9 oksida = {total9:.2f}% dari 100%")
        if others < 0:
            st.error(
                "Total 9 oksida melebihi 100% — Lain-lain di-clip ke 0%. "
                "Turunkan salah satu slider di atas.", icon="⚠️"
            )
    comp["others_pct"] = max(others, 0.0)
    return comp, total9


def _knob_inputs(df: pd.DataFrame) -> dict[str, float]:
    st.markdown("##### Parameter Proses")
    cols = st.columns(5)
    knobs = {}
    for i, k in enumerate(schema.KNOBS):
        lo, hi = schema.SAFE_BOUNDS[k]
        knobs[k] = cols[i].slider(
            schema.label(k), float(lo), float(hi), key=f"pl_{k}",
        )
    return knobs


def _bounds_warning(comp: dict, knobs: dict) -> None:
    wb = predict.within_bounds(comp, knobs)
    out = [schema.label(f) for f, ok in wb.items() if not ok]
    if out:
        st.warning(
            "**Ekstrapolasi** — di luar rentang data latih model utk: "
            + ", ".join(out) + ". Prediksi ML pada titik ini kurang bisa "
            "dipercaya; kalkulator fisika di bawah tetap berlaku penuh "
            "(deterministik, bukan hasil belajar dari data).",
            icon=":material/explore:",
        )


def _prediction_comparison(comp: dict, knobs: dict,
                           wet_feed_t: float, moisture_frac: float) -> None:
    st.markdown("##### Prediksi Real-Time — ML vs Kalkulator Neraca Massa")
    _bounds_warning(comp, knobs)

    dry = wet_feed_t * (1.0 - moisture_frac)
    scale_ml = dry / ML_TRAIN_DRY_FEED
    ml = predict.predict_one(comp, knobs)
    for k in SCALED_TARGETS:
        if k in ml:
            ml[k] *= scale_ml
    phys = mass_balance.run_dict(
        comp, knobs, wet_feed_t=wet_feed_t, moisture_frac=moisture_frac
    )
    if abs(scale_ml - 1.0) > 1e-9:
        st.caption(
            f"OPEX & red mud diskalakan ke dry feed {dry:,.0f} t/jam "
            f"({scale_ml:.2f}× basis latih {ML_TRAIN_DRY_FEED:,.0f} t/jam) — "
            "neraca massa linear terhadap dry feed (formula xlsm); "
            "recovery & yield bebas skala."
        )

    rows = [
        ("recovery_pct", "Recovery Al", "{:.2f}%"),
        ("total_opex", "Total OPEX/jam", "{:,.0f}"),
        ("red_mud_t", "Red Mud Basah", "{:.2f} t"),
        ("precip_yield_pct", "Yield Presipitasi", "{:.2f}%"),
    ]
    c_ml, c_gap, c_phys = st.columns([5, 1, 5])
    c_ml.markdown("**Model ML (LightGBM surrogate)**")
    c_phys.markdown("**Kalkulator Excel (neraca massa)**")
    for key, label_, fmt in rows:
        mlv = ml.get(key)
        phv = phys.get(key)
        c_ml.metric(label_, fmt.format(mlv) if mlv is not None else "n/a")
        if mlv is not None and phv:
            gap_pct = (mlv - phv) / phv * 100.0 if phv else 0.0
            c_gap.markdown(
                f"<div style='text-align:center;padding-top:28px;color:{ui.MUTED};"
                f"font-size:0.75em'>Δ{gap_pct:+.1f}%</div>", unsafe_allow_html=True,
            )
        else:
            c_gap.markdown("")
        c_phys.metric(label_, fmt.format(phv) if phv is not None else "n/a")

    with st.expander("Rincian neraca massa (fisika/Excel) — semua besaran antara"):
        detail = {
            "Efisiensi Digesti (%)": phys["digestion_eff_pct"],
            "Causticity liquor aktual": phys["causticity"],
            "Al dari bauxite segar (t/jam)": phys["al_feed_t"],
            "Al dari recycle spent liquor (t/jam)": phys["al_recycled_t"],
            "Al hilang ke red mud (t/jam)": phys["al_lost_redmud_t"],
            "Al(OH)3 kering diproduksi (t/jam)": phys["hydrate_t"],
            "Make-up NaOH (t/jam)": phys["naoh_makeup_t"],
            "Total CaO terpakai (t/jam)": phys["cao_total_t"],
            "OPEX NaOH (/jam)": phys["naoh_opex"],
            "OPEX CaO (/jam)": phys["cao_opex"],
        }
        d1, d2 = st.columns(2)
        items = list(detail.items())
        for i, (k, v) in enumerate(items):
            (d1 if i % 2 == 0 else d2).metric(k, f"{v:,.3f}")


# --------------------------------------------------------------------------
# What-if parameter simulation — sensitivitas per parameter pada komposisi ini
# --------------------------------------------------------------------------
def _sweep_knob(comp: dict, knobs: dict, sweep_key: str, target: str, n: int = 21) -> pd.DataFrame:
    lo, hi = schema.SAFE_BOUNDS[sweep_key]
    xs = np.linspace(lo, hi, n)
    kdf = pd.DataFrame({k: np.full(n, knobs[k]) for k in schema.KNOBS})
    kdf[sweep_key] = xs
    pred = predict.predict_frame(predict.frame(comp, kdf))
    return pd.DataFrame({sweep_key: xs, target: pred[target].to_numpy()})


def _sensitivity_section(comp: dict, knobs: dict) -> None:
    st.markdown("##### Simulasi What-If Parameter — sensitivitas pada komposisi ini")
    st.caption(
        "Tiap kurva: SATU parameter disapu sepanjang rentang amannya, parameter "
        "lain & komposisi bauksit ditahan pada nilai yang Anda atur di atas. "
        "Titik putih = posisi slider Anda saat ini."
    )
    target = st.selectbox(
        "Target yang disimulasikan", schema.TARGETS, format_func=schema.label,
        key="pl_sens_target",
    )

    n_knobs = len(schema.KNOBS)
    fig = make_subplots(rows=1, cols=n_knobs,
                         subplot_titles=[schema.label(k) for k in schema.KNOBS],
                         horizontal_spacing=0.045)
    deltas = {}
    for i, k in enumerate(schema.KNOBS):
        sw = _sweep_knob(comp, knobs, k, target)
        fig.add_trace(
            go.Scatter(x=sw[k], y=sw[target], mode="lines",
                       line=dict(color=ui.SERIES[i % len(ui.SERIES)], width=2.5),
                       showlegend=False),
            row=1, col=i + 1,
        )
        cur_y = float(np.interp(knobs[k], sw[k], sw[target]))
        fig.add_trace(
            go.Scatter(x=[knobs[k]], y=[cur_y], mode="markers",
                       marker=dict(color=ui.INK, size=10, line=dict(color=ui.SERIES[i], width=2)),
                       showlegend=False, hovertemplate="posisi Anda<extra></extra>"),
            row=1, col=i + 1,
        )
        deltas[k] = float(sw[target].iloc[-1] - sw[target].iloc[0])

    fig = ui.base_layout(fig, height=260)
    fig.update_annotations(font=dict(color=ui.INK2, size=11))
    st.plotly_chart(fig, width="stretch", key="pl_sens_grid")

    st.markdown(f"**Ranking pengaruh parameter terhadap {schema.label(target)}**")
    order = sorted(deltas, key=lambda k: abs(deltas[k]), reverse=True)
    tfig = go.Figure(go.Bar(
        x=[deltas[k] for k in order], y=[schema.label(k) for k in order],
        orientation="h",
        marker=dict(color=[ui.STATUS["good"] if deltas[k] >= 0 else ui.STATUS["critical"]
                            for k in order]),
        hovertemplate="%{y}: %{x:+.2f}<extra></extra>",
    ))
    tfig.add_vline(x=0, line=dict(color=ui.GRID, width=1))
    tfig = ui.base_layout(tfig, height=210,
                           title=f"Δ{schema.label(target)} dari ujung-ke-ujung rentang aman")
    tfig.update_yaxes(autorange="reversed")
    st.plotly_chart(tfig, width="stretch", key="pl_tornado")
    top = order[0]
    st.caption(
        f"Untuk komposisi bauksit yang Anda masukkan, **{schema.label(top)}** "
        f"punya pengaruh terbesar terhadap {schema.label(target)} "
        f"(Δ{deltas[top]:+.2f} sepanjang rentang aman)."
    )


def _retrain_expander() -> None:
    with st.expander(":material/autorenew: Latih ulang model ML dari data terbaru"):
        st.caption(
            "Melatih ulang ke-4 model LightGBM surrogate dari "
            "`data/raw/data.csv` (5-fold cross-validation, ±5-10 detik)."
        )
        if st.button("Latih Ulang Sekarang", key="pl_retrain_btn"):
            with st.spinner("Melatih model..."):
                report = train.train_all(verbose=False)
            st.success(
                f"Selesai dalam {report['elapsed_sec']:.1f} dtk — "
                f"{len(report['trained'])} model dilatih ({report['rows']} baris)."
            )
            mcols = st.columns(len(report["metrics"]) or 1)
            for i, (t, m) in enumerate(report["metrics"].items()):
                mcols[i].metric(schema.label(t), f"R²={m['cv_r2']:.4f}",
                                 f"MAE {m['cv_mae']:.3g}")
            st.cache_data.clear()


def render(df: pd.DataFrame) -> None:
    _init_state(df)
    st.info(
        "**Prediction Lab** — masukkan komposisi bauksit & parameter proses "
        "bebas (tidak terikat jam replay), lihat prediksi real-time, dan "
        "simulasikan pengaruh tiap parameter. Ini melengkapi tab "
        "*Digesti & Pra-desilikasi* yang terikat pada baris histori tertentu.",
        icon=":material/science:",
    )
    comp, _ = _composition_inputs(df)
    st.divider()
    knobs = _knob_inputs(df)
    st.divider()
    wet_feed_t, moisture_frac = _feed_inputs()
    st.divider()
    _prediction_comparison(comp, knobs, wet_feed_t, moisture_frac)
    st.divider()
    _sensitivity_section(comp, knobs)
    st.divider()
    _retrain_expander()
