"""Optimizer multi-objektif NSGA-II (M2) — carbon-aware (I2, doc 12).

Diberi komposisi bauksit (given), cari setpoint 5 knob yang mengoptimalkan:
  max recovery, min NET OPEX, min red mud
NET OPEX = OPEX - nilai CO2 (red mud x 23 kg CO2/ton x harga karbon) ->
optimizer "melihat" nilai karbonasi red mud sebagai kredit (doc 12 I2).

Guardrail (doc 07): bounds = irisan rentang data training & amplop operasi aman.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from src import schema
from src.models import predict
from src.physics import carbonation

# Konversi harga karbon ke satuan OPEX data (asumsi USD): Rp30rb/t / ~Rp16rb per USD.
DEFAULT_CARBON_PRICE_OPEX = carbonation.CARBON_PRICE_IDR_PER_TON / 16_000.0


def guardrail_bounds() -> dict[str, tuple[float, float]]:
    trained = predict.meta()["bounds"]
    out = {}
    for k in schema.KNOBS:
        lo_t, hi_t = trained[k]
        lo_s, hi_s = schema.SAFE_BOUNDS[k]
        out[k] = (max(lo_t, lo_s), min(hi_t, hi_s))
    return out


class _SetpointProblem(Problem):
    def __init__(self, composition: dict, carbon_price: float, feed_rate: float, moisture: float):
        self.composition = composition
        self.carbon_price = carbon_price
        self.scale_factor = (feed_rate * (1 - (moisture / 100.0))) / 150.0
        b = guardrail_bounds()
        super().__init__(
            n_var=len(schema.KNOBS),
            n_obj=3,
            xl=np.array([b[k][0] for k in schema.KNOBS]),
            xu=np.array([b[k][1] for k in schema.KNOBS]),
        )

    def _evaluate(self, X, out, *args, **kwargs):
        knobs = pd.DataFrame(X, columns=schema.KNOBS)
        pred = predict.predict_frame(predict.frame(self.composition, knobs))
        
        # Scale outputs
        pred["red_mud_t"] *= self.scale_factor
        pred["total_opex"] *= self.scale_factor
        
        co2_value = pred["red_mud_t"] * carbonation.CO2_PER_TON_RM * self.carbon_price
        net_opex = pred["total_opex"] - co2_value
        out["F"] = np.column_stack(
            [-pred["recovery_pct"], net_opex, pred["red_mud_t"]]
        )


def pareto(composition: dict, *, carbon_price: float = DEFAULT_CARBON_PRICE_OPEX,
           pop: int = 60, gen: int = 40, seed: int = 42,
           feed_rate: float = 150.0, moisture: float = 0.0) -> pd.DataFrame:
    """Pareto front setpoint untuk satu komposisi bauksit."""
    problem = _SetpointProblem(composition, carbon_price, feed_rate, moisture)
    res = minimize(
        problem,
        NSGA2(pop_size=pop),
        get_termination("n_gen", gen),
        seed=seed,
        verbose=False,
    )
    knobs = pd.DataFrame(res.X, columns=schema.KNOBS)
    pred = predict.predict_frame(predict.frame(composition, knobs)).reset_index(drop=True)
    
    scale_factor = (feed_rate * (1 - (moisture / 100.0))) / 150.0
    pred["total_opex"] *= scale_factor
    pred["red_mud_t"] *= scale_factor
    
    df = pd.concat([knobs.reset_index(drop=True), pred], axis=1)
    df["co2_t"] = df["red_mud_t"] * carbonation.CO2_PER_TON_RM
    df["carbon_value"] = df["co2_t"] * carbon_price
    df["net_opex"] = df["total_opex"] - df["carbon_value"]
    return df.sort_values("recovery_pct", ascending=False).reset_index(drop=True)


def pick(df: pd.DataFrame, w_recovery: float = 0.5, w_opex: float = 0.3,
         w_redmud: float = 0.2) -> pd.Series:
    """Pilih satu titik operasi dari Pareto dengan bobot prioritas (slider UI)."""
    def norm(s, invert=False):
        rng = s.max() - s.min()
        z = (s - s.min()) / rng if rng > 0 else s * 0
        return 1 - z if invert else z

    score = (
        w_recovery * norm(df["recovery_pct"])
        + w_opex * norm(df["net_opex"], invert=True)
        + w_redmud * norm(df["red_mud_t"], invert=True)
    )
    return df.loc[score.idxmax()]
