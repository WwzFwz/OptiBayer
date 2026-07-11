"""SHAP explainability: global (slide) + per-prediksi (kartu advisory)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from src import schema

_explainers: dict[str, shap.TreeExplainer] = {}


def _explainer(name: str, model) -> shap.TreeExplainer:
    if name not in _explainers:
        _explainers[name] = shap.TreeExplainer(model)
    return _explainers[name]


def global_importance(name: str, model, X: pd.DataFrame) -> pd.Series:
    """Rata-rata |SHAP| per fitur, urut menurun."""
    sv = _explainer(name, model).shap_values(X)
    return (
        pd.Series(np.abs(sv).mean(axis=0), index=X.columns)
        .sort_values(ascending=False)
    )


def top_factors(name: str, model, row: pd.DataFrame, k: int = 3) -> list[dict]:
    """Faktor SHAP terbesar untuk SATU prediksi — bahan kartu 'kenapa'."""
    sv = _explainer(name, model).shap_values(row)[0]
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
