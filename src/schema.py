"""Single source of schema (P1, doc 09).

Satu-satunya file yang tahu nama kolom mentah. Semua modul lain memakai nama
kanonik. Pencocokan header dilakukan pada bentuk ternormalisasi (lowercase,
alfanumerik saja) supaya tahan terhadap spasi ekstra & karakter rusak cp1252.
"""

from __future__ import annotations

import re

import pandas as pd

# CATATAN LINGKUNGAN: pandas>=3.0 mengaktifkan `future.infer_string=True`
# (Index string via PyArrow) secara default. Kombinasi ini + thread pekerja
# Streamlit (tiap rerun = thread baru) memicu segfault pada string_arrow saat
# DataFrame/Index string dibangun berulang dari thread non-utama. Dinonaktifkan
# di sini — modul pertama yang diimpor hampir semua bagian aplikasi.
pd.set_option("future.infer_string", False)

# role: input (komposisi bauksit) | knob (bisa dikendalikan) | target (prediksi)
#       | intermediate (hasil neraca massa) | constant (bernilai tunggal di data
#       sintesis — dipantau capability, bisa berubah di data asli tahap 2)
# Key = prefix dari header ternormalisasi.
_MAP: list[tuple[str, str, str]] = [
    # --- INPUT: komposisi bauksit (%) ---
    ("kadaral2o3",                      "al2o3_pct",          "input"),
    ("reactivesio2",                    "reactive_sio2_pct",  "input"),
    ("fe2o3",                           "fe2o3_pct",          "input"),
    ("tio2",                            "tio2_pct",           "input"),
    ("caocalciumoxide",                 "cao_pct",            "input"),
    ("mgomagnesiumoxide",               "mgo_pct",            "input"),
    ("na2osodiumoxide",                 "na2o_pct",           "input"),
    ("k2opotassiumoxide",               "k2o_pct",            "input"),
    ("cr2o3chromiumoxide",              "cr2o3_pct",          "input"),
    ("others",                          "others_pct",         "input"),
    # --- KNOB: parameter proses ---
    ("bauxiteparticlesize",             "particle_size_um",   "knob"),
    ("suhudigester",                    "digester_temp_c",    "knob"),
    ("targetnaohsolutionconcentration", "naoh_conc_gl",       "knob"),
    ("precipitationtemperature",        "precip_temp_c",      "knob"),
    ("seedaluminohydrateratio",         "seed_ratio",         "knob"),
    # --- TARGET ---
    ("alumuniumrecoveryrate",           "recovery_pct",       "target"),
    ("totalopex",                       "total_opex",         "target"),
    ("wetredmuddischarge",              "red_mud_t",          "target"),
    ("precipitationyield",              "precip_yield_pct",   "target"),
    # --- INTERMEDIATE: neraca massa (JANGAN jadi fitur — data leakage) ---
    ("alumuniumfeed",                   "al_feed_t",          "intermediate"),
    ("alumuniuminrecycledspentliquor",  "al_recycled_t",      "intermediate"),
    ("alumuniumlostinredmud",           "al_lost_redmud_t",   "intermediate"),
    ("aluminahydrateseed",              "seed_t",             "intermediate"),
    ("purealoh3",                       "hydrate_t",          "intermediate"),
    ("naohconsumed",                    "naoh_consumed_t",    "intermediate"),
    ("netmakeupnaoh",                   "naoh_makeup_t",      "intermediate"),
    ("caohconsumed",                    "caoh_predesil_t",    "intermediate"),
    ("caoh2lostinredmud",               "caoh2_lost_t",       "intermediate"),
    ("caoh2consumption",                "caoh2_cond_t",       "intermediate"),
    ("totalcaoconsumed",                "cao_total_t",        "intermediate"),
    ("caoadditioninprocess",            "cao_addition_t",     "intermediate"),
    ("waterconsumption",                "water_consumption_t", "intermediate"),
    ("wateraddedfromredmudwashing",     "water_wash_t",       "intermediate"),
    ("waterremovedthroughevaporation",  "water_evap_t",       "intermediate"),
    ("digestionefficiencyofbauxite",    "digestion_eff_pct",  "intermediate"),
    ("totalnaohopex",                   "naoh_opex",          "intermediate"),
    ("totalcaoopex",                    "cao_opex",           "intermediate"),
    ("alsirati",                        "al_si_ratio",        "intermediate"),
    # --- CONSTANT di data sintesis (capability memantau kalau nanti bervariasi) ---
    ("targetcasiratio",                 "ca_si_ratio",        "constant"),
    ("predesilicationprocessefficiency", "predesil_eff",      "constant"),
    ("steaminjected",                   "steam_t",            "constant"),
    ("lsratio",                         "ls_ratio",           "constant"),
    ("digestionsteamevaporationloss",   "steam_evap_loss",    "constant"),
    ("steamflashingwater",              "steam_flash",        "constant"),
    ("clarificationprocessefficiency",  "clarif_eff",         "constant"),
    ("freemoisture",                    "free_moisture",      "constant"),
    ("drybauxitefeedrate",              "feed_rate_t",        "constant"),
    ("bauxitefeedrate",                 "wet_feed_rate_t",    "constant"),
    ("moistureinbauxite",               "feed_moisture_frac", "constant"),
    ("naohaffectedbycarbonation",       "naoh_carbonation_frac", "constant"),
    ("washwateraddedtoredmud",          "wash_water_ratio",   "constant"),
    ("redmudwashefficiency",            "wash_eff",           "constant"),
    ("spentliquorna2co3",               "na2co3_conv_eff",    "constant"),
    ("minimumcausticity",               "causticity",         "constant"),
]

