"""AI RED MUD — CRO Console (doc 10).

Jalankan:  python -m streamlit run app/main.py
(JANGAN menamai file ini app.py — akan shadow package `app` saat streamlit run.)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# CATATAN LINGKUNGAN: PyArrow (dipakai pandas>=3.0 & internal st.dataframe)
# default ke allocator 'mimalloc', yang di beberapa lingkungan sandbox/container
# menyebabkan segfault saat diakses dari thread rerun Streamlit (setiap rerun
# = thread baru). HARUS di-set SEBELUM pandas/streamlit/pyarrow ter-import.
# Allocator 'system' sedikit lebih lambat tapi jauh lebih portabel — dampak
# performa untuk ukuran data aplikasi ini (ribuan baris) tidak signifikan.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from app import ui
from app.views import (digestion, liquor, overview, pfd, precip,
                       prediction_lab, redmud)
from src import capability
from src.advisory import context as adv_context
from src.advisory import providers, template
from src.data import replay
from src.data.adapters import load_clean
from src.physics import carbonation

st.set_page_config(
    page_title="AI RED MUD — CRO Console", page_icon="🏭", layout="wide"
)

# Artefak model di-gitignore (regenerable). Clone segar / deploy cloud:
# latih otomatis sekali di startup — sekalian bukti klaim "retrain dalam menit".
from src.models import registry as _registry  # noqa: E402

if not _registry.available():
    from src.models.train import train_all

    with st.spinner("Model belum ada — melatih surrogate dari data (±30 dtk)..."):
        train_all(str(ROOT / "data" / "raw" / "data.csv"))
    st.toast("Surrogate terlatih & tersimpan ke registry")


# ---------- data & model (cache) ----------
@st.cache_data(show_spinner="Memuat data pabrik...")
def _load():
    df = load_clean(str(ROOT / "data" / "raw" / "data.csv"))
    return df


@st.cache_data(show_spinner=False)
def _sequence(scenario: str):
    return replay.build_sequence(_load(), scenario)


@st.cache_data(show_spinner="Menghitung advisory (surrogate + optimizer)...")
def _context(scenario: str, hour: int, weights: tuple):
    row = _sequence(scenario).iloc[hour]
    return adv_context.build(row, weights=weights)


df = _load()
caps = capability.detect(df)

# ---------- session state ----------
ss = st.session_state
ss.setdefault("hour", 8)
ss.setdefault("playing", False)
ss.setdefault("advisory_log", [])
ss.setdefault("scenario", replay.SCENARIOS[0])

# ---------- sidebar: kendali replay & prioritas ----------
with st.sidebar:
    st.markdown("## AI RED MUD")
    st.caption("Bayer Process Advisor — demo replay (streaming-ready, doc 07)")

    scenario = st.selectbox("Skenario replay", replay.SCENARIOS,
                            index=replay.SCENARIOS.index(ss.scenario))
    if scenario != ss.scenario:
        ss.scenario = scenario
        ss.hour = 8
        ss.playing = False

    seq = _sequence(ss.scenario)
    c1, c2 = st.columns(2)
    if c1.button("▶ Play" if not ss.playing else "⏸ Pause", width="stretch"):
        ss.playing = not ss.playing
        st.rerun()
    if c2.button("⏭ +1 jam", width="stretch"):
        ss.hour = min(ss.hour + 1, len(seq) - 1)
    speed = st.slider("Detik per jam simulasi", 1.0, 5.0, 2.0, 0.5)
    ss.hour = st.slider("Jam simulasi", 0, len(seq) - 1, ss.hour)

    st.divider()
    st.markdown("**Prioritas optimasi** (bobot Pareto)")
    w_rec = st.slider("Recovery", 0.0, 1.0, 0.5, 0.05)
    w_opx = st.slider("OPEX", 0.0, 1.0, 0.3, 0.05)
    w_rm = st.slider("Red mud / ESG", 0.0, 1.0, 0.2, 0.05)
    total_w = max(w_rec + w_opx + w_rm, 1e-9)
    weights = (w_rec / total_w, w_opx / total_w, w_rm / total_w)

    st.divider()
    st.caption(
        f"Advisory backend: **{providers.provider_name()}** "
        "(ubah via env `LLM_PROVIDER`)  \n"
        f"Fitur ML off (kolom konstan): "
        f"{', '.join(k for k, v in caps.items() if not v) or '—'}"
    )

row = seq.iloc[ss.hour]
ctx = _context(ss.scenario, ss.hour, weights)

# ---------- header ----------
st.markdown(
    f"### AI RED MUD · Pabrik Alumina — Konsol CRO  "
    f"<span style='color:{ui.MUTED};font-size:0.7em'>Shift "
    f"{ss.hour // 8 % 3 + 1} · Jam simulasi {ss.hour:02d}:00 · "
    f"Skenario: {ss.scenario}</span>",
    unsafe_allow_html=True,
)

# ---------- KPI row (stat tiles, doc 10) ----------
hist = seq.iloc[: ss.hour + 1]
co2_now = carbonation.assess(float(row["red_mud_t"])).co2_sequestered_t


def _delta(col: str, fmt: str = "{:+.1f}") -> str | None:
    if ss.hour == 0:
        return None
    return fmt.format(float(row[col]) - float(seq.iloc[ss.hour - 1][col]))


k = st.columns(6)
ui.kpi(k[0], "Recovery Al", f"{row['recovery_pct']:.1f}%",
       ui.status_of(row["recovery_pct"], (85, 101), (82, 85)), _delta("recovery_pct"))
ui.kpi(k[1], "OPEX / jam", f"{row['total_opex']:,.0f}",
       ui.status_of(-row["total_opex"], (-2500, 0), (-3400, -2500)),
       _delta("total_opex", "{:+,.0f}"))
ui.kpi(k[2], "Silika Reaktif", f"{row['reactive_sio2_pct']:.1f}%",
       ui.status_of(-row["reactive_sio2_pct"], (-5.5, 0), (-6.3, -5.5)),
       _delta("reactive_sio2_pct"))
ui.kpi(k[3], "Red Mud", f"{row['red_mud_t']:.1f} t",
       ui.status_of(-row["red_mud_t"], (-75, 0), (-85, -75)), _delta("red_mud_t"))
ui.kpi(k[4], "Potensi CO₂ capture", f"{co2_now:.2f} t", "good")
ui.kpi(k[5], "Causticity", f"{row.get('causticity', 0.85):.2f}", "good")

# ---------- advisory (selalu terlihat, doc 10) ----------
st.markdown("#### Advisory")
cards = template.cards(ctx)
for i, card in enumerate(cards[:3]):
    ui.advisory_card(card, key=f"{ss.hour}_{i}")

if providers.provider_name() != "template":
    with st.expander(":material/smart_toy: Narasi advisory (LLM)"):
        if st.button("Generate narasi"):
            text, backend = providers.advise(ctx)
            st.markdown(text)
            st.caption(f"backend: {backend}")

# ---------- tabs = stasiun (doc 10) ----------
tabs = st.tabs([
    ":material/monitoring: Overview",
    ":material/account_tree: Diagram Proses",
    ":material/local_fire_department: Digesti",
    ":material/science: Liquor Loop",
    ":material/ac_unit: Presipitasi",
    ":material/recycling: Red Mud & CCUS",
    ":material/biotech: Prediction Lab",
])
with tabs[0]:
    overview.render(df, seq, ss.hour)
with tabs[1]:
    pfd.render(row, ctx)
with tabs[2]:
    if caps["surrogate"]:
        digestion.render(row, ctx)
    else:
        ui.empty_state("Peta operasi", "model surrogate belum terlatih")
with tabs[3]:
    if caps["physics_na_balance"]:
        liquor.render(row, ctx)
    else:
        ui.empty_state("Neraca Na", "kolom neraca natrium tidak tersedia di data")
with tabs[4]:
    precip.render(row, ctx)
with tabs[5]:
    if caps["sankey_al"]:
        redmud.render(row, ctx)
    else:
        ui.empty_state("Sankey Al", "kolom neraca aluminium tidak tersedia")
with tabs[6]:
    if caps["surrogate"]:
        prediction_lab.render(df)
    else:
        ui.empty_state("Prediction Lab", "model surrogate belum terlatih")

# ---------- auto play ----------
if ss.playing:
    if ss.hour < len(seq) - 1:
        time.sleep(speed)
        ss.hour += 1
        st.rerun()
    else:
        ss.playing = False
