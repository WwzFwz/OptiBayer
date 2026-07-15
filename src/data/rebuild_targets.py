"""Perbaiki data.csv v2: hitung ulang kolom OUTPUT dari kolom INPUT.

LATAR (2026-07-15): data.csv v2 (ekspor macro VBA xlsm UPDATED, basis wet
1000 t/jam & moisture 20%) terbukti TIDAK konsisten antar-kolom di dalam satu
baris: korelasi silika vs recovery = +0.01 (seharusnya kuat negatif), dan
target CSV vs hitung-ulang formula = korelasi ~0. Akar masalah: macro
menjalankan `Application.Calculation = xlCalculationManual` lalu hanya satu
pass `wsCalc.Calculate` per sheet per iterasi — referensi melingkar
spent-liquor (butuh iterative calculation) belum konvergen ketika nilai
disalin, sehingga output baris i tercampur sisa perhitungan baris i-1.

SOLUSI di modul ini: baca CSV apa adanya, ambil kolom input (komposisi 10
oksida) + parameter proses (5 knob), jalankan `src.physics.mass_balance.run`
(port literal formula workbook, tervalidasi galat <0.11% pada data v1) pada
basis wet 1000 / moisture 0.2, lalu tulis ulang HANYA kolom output — posisi
kolom, header, dan gaya format (persen 2 desimal, desimal titik) dipertahankan
persis seperti keluaran macro.

Saran perbaikan di sisi Excel (untuk re-export berikutnya): aktifkan
File > Options > Formulas > Enable iterative calculation, dan di macro ganti
loop `wsCalc.Calculate` dengan beberapa kali `Application.CalculateFullRebuild`
/ `Application.Calculate` sampai nilai sel monitor stabil, SEBELUM menyalin.

Pakai:
    python -m src.data.rebuild_targets --in data/raw/data.csv --out data/raw/data.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.physics import mass_balance

WET_FEED_T = 1000.0   # Dashboard!C6 (xlsm UPDATED)
MOISTURE = 0.2        # Dashboard!C7

# indeks kolom 0-based pada CSV v2 (55 kolom)
IDX_INPUTS = list(range(10))          # komposisi (persen, ber-'%')
IDX_KNOBS = {"particle_size_um": 28, "digester_temp_c": 33,
             "naoh_conc_gl": 35, "precip_temp_c": 38, "seed_ratio": 41}
INPUT_KEYS = ["al2o3_pct", "reactive_sio2_pct", "fe2o3_pct", "tio2_pct",
              "cao_pct", "mgo_pct", "na2o_pct", "k2o_pct", "cr2o3_pct",
              "others_pct"]

# indeks kolom output -> (field MassBalanceResult, format)
#   "f"  = float polos, "p2" = persen 2 desimal ber-'%', "fr" = fraksi polos
OUTPUT_MAP: dict[int, tuple[str, str]] = {
    10: ("al_feed_t", "f"),
    11: ("al_recycled_t", "f"),
    12: ("al_lost_redmud_t", "f"),
    13: ("seed_t", "f"),
    14: ("recovery_pct", "p2"),
    15: ("hydrate_t", "f"),
    16: ("naoh_consumed_t", "f"),
    17: ("naoh_makeup_t", "f"),
    18: ("caoh_predesil_t", "f"),
    19: ("caoh2_lost_t", "f"),
    20: ("caoh2_cond_t", "f"),
    21: ("cao_total_t", "f"),
    22: ("cao_addition_t", "f"),
    23: ("water_consumption_t", "f"),
    24: ("water_wash_t", "f"),
    25: ("water_evap_t", "f"),
    26: ("red_mud_t", "f"),
    31: ("digestion_eff_pct", "p2"),
    39: ("precip_yield_pct", "fr"),   # v2 menyimpan yield sbg fraksi mentah
    48: ("naoh_opex", "f"),
    49: ("cao_opex", "f"),
    50: ("total_opex", "f"),
}
IDX_ALSI = 51  # Al/Si ratio = al2o3_pct / reactive_sio2_pct


def _num(cell: str) -> float:
    return float(cell.strip().rstrip("%").replace(",", "."))


def _fmt(value: float, kind: str) -> str:
    if kind == "p2":
        return f"{value:.2f}%"
    if kind == "fr":
        return f"{value / 100.0:.9f}"
    return f"{value:.7f}"


def rebuild(path_in: str | Path, path_out: str | Path) -> dict:
    lines = Path(path_in).read_text(encoding="cp1252").splitlines()
    header, rows = lines[0], lines[1:]
    out_lines = [header]
    n_fixed = 0

    for line in rows:
        if not line.strip():
            continue
        cells = line.split(";")
        comp = {k: _num(cells[i]) for k, i in zip(INPUT_KEYS, IDX_INPUTS)}
        knobs = {k: _num(cells[i]) for k, i in IDX_KNOBS.items()}

        res = mass_balance.run(comp, knobs,
                               wet_feed_t=WET_FEED_T, moisture_frac=MOISTURE)
        for idx, (field_name, kind) in OUTPUT_MAP.items():
            cells[idx] = _fmt(getattr(res, field_name), kind)
        cells[IDX_ALSI] = f"{comp['al2o3_pct'] / max(comp['reactive_sio2_pct'], 1e-9):.7f}"
        out_lines.append(";".join(cells))
        n_fixed += 1

    Path(path_out).write_text("\n".join(out_lines) + "\n", encoding="cp1252")
    return {"rows": n_fixed, "out": str(path_out)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="path_in", default="data/raw/data.csv")
    ap.add_argument("--out", dest="path_out", default="data/raw/data.csv")
    args = ap.parse_args()
    print(rebuild(args.path_in, args.path_out))
