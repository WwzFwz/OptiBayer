"""Kurva kelarutan ekuilibrium gibbsite (Ceq) — physics overlay presipitasi.

Bentuk korelasi Misra untuk kelarutan Al2O3 dalam larutan kaustik:
    (A/C)_eq = exp(6.2106 - 2486.7/T_K + 1.0875*C/1000)
A = konsentrasi Al2O3 terlarut (g/L), C = kaustik sebagai Na2O (g/L), T_K = Kelvin.

Catatan jujur (doc 06): korelasi literatur, BELUM dikalibrasi ke pabrik — dipakai
sebagai overlay arah ("gap supersaturasi = yield yang belum diambil"), bukan angka
absolut. Kalibrasi = pekerjaan tahap 2 dengan data liquor asli.
"""

from __future__ import annotations

import numpy as np


def ceq_ratio(temp_c: float | np.ndarray, caustic_gl: float) -> np.ndarray:
    t_k = np.asarray(temp_c, dtype=float) + 273.15
    return np.exp(6.2106 - 2486.7 / t_k + 1.0875 * caustic_gl / 1000.0)


def ceq(temp_c: float | np.ndarray, caustic_gl: float) -> np.ndarray:
    """Konsentrasi Al2O3 ekuilibrium (g/L) pada suhu & kaustik tertentu."""
    return ceq_ratio(temp_c, caustic_gl) * caustic_gl


def supersaturation_gap(a_gl: float, temp_c: float, caustic_gl: float) -> float:
    """Driving force presipitasi (g/L): A aktual - A ekuilibrium.

    Positif besar = masih banyak alumina terlarut yang BISA diendapkan
    (uang yang belum diambil); mendekati 0 = liquor hampir 'habis'.
    """
    return float(a_gl - ceq(temp_c, caustic_gl))


def ceq_curve(caustic_gl: float, t_range=(45.0, 80.0), n: int = 50):
    """(suhu, Ceq) untuk chart kurva di tab presipitasi."""
    temps = np.linspace(*t_range, n)
    return temps, ceq(temps, caustic_gl)
