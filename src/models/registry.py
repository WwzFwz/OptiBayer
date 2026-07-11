"""Model registry (P5, doc 09): artefak + metadata, app tidak pernah menebak."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


def data_hash(df: pd.DataFrame) -> str:
    return hashlib.md5(
        pd.util.hash_pandas_object(df, index=False).values.tobytes()
    ).hexdigest()[:12]


def save(name: str, model, *, features: list[str], bounds: dict, metrics: dict,
         dhash: str, extra: dict | None = None) -> None:
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODELS_DIR / f"{name}.joblib")
    meta = {
        "name": name,
        "features": features,
        "bounds": bounds,
        "metrics": metrics,
        "data_hash": dhash,
        **(extra or {}),
    }
    (MODELS_DIR / f"{name}.meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )


def load(name: str):
    model = joblib.load(MODELS_DIR / f"{name}.joblib")
    meta = json.loads((MODELS_DIR / f"{name}.meta.json").read_text(encoding="utf-8"))
    return model, meta


def available() -> list[str]:
    if not MODELS_DIR.exists():
        return []
    return sorted(p.stem for p in MODELS_DIR.glob("*.joblib"))
