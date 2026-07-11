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
          weights: tuple[float, float, float] = (0.5, 0.3, 0.2)) -> dict:
    comp = predict.composition_of(row)
    knobs = predict.knobs_of(row)
    pred_now = predict.predict_one(comp, knobs)

    pf = pareto.pareto(comp, gen=25, pop=40)          # cepat untuk per-tick
    reco = pareto.pick(pf, *weights)
    reco_knobs = {k: float(reco[k]) for k in schema.KNOBS}

    model, _ = registry.load("surrogate_recovery_pct")
    factors = explain.top_factors(
        "surrogate_recovery_pct", model, predict.frame(comp, knobs)
    )

    return {
        "composition": comp,
        "knobs_now": knobs,
        "actual": {t: float(row[t]) for t in predict.TARGETS if t in row},
        "predicted_now": pred_now,
        "recommended_knobs": reco_knobs,
        "predicted_if_followed": {
            t: float(reco[t]) for t in predict.TARGETS if t in reco
        },
        "delta_if_followed": {
            t: float(reco[t]) - pred_now[t] for t in predict.TARGETS if t in reco
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
