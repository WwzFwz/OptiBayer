"""Verifikasi silang surrogate ML terhadap kalkulator neraca massa (doc 14 A1/C4).

LATAR. Target di `data/raw/data.csv` dihasilkan ulang oleh
`src.data.rebuild_targets` memakai `src.physics.mass_balance.run` — jadi
surrogate LightGBM sesungguhnya belajar meniru KALKULATOR DETERMINISTIK, bukan
pabrik. Itu sebabnya R² 0.99 tidak boleh dibaca sebagai akurasi dunia nyata
(doc 14 A1). Modul ini mengubah fakta itu dari "pengakuan di slide" menjadi
ANGKA YANG DIUKUR:

* `verify()`      — satu titik operasi: ML vs fisika, ditandai kalau selisihnya
                    melebihi interval konformal 90% milik model itu sendiri.
                    Dipakai advisory: setiap rekomendasi setpoint dicek fisika
                    sebelum ditampilkan ke operator.
* `fidelity()`    — studi batch: sampel acak di dalam & di luar rentang latih,
                    melaporkan sebaran galat + kecepatan relatif.

Kenapa fisika tidak dipakai langsung saja sebagai pengganti ML? Karena
`mass_balance.run` hanya berlaku selama formula workbook berlaku. Surrogate ada
untuk dilatih ulang pada data historian nyata (yang tidak punya rumus tertutup)
— dan ia 7–8x lebih cepat per evaluasi, yang terasa di loop NSGA-II. Selama
fase sintesis ini, fisika berperan sebagai WASIT, bukan pesaing.
"""

from __future__ import annotations

import time

import numpy as np

from src import schema
from src.models import predict
from src.physics import mass_balance

# Basis operasi kalkulator (sama dengan src/data/rebuild_targets.py).
WET_FEED_T = 1000.0
MOISTURE = 0.2

# Target yang dihitung oleh KEDUA jalur (ML & neraca massa).
SHARED_TARGETS: tuple[str, ...] = (
    "recovery_pct", "total_opex", "red_mud_t", "precip_yield_pct",
)

# Toleransi cadangan (relatif) kalau model belum punya kuantil konformal.
FALLBACK_TOL_REL = 0.02

# Selisih ML-vs-fisika dinyatakan MENCURIGAKAN bila melampaui
# FAKTOR_TOLERANSI x setengah-lebar interval konformal.
#
# Kenapa 2x dan bukan 1x? Karena titik yang diperiksa bukan titik acak,
# melainkan SETPOINT PILIHAN OPTIMIZER — dan optimizer surrogate secara
# sistematis berdiri di tempat modelnya paling optimistis (winner's curse).
# Terukur pada 64 setpoint rekomendasi lintas dua skenario: selisih melampaui
# 1x interval pada 6-25% kasus (p90 = 1.0-2.0x) padahal modelnya sehat. Ambang
# 1x akan membuat kartu peringatan menyala terus dan operator berhenti
# mempercayainya; ambang 2x hanya menyala di kasus yang benar-benar menonjol.
FAKTOR_TOLERANSI = 2.0


def physics_targets(composition: dict[str, float], knobs: dict[str, float],
                    wet_feed_t: float = WET_FEED_T,
                    moisture_frac: float = MOISTURE) -> dict[str, float]:
    """Jalankan neraca massa deterministik untuk titik operasi yang sama."""
    res = mass_balance.run(composition, knobs, wet_feed_t=wet_feed_t,
                           moisture_frac=moisture_frac)
    return {t: float(getattr(res, t)) for t in SHARED_TARGETS
            if hasattr(res, t)}


def verify(composition: dict[str, float], knobs: dict[str, float],
           level: float = 0.90, faktor: float = FAKTOR_TOLERANSI, **kw) -> dict:
    """Cek satu titik operasi: prediksi ML vs fisika eksak.

    Sebuah target dinyatakan LOLOS bila |ML − fisika| masih di dalam
    `faktor` x setengah-lebar interval konformalnya sendiri (lihat
    FAKTOR_TOLERANSI untuk alasan angka 2x). Kalau model belum punya kuantil
    konformal, dipakai toleransi relatif 2%.

    Returns
    -------
    {"ok": bool, "n_gagal": int, "rows": [{target, label, ml, fisika,
     selisih, selisih_rel, tol, ok, basis_tol, rasio}]}
    """
    ml = predict.predict_one(composition, knobs)
    phys = physics_targets(composition, knobs, **kw)

    rows = []
    for t in SHARED_TARGETS:
        if t not in ml or t not in phys:
            continue
        half = predict.halfwidth(t, level)
        basis = f"{faktor:g}x konformal" if half is not None else "relatif-2%"
        tol = (half * faktor if half is not None
               else abs(phys[t]) * FALLBACK_TOL_REL)
        diff = float(ml[t] - phys[t])
        rows.append({
            "target": t,
            "label": schema.label(t),
            "ml": round(float(ml[t]), 4),
            "fisika": round(float(phys[t]), 4),
            "selisih": round(diff, 4),
            "selisih_rel": round(abs(diff) / max(abs(phys[t]), 1e-9), 6),
            "tol": round(float(tol), 4),
            "basis_tol": basis,
            "rasio": round(abs(diff) / max(float(tol), 1e-9), 3),
            "ok": abs(diff) <= tol,
        })

    gagal = [r for r in rows if not r["ok"]]
    return {
        "ok": not gagal,
        "n_gagal": len(gagal),
        "level": level,
        "rows": rows,
        "gagal_label": [r["label"] for r in gagal],
    }


