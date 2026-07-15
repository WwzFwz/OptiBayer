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
ss.setdefault("theme_mode", "dark")


def _set_core_theme(mode: str) -> None:
    """Ganti tema inti Streamlit saat runtime.

    Tidak ada API resmi utk ini; set opsi config lalu rerun — bekerja pada
    versi Streamlit saat ini. Kalau suatu saat gagal, chart TETAP mengikuti
    mode (ui.apply) dan tema inti bisa diganti manual via ☰ > Settings > Theme.
    """
    try:
        from streamlit import config as _cfg
        if mode == "light":
            vals = {"theme.base": "light", "theme.backgroundColor": "#f9f9f7",
                    "theme.secondaryBackgroundColor": "#fcfcfb",
                    "theme.textColor": "#0b0b0b", "theme.primaryColor": "#2a78d6"}
        else:
            vals = {"theme.base": "dark", "theme.backgroundColor": "#0d0d0d",
                    "theme.secondaryBackgroundColor": "#1a1a19",
                    "theme.textColor": "#ffffff", "theme.primaryColor": "#3987e5"}
        for k, v in vals.items():
            _cfg.set_option(k, v)
    except Exception:
        pass


# Pengaman modul-basi: server Streamlit yang hidup sejak sebelum update kode
# menyimpan modul lama di sys.modules (script di-rerun, modul TIDAK di-reimport).
# Kalau ui versi lama (belum punya apply), paksa reload sebelum dipakai.
if not hasattr(ui, "apply"):
    import importlib

    importlib.reload(ui)

ui.apply(ss.theme_mode)   # palet chart mengikuti mode SEBELUM view dirender
ui.inject_css(ss.theme_mode)  # light mode penuh + gaya tombol (lihat ui.py)
ss.setdefault("nav", ui.NAV_LABELS["overview"])
ss.setdefault("onboard_done", False)

# ---------- sidebar: kendali replay & prioritas ----------
with st.sidebar:
    st.markdown("## AI RED MUD")
    st.caption("Bayer Process Advisor — demo replay (streaming-ready, doc 07)")

    st.markdown("**Skenario Demo**")
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

    if st.button("Muat jam ini → Prediction Lab", icon=":material/biotech:",
                 width="stretch",
                 help="Salin komposisi & setpoint jam aktif ke Prediction Lab "
                      "untuk dieksperimen bebas"):
        prediction_lab._apply_row(seq.iloc[ss.hour])
        ss["_pl_init"] = True
        ui.goto("lab")

    st.divider()
    st.markdown("**Prioritas optimasi** (bobot Pareto)")
    w_rec = st.slider("Recovery", 0.0, 1.0, 0.5, 0.05)
    w_opx = st.slider("OPEX", 0.0, 1.0, 0.3, 0.05)
    w_rm = st.slider("Red mud / ESG", 0.0, 1.0, 0.2, 0.05)
    total_w = max(w_rec + w_opx + w_rm, 1e-9)
    weights = (w_rec / total_w, w_opx / total_w, w_rm / total_w)

    st.divider()
    st.markdown("**Tampilan**")
    light_on = st.toggle(
        "Mode terang", value=(ss.theme_mode == "light"),
        help="Tema putih untuk ruangan terang; chart & diagram ikut menyesuaikan",
    )
    _new_mode = "light" if light_on else "dark"
    if _new_mode != ss.theme_mode:
        ss.theme_mode = _new_mode
        _set_core_theme(_new_mode)
        st.rerun()

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
# jam simulasi kumulatif (0-95) -> tampilan manusiawi: Hari N · HH:00 · Shift
_day = ss.hour // 24 + 1
_clock = ss.hour % 24
_shift = _clock // 8 + 1
st.markdown(
    f"### AI RED MUD · Pabrik Alumina — Konsol CRO  "
    f"<span style='color:{ui.MUTED};font-size:0.7em'>Hari {_day} · "
    f"{_clock:02d}:00 · Shift {_shift} · Skenario: {ss.scenario}</span>",
    unsafe_allow_html=True,
)

