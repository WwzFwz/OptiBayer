"""Kalkulator karbonasi red mud — direct aqueous carbonation.

Koefisien dari paper (ScienceDirect 2026, S1743967126000553):
- kapasitas sekuestrasi ~2.3 g CO2 / 100 g red mud  ->  23 kg CO2 / ton RM
- rasio liquid-to-solid (L/S) 2:1
- pH awal 11-13 -> karbonasi menetralkan ke arah pita layak (Permen LHK 6/2021: 7-10)
- bukti stabilisasi: mass loss 14.19% (terkarbonasi) vs 10.74% (mentah)

Murni stoikiometri/koefisien literatur — TIDAK butuh data training (doc 06 Bag. 2).
"""

from __future__ import annotations

from dataclasses import dataclass

CO2_PER_TON_RM = 0.023        # ton CO2 / ton red mud (paper: 2.3 g/100 g)
LS_RATIO = 2.0                # L/S 2:1 (paper)
PH_BEFORE = (11.0, 13.0)      # pH red mud segar (paper)
PH_AFTER_EST = (8.0, 9.5)     # estimasi pasca-karbonasi (arah netralisasi paper)
PH_REG_BAND = (7.0, 10.0)     # Permen LHK No. 6/2021

# Harga karbon indikatif (ASUMSI, konfigurable): pajak karbon RI Rp30/kg CO2e
# = Rp30.000/ton; IDXCarbon berkisar Rp30-60rb/ton. Default konservatif.
CARBON_PRICE_IDR_PER_TON = 30_000.0


@dataclass
class CarbonationResult:
    red_mud_t: float
    co2_sequestered_t: float
    water_needed_t: float
    ph_before: tuple
    ph_after_est: tuple
    compliant_est: bool
    carbon_value_idr: float


def assess(red_mud_t: float,
           carbon_price_idr: float = CARBON_PRICE_IDR_PER_TON) -> CarbonationResult:
    co2 = red_mud_t * CO2_PER_TON_RM
    return CarbonationResult(
        red_mud_t=red_mud_t,
        co2_sequestered_t=co2,
        water_needed_t=red_mud_t * LS_RATIO,
        ph_before=PH_BEFORE,
        ph_after_est=PH_AFTER_EST,
        compliant_est=PH_AFTER_EST[0] >= PH_REG_BAND[0]
        and PH_AFTER_EST[1] <= PH_REG_BAND[1],
        carbon_value_idr=co2 * carbon_price_idr,
    )
