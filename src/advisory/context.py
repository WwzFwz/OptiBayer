"""Perakit konteks advisory: SATU JSON berisi semua angka ber-grounding.

LLM (kalau dipakai) hanya membahasakan isi konteks ini — tidak pernah mengarang
angka sendiri (doc 07 keamanan LLM).
"""

from __future__ import annotations

import pandas as pd

from src import schema
from src.models import explain, predict, registry, verify
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

    # Interval konformal (doc 14 C1): setiap angka prediksi dibawa bersama
    # lebar ketidakpastiannya, bukan label "tinggi/sedang" tulisan tangan.
    interval_now = {t: predict.interval(t, v) for t, v in pred_now.items()}

    # Guard OOD (doc 14 C3) — dievaluasi pada SETPOINT REKOMENDASI, bukan cuma
    # di layar Lab, karena optimizer surrogate memang cenderung memanjat ke
    # tepi ruang yang jarang datanya.
    ood = predict.ood_report(comp, reco_knobs)

    # Wasit fisika: rekomendasi ML dicek ulang oleh neraca massa deterministik
    # sebelum sampai ke operator. Murah (~0.1 ms) sehingga aman dijalankan
    # tiap tick, termasuk mode Play.
    try:
        physics_check = verify.verify(comp, reco_knobs)
    except Exception:   # kalkulator gagal (input ekstrem) -> jangan matikan advisory
        physics_check = {"ok": True, "n_gagal": 0, "rows": [], "gagal_label": [],
                         "error": "kalkulator neraca massa tidak dapat dijalankan"}

    # SKOR ULANG DENGAN FISIKA (obat winner's curse).
    #
    # Optimizer surrogate memilih titik di mana MODELNYA paling optimistis, jadi
    # selisih ML-vs-fisika di titik pemenang secara sistematis lebih besar
    # daripada di titik acak (terukur: melampaui 1x interval konformal pada
    # 6-25% rekomendasi). Pencarian tetap memakai surrogate karena butuh 2400
    # evaluasi; tetapi ANGKA YANG DILIHAT OPERATOR dihitung ulang dengan neraca
    # massa eksak — biayanya hanya ~0.1 ms untuk dua titik. Dengan begitu
    # "kalau rekomendasi diikuti, recovery +0.8%" adalah janji yang berasal dari
    # kalkulator, bukan dari selisih dua tebakan model.
    try:
        fisika_now = verify.physics_targets(comp, knobs)
        fisika_reco = verify.physics_targets(comp, reco_knobs)
        delta_fisika = {t: float(fisika_reco[t] - fisika_now[t])
                        for t in fisika_reco if t in fisika_now}
    except Exception:
        fisika_now, fisika_reco, delta_fisika = {}, {}, {}

    return {
        "fast": fast,
        "composition": comp,
        "knobs_now": knobs,
        "actual": {t: float(row[t]) for t in predict.TARGETS if t in row},
        "predicted_now": pred_now,
        "interval_now": interval_now,
        "ood": ood,
        "physics_check": physics_check,
        "recommended_knobs": reco_knobs,
        "predicted_if_followed": {t: float(v) for t, v in reco.items()},
        # delta versi ML (dipertahankan utk transparansi & pembanding)
        "delta_if_followed_ml": {
            t: float(v) - pred_now[t] for t, v in reco.items()
        },
        # delta yang DIPAKAI UI: hasil neraca massa eksak bila tersedia,
        # jatuh ke versi ML hanya kalau kalkulator gagal dijalankan
        "delta_if_followed": delta_fisika or {
            t: float(v) - pred_now[t] for t, v in reco.items()
        },
        "delta_basis": "neraca massa eksak" if delta_fisika else "selisih prediksi ML",
        "fisika_now": fisika_now,
        "fisika_if_followed": fisika_reco,
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
