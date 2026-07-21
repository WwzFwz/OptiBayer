"""Regret Meter (I1, doc 12): berapa nilai yang tertinggal kalau advisory diabaikan.

Untuk tiap baris shift: cari setpoint terbaik via pencarian kandidat tervektorisasi
(cepat — ratusan prediksi batch, bukan NSGA-II per baris), lalu bandingkan dengan
hasil aktual. Selisih agregat = "regret" shift dalam satuan OPEX, recovery, red mud.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import schema
from src.models import predict
from src.optimize.pareto import guardrail_bounds

_N_CANDIDATES = 256


def _candidates(seed: int = 7) -> pd.DataFrame:
    """Sampel kandidat setpoint tetap (dipakai ulang semua baris — deterministik)."""
    rng = np.random.default_rng(seed)
    b = guardrail_bounds()
    return pd.DataFrame(
        {k: rng.uniform(b[k][0], b[k][1], _N_CANDIDATES) for k in schema.KNOBS}
    )


def best_for_row(row: pd.Series, w_recovery: float = 0.6,
                 w_opex: float = 0.4) -> tuple[dict, dict]:
    """Setpoint kandidat terbaik untuk satu baris -> (knobs, prediksi)."""
    comp = predict.composition_of(row)
    cand = _candidates()
    pred = predict.predict_frame(predict.frame(comp, cand))

    rec, opx = pred["recovery_pct"], pred["total_opex"]
    rec_n = (rec - rec.min()) / max(rec.max() - rec.min(), 1e-9)
    opx_n = (opx - opx.min()) / max(opx.max() - opx.min(), 1e-9)
    i = (w_recovery * rec_n - w_opex * opx_n).idxmax()
    return cand.loc[i].to_dict(), pred.loc[i].to_dict()


def shift_series(shift_df: pd.DataFrame) -> pd.DataFrame:
    """Per-baris: recovery aktual vs counterfactual (untuk chart overlay regret)."""
    rows = []
    for idx, r in shift_df.iterrows():
        _, best = best_for_row(r)
        rows.append({
            "sim_hour": int(idx),
            "actual": float(r["recovery_pct"]),
            "counterfactual": float(best["recovery_pct"]),
        })
    return pd.DataFrame(rows)


def shift_regret(shift_df: pd.DataFrame) -> dict:
    """Counterfactual satu shift: aktual vs seandainya advisory diikuti."""
    actual = {
        "recovery_pct": shift_df["recovery_pct"].mean(),
        "total_opex": shift_df["total_opex"].sum(),
        "red_mud_t": shift_df["red_mud_t"].sum(),
    }
    best_rows = [best_for_row(r)[1] for _, r in shift_df.iterrows()]
    best = pd.DataFrame(best_rows)
    counterfactual = {
        "recovery_pct": best["recovery_pct"].mean(),
        "total_opex": best["total_opex"].sum(),
        "red_mud_t": best["red_mud_t"].sum(),
    }
    return {
        "n_rows": len(shift_df),
        "actual": actual,
        "counterfactual": counterfactual,
        "delta": {k: counterfactual[k] - actual[k] for k in actual},
    }
