"""Pipeline pelatihan model surrogate (P4, doc 09/11).

Untuk setiap target di `schema.TARGETS` (recovery_pct, total_opex, red_mud_t,
precip_yield_pct):

1. Susun fitur X = df[schema.FEATURES] (10 komposisi + 5 parameter proses,
   TANPA kolom intermediate — anti data-leakage, lihat schema.py) dan y = target.
2. ADU beberapa keluarga model (FAMILIES) dengan fold yang sama; pemenangnya
   MAE cross-validation terkecil di antara yang lolos anggaran kecepatan.
   Skor semua pesaing disimpan supaya keputusannya bisa diaudit (doc 14 C2,
   bukti di docs/21).
3. Kuantil KONFORMAL dari residual out-of-fold -> interval prediksi bergaransi
   cakupan (doc 14 C1), dipakai src.models.predict.interval().
4. Latih model final di seluruh data, simpan lewat src.models.registry.save().
5. Tulis models/metrics.json gabungan (dibaca README & endpoint /v1/model/health).

CLI:
    python -m src.models.train --data data/raw/data.csv --splits 5

Dipanggil juga saat build image Docker, supaya permintaan pertama tidak
menunggu pelatihan.
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
LGBM_PARAMS: dict = {
    "n_estimators": 400,
    "learning_rate": 0.045,
    "max_depth": 5,
    "num_leaves": 24,
    "min_child_samples": 8,
    "subsample": 0.85,
    "subsample_freq": 1,
    "colsample_bytree": 0.85,
    "reg_lambda": 0.5,
    "random_state": 42,
    "verbosity": -1,
}


# Tingkat kepercayaan interval konformal yang dihitung & disimpan per target.
CONFORMAL_LEVELS: tuple[float, ...] = (0.80, 0.90, 0.95)

# Anggaran waktu prediksi: optimizer NSGA-II memanggil surrogate 2400x per
# jalan, jadi model yang lambat (mis. RandomForest ~30 us/baris) ditolak
# meskipun skornya bagus.
MAX_US_PER_PREDIKSI = 15.0

# Keluarga model yang diadu per target. Dulu LightGBM dipilih karena argumen;
# sekarang dipilih karena BUKTI validasi silang (doc 14 C2). Ternyata tidak ada
# satu pemenang tunggal: target yang berasal dari formula fisika yang mulus
# (recovery, red mud, yield) lebih cocok ke ridge-polinomial, sedangkan OPEX
# yang bertingkat lebih cocok ke gradient boosting. Lihat docs/21.
FAMILIES: dict[str, str] = {
    "lightgbm": "LightGBM (gradient boosting, pohon dangkal)",
    "ridge_poly2": "Ridge + interaksi polinomial derajat 2",
    "hist_gbdt": "HistGradientBoosting (scikit-learn)",
}


def _build(family: str):
    if family == "lightgbm":
        return LGBMRegressor(**LGBM_PARAMS)
    if family == "ridge_poly2":
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import PolynomialFeatures, StandardScaler

        return make_pipeline(
            StandardScaler(),
            PolynomialFeatures(degree=2, include_bias=False),
            Ridge(alpha=10.0),
        )
    if family == "hist_gbdt":
        from sklearn.ensemble import HistGradientBoostingRegressor

        return HistGradientBoostingRegressor(
            max_depth=5, learning_rate=0.045, max_iter=400, random_state=42)
    raise ValueError(f"keluarga model tak dikenal: {family}")


def _make_model(family: str = "lightgbm"):
    return _build(family)


def conformal_quantiles(residuals: np.ndarray,
                        levels: tuple[float, ...] = CONFORMAL_LEVELS) -> dict:
    """Kuantil konformal |residual| out-of-fold + cakupan empirisnya.

    Ini *cross-conformal* (skor nonkonformitas = |y - ŷ_out-of-fold|): interval
    ±q(level) menjaga cakupan mendekati `level` tanpa mengasumsikan bentuk
    distribusi galat. Koreksi sampel-hingga ceil((n+1)·level)/n dipakai supaya
    tidak optimistis di n kecil (Vovk et al.; MAPIE memakai skor yang sama).

    CATATAN KEJUJURAN: data latih saat ini adalah keluaran kalkulator neraca
    massa deterministik (lihat src/data/rebuild_targets.py), jadi residual di
    sini murni GALAT SURROGATE terhadap kalkulator — bukan ketidakpastian
    pabrik nyata. Begitu data historian masuk, fungsi ini tidak berubah tapi
    artinya naik kelas jadi ketidakpastian sesungguhnya.
    """
    absr = np.abs(np.asarray(residuals, dtype=float))
    n = len(absr)
    out: dict[str, dict] = {}
    for level in levels:
        if n < 2:
            q = float(absr.max()) if n else 0.0
        else:
            rank = min(1.0, np.ceil((n + 1) * level) / n)
            q = float(np.quantile(absr, rank, method="higher"))
        out[f"{level:.2f}"] = {
            "q": q,
            "coverage_empiris": float(np.mean(absr <= q)) if n else 0.0,
        }
    return out


def train_one(df: pd.DataFrame, target: str, n_splits: int = 5,
              random_state: int = 42, family: str | None = None) -> dict:
    """Latih satu target: pilih keluarga model, CV out-of-fold, fit final.

    `family=None` (default) berarti PILIH OTOMATIS: semua keluarga di FAMILIES
    diadu dengan fold yang sama, pemenangnya adalah MAE cross-validation
    terkecil di antara yang lolos anggaran kecepatan prediksi. Semua skor
    pesaing ikut disimpan di metadata supaya keputusannya bisa diaudit.
    """
    X = df[schema.FEATURES]
    y = df[target].to_numpy(dtype=float)
    n = len(y)

    n_splits_eff = max(2, min(n_splits, n))
    kf = KFold(n_splits=n_splits_eff, shuffle=True, random_state=random_state)

    kandidat = [family] if family else list(FAMILIES)
    seleksi: dict[str, dict] = {}
    for f in kandidat:
        model_f = _make_model(f)
        oof_f = cross_val_predict(model_f, X, y, cv=kf, n_jobs=1)
        t0 = time.perf_counter()
        model_f.fit(X, y)
        model_f.predict(X.head(min(200, len(X))))
        us = (time.perf_counter() - t0) / min(200, len(X)) * 1e6
        seleksi[f] = {
            "cv_r2": float(r2_score(y, oof_f)),
            "cv_mae": float(mean_absolute_error(y, oof_f)),
            "us_per_prediksi": float(us),
            "_oof": oof_f,
        }

    layak = {f: s for f, s in seleksi.items()
             if s["us_per_prediksi"] <= MAX_US_PER_PREDIKSI} or seleksi
    terpilih = min(layak, key=lambda f: layak[f]["cv_mae"])
    oof = seleksi[terpilih].pop("_oof")
    for s in seleksi.values():
        s.pop("_oof", None)

    resid = y - oof
    metrics = {
        "cv_r2": float(r2_score(y, oof)),
        "cv_mae": float(mean_absolute_error(y, oof)),
        "cv_resid_std": float(np.std(resid, ddof=1)) if n > 1 else 0.0,
        "n_rows": int(n),
        "n_splits": int(n_splits_eff),
        "conformal": conformal_quantiles(resid),
        "family": terpilih,
        "family_label": FAMILIES.get(terpilih, terpilih),
        "seleksi": {f: {k: round(v, 6) for k, v in s.items()}
                    for f, s in seleksi.items()},
    }

    final_model = _make_model(terpilih)
    final_model.fit(X, y)

    bounds = {c: (float(df[c].min()), float(df[c].max())) for c in schema.FEATURES}
    return {"model": final_model, "metrics": metrics, "bounds": bounds,
            "family": terpilih}


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
            extra={"family": result["family"]},
        )
        all_metrics[target] = result["metrics"]
        trained.append(target)
        if verbose:
            m = result["metrics"]
            c90 = m["conformal"]["0.90"]
            kalah = ", ".join(
                f"{f} MAE={s['cv_mae']:.4f}"
                for f, s in m["seleksi"].items() if f != m["family"]
            )
            print(
                f"[selesai] surrogate_{target}: {m['family']}  "
                f"R2={m['cv_r2']:.4f}  MAE={m['cv_mae']:.4f}  "
                f"n={m['n_rows']}  +-{c90['q']:.3f} @90% "
                f"(cakupan {c90['coverage_empiris']:.1%})"
            )
            if kalah:
                print(f"           dikalahkan: {kalah}")

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
