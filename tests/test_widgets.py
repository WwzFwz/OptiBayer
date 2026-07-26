"""Uji interaksi widget Streamlit (Prediction Lab & Overview).

Menekan tombol dan menggeser slider sungguhan untuk menangkap exception yang
lolos dari smoke test dasar.

CATATAN SEJARAH. Berkas ini menggantikan `test_new_features_interactive.py`,
yang SUDAH RUSAK sebelum ditulis ulang: ia berasumsi seluruh halaman dirender
sekaligus (peninggalan zaman `st.tabs`), padahal navigasi sejak commit c61f251
memakai `st.segmented_control` sehingga hanya SATU halaman hidup per run.
Akibatnya semua widget Prediction Lab "tidak ditemukan". Ia juga tidak pernah
dikoleksi pytest (hanya punya `main()`) dan memanggil `sys.exit(1)` saat gagal,
jadi kerusakannya tak pernah kelihatan. Versi ini berpindah halaman lebih dulu
lewat session_state, persis seperti pengguna menekan tombol navigasi.
"""

import pytest
from streamlit.testing.v1 import AppTest

from app import ui
from tests.conftest import ROOT

pytestmark = pytest.mark.slow

_cache: dict[str, AppTest] = {}


def buka(halaman: str, models_siap) -> AppTest:
    """AppTest yang sudah berada di halaman `halaman` (kunci ui.NAV_LABELS)."""
    if halaman not in _cache:
        at = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=300)
        at.run()
        assert not at.exception, at.exception
        if halaman != "overview":
            at.session_state["nav"] = ui.NAV_LABELS[halaman]
            at.run()
            assert not at.exception, at.exception
        _cache[halaman] = at
    return _cache[halaman]


@pytest.fixture(scope="module")
def lab(models_siap):
    return buka("lab", models_siap)


@pytest.fixture(scope="module")
def overview(models_siap):
    return buka("overview", models_siap)


def _klik(at: AppTest, cocok: str):
    tombol = [b for b in at.button if cocok in (b.label or "")]
    assert tombol, (f"tombol '{cocok}' tidak ditemukan; "
                    f"tersedia: {[b.label for b in at.button][:8]}")
    tombol[0].click().run()
    assert not at.exception, at.exception


# ------------------------------------------------------- Prediction Lab
def test_sampel_acak_dan_reset(lab):
    _klik(lab, "Sampel acak")
    _klik(lab, "Reset ke rata-rata")


def test_slider_komposisi_ekstrem(lab):
    sliders = [s for s in lab.slider if "Al₂O₃" in (s.label or "")]
    assert sliders, "slider Al2O3 tidak ditemukan"
    sliders[0].set_value(sliders[0].max).run()
    assert not lab.exception, lab.exception


def test_slider_suhu_digester_minimum(lab):
    sliders = [s for s in lab.slider if "Suhu Digester" in (s.label or "")]
    assert sliders, "slider suhu digester tidak ditemukan"
    sliders[0].set_value(sliders[0].min).run()
    assert not lab.exception, lab.exception


def test_ganti_target_sensitivitas(lab):
    sel = [s for s in lab.selectbox if s.key == "pl_sens_target"]
    assert sel, "selectbox target sensitivitas tidak ditemukan"
    sel[0].set_value("total_opex").run()
    assert not lab.exception, lab.exception


def test_latih_ulang_model(lab):
    """Jalur nyata operator: melatih ulang seluruh surrogate dari UI.

    Paling lambat di suite (mengadu 3 keluarga model x 4 target), tapi inilah
    satu-satunya tes yang menyentuh pipeline latih -> registry -> cache bersih
    dari sisi pengguna.
    """
    tombol = [b for b in lab.button if b.key == "pl_retrain_btn"]
    assert tombol, "tombol latih ulang tidak ditemukan"
    tombol[0].click().run()
    assert not lab.exception, lab.exception


# -------------------------------------------------------------- Overview
def test_regret_dan_handover(overview):
    _klik(overview, "Hitung regret")
    _klik(overview, "laporan serah-terima")


def test_ganti_target_korelasi(overview):
    sel = [s for s in overview.selectbox if s.key == "ov_corr_target"]
    assert sel, "selectbox korelasi target tidak ditemukan"
    sel[0].set_value("red_mud_t").run()
    assert not overview.exception, overview.exception
