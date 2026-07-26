"""Uji inersia & dead-time proses (doc 14 A2).

Yang dijaga di sini bukan cuma rumusnya, tapi JANJI YANG DIBUAT KE OPERATOR:
angka rekomendasi adalah kondisi mantap, dan sistem harus terang-terangan
menyebut butuh berapa lama — termasuk terang-terangan bahwa tetapan waktunya
asumsi, bukan hasil belajar.
"""

from __future__ import annotations

import math

import pytest

from src.physics import dynamics


def test_sebelum_dead_time_belum_bergerak():
    """Digester tidak menjawab detik itu juga."""
    v = dynamics.nilai_pada(awal=88.0, mantap=90.0, t_jam=0.4,
                            dead_time_jam=0.5, tetapan_jam=1.5)
    assert v == 88.0


def test_satu_tetapan_waktu_mencapai_63_persen():
    """Sifat baku sistem orde-1 — kalau ini bergeser, modelnya bukan orde-1 lagi."""
    awal, mantap, L, T = 0.0, 100.0, 0.0, 2.0
    v = dynamics.nilai_pada(awal, mantap, t_jam=T, dead_time_jam=L, tetapan_jam=T)
    assert v == pytest.approx(63.2, abs=0.3)


def test_tiga_tetapan_waktu_mencapai_95_persen():
    awal, mantap, T = 0.0, 100.0, 2.0
    v = dynamics.nilai_pada(awal, mantap, t_jam=3 * T, dead_time_jam=0.0, tetapan_jam=T)
    assert v == pytest.approx(95.0, abs=0.5)


def test_menuju_nilai_mantap_tanpa_melewati():
    """Model orde-1 tidak boleh overshoot — kalau iya, operator akan melihat
    recovery melompati targetnya dan kehilangan kepercayaan."""
    awal, mantap = 88.0, 90.0
    sebelumnya = awal
    for i in range(1, 200):
        v = dynamics.nilai_pada(awal, mantap, i * 0.1, 0.5, 1.5)
        assert awal <= v <= mantap + 1e-9
        assert v >= sebelumnya - 1e-9      # monoton naik
        sebelumnya = v
    assert v == pytest.approx(mantap, abs=0.01)


def test_arah_turun_juga_benar():
    awal, mantap = 500.0, 480.0
    v = dynamics.nilai_pada(awal, mantap, 10.0, 0.75, 2.5)
    assert mantap <= v <= awal
    assert v == pytest.approx(mantap, abs=1.0)


def test_respons_membentuk_lintasan_lengkap():
    r = dynamics.respons("recovery_pct", 88.0, 90.0)
    assert r.titik[0]["jam"] == 0.0
    assert r.titik[0]["nilai"] == pytest.approx(88.0)
    assert r.titik[-1]["nilai"] == pytest.approx(90.0, abs=0.15)
    assert r.t95_jam == pytest.approx(r.dead_time_jam + 3 * r.tetapan_jam)


def test_target_tak_dikenal_pakai_tetapan_konservatif():
    """Kalau target baru muncul, sistem harus menebak LAMBAT — jangan pernah
    menjanjikan respons lebih cepat daripada yang bisa dibuktikan."""
    L, T = dynamics.tetapan("target_yang_belum_ada")
    assert (L, T) == dynamics.TETAPAN_CADANGAN
    assert T >= max(t for _, t in dynamics.TETAPAN_DEFAULT.values()) / 2


def test_ringkasan_menyebut_target_paling_lambat():
    awal = {"recovery_pct": 88.0, "precip_yield_pct": 80.0}
    mantap = {"recovery_pct": 90.0, "precip_yield_pct": 81.0}
    r = dynamics.ringkasan(awal, mantap)
    assert r["tersedia"]
    # yield presipitasi paling lambat (T=4 jam) -> dialah penentu t95
    assert r["target_paling_lambat"] == "precip_yield_pct"
    assert r["t95_jam"] == pytest.approx(13.0, abs=0.01)


def test_ringkasan_selalu_menyebut_sumber_asumsi():
    """Kejujuran wajib: tetapan ini BUKAN hasil belajar dari data."""
    r = dynamics.ringkasan({"recovery_pct": 88.0}, {"recovery_pct": 90.0})
    assert "belum dikalibrasi" in r["sumber"]


def test_ringkasan_kosong_saat_tak_ada_pasangan():
    r = dynamics.ringkasan({}, {})
    assert r["tersedia"] is False


def test_identifikasi_dari_data_menolak_dgn_jelas():
    """Lebih baik gagal terang-terangan daripada mengarang tetapan waktu dari
    data steady-state yang memang tidak memuat informasi dinamika."""
    with pytest.raises(NotImplementedError, match="time-series"):
        dynamics.tetapan_dari_data(None)


def test_capability_time_series_mati_di_data_sekarang(df):
    from src import capability

    assert capability.detect(df)["time_series"] is False


def test_kartu_advisory_menyebut_waktu(seq_spike, models_siap):
    from src.advisory import context, template

    ctx = context.build(seq_spike.iloc[8], fast=False)
    assert ctx["dinamika"]["tersedia"]
    teks = " ".join(c["impact"] for c in template.cards(ctx))
    assert "MANTAP" in teks
    assert "jam" in teks


def test_tetapan_masuk_akal_secara_fisik():
    """Urutan inersia harus mengikuti proses: OPEX (biaya reagen, cepat) <
    recovery (digester) < red mud < yield presipitasi (paling lambat)."""
    t = {k: v[1] for k, v in dynamics.TETAPAN_DEFAULT.items()}
    assert t["total_opex"] < t["recovery_pct"] < t["red_mud_t"] < t["precip_yield_pct"]
    for L, T in dynamics.TETAPAN_DEFAULT.values():
        assert 0 <= L < 24 and 0 < T < 24
        assert math.isfinite(L) and math.isfinite(T)
