"""Prediktor terpadu: satu pintu untuk app, optimizer, dan regret meter.

Model dimuat sekali dari registry; prediksi selalu lewat DataFrame berkolom
schema.FEATURES supaya urutan fitur tidak pernah salah.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from src import schema
from src.models import registry

TARGETS = ["recovery_pct", "total_opex", "red_mud_t", "precip_yield_pct"]


@lru_cache(maxsize=None)
def _model(target: str):
    return registry.load(f"surrogate_{target}")


def meta(target: str = "recovery_pct") -> dict:
    return _model(target)[1]


def frame(composition: dict, knobs: pd.DataFrame | dict) -> pd.DataFrame:
    """Rakit matriks fitur: 1 komposisi x N kandidat knob."""
    if isinstance(knobs, dict):
        knobs = pd.DataFrame([knobs])
    X = pd.DataFrame(index=knobs.index)
    for c in schema.INPUTS:
        X[c] = composition[c]
    for c in schema.KNOBS:
        X[c] = knobs[c].values
    return X[schema.FEATURES]


def predict_frame(X: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=X.index)
    for t in TARGETS:
        try:
            model, _ = _model(t)
        except FileNotFoundError:
            continue
        out[t] = model.predict(X)
    return out


def predict_one(composition: dict, knobs: dict) -> dict:
    return predict_frame(frame(composition, knobs)).iloc[0].to_dict()


def anomaly(target: str, actual: float, predicted: float, n_sigma: float = 3.0) -> bool:
    """Deteksi anomali residual: |aktual - prediksi| > n_sigma x std residual CV."""
    resid_std = _model(target)[1]["metrics"]["cv_resid_std"]
    return abs(actual - predicted) > n_sigma * resid_std


def composition_of(row: pd.Series) -> dict:
    return {c: float(row[c]) for c in schema.INPUTS}


def knobs_of(row: pd.Series) -> dict:
    return {c: float(row[c]) for c in schema.KNOBS}