# Kolom mentah yang sengaja dibuang (pemisah visual kosong).
DROP_PREFIXES = ("konsentrasidll",)

INPUTS = [c for _, c, r in _MAP if r == "input"]
KNOBS = [c for _, c, r in _MAP if r == "knob"]
TARGETS = [c for _, c, r in _MAP if r == "target"]
INTERMEDIATES = [c for _, c, r in _MAP if r == "intermediate"]
CONSTANTS = [c for _, c, r in _MAP if r == "constant"]
FEATURES = INPUTS + KNOBS  # fitur model — TANPA intermediate (anti-leakage)

ROLE = {c: r for _, c, r in _MAP}

# Kolom yang nilainya persen-string ("87,61%") di file mentah.
PERCENT_COLS = set(INPUTS) | {"recovery_pct", "precip_yield_pct", "digestion_eff_pct"}

# Amplop operasi aman (guardrail optimizer & validasi) — irisan rentang data
# sintesis dan batas alarm proses (doc 02/06). Diperbarui saat data asli datang.
SAFE_BOUNDS: dict[str, tuple[float, float]] = {
    "particle_size_um": (50.0, 75.0),
    "digester_temp_c": (140.0, 150.0),
    "naoh_conc_gl": (140.0, 160.0),
    "precip_temp_c": (50.0, 70.0),
    "seed_ratio": (2.0, 3.0),
}

# Rentang fisik masuk akal untuk validasi data masuk.
PHYSICAL_RANGES: dict[str, tuple[float, float]] = {
    "al2o3_pct": (20.0, 80.0),
    "reactive_sio2_pct": (0.0, 20.0),
    "recovery_pct": (0.0, 100.0),
    "precip_yield_pct": (0.0, 100.0),
    "digestion_eff_pct": (0.0, 100.0),
    "total_opex": (0.0, float("inf")),
    "red_mud_t": (0.0, float("inf")),
    "naoh_makeup_t": (0.0, float("inf")),
    "cao_addition_t": (0.0, float("inf")),
    "feed_rate_t": (0.0, float("inf")),
    "free_moisture": (0.0, 100.0),
}

# Label tampilan (Bahasa operator) untuk dashboard.
LABELS = {
    "al2o3_pct": "Kadar Al₂O₃ (%)",
    "reactive_sio2_pct": "Silika Reaktif (%)",
    "particle_size_um": "Ukuran Partikel (µm)",
    "digester_temp_c": "Suhu Digester (°C)",
    "naoh_conc_gl": "Konsentrasi NaOH (g/L)",
    "precip_temp_c": "Suhu Presipitasi (°C)",
    "seed_ratio": "Rasio Seed",
    "recovery_pct": "Recovery Al (%)",
    "total_opex": "Total OPEX (/jam)",
    "red_mud_t": "Red Mud Basah (ton)",
    "precip_yield_pct": "Yield Presipitasi (%)",
    "causticity": "Causticity",
    "naoh_opex": "OPEX NaOH (/jam)",
    "cao_opex": "OPEX CaO (/jam)",
    "digestion_eff_pct": "Efisiensi Digesti (%)",
    "al_lost_redmud_t": "Al Hilang ke Red Mud (ton)",
    "naoh_makeup_t": "Make-up NaOH (ton)",
    "cao_addition_t": "Dosis CaO (ton)",
    "feed_rate_t": "Dry Feed Rate (ton/jam)",
    "free_moisture": "Moisture (%)",
    "wet_feed_rate_t": "Wet Feed Rate (ton/jam)",
    "feed_moisture_frac": "Moisture Bauksit (fraksi)",
    "al_si_ratio": "Rasio Al/Si",
    "fe2o3_pct": "Fe₂O₃ — Hematit, inert (%)",
    "tio2_pct": "TiO₂ — Rutil/Anatas, inert (%)",
    "cao_pct": "CaO — Kapur, inert (%)",
    "mgo_pct": "MgO — Magnesia, inert (%)",
    "na2o_pct": "Na₂O — Soda, inert (%)",
    "k2o_pct": "K₂O — Kalium Oksida, inert (%)",
    "cr2o3_pct": "Cr₂O₃ — Krom Oksida, inert (%)",
    "others_pct": "Lain-lain / LOI (%)",
}


def normalize_header(raw: str) -> str:
    """'Suhu Digester   ' -> 'suhudigester' (tahan spasi & karakter rusak)."""
    return re.sub(r"[^a-z0-9]", "", raw.lower())


def match_canonical(raw: str) -> str | None:
    """Nama kanonik untuk sebuah header mentah, atau None kalau tak dikenal.

    Prefix terpanjang menang, supaya 'totalnaohopex' tidak tertelan 'totalopex'.
    """
    norm = normalize_header(raw)
    if any(norm.startswith(p) for p in DROP_PREFIXES):
        return None
    best = None
    for prefix, canonical, _ in _MAP:
        if norm.startswith(prefix):
            if best is None or len(prefix) > len(best[0]):
                best = (prefix, canonical)
    return best[1] if best else None


def label(col: str) -> str:
    return LABELS.get(col, col)
