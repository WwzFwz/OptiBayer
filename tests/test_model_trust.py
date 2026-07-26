"""Uji lapisan kepercayaan model: interval konformal, guard OOD, wasit fisika.

Tes-tes ini menjaga sifat yang MENENTUKAN apakah angka di layar boleh dipercaya
operator. Semua ambang di sini berasal dari pengukuran (lihat docs/21), bukan
angka yang enak dilihat — kalau ada yang gagal, artinya ada sifat nyata yang
berubah, bukan sekadar tes rewel.
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.model_selection import KFold, cross_val_predict, train_test_split

from src import schema
from src.models import predict, train, verify


# ---------------------------------------------------------------- konformal
def test_setiap_model_punya_kuantil_konformal(models_siap):
    for target in models_siap:
        half = predict.halfwidth(target, 0.90)
        assert half is not None, f"{target} tidak punya kuantil konformal"
        assert half > 0


def test_interval_melebar_saat_level_dinaikkan(models_siap):
    for target in models_siap:
        h80 = predict.halfwidth(target, 0.80)
        h95 = predict.halfwidth(target, 0.95)
        assert h80 is not None and h95 is not None
        assert h80 <= h95, f"{target}: interval 80% harus <= 95%"


def test_interval_mengurung_prediksi(models_siap):
    iv = predict.interval("recovery_pct", 88.0, 0.90)
    assert iv is not None
    assert iv["lo"] <= 88.0 <= iv["hi"]
    assert iv["level"] == pytest.approx(0.90)


def test_cakupan_konformal_pada_data_held_out(df):
    """Kuantil dikalibrasi HANYA dari data latih, cakupan diukur di data uji.

    Inilah pembuktian yang sesungguhnya: mengukur cakupan pada residual yang
    sama yang membentuk kuantilnya bersifat tautologis. Toleransi +-7 pp
    memperhitungkan ragam sampel pada n_test ~250.
    """
    X = df[schema.FEATURES]
    for target in ("recovery_pct", "red_mud_t"):
        y = df[target].to_numpy(dtype=float)
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0)
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        model = train._make_model("lightgbm")
        oof = cross_val_predict(model, Xtr, ytr, cv=kf, n_jobs=1)
        q = train.conformal_quantiles(ytr - oof)["0.90"]["q"]

        model.fit(Xtr, ytr)
        cakupan = float(np.mean(np.abs(yte - model.predict(Xte)) <= q))
        assert 0.83 <= cakupan <= 0.97, f"{target}: cakupan {cakupan:.1%} jauh dari 90%"


# --------------------------------------------------------------------- OOD
def test_ood_bersih_untuk_baris_data_nyata(df, models_siap):
    row = df.iloc[0]
    rep = predict.ood_report(predict.composition_of(row), predict.knobs_of(row))
    assert rep["ok"], rep["alasan"]
    assert rep["komposisi_wajar"]
    assert rep["komposisi_total_pct"] == pytest.approx(100.0, abs=0.5)


def test_ood_menangkap_komposisi_tak_masuk_akal(df, models_siap):
    """Semua fitur bisa saja berada di dalam rentang per-fitur, tapi jumlah
    oksidanya ngawur — kasus inilah yang lolos dari `within_bounds` saja."""
    row = df.iloc[0]
    comp = predict.composition_of(row)
    comp["al2o3_pct"] = comp["al2o3_pct"] * 0.5   # jumlah jadi jauh dari 100%
    rep = predict.ood_report(comp, predict.knobs_of(row))
    assert not rep["ok"]
    assert not rep["komposisi_wajar"]
    assert any("oksida" in a for a in rep["alasan"])


def test_ood_menangkap_ekstrapolasi_knob(df, models_siap):
    row = df.iloc[0]
    knobs = predict.knobs_of(row)
    lo, hi = predict.meta()["bounds"]["digester_temp_c"]
    knobs["digester_temp_c"] = hi + 20.0
    rep = predict.ood_report(predict.composition_of(row), knobs)
    assert not rep["ok"]
    assert rep["n_out"] >= 1
    assert any(o["feature"] == "digester_temp_c" for o in rep["offenders"])


# ------------------------------------------------------------ wasit fisika
def test_surrogate_sepakat_dengan_fisika_di_data_nyata(df, models_siap):
    """Pada baris data sungguhan, ML dan neraca massa harus sepakat."""
    gagal = 0
    n = 25
    for i in range(n):
        row = df.iloc[i]
        hasil = verify.verify(predict.composition_of(row), predict.knobs_of(row))
        gagal += 0 if hasil["ok"] else 1
    assert gagal <= 2, f"{gagal}/{n} baris nyata tidak lolos wasit fisika"


def test_fidelitas_memburuk_saat_ekstrapolasi(models_siap):
    """Justifikasi terukur untuk guard OOD (doc 14 C3).

    Kalau suatu saat pernyataan ini TIDAK lagi benar, teks peringatan di
    template advisory harus ikut diperbaiki — karena ia mengutip angka ini.
    """
    rep = verify.fidelity(n=60, seed=1)
    dalam = rep["galat"]["perturbasi_data"]["per_target"]["recovery_pct"]
    luar = rep["galat"]["ekstrapolasi"]["per_target"]["recovery_pct"]
    assert luar["nmae_median_pct"] > dalam["nmae_median_pct"]


def test_titik_fisika_mustahil_ditolak():
    assert not verify._fisika_masuk_akal({"total_opex": -605.0, "red_mud_t": 400.0})
    assert not verify._fisika_masuk_akal({"total_opex": 1000.0, "red_mud_t": 0.0})
    assert not verify._fisika_masuk_akal(
        {"total_opex": 1000.0, "red_mud_t": 400.0, "recovery_pct": 140.0})
    assert verify._fisika_masuk_akal(
        {"total_opex": 1000.0, "red_mud_t": 400.0, "recovery_pct": 88.0})


# ------------------------------------------------------- pemilihan keluarga
def test_metadata_menyimpan_keluarga_dan_pesaingnya(models_siap):
    """Keputusan 'model apa yang dipakai' harus bisa diaudit dari artefak."""
    for target in models_siap:
        m = predict.meta(target).get("metrics", {})
        assert m.get("family") in train.FAMILIES
        assert m.get("seleksi"), f"{target}: skor pesaing tidak tersimpan"
        terpilih = m["family"]
        for lawan, skor in m["seleksi"].items():
            if lawan != terpilih:
                assert m["cv_mae"] <= skor["cv_mae"] + 1e-9, (
                    f"{target}: {lawan} lebih baik tapi tidak dipilih")


def test_advisory_memakai_delta_fisika(seq_spike, models_siap):
    """Janji 'kalau diikuti, recovery +X' harus berasal dari neraca massa."""
    from src.advisory import context

    ctx = context.build(seq_spike.iloc[8], fast=False)
    assert ctx["delta_basis"] == "neraca massa eksak"
    assert set(ctx["delta_if_followed"]) >= {"recovery_pct", "total_opex"}
