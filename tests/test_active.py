"""Uji active learning (doc 12 I9).

Sifat yang dijaga di sini bersifat KESELAMATAN dan KEJUJURAN, bukan sekadar
"fungsi mengembalikan sesuatu": usulan tidak boleh pernah menyuruh pabrik
keluar dari amplop operasi aman, dan tidak boleh mengusulkan komposisi bauksit
yang mustahil.
"""

from __future__ import annotations

import numpy as np
import pytest

from src import schema
from src.models import active


@pytest.fixture(scope="module")
def usulan(models_siap):
    return active.usulkan(n=5, n_kandidat=60, seed=1)


def test_mengembalikan_jumlah_yang_diminta(usulan):
    assert usulan["n_usulan"] == 5
    assert len(usulan["usulan"]) == 5


def test_terurut_dari_paling_bernilai(usulan):
    skor = [u["skor"] for u in usulan["usulan"]]
    assert skor == sorted(skor, reverse=True)


def test_semua_usulan_di_dalam_amplop_operasi_aman(usulan):
    """Menyuruh pabrik keluar batas aman demi data adalah saran yang SALAH,
    seberapa pun informatifnya secara statistik."""
    for u in usulan["usulan"]:
        for k, v in u["knobs"].items():
            lo, hi = schema.SAFE_BOUNDS[k]
            assert lo - 1e-6 <= v <= hi + 1e-6, f"{k}={v} di luar [{lo}, {hi}]"


def test_komposisi_usulan_tetap_masuk_akal(usulan):
    """Komposisi diambil dari baris nyata, jadi harus tetap menjumlah ~100%."""
    for u in usulan["usulan"]:
        total = sum(u["composition"].values())
        assert total == pytest.approx(100.0, abs=0.5)


def test_usulan_lolos_guard_ood(usulan, models_siap):
    """Titik yang disarankan untuk diukur harus titik yang memang boleh
    dijalankan — bukan titik yang akan ditolak guard sistem sendiri."""
    from src.models import predict

    for u in usulan["usulan"]:
        lap = predict.ood_report(u["composition"], u["knobs"])
        assert lap["komposisi_wajar"], lap["alasan"]


def test_skor_mencerminkan_ketidakpastian(usulan):
    """Yang teratas harus benar-benar lebih tidak pasti daripada yang terbawah
    — kalau tidak, pengurutannya tak bermakna."""
    atas, bawah = usulan["usulan"][0], usulan["usulan"][-1]
    assert atas["skor"] > bawah["skor"]
    assert (atas["selisih_fisika"] >= bawah["selisih_fisika"]
            or atas["kelangkaan"] >= bawah["kelangkaan"])


def test_menyebut_target_mana_yang_paling_meleset(usulan):
    for u in usulan["usulan"]:
        assert u["target_paling_meleset"]


def test_kelangkaan_baris_latih_kecil(df, models_siap):
    """Sanity: baris yang MEMANG ADA di data latih harus punya kelangkaan ~0.
    Kalau tidak, metrik jaraknya salah dan seluruh peringkat ikut salah."""
    Z, mu, sd = active._ruang_ternormalisasi(df)
    row = df.iloc[10]
    titik = {f: float(row[f]) for f in schema.FEATURES}
    assert active._kelangkaan(titik, Z, mu, sd) == pytest.approx(0.0, abs=1e-6)


def test_kelangkaan_naik_utk_titik_jauh(df, models_siap):
    Z, mu, sd = active._ruang_ternormalisasi(df)
    row = df.iloc[10]
    dekat = {f: float(row[f]) for f in schema.FEATURES}
    jauh = dict(dekat, digester_temp_c=float(row["digester_temp_c"]) + 50)
    assert (active._kelangkaan(jauh, Z, mu, sd)
            > active._kelangkaan(dekat, Z, mu, sd))


def test_fitur_konstan_tidak_meledakkan_jarak(df):
    """Data sintesis punya kolom konstan; pembagian oleh sd=0 akan menghasilkan
    inf/NaN dan merusak seluruh peringkat."""
    Z, mu, sd = active._ruang_ternormalisasi(df)
    assert np.isfinite(Z).all()
    assert (sd > 0).all()


def test_bobot_terdokumentasi_di_hasil(usulan):
    assert usulan["bobot"]["selisih_fisika"] + usulan["bobot"]["kelangkaan"] == 1.0
    assert "amplop operasi aman" in usulan["catatan"]
