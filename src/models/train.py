"""Pipeline pelatihan model surrogate LightGBM (P4, doc 09/11).

Untuk setiap target di `schema.TARGETS` (recovery_pct, total_opex, red_mud_t,
precip_yield_pct):

1. Susun fitur X = df[schema.FEATURES] (10 komposisi + 5 parameter proses,
   TANPA kolom intermediate — anti data-leakage, lihat schema.py) dan y = target.
2. 5-fold cross-validation (out-of-fold prediction) dengan LightGBM Regressor
   -> cv_r2, cv_mae, cv_resid_std (dipakai src.models.predict.anomaly()).
3. Latih model final di seluruh data, simpan lewat src.models.registry.save().
4. Tulis models/metrics.json gabungan (dibaca README/dashboard).

CLI:
    python -m src.models.train --data data/raw/data.csv --splits 5

Dipanggil juga langsung dari app/main.py saat registry kosong (auto-train
sekali di startup), dan dari UI "Latih Ulang Model" (app/views/prediction_lab.py).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict

from src import schema
from src.data.adapters import load_clean
from src.data.validate import validate
from src.models import registry

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "raw" / "data.csv"
MIN_ROWS_FOR_CV = 30

# Hyperparameter LightGBM — konservatif relatif thd ukuran data (~1000 baris,
# 15 fitur) supaya tidak overfit: pohon dangkal, jumlah daun kecil, subsample
# baris/kolom, dan L2 ringan.
LGBM_PARAMS: dict = dict(
    n_estimators=400,
    learning_rate=0.045,
    max_depth=5,
    num_leaves=24,
    min_child_samples=8,
    subsample=0.85,
    subsample_freq=1,
    colsample_bytree=0.85,
    reg_lambda=0.5,
    random_state=42,
    verbosity=-1,
)


def _make_model() -> LGBMRegressor:
    return LGBMRegressor(**LGBM_PARAMS)


def train_one(df: pd.DataFrame, target: str, n_splits: int = 5,
              random_state: int = 42) -> dict:
    """Latih satu target: CV out-of-fold utk metrik + fit final di semua data."""
    X = df[schema.FEATURES]
    y = df[target].to_numpy(dtype=float)
    n = len(y)

    n_splits_eff = max(2, min(n_splits, n))
    kf = KFold(n_splits=n_splits_eff, shuffle=True, random_state=random_state)
    oof = cross_val_predict(_make_model(), X, y, cv=kf, n_jobs=1)

    resid = y - oof
    metrics = {
        "cv_r2": float(r2_score(y, oof)),
        "cv_mae": float(mean_absolute_error(y, oof)),
        "cv_resid_std": float(np.std(resid, ddof=1)) if n > 1 else 0.0,
        "n_rows": int(n),
        "n_splits": int(n_splits_eff),
    }

    final_model = _make_model()
    final_model.fit(X, y)

    bounds = {c: (float(df[c].min()), float(df[c].max())) for c in schema.FEATURES}
    return {"model": final_model, "metrics": metrics, "bounds": bounds}


def train_all(data_path: str | Path = DEFAULT_DATA, n_splits: int = 5,
              verbose: bool = True) -> dict:
    """Latih surrogate utk semua target yang tersedia & bervariasi di data.

    Returns
    -------
    dict laporan: {"trained": [...], "skipped": [...], "data_hash": str,
    "rows": int, "metrics": {target: {...}}, "elapsed_sec": float}
    dipakai oleh UI ("Latih Ulang Model") utk menampilkan ringkasan hasil.
    """
    t0 = time.time()
    df = load_clean(data_path)

    report = validate(df)
    if not report["ok"]:
        raise ValueError(f"Data tidak lolos validasi kualitas: {report['issues']}")
    if len(df) < MIN_ROWS_FOR_CV:
        raise ValueError(
            f"Hanya {len(df)} baris valid (< {MIN_ROWS_FOR_CV}) — "
            "terlalu sedikit utk melatih model yang andal."
        )

    dhash = registry.data_hash(df)
    all_metrics: dict[str, dict] = {}
    trained: list[str] = []
    skipped: list[str] = []

    for target in schema.TARGETS:
        if target not in df.columns or df[target].nunique(dropna=True) < 5:
            skipped.append(target)
            if verbose:
                print(f"[lewati] {target}: kolom tidak tersedia / tidak bervariasi")
            continue

        result = train_one(df, target, n_splits=n_splits)
        registry.save(
            f"surrogate_{target}",
            result["model"],
            features=list(schema.FEATURES),
            bounds=result["bounds"],
            metrics=result["metrics"],
            dhash=dhash,
        )
        all_metrics[target] = result["metrics"]
        trained.append(target)
        if verbose:
            m = result["metrics"]
            print(
                f"[selesai] surrogate_{target}: "
                f"R²={m['cv_r2']:.4f}  MAE={m['cv_mae']:.4f}  "
                f"resid_std={m['cv_resid_std']:.4f}  n={m['n_rows']}"
            )

    registry.MODELS_DIR.mkdir(exist_ok=True)
    metrics_path = registry.MODELS_DIR / "metrics.json"
    metrics_path.write_text(
        json.dumps({"data_hash": dhash, "targets": all_metrics}, indent=2),
        encoding="utf-8",
    )

    # Bersihkan cache in-memory src.models.predict supaya model baru langsung
    # terpakai tanpa perlu restart proses (mis. setelah tombol "Latih Ulang").
    try:
        from src.models import predict as _predict
        _predict.clear_cache()
    except ImportError:
        pass

    elapsed = time.time() - t0
    if verbose:
        print(f"Selesai: {len(trained)} model dilatih dalam {elapsed:.1f} detik "
              f"({len(df)} baris, data_hash={dhash}).")

    return {
        "trained": trained,
        "skipped": skipped,
        "data_hash": dhash,
        "rows": len(df),
        "metrics": all_metrics,
        "elapsed_sec": round(elapsed, 2),
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Latih model surrogate LightGBM — OPtiBayer-AI Bayer Process Advisor"
    )
    parser.add_argument("--data", default=str(DEFAULT_DATA), help="path ke CSV mentah")
    parser.add_argument("--splits", type=int, default=5, help="jumlah fold cross-validation")
    parser.add_argument("--quiet", action="store_true", help="matikan log per-target")
    args = parser.parse_args()
    train_all(args.data, n_splits=args.splits, verbose=not args.quiet)


if __name__ == "__main__":
    _cli()
