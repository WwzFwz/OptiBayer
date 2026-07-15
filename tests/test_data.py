"""Uji fondasi data (M0): adapter -> kanonik bersih -> capability sesuai harapan."""

import pandas as pd

from src import capability, schema
from src.data.adapters import load_clean
from src.data.validate import validate


def test_load_clean():
    df = load_clean()
    # semua kolom kanonik numerik, tidak ada NaN di kolom model
    assert not df.empty and len(df) > 850
    for col in schema.FEATURES + schema.TARGETS:
        assert col in df.columns, col
        assert pd.api.types.is_numeric_dtype(df[col]), col
        assert df[col].notna().all(), col
    # cacat generator sudah tertangani (v1: dig eff >100; v2: recovery >100)
    assert df["digestion_eff_pct"].max() <= 100.0
    assert df["recovery_pct"].max() <= 100.0
    assert (df["naoh_makeup_t"] >= 0).all()
    assert (df["total_opex"] >= 0).all()
    # normalisasi skala v1/v2: persen tetap persen, rasio tetap fraksi
    assert 70 < df["recovery_pct"].mean() < 100
    assert 60 < df["precip_yield_pct"].mean() < 95, "yield harus skala persen"
    assert df["predesil_eff"].max() <= 1.01, "efisiensi harus fraksi 0-1"
    assert df["wash_eff"].max() <= 1.01


def test_validate_ok():
    report = validate(load_clean())
    assert report["ok"], report["issues"]


def test_capability():
    caps = capability.detect(load_clean())
    assert caps["surrogate"] and caps["optimizer"] and caps["replay"]
    # kolom-kolom ini konstan di data sintesis -> fitur harus OFF (doc 06 Bag. 6)
    assert not caps["soft_sensor_causticity"]
    assert not caps["mud_washing_knob"]
    # kalkulator fisika selalu ON
    assert caps["physics_carbonation"] and caps["physics_ceq"]


if __name__ == "__main__":
    test_load_clean()
    test_validate_ok()
    test_capability()
    print("M0 OK")
