"""Validasi kualitas DataFrame kanonik sebelum dipakai model/dashboard."""

from __future__ import annotations

import pandas as pd

from src import schema


def validate(df: pd.DataFrame) -> dict:
    """Laporan kualitas. `ok=False` berarti data TIDAK layak umpan model."""
    issues: list[str] = []

    missing = [c for c in schema.FEATURES + ["recovery_pct", "total_opex"] if c not in df.columns]
    if missing:
        issues.append(f"kolom wajib hilang: {missing}")

    nan_cols = {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()}
    model_nan = {c: n for c, n in nan_cols.items() if c in schema.FEATURES or c in schema.TARGETS}
    if model_nan:
        issues.append(f"NaN di kolom model: {model_nan}")

    out_of_range: dict[str, int] = {}
    for col, (lo, hi) in schema.PHYSICAL_RANGES.items():
        if col in df.columns:
            n = int(((df[col] < lo) | (df[col] > hi)).sum())
            if n:
                out_of_range[col] = n
    if out_of_range:
        issues.append(f"nilai di luar rentang fisik: {out_of_range}")

    return {
        "ok": not issues,
        "rows": len(df),
        "issues": issues,
        "nan_counts": nan_cols,
    }
