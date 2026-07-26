"""Uji M2: fisika + optimizer + regret — tanpa dashboard (doc 09 §5).

Dulu berupa satu `main()` sehingga pytest tidak pernah mengoleksinya; kini
dipecah jadi beberapa fungsi test agar kegagalan menunjuk ke bagian yang tepat.
"""

import time

import pytest

from src.models import predict
from src.optimize import goal_seek, pareto, regret
from src.physics import carbonation, na_balance, precipitation


def test_karbonasi_stoikiometri(df):
    row = df.iloc[0]
    c = carbonation.assess(row["red_mud_t"])
    assert abs(c.co2_sequestered_t - 0.023 * row["red_mud_t"]) < 1e-9
    assert c.water_needed_t == 2 * row["red_mud_t"]


def test_kurva_ceq_masuk_akal():
    gap = precipitation.supersaturation_gap(a_gl=120, temp_c=60, caustic_gl=150)
    ceq60 = precipitation.ceq(60, 150)
    assert gap > 0
    assert 20 < ceq60 < 120


def test_neraca_natrium(df):
    row = df.iloc[0]
    nb = na_balance.breakdown(row)
    assert nb["dsp_loss_t"] > 0
    assert nb["physical_loss_t"] >= 0
    ca = na_balance.cao_advisory(row)
    assert ca["cao_recommended_t"] > 0
    assert ca["status"] in ("over-dosing", "under-dosing", "sesuai")


def test_pareto_menghasilkan_front(df, models_siap):
    comp = predict.composition_of(df.iloc[0])
    t0 = time.time()
    pf = pareto.pareto(comp)
    dt = time.time() - t0
    assert len(pf) >= 20
    assert dt < 30, f"optimizer terlalu lambat: {dt:.1f} dtk"
    best = pareto.pick(pf)
    assert best["recovery_pct"] > 0


def test_silika_tinggi_menurunkan_recovery_optimal(df, models_siap):
    comp = predict.composition_of(df.iloc[0])
    lo = dict(comp, reactive_sio2_pct=2.0)
    hi = dict(comp, reactive_sio2_pct=7.0)
    rec_lo = pareto.pick(pareto.pareto(lo))["recovery_pct"]
    rec_hi = pareto.pick(pareto.pareto(hi))["recovery_pct"]
    assert rec_lo > rec_hi, "silika tinggi harus menurunkan recovery optimal"


def test_goal_seek_mencapai_target(df, models_siap):
    kandidat = df[df["reactive_sio2_pct"] < 4.0]
    if kandidat.empty:
        pytest.skip("tidak ada baris silika rendah di data ini")
    comp_lo = predict.composition_of(kandidat.iloc[0])
    gs = goal_seek.cheapest_for_recovery(comp_lo, target_recovery=88.0)
    assert gs
    assert gs["prediction"]["recovery_pct"] >= 87.75


def test_regret_shift(df, models_siap):
    rg = regret.shift_regret(df.iloc[:8])
    assert "actual" in rg and "counterfactual" in rg
    assert rg["actual"]["recovery_pct"] > 0
