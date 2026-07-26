"""SHAP explainability: global (slide) + per-prediksi (kartu advisory).

AGNOSTIK KELUARGA MODEL. Sejak pemilihan model dilakukan per target lewat
bukti CV (lihat src/models/benchmark.py & train.py), surrogate tidak selalu
berupa pohon: `recovery_pct` misalnya dimenangkan pipeline ridge-polinomial.
`shap.TreeExplainer` hanya sah untuk model pohon, jadi di sini dipilih
otomatis:

  * model pohon (LightGBM/HistGB/RandomForest) -> TreeExplainer (eksak & cepat)
  * model lain (pipeline linear/poly, dll)     -> PermutationExplainer atas
    fungsi predict, dengan latar belakang ringkas dari data latih

Keduanya menghasilkan bentuk keluaran yang sama, sehingga context.py & kartu
advisory tidak perlu tahu keluarga model apa yang sedang dipakai.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from src import schema

_explainers: dict[str, object] = {}

# Jumlah baris latar belakang untuk explainer agnostik. Kecil disengaja:
# PermutationExplainer dipanggil di jalur advisory per jam, jadi biaya harus
# tetap milidetik. 40 baris sudah stabil untuk 15 fitur.
_N_LATAR = 40


def _is_tree(model) -> bool:
    """Deteksi model pohon tanpa mengimpor tiap pustaka secara paksa."""
    nama = type(model).__name__.lower()
    return any(k in nama for k in (
        "lgbm", "lightgbm", "xgb", "catboost",
        "forest", "tree", "gradientboosting", "histgradient",
    ))


def _latar(X: pd.DataFrame) -> pd.DataFrame:
    if len(X) <= _N_LATAR:
        return X
    return X.sample(_N_LATAR, random_state=0)


def _explainer(name: str, model, X: pd.DataFrame | None = None):
    """Explainer ter-cache untuk sebuah model, sesuai keluarganya."""
    if name in _explainers:
        return _explainers[name]

    if _is_tree(model):
        exp = shap.TreeExplainer(model)
    else:
        if X is None or X.empty:
            raise ValueError(
                "explainer agnostik butuh contoh data latar (parameter X)")
        exp = shap.PermutationExplainer(model.predict, _latar(X))
    _explainers[name] = exp
    return exp


def clear_cache() -> None:
    """Buang explainer ter-cache (dipanggil setelah model dilatih ulang)."""
    _explainers.clear()


def _nilai_shap(exp, X: pd.DataFrame) -> np.ndarray:
    """Ambil matriks SHAP (n_baris x n_fitur) dari explainer apa pun."""
    if isinstance(exp, shap.TreeExplainer):
        return np.asarray(exp.shap_values(X))
    return np.asarray(exp(X).values)


def global_importance(name: str, model, X: pd.DataFrame) -> pd.Series:
    """Rata-rata |SHAP| per fitur, urut menurun."""
    sv = _nilai_shap(_explainer(name, model, X), X)
    return (
        pd.Series(np.abs(sv).mean(axis=0), index=X.columns)
        .sort_values(ascending=False)
    )


def top_factors(name: str, model, row: pd.DataFrame, k: int = 3,
                background: pd.DataFrame | None = None) -> list[dict]:
    """Faktor SHAP terbesar untuk SATU prediksi — bahan kartu 'kenapa'.

    `background` hanya dipakai (dan hanya dibutuhkan) oleh model non-pohon;
    kalau tidak diberikan, data latih dimuat sekali dari adapters.
    """
    if background is None and not _is_tree(model) and name not in _explainers:
        from src.data.adapters import load_clean

        background = load_clean()[list(schema.FEATURES)]

    sv = _nilai_shap(_explainer(name, model, background), row)[0]
    order = np.argsort(-np.abs(sv))[:k]
    return [
        {
            "feature": row.columns[i],
            "label": schema.label(row.columns[i]),
            "value": float(row.iloc[0, i]),
            "shap": float(sv[i]),
            "direction": "menaikkan" if sv[i] > 0 else "menurunkan",
        }
        for i in order
    ]