# ---------- onboarding sekali-tampil ----------
if not ss.onboard_done:
    with st.container(border=True):
        b1, b2, b3 = st.columns([5.5, 2.4, 1.1])
        b1.markdown(
            "**Baru di sini?** Alur demo terbaik: jalankan skenario "
            "**Gangguan: Silika Spike** — perhatikan KPI memerah sekitar jam 24, "
            "kartu advisory muncul dengan rekomendasi setpoint + dampak angkanya."
        )
        if b2.button("Mulai demo Silika Spike", type="primary",
                     icon=":material/play_arrow:", width="stretch"):
            ss.scenario = replay.SCENARIOS[1]
            ss.hour = 20
            ss.playing = True
            ss.onboard_done = True
            st.rerun()
        if b3.button("Tutup", icon=":material/close:", width="stretch"):
            ss.onboard_done = True
            st.rerun()

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
       ui.status_of(-row["total_opex"], (-25000, 0), (-40000, -25000)),
       _delta("total_opex", "{:+,.0f}"), invert=True)
ui.kpi(k[2], "Silika Reaktif", f"{row['reactive_sio2_pct']:.1f}%",
       ui.status_of(-row["reactive_sio2_pct"], (-5.5, 0), (-6.3, -5.5)),
       _delta("reactive_sio2_pct"), invert=True)
ui.kpi(k[3], "Red Mud", f"{row['red_mud_t']:.1f} t",
       ui.status_of(-row["red_mud_t"], (-500, 0), (-580, -500)),
       _delta("red_mud_t"), invert=True)
ui.kpi(k[4], "Potensi CO₂ capture", f"{co2_now:.2f} t", "good")
ui.kpi(k[5], "Causticity", f"{row.get('causticity', 0.85):.2f}", "good")

# ---------- advisory (selalu terlihat, doc 10) ----------
st.markdown("#### Advisory")
cards = template.cards(ctx)
# 3 terpenting selalu tampil (anti alarm-fatigue); sisanya tetap bisa diakses
for i, card in enumerate(cards[:3]):
    ui.advisory_card(card, key=f"{ss.hour}_{i}")
if len(cards) > 3:
    _extra = cards[3:]
    with st.expander(
        f":material/expand_more: Lihat {len(_extra)} advisory lainnya "
        f"(prioritas lebih rendah)"
    ):
        for i, card in enumerate(_extra, start=3):
            ui.advisory_card(card, key=f"{ss.hour}_{i}")

if providers.provider_name() != "template":
    with st.expander(":material/smart_toy: Narasi advisory (LLM)"):
        if st.button("Generate narasi"):
            text, backend = providers.advise(ctx)
            st.markdown(text)
            st.caption(f"backend: {backend}")

# ---------- navigasi = stasiun (doc 10) ----------
# segmented control ber-state (bukan st.tabs) supaya tombol lain bisa
# melompat antar halaman (ui.goto — mis. kartu advisory -> peta operasi).
_nav_options = list(ui.NAV_LABELS.values())
nav_sel = st.segmented_control(
    "Navigasi", _nav_options, key="nav", label_visibility="collapsed",
)
page = nav_sel or ui.NAV_LABELS["overview"]

if page == ui.NAV_LABELS["overview"]:
    overview.render(df, seq, ss.hour)
elif page == ui.NAV_LABELS["pfd"]:
    pfd.render(row, ctx, hist=seq.iloc[: ss.hour + 1])
elif page == ui.NAV_LABELS["digestion"]:
    if caps["surrogate"]:
        digestion.render(row, ctx)
    else:
        ui.empty_state("Peta operasi", "model surrogate belum terlatih")
elif page == ui.NAV_LABELS["liquor"]:
    if caps["physics_na_balance"]:
        liquor.render(row, ctx)
    else:
        ui.empty_state("Neraca Na", "kolom neraca natrium tidak tersedia di data")
elif page == ui.NAV_LABELS["precip"]:
    precip.render(row, ctx)
elif page == ui.NAV_LABELS["redmud"]:
    if caps["sankey_al"]:
        redmud.render(row, ctx)
    else:
        ui.empty_state("Sankey Al", "kolom neraca aluminium tidak tersedia")
elif page == ui.NAV_LABELS["lab"]:
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
