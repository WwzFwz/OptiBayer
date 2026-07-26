"""Benchmark keluarga model — menjawab "kenapa LightGBM?" dengan angka (doc 14 C2).

Sampai sekarang pilihan LightGBM hanya dibela dengan argumen. Modul ini
menjalankan validasi silang yang SAMA (5-fold, fitur sama, seed sama) untuk
beberapa kandidat, lalu melaporkan R², MAE, dan biaya waktu latih/prediksi.

Yang dibandingkan dan alasannya:
  * dummy_rata2   — penebak rerata; lantai dasar, memastikan R² lain bermakna
  * ridge         — linear beregularisasi; kalau ini menang, pohon berlebihan
  * ridge_poly2   — linear + interaksi derajat 2; menguji apakah non-linearitas
                    proses sudah cukup ditangkap fitur silang sederhana
  * random_forest — bagging pohon; pembanding klasik yang kuat & tahan setelan
  * hist_gbdt     — gradient boosting bawaan scikit-learn (tanpa dependensi tambahan)
  * lightgbm      — pilihan produksi saat ini

Pakai:
    python -m src.models.benchmark               # tabel markdown ke layar
    python -m src.models.benchmark --json        # JSON mentah
    python -m src.models.benchmark --out docs/benchmark.md
"""

from __future__ import annotations

import argparse
import json
import time

import numpy as np
from lightgbm import LGBMRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from src import schema
from src.data.adapters import load_clean
from src.models.train import LGBM_PARAMS


def kandidat() -> dict:
    """Model pembanding. Semua dipakai apa adanya — tanpa tuning berat, supaya
    perbandingannya jujur terhadap LightGBM yang juga tidak di-tuning berat."""
    return {
        "dummy_rata2": DummyRegressor(strategy="mean"),
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "ridge_poly2": make_pipeline(
            StandardScaler(),
            PolynomialFeatures(degree=2, include_bias=False),
            Ridge(alpha=10.0),
        ),
        "random_forest": RandomForestRegressor(
            n_estimators=300, max_depth=None, min_samples_leaf=2,
            random_state=42, n_jobs=1),
        "hist_gbdt": HistGradientBoostingRegressor(
            max_depth=5, learning_rate=0.045, max_iter=400, random_state=42),
        "lightgbm": LGBMRegressor(**LGBM_PARAMS),
    }


def jalankan(n_splits: int = 5, seed: int = 42, targets: list[str] | None = None) -> dict:
    df = load_clean()
    X = df[schema.FEATURES]
    targets = targets or list(schema.TARGETS)
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)

    hasil: dict[str, dict] = {}
    for target in targets:
        if target not in df.columns:
            continue
        y = df[target].to_numpy(dtype=float)
        per_model = {}
        for nama, model in kandidat().items():
            t0 = time.perf_counter()
            oof = cross_val_predict(model, X, y, cv=kf, n_jobs=1)
            waktu_cv = time.perf_counter() - t0

            m = model
            t0 = time.perf_counter()
            m.fit(X, y)
            waktu_fit = time.perf_counter() - t0

            t0 = time.perf_counter()
            m.predict(X)
            waktu_pred = (time.perf_counter() - t0) / len(X) * 1e6  # µs/baris

            per_model[nama] = {
                "cv_r2": round(float(r2_score(y, oof)), 5),
                "cv_mae": round(float(mean_absolute_error(y, oof)), 4),
                "detik_cv": round(waktu_cv, 2),
                "detik_fit": round(waktu_fit, 3),
                "us_per_prediksi": round(float(waktu_pred), 2),
            }
        hasil[target] = per_model
    return {"n_rows": len(df), "n_splits": n_splits, "hasil": hasil}


def _keluarga_terpasang(target: str) -> str | None:
    """Keluarga model yang BENAR-BENAR terpasang di registry untuk target ini.

    Dibaca dari artefak, bukan ditebak: sejak pemilihan dilakukan per target
    (train.train_one), menandai "lightgbm" secara harfiah di tabel akan
    menyesatkan pembaca.
    """
    try:
        from src.models import predict

        return predict.meta(target).get("metrics", {}).get("family")
    except Exception:
        return None


def tabel_markdown(rep: dict) -> str:
    baris = [
        "# Benchmark model surrogate (doc 14 C2)",
        "",
        f"Data {rep['n_rows']} baris · {rep['n_splits']}-fold CV · fitur & seed identik "
        "untuk semua kandidat.",
        "",
        "> Catatan penting: target di data ini dihasilkan ulang oleh kalkulator "
        "neraca massa deterministik, jadi angka R² mengukur seberapa setia sebuah "
        "model meniru KALKULATOR — bukan akurasi terhadap pabrik nyata (doc 14 A1).",
        "",
    ]
    for target, per_model in rep["hasil"].items():
        baris += [f"## {schema.label(target)} (`{target}`)", "",
                  "| Model | CV R² | CV MAE | Latih (dtk) | Prediksi (µs/baris) |",
                  "|---|---:|---:|---:|---:|"]
        urut = sorted(per_model.items(), key=lambda kv: -kv[1]["cv_r2"])
        dipakai = _keluarga_terpasang(target)
        for nama, m in urut:
            tanda = " **←dipakai**" if nama == dipakai else ""
            baris.append(
                f"| {nama}{tanda} | {m['cv_r2']:.4f} | {m['cv_mae']:.4f} | "
                f"{m['detik_fit']:.3f} | {m['us_per_prediksi']:.2f} |"
            )
        baris.append("")
    return "\n".join(baris)


def _cli() -> None:
    ap = argparse.ArgumentParser(description="Benchmark keluarga model surrogate")
    ap.add_argument("--splits", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="tulis tabel markdown ke berkas ini")
    args = ap.parse_args()

    rep = jalankan(n_splits=args.splits)
    if args.json:
        print(json.dumps(rep, indent=2))
        return

    md = tabel_markdown(rep)
    if args.out:
        from pathlib import Path

        Path(args.out).write_text(md, encoding="utf-8")
        print(f"tabel ditulis ke {args.out}")
    # ringkasan layar (ASCII saja — konsol Windows memakai cp1252)
    for target, per_model in rep["hasil"].items():
        urut = sorted(per_model.items(), key=lambda kv: -kv[1]["cv_r2"])
        juara = urut[0][0]
        lgbm = per_model.get("lightgbm", {})
        print(f"\n{target}: juara={juara}")
        for nama, m in urut:
            selisih = m["cv_r2"] - lgbm.get("cv_r2", np.nan)
            print(f"   {nama:16s} R2={m['cv_r2']:.5f} MAE={m['cv_mae']:10.4f} "
                  f"fit={m['detik_fit']:6.3f}s pred={m['us_per_prediksi']:6.2f}us "
                  f"(dR2 vs lgbm {selisih:+.5f})")


if __name__ == "__main__":
    _cli()
