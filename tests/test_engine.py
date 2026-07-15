"""Uji M2: fisika + optimizer + regret — jalan dari CLI tanpa dashboard (doc 09 §5)."""

import time

from src.data.adapters import load_clean
from src.models import predict
from src.optimize import goal_seek, pareto, regret
from src.physics import carbonation, na_balance, precipitation


def main():
    df = load_clean()
    row = df.iloc[0]
    comp = predict.composition_of(row)

    # fisika (skala-agnostik: v1 basis 100 t maupun v2 skala pabrik)
    c = carbonation.assess(row["red_mud_t"])
    assert abs(c.co2_sequestered_t - 0.023 * row["red_mud_t"]) < 1e-9
    assert c.water_needed_t == 2 * row["red_mud_t"]
    print(f"karbonasi: {row['red_mud_t']:.1f} t RM -> {c.co2_sequestered_t:.2f} t CO2, "
          f"nilai Rp{c.carbon_value_idr:,.0f}")

    gap = precipitation.supersaturation_gap(a_gl=120, temp_c=60, caustic_gl=150)
    ceq60 = precipitation.ceq(60, 150)
    assert gap > 0 and 20 < ceq60 < 120, (gap, ceq60)
    print(f"Ceq(60C,150g/L) = {float(ceq60):.1f} g/L, gap contoh = {gap:.1f} g/L")

    nb = na_balance.breakdown(row)
    assert nb["dsp_loss_t"] > 0 and nb["physical_loss_t"] >= 0
    ca = na_balance.cao_advisory(row)
    print(f"neraca Na: DSP {nb['dsp_loss_t']:.2f} t | soda mati net "
          f"{nb['dead_soda_net_t']:.2f} t | fisik {nb['physical_loss_t']:.2f} t | "
          f"CaO advisory: {ca['cao_recommended_t']:.2f} t vs aktual "
          f"{ca['cao_actual_t']:.2f} t ({ca['status']})")

    # optimizer — uji fisik doc 11: silika rendah vs tinggi harus beda rekomendasi
    t0 = time.time()
    pf = pareto.pareto(comp)
    dt = time.time() - t0
    assert len(pf) >= 20 and dt < 30, (len(pf), dt)
    best = pareto.pick(pf)
    print(f"pareto: {len(pf)} solusi dalam {dt:.1f} dtk; pilihan seimbang: "
          f"T={best['digester_temp_c']:.1f}C NaOH={best['naoh_conc_gl']:.0f} "
          f"-> rec {best['recovery_pct']:.1f}% opex {best['total_opex']:.0f}")

    lo = dict(comp, reactive_sio2_pct=2.0)
    hi = dict(comp, reactive_sio2_pct=7.0)
    rec_lo = pareto.pick(pareto.pareto(lo))["recovery_pct"]
    rec_hi = pareto.pick(pareto.pareto(hi))["recovery_pct"]
    assert rec_lo > rec_hi, "silika tinggi harus menurunkan recovery optimal"
    print(f"silika 2% -> rec optimal {rec_lo:.1f}% | silika 7% -> {rec_hi:.1f}%")

    # goal-seek pada bauksit silika rendah (target harus feasible utk komposisinya)
    comp_lo = predict.composition_of(
        df[df["reactive_sio2_pct"] < 4.0].iloc[0]
    )
    gs = goal_seek.cheapest_for_recovery(comp_lo, target_recovery=88.0)
    assert gs and gs["prediction"]["recovery_pct"] >= 87.75
    print(f"goal-seek rec>=88% (silika rendah): opex "
          f"{gs['prediction']['total_opex']:.0f} "
          f"(rec {gs['prediction']['recovery_pct']:.1f}%)")

    # regret meter pada 'shift' 8 baris
    t0 = time.time()
    rg = regret.shift_regret(df.iloc[:8])
    print(f"regret 8 baris ({time.time()-t0:.1f} dtk): recovery aktual "
          f"{rg['actual']['recovery_pct']:.1f}% vs bisa {rg['counterfactual']['recovery_pct']:.1f}%")
    print("M2 OK")


if __name__ == "__main__":
    main()
