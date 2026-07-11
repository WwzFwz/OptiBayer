"""Training CLI (M1, doc 11).

    python -m src.models.train --data data/raw/data.csv

Melatih surrogate LightGBM untuk semua target yang capability-nya ON,
5-fold CV, simpan artefak + metadata ke registry, tulis models/metrics.json.
Ganti dataset = ganti --data (arsitektur data-agnostic, doc 09).
"""

from __future__ import annotations

import argparse
import json

import numpy as np
from lightgbm import LGBMRegressor
from sklearn.model_selection import KFold, cross_val_predict

from src import capability, schema
from src.data.adapters import load_clean
from src.data.validate import validate
from src.models import registry

TARGETS_ALL = ["recovery_pct", "total_opex", "red_mud_t", "precip_yield_pct"]

LGBM_PARAMS = dict(
    n_estimators=500,
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=10,
    random_state=42,
    verbosity=-1,
)


def train_all(data_path: str = "data/raw/data.csv") -> dict:
    df = load_clean(data_path)
    report = validate(df)
    if not report["ok"]:
        raise SystemExit(f"Data tidak lolos validasi: {report['issues']}")

    caps = capability.detect(df)
    if not caps["surrogate"]:
        raise SystemExit("Capability 'surrogate' OFF — kolom inti tidak bervariasi.")

    X = df[schema.FEATURES]
    dhash = registry.data_hash(df)
    bounds = {c: [float(df[c].min()), float(df[c].max())] for c in schema.FEATURES}

    targets = [t for t in TARGETS_ALL if t != "precip_yield_pct" or caps["precip_yield_model"]]
    all_metrics = {}
    for target in targets:
        y = df[target]
        model = LGBMRegressor(**LGBM_PARAMS)
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        pred = cross_val_predict(model, X, y, cv=cv)
        resid = y - pred
        metrics = {
            "cv_r2": float(1 - (resid**2).sum() / ((y - y.mean()) ** 2).sum()),
            "cv_mae": float(resid.abs().mean()),
            "cv_resid_std": float(resid.std()),  # dipakai deteksi anomali (replay)
            "n_rows": len(df),
        }
        model.fit(X, y)
        registry.save(
            f"surrogate_{target}", model,
            features=schema.FEATURES, bounds=bounds, metrics=metrics, dhash=dhash,
        )
        all_metrics[target] = metrics
        print(f"{target:18s} R2={metrics['cv_r2']:.4f} MAE={metrics['cv_mae']:.4f}")

    (registry.MODELS_DIR / "metrics.json").write_text(
        json.dumps({"data_hash": dhash, "targets": all_metrics}, indent=2),
        encoding="utf-8",
    )
    return all_metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/data.csv")
    args = ap.parse_args()
    train_all(args.data)
