"""Perakit konteks advisory: SATU JSON berisi semua angka ber-grounding.

LLM (kalau dipakai) hanya membahasakan isi konteks ini — tidak pernah mengarang
angka sendiri (doc 07 keamanan LLM).
"""

from __future__ import annotations

import pandas as pd

from src import schema
from src.models import explain, predict, registry
from src.optimize import pareto
from src.physics import carbonation, na_balance

SILIKA_WARNING = 5.5
SILIKA_CRITICAL = 6.3


def build(row: pd.Series, history: pd.DataFrame | None = None,
          weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
          fast: bool = False) -> dict:
    """Konteks advisory satu jam operasi.

    fast=True (dipakai saat mode Play): LEWATI optimizer NSGA-II & SHAP —
    tick jadi ~20x lebih ringan; rekomendasi = setpoint saat ini (delta 0)
    dan kartu advisory menampilkan ajakan Pause utk analisis penuh. Analisis
    dalam memang dilakukan saat berhenti — meniru ritme operator nyata.
    """
    comp = predict.composition_of(row)
    knobs = predict.knobs_of(row)
    pred_now = predict.predict_one(comp, knobs)

    if fast:
        reco_knobs = dict(knobs)
        reco = dict(pred_now)
        factors: list = []
    else:
        pf = pareto.pareto(comp, gen=25, pop=40)      # cepat untuk per-tick
        picked = pareto.pick(pf, *weights)
        reco_knobs = {k: float(picked[k]) for k in schema.KNOBS}
        reco = {t: float(picked[t]) for t in predict.TARGETS if t in picked}
        model, _ = registry.load("surrogate_recovery_pct")
        factors = explain.top_factors(
            "surrogate_recovery_pct", model, predict.frame(comp, knobs)
        )

    return {
        "fast": fast,
        "composition": comp,
        "knobs_now": knobs,
        "actual": {t: float(row[t]) for t in predict.TARGETS if t in row},
        "predicted_now": pred_now,
        "recommended_knobs": reco_knobs,
        "predicted_if_followed": {t: float(v) for t, v in reco.items()},
        "delta_if_followed": {
            t: float(v) - pred_now[t] for t, v in reco.items()
        },
        "shap_factors": factors,
        "na_balance": na_balance.breakdown(row),
        "cao_advisory": na_balance.cao_advisory(row),
        "carbonation": carbonation.assess(float(row["red_mud_t"])).__dict__,
        "anomaly_recovery": predict.anomaly(
            "recovery_pct", float(row["recovery_pct"]), pred_now["recovery_pct"]
        ),
        "silika_level": (
            "critical" if row["reactive_sio2_pct"] >= SILIKA_CRITICAL
            else "warning" if row["reactive_sio2_pct"] >= SILIKA_WARNING
            else "normal"
        ),
    }
