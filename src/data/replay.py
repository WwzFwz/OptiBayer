"""Plant replay (Lapis 0, doc 09): memutar baris data sebagai 'shift feed'.

Interface tipis — di produksi diganti connector historian tanpa menyentuh app.
Skenario gangguan TIDAK mengarang angka: 'silika spike' = lompat ke baris-baris
NYATA ber-silika tinggi dari dataset, sehingga seluruh neraca massa tetap
konsisten dengan generator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SCENARIOS = ("Operasi Normal", "Gangguan: Silika Spike")


def build_sequence(df: pd.DataFrame, scenario: str = SCENARIOS[0],
                   n: int = 96, spike_at: int = 24, seed: int = 11) -> pd.DataFrame:
    """Urutan baris yang diputar dashboard (n 'jam' simulasi).

    Silika spike: jam 0..spike_at-1 normal (silika < 4.5%), lalu masuk deretan
    baris silika tinggi (> 6.3%) — meniru kedatangan pengiriman bauksit kotor.
    """
    rng = np.random.default_rng(seed)
    normal = df[df["reactive_sio2_pct"] < 4.5]
    high = df[df["reactive_sio2_pct"] > 6.3]

    if scenario == SCENARIOS[1] and len(high) >= 8:
        idx_normal = rng.choice(normal.index, size=spike_at, replace=True)
        idx_high = rng.choice(high.index, size=n - spike_at, replace=True)
        idx = np.concatenate([idx_normal, idx_high])
    else:
        idx = rng.choice(normal.index, size=n, replace=True)

    seq = df.loc[idx].reset_index(drop=True)
    seq.index.name = "sim_hour"
    return seq
