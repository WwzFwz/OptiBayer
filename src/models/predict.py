"""API prediksi model surrogate (P5, doc 09) — satu-satunya pintu ke model ML.

Semua modul lain (views, optimize/, advisory/) HANYA memanggil fungsi di sini,
tidak pernah membuka `models/*.joblib` langsung. Ini membuat model bisa
diganti/di-retrain tanpa menyentuh kode pemanggil (kontrak P5, doc 09).

Fungsi inti:
- `composition_of(row)` / `knobs_of(row)`   -> ekstrak dict dari baris data
- `frame(composition, knobs)`               -> susun DataFrame fitur (schema.FEATURES)
- `predict_frame(X)`                        -> prediksi banyak baris sekaligus
- `predict_one(composition, knobs)`         -> prediksi satu titik operasi (dict)
- `meta(target)`                            -> metadata model (fitur/bounds/metrik)
- `anomaly(target, actual, predicted)`      -> deteksi anomali (>3x resid_std CV)
- `within_bounds(composition, knobs)`       -> cek ekstrapolasi di luar data latih
- `interval(target, value, level)`          -> interval konformal (doc 14 C1)
- `predict_one_interval(comp, knobs)`       -> prediksi + interval sekaligus
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import schema
from src.models import registry

# role: schema.TARGETS statis (BUKAN difilter oleh registry.available() saat
# import) supaya tidak "membeku kosong" kalau modul ini ter-import sebelum
# training pertama selesai (lihat app/main.py: import views -> import modul
# ini -> baru training-jika-kosong dijalankan). predict_frame/predict_one
# menangani model yang belum ada dengan aman (lewat _get, di bawah).
TARGETS: list[str] = list(schema.TARGETS)

_MODEL_CACHE: dict[str, tuple] = {}


def clear_cache() -> None:
    """Bersihkan cache model in-memory (dipanggil setelah retrain)."""
    _MODEL_CACHE.clear()


def _get(target: str):
    if target not in _MODEL_CACHE:
        _MODEL_CACHE[target] = registry.load(f"surrogate_{target}")
    return _MODEL_CACHE[target]


def available_targets() -> list[str]:
    """Target yang modelnya benar-benar ada di registry saat ini."""
    have = set(registry.available())
    return [t for t in TARGETS if f"surrogate_{t}" in have]


def composition_of(row) -> dict[str, float]:
    """Ekstrak 10 komposisi bauksit (schema.INPUTS) dari satu baris/Series."""
    return {c: float(row[c]) for c in schema.INPUTS}


def knobs_of(row) -> dict[str, float]:
    """Ekstrak 5 parameter proses (schema.KNOBS) dari satu baris/Series."""
    return {c: float(row[c]) for c in schema.KNOBS}


def frame(composition: dict[str, float], knobs) -> pd.DataFrame:
    """Susun DataFrame fitur (kolom = schema.FEATURES) dari komposisi + knob.

    `knobs` boleh dict (-> 1 baris) atau DataFrame berkolom schema.KNOBS
    (-> banyak baris, komposisi di-broadcast sama utk semua baris — dipakai
    optimizer/regret utk menguji banyak kombinasi parameter pada komposisi
    bauksit yang sama).
    """
    if isinstance(knobs, pd.DataFrame):
        n = len(knobs)
        idx = knobs.index
        data = {c: np.full(n, float(composition[c]), dtype=float) for c in schema.INPUTS}
        out = pd.DataFrame(data, index=idx)
        for c in schema.KNOBS:
            out[c] = pd.to_numeric(knobs[c], errors="coerce").to_numpy(dtype=float)
        return out[list(schema.FEATURES)]

    row = {c: float(composition[c]) for c in schema.INPUTS}
    row.update({c: float(knobs[c]) for c in schema.KNOBS})
    return pd.DataFrame([row], columns=list(schema.FEATURES))


def predict_frame(X: pd.DataFrame) -> pd.DataFrame:
    """Prediksi semua target yang modelnya tersedia utk setiap baris di X.

    X harus memuat (minimal) kolom schema.FEATURES. Mengembalikan DataFrame
    HANYA berisi kolom target (recovery_pct, total_opex, red_mud_t,
    precip_yield_pct — sesuai yang tersedia), index sama dengan X, TANPA
    ikut menyalin kolom fitur X (supaya aman di-`pd.concat` dengan knobs/X
    lain tanpa duplikasi nama kolom — lihat src/optimize/pareto.py & regret.py).
    """
    Xf = X[list(schema.FEATURES)]
    out = pd.DataFrame(index=X.index)
    for target in TARGETS:
        try:
            model, _ = _get(target)
        except FileNotFoundError:
            continue
        out[target] = model.predict(Xf)
    return out


def predict_one(composition: dict[str, float], knobs: dict[str, float]) -> dict[str, float]:
    """Prediksi satu titik operasi -> dict {target: nilai}."""
    X = frame(composition, knobs)
    pred = predict_frame(X)
    return {c: float(pred.iloc[0][c]) for c in pred.columns}


def meta(target: str = "recovery_pct") -> dict:
    """Metadata model (features/bounds/metrics/data_hash) — default recovery_pct
    karena semua target dilatih dari X yang identik (bounds sama utk semua)."""
    _, m = _get(target)
    return m


def anomaly(target: str, actual: float, predicted: float, k: float = 3.0) -> bool:
    """True bila |actual-predicted| melebihi k x simpangan residual CV model.

    Ambang default k=3 (doc 11: "selisih melebihi 3x simpangan residual
    validasi silang model").
    """
    try:
        _, m = _get(target)
    except FileNotFoundError:
        return False
    resid_std = float(m.get("metrics", {}).get("cv_resid_std", 0.0))
    if resid_std <= 0:
        return False
    return abs(actual - predicted) > k * resid_std


DEFAULT_LEVEL = 0.90


def halfwidth(target: str, level: float = DEFAULT_LEVEL) -> float | None:
    """Setengah-lebar interval konformal target (None kalau model belum punya).

    Model lama (dilatih sebelum fitur ini) tidak punya blok `conformal` di
    metadata -> kembalikan None supaya pemanggil bisa diam-diam menyembunyikan
    interval alih-alih menampilkan angka palsu.
    """
    try:
        _, m = _get(target)
    except FileNotFoundError:
        return None
    conf = m.get("metrics", {}).get("conformal")
    if not conf:
        return None
    entry = conf.get(f"{level:.2f}")
    if entry is None:  # level tak tersedia -> ambil level terdekat
        try:
            key = min(conf, key=lambda k: abs(float(k) - level))
        except ValueError:
            return None
        entry = conf[key]
    q = float(entry.get("q", 0.0))
    return q if q > 0 else None


def interval(target: str, value: float, level: float = DEFAULT_LEVEL) -> dict | None:
    """Interval konformal di sekitar satu prediksi.

    Returns {"lo","hi","half","level","coverage"} atau None bila model belum
    punya kuantil konformal. `value` adalah prediksi titik dari model yang sama.
    """
    half = halfwidth(target, level)
    if half is None:
        return None
    _, m = _get(target)
    conf = m["metrics"]["conformal"]
    key = f"{level:.2f}" if f"{level:.2f}" in conf else min(
        conf, key=lambda k: abs(float(k) - level))
    lo, hi = value - half, value + half
    # jepit ke rentang fisik yang masuk akal (persentase tak bisa >100 / <0)
    phys = schema.PHYSICAL_RANGES.get(target)
    if phys:
        lo, hi = max(lo, phys[0]), min(hi, phys[1])
    return {
        "lo": float(lo), "hi": float(hi), "half": float(half),
        "level": float(key),
        "coverage": float(conf[key].get("coverage_empiris", 0.0)),
    }


def predict_one_interval(composition: dict[str, float], knobs: dict[str, float],
                         level: float = DEFAULT_LEVEL) -> dict[str, dict]:
    """Prediksi satu titik operasi + interval konformal per target.

    -> {target: {"value": float, "interval": {...} | None}}
    """
    point = predict_one(composition, knobs)
    return {t: {"value": v, "interval": interval(t, v, level)}
            for t, v in point.items()}


def within_bounds(composition: dict[str, float], knobs: dict[str, float],
                   target: str = "recovery_pct") -> dict[str, bool]:
    """Cek tiap fitur (komposisi+knob) terhadap rentang data latih model.

    False berarti nilai tsb EKSTRAPOLASI di luar apa yang pernah dilihat
    model saat dilatih — prediksi pada titik itu kurang bisa dipercaya.
    Dipakai UI "Prediction Analysis" utk memperingatkan operator (doc 14,
    item C3: guardrail out-of-domain utk input manual).
    """
    bounds = meta(target).get("bounds", {})
    values = {**composition, **knobs}
    result = {}
    for feat in schema.FEATURES:
        if feat not in bounds or feat not in values:
            continue
        lo, hi = bounds[feat]
        result[feat] = lo <= values[feat] <= hi
    return result


# Jumlah oksida komposisi bauksit harus mendekati 100%. Terukur pada data
# latih: 99.97–100.02%. Toleransi dilonggarkan ke ±0.5 pp supaya input manual
# operator (pembulatan assay lab) tidak diprotes tanpa alasan.
KOMPOSISI_TOTAL_TOL = 0.5


def ood_report(composition: dict[str, float], knobs: dict[str, float],
               target: str = "recovery_pct") -> dict:
    """Ringkasan out-of-distribution: aman/tidak + fitur mana & seberapa jauh.

    Dua lapis pemeriksaan, keduanya berdasar pengukuran (lihat
    src/models/verify.py):

    1. EKSTRAPOLASI kotak — fitur di luar rentang data latih. Terbukti
       menaikkan galat surrogate vs fisika: NMAE recovery median 1.7% -> 3.4%,
       p95 4.4% -> 23.8% saat kotak dilebarkan 25%.
    2. PLAUSIBILITAS FISIK — jumlah oksida menyimpang dari 100%. Titik seperti
       ini lolos pemeriksaan (1) per fitur tapi bisa membuat kalkulator neraca
       massa sendiri mengeluarkan nilai mustahil (mis. OPEX negatif), jadi
       prediksi di sana tidak berarti apa-apa.

    Dipakai optimizer (jangan merekomendasikan setpoint di daerah yang tak
    pernah dilihat model) dan kartu advisory, bukan hanya layar Lab.
    """
    bounds = meta(target).get("bounds", {})
    values = {**composition, **knobs}
    offenders = []
    for feat in schema.FEATURES:
        if feat not in bounds or feat not in values:
            continue
        lo, hi = bounds[feat]
        v = float(values[feat])
        if v < lo or v > hi:
            span = max(hi - lo, 1e-9)
            jarak = (lo - v if v < lo else v - hi) / span
            offenders.append({
                "feature": feat, "label": schema.label(feat), "value": v,
                "lo": float(lo), "hi": float(hi),
                "keluar_frac": round(float(jarak), 4),
            })
    offenders.sort(key=lambda o: o["keluar_frac"], reverse=True)

    total_komposisi = sum(float(composition.get(c, 0.0)) for c in schema.INPUTS)
    komposisi_wajar = abs(total_komposisi - 100.0) <= KOMPOSISI_TOTAL_TOL

    return {
        "ok": not offenders and komposisi_wajar,
        "n_out": len(offenders),
        "offenders": offenders,
        "labels": [o["label"] for o in offenders],
        "komposisi_total_pct": round(total_komposisi, 3),
        "komposisi_wajar": komposisi_wajar,
        "alasan": (
            [] if not offenders else
            [f"{len(offenders)} fitur di luar rentang data latih"]
        ) + (
            [] if komposisi_wajar else
            [f"jumlah oksida {total_komposisi:.2f}% (seharusnya ~100%)"]
        ),
    }