def _sample_box(rng: np.random.Generator, bounds: dict, n: int,
                expand: float = 0.0) -> list[dict]:
    """n titik acak seragam di dalam `bounds`, opsional dilebarkan `expand`.

    PERINGATAN PEMAKAIAN: titik seperti ini sah per-fitur tapi belum tentu sah
    secara FISIK — komposisi hasil undian tidak menjumlah 100% (terukur: median
    101.5%, sementara semua baris latih 99.97–100.02%). Populasi ini dipakai
    sebagai UJI TEKAN, bukan sebagai wakil kondisi operasi nyata.
    """
    out = []
    for _ in range(n):
        point = {}
        for feat, (lo, hi) in bounds.items():
            span = hi - lo
            point[feat] = float(rng.uniform(lo - expand * span,
                                            hi + expand * span))
        out.append(point)
    return out


def _sample_perturbasi(rng: np.random.Generator, df, n: int,
                       jitter: float = 0.05) -> list[dict]:
    """n titik realistis: baris data nyata digoyang, komposisi dinormalkan 100%.

    Inilah populasi yang benar untuk menilai fidelitas pada kondisi operasi
    yang mungkin terjadi — ia tetap berada di manifold data (jumlah oksida
    100%), tidak seperti undian kotak.
    """
    idx = rng.integers(0, len(df), size=n)
    bounds = predict.meta("recovery_pct").get("bounds", {})
    out = []
    for i in idx:
        row = df.iloc[int(i)]
        comp = {c: float(row[c]) * (1 + rng.uniform(-jitter, jitter))
                for c in schema.INPUTS}
        total = sum(comp.values())
        comp = {c: v / total * 100.0 for c, v in comp.items()}  # normalkan 100%
        knobs = {}
        for c in schema.KNOBS:
            lo, hi = bounds.get(c, schema.SAFE_BOUNDS.get(c, (row[c], row[c])))
            v = float(row[c]) * (1 + rng.uniform(-jitter, jitter))
            knobs[c] = float(min(max(v, lo), hi))
        out.append({**comp, **knobs})
    return out


def _fisika_masuk_akal(ph: dict) -> bool:
    """Keluaran neraca massa yang mustahil menandai INPUT-nya yang tak masuk akal.

    Terukur pada undian kotak: sebagian titik menghasilkan OPEX NEGATIF
    (mis. −605) — di situ galat relatif meledak ribuan persen padahal yang
    rusak adalah titik ujinya, bukan modelnya. Titik begini dikeluarkan dari
    statistik dan dihitung terpisah sebagai `n_tak_masuk_akal`.
    """
    if not ph or any(not np.isfinite(v) for v in ph.values()):
        return False
    if ph.get("total_opex", 0.0) <= 0 or ph.get("red_mud_t", 0.0) <= 0:
        return False
    for t in ("recovery_pct", "precip_yield_pct"):
        if t in ph and not (0.0 <= ph[t] <= 100.0):
            return False
    return True


