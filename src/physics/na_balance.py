"""Neraca natrium + kaustisasi stoikiometrik.

Memberi: (a) breakdown kebocoran NaOH untuk Sankey natrium, (b) advisory dosis
CaO berbasis stoikiometri — fallback fisika selama soft sensor causticity OFF
(kolom masih konstan di data sintesis, doc 06 Bag. 6).

Semua angka adalah ESTIMASI ber-asumsi-eksplisit (basis baris = ~100 t bauksit
kering). Reaksi kaustisasi: Na2CO3 + Ca(OH)2 -> 2 NaOH + CaCO3.
"""

from __future__ import annotations

import pandas as pd

# kg NaOH terkunci per kg SiO2 reaktif yang membentuk sodalit/DSP (literatur ~0.8-1.2)
NAOH_PER_SIO2_DSP = 0.85
MW_NAOH, MW_NA2CO3, MW_CAO = 40.0, 106.0, 56.0


def breakdown(row: pd.Series) -> dict:
    """Dekomposisi kebocoran NaOH satu baris operasi (ton, basis 100 t bauksit)."""
    sio2_t = float(row["reactive_sio2_pct"])          # % pada basis 100 t ≈ ton
    predesil_eff = float(row.get("predesil_eff", 0.8))
    carb_frac = float(row.get("naoh_carbonation_frac", 0.1))
    conv_eff = float(row.get("na2co3_conv_eff", 0.9))
    makeup = float(row["naoh_makeup_t"])
    consumed = float(row["naoh_consumed_t"])

    # kimiawi: silika yang lolos pra-desilikasi membentuk DSP di digester
    dsp_loss = NAOH_PER_SIO2_DSP * sio2_t * (1.0 - predesil_eff)
    # soda mati: NaOH terkarbonasi; kaustisasi memulihkan conv_eff-nya
    naoh_carbonated = carb_frac * consumed
    dead_soda_net = naoh_carbonated * (1.0 - conv_eff)
    # fisik: sisa make-up yang tidak terjelaskan ~ inklusi kelembapan red mud
    physical_loss = max(makeup - dsp_loss - dead_soda_net, 0.0)

    return {
        "makeup_t": makeup,
        "consumed_t": consumed,
        "dsp_loss_t": dsp_loss,
        "naoh_carbonated_t": naoh_carbonated,
        "dead_soda_net_t": dead_soda_net,
        "physical_loss_t": physical_loss,
        "recycled_t": max(consumed - makeup, 0.0),
    }


def cao_advisory(row: pd.Series) -> dict:
    """Dosis CaO stoikiometrik untuk kaustisasi soda mati vs dosis aktual."""
    consumed = float(row["naoh_consumed_t"])
    carb_frac = float(row.get("naoh_carbonation_frac", 0.1))
    conv_eff = float(row.get("na2co3_conv_eff", 0.9))
    actual = float(row.get("cao_addition_t", float("nan")))

    na2co3_t = carb_frac * consumed * (MW_NA2CO3 / (2 * MW_NAOH))
    cao_needed = na2co3_t * (MW_CAO / MW_NA2CO3) / max(conv_eff, 1e-6)

    status = "n/a"
    if actual == actual:  # not NaN
        ratio = actual / cao_needed if cao_needed > 0 else float("inf")
        status = "over-dosing" if ratio > 1.15 else "under-dosing" if ratio < 0.85 else "sesuai"
    return {
        "na2co3_est_t": na2co3_t,
        "cao_recommended_t": cao_needed,
        "cao_actual_t": actual,
        "status": status,
    }
