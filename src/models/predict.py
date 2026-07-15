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
