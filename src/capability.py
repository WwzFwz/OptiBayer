"""Capability detection (P3, doc 09).

Fitur app menyala/mati otomatis berdasarkan kolom yang TERSEDIA dan BERVARIASI
di data. Contoh: data sintesis punya `causticity` tapi konstan -> soft sensor
causticity OFF; kalau data asli tahap 2 memvariasikannya -> otomatis ON.
"""

from __future__ import annotations

import pandas as pd

from src import schema


def _varies(df: pd.DataFrame, col: str, min_unique: int = 5) -> bool:
    return (
        col in df.columns
        and df[col].notna().any()
        and df[col].nunique(dropna=True) >= min_unique
    )


def detect(df: pd.DataFrame) -> dict[str, bool]:
    surrogate_core = all(_varies(df, c) for c in schema.INPUTS + schema.KNOBS) and all(
        _varies(df, t) for t in ("recovery_pct", "total_opex", "red_mud_t")
    )
    return {
        # model & optimizer inti
        "surrogate": surrogate_core,
        "precip_yield_model": _varies(df, "precip_yield_pct"),
        "optimizer": surrogate_core,
        # fitur yang menunggu data bervariasi (doc 06 Bag. 6)
        "soft_sensor_causticity": _varies(df, "causticity"),
        "mud_washing_knob": _varies(df, "wash_water_ratio") and _varies(df, "wash_eff"),
        "carbonation_soft_sensor": _varies(df, "naoh_carbonation_frac"),
        # kalkulator fisika: selalu ON (tidak butuh data training)
        "physics_carbonation": True,
        "physics_ceq": True,
        "physics_na_balance": "naoh_consumed_t" in df.columns,
        # penyajian
        "sankey_na": all(
            c in df.columns for c in ("naoh_consumed_t", "naoh_makeup_t", "red_mud_t")
        ),
        "sankey_al": all(
            c in df.columns
            for c in ("al_feed_t", "hydrate_t", "al_lost_redmud_t", "al_recycled_t")
        ),
        "replay": len(df) > 10,
    }


def summary(caps: dict[str, bool]) -> str:
    on = sorted(k for k, v in caps.items() if v)
    off = sorted(k for k, v in caps.items() if not v)
    return f"ON: {', '.join(on)}\nOFF: {', '.join(off) or '-'}"
