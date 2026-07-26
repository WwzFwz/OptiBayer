"""Goal-seek: "target recovery >= X%, cari setpoint ter-murah" (doc 03 mode 2)."""

from __future__ import annotations

import numpy as np
from scipy.optimize import differential_evolution

from src import schema
from src.models import predict
from src.optimize.pareto import guardrail_bounds


def cheapest_for_recovery(composition: dict, target_recovery: float,
                          seed: int = 42) -> dict | None:
    """Setpoint OPEX-minimum dengan recovery >= target. None kalau tak tercapai."""
    b = guardrail_bounds()
    bounds = [b[k] for k in schema.KNOBS]

    def objective(x: np.ndarray) -> float:
        knobs = dict(zip(schema.KNOBS, x, strict=False))
        p = predict.predict_one(composition, knobs)
        penalty = max(target_recovery - p["recovery_pct"], 0.0) * 1e4
        return p["total_opex"] + penalty

    res = differential_evolution(
        objective, bounds, seed=seed, maxiter=60, popsize=12, tol=1e-6, polish=True
    )
    knobs = dict(zip(schema.KNOBS, [float(v) for v in res.x], strict=False))
    pred = predict.predict_one(composition, knobs)
    if pred["recovery_pct"] < target_recovery - 0.25:  # toleransi kecil
        return None
    return {"knobs": knobs, "prediction": pred}