def fidelity(n: int = 200, seed: int = 0, expand: float = 0.25) -> dict:
    """Studi fidelitas: seberapa setia surrogate meniru kalkulator?

    Tiga populasi sampel, dari paling realistis ke paling ekstrem:
      * perturbasi_data — baris data nyata digoyang ±5%, komposisi tetap
                          menjumlah 100% (WAKIL KONDISI OPERASI)
      * kotak_acak      — undian seragam dalam rentang per-fitur; sah menurut
                          `within_bounds` tapi sering tak masuk akal secara
                          fisik → memperlihatkan batas guard kotak (doc 14 C3)
      * ekstrapolasi    — kotak dilebarkan `expand` (default 25%) ke luar
                          rentang latih

    Metrik dilaporkan sebagai galat ABSOLUT dan NMAE (galat ÷ rentang target di
    data latih). MAPE sengaja TIDAK dijadikan metrik utama: pada target yang
    bisa mendekati nol ia meledak dan menyesatkan (terbukti: satu titik dengan
    fisika −605 menghasilkan "MAPE 845%" padahal itu titik uji yang rusak).

    Juga mengukur waktu per evaluasi kedua jalur — dasar klaim kecepatan yang
    boleh dipakai di pitch (JANGAN mengarang angka speedup).
    """
    from src.data.adapters import load_clean

    bounds = predict.meta("recovery_pct").get("bounds", {})
    bounds = {f: tuple(map(float, b)) for f, b in bounds.items()
              if f in schema.FEATURES}
    rng = np.random.default_rng(seed)
    df = load_clean()
    rentang = {t: float(df[t].max() - df[t].min()) for t in SHARED_TARGETS
               if t in df.columns}

    populasi = {
        "perturbasi_data": _sample_perturbasi(rng, df, n),
        "kotak_acak": _sample_box(rng, bounds, n),
        "ekstrapolasi": _sample_box(rng, bounds, n, expand=expand),
    }

    hasil: dict[str, dict] = {}
    for nama, titik_titik in populasi.items():
        errs: dict[str, list[float]] = {t: [] for t in SHARED_TARGETS}
        n_buruk = 0
        for point in titik_titik:
            comp = {c: point[c] for c in schema.INPUTS}
            knobs = {c: point[c] for c in schema.KNOBS}
            ph = physics_targets(comp, knobs)
            if not _fisika_masuk_akal(ph):
                n_buruk += 1
                continue
            ml = predict.predict_one(comp, knobs)
            for t in SHARED_TARGETS:
                if t in ml and t in ph:
                    errs[t].append(abs(ml[t] - ph[t]))
        hasil[nama] = {
            "n_dipakai": len(titik_titik) - n_buruk,
            "n_tak_masuk_akal": n_buruk,
            "per_target": {
                t: {
                    "abs_median": round(float(np.median(v)), 4),
                    "abs_p95": round(float(np.percentile(v, 95)), 4),
                    "abs_max": round(float(np.max(v)), 4),
                    "nmae_median_pct": round(
                        float(np.median(v)) / max(rentang.get(t, 1.0), 1e-9) * 100, 3),
                    "nmae_p95_pct": round(
                        float(np.percentile(v, 95)) / max(rentang.get(t, 1.0), 1e-9) * 100, 3),
                }
                for t, v in errs.items() if v
            },
        }

    # kecepatan: fisika satu-satu vs ML batch (cara pakai sebenarnya di optimizer)
    titik = _sample_perturbasi(rng, df, 1)[0]
    comp = {c: titik[c] for c in schema.INPUTS}
    knobs = {c: titik[c] for c in schema.KNOBS}

    t0 = time.perf_counter()
    for _ in range(200):
        physics_targets(comp, knobs)
    fisika_us = (time.perf_counter() - t0) / 200 * 1e6

    import pandas as pd
    kdf = pd.DataFrame([knobs] * 2000)
    X = predict.frame(comp, kdf)
    predict.predict_frame(X)  # pemanasan (muat model)
    t0 = time.perf_counter()
    predict.predict_frame(X)
    ml_us = (time.perf_counter() - t0) / 2000 * 1e6

    return {
        "n_sampel": n,
        "expand_ekstrapolasi": expand,
        "rentang_target": rentang,
        "galat": hasil,
        "kecepatan": {
            "fisika_us_per_eval": round(fisika_us, 1),
            "ml_us_per_eval_batch": round(ml_us, 2),
            "speedup": round(fisika_us / max(ml_us, 1e-9), 1),
        },
    }


def _cli() -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Uji fidelitas surrogate vs fisika")
    ap.add_argument("-n", type=int, default=200, help="jumlah sampel per populasi")
    ap.add_argument("--json", action="store_true", help="keluarkan JSON mentah")
    args = ap.parse_args()

    rep = fidelity(n=args.n)
    if args.json:
        print(json.dumps(rep, indent=2))
        return

    judul = {
        "perturbasi_data": "baris nyata digoyang +-5%, komposisi tetap 100%",
        "kotak_acak": "undian dalam rentang per-fitur (uji tekan)",
        "ekstrapolasi": f"kotak dilebarkan +{rep['expand_ekstrapolasi']:.0%}",
    }
    print(f"Fidelitas surrogate vs neraca massa ({rep['n_sampel']} sampel/populasi)")
    print("NMAE = galat absolut dibagi rentang target di data latih.")
    for populasi, blok in rep["galat"].items():
        print(f"\n  {populasi} ({judul.get(populasi, '')}) "
              f"- dipakai {blok['n_dipakai']}, dibuang tak-masuk-akal "
              f"{blok['n_tak_masuk_akal']}:")
        for t, m in blok["per_target"].items():
            print(f"    {schema.label(t):26s} NMAE median {m['nmae_median_pct']:6.3f}%  "
                  f"p95 {m['nmae_p95_pct']:7.3f}%   (abs median {m['abs_median']:.3f})")
    k = rep["kecepatan"]
    print(f"\n  kecepatan: fisika {k['fisika_us_per_eval']} us/eval vs "
          f"ML {k['ml_us_per_eval_batch']} us/eval (batch) -> {k['speedup']}x")


if __name__ == "__main__":
    _cli()
