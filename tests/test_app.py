"""Uji dashboard Streamlit end-to-end via AppTest: skrip harus jalan tanpa exception.

Ditandai `slow` karena satu AppTest menjalankan seluruh aplikasi (termasuk
optimizer). Jalankan hanya yang cepat dengan:  pytest -m "not slow"
"""

import pytest
from streamlit.testing.v1 import AppTest

from tests.conftest import ROOT

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def app(models_siap):
    at = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=300)
    at.run()
    return at


def test_boot_tanpa_exception(app):
    assert not app.exception, app.exception
    assert len(app.metric) >= 6, f"metric={len(app.metric)}"


def test_pemilih_skenario_hadir(app):
    assert app.sidebar.selectbox[0].value in (
        "Operasi Normal", "Gangguan: Silika Spike")


def test_skenario_spike_dan_lompat_jam(app):
    app.sidebar.selectbox[0].set_value("Gangguan: Silika Spike").run()
    assert not app.exception, app.exception
    # slider 'Jam simulasi' = slider ke-2 di sidebar (setelah 'Detik per jam')
    app.sidebar.slider[1].set_value(30).run()
    assert not app.exception, app.exception


def test_toggle_tema_terang_dan_gelap(app):
    from app import ui

    app.sidebar.toggle[0].set_value(True).run()
    assert not app.exception, app.exception
    assert ui.MODE == "light" and ui.SURFACE == "#fcfcfb", (ui.MODE, ui.SURFACE)

    app.sidebar.toggle[0].set_value(False).run()
    assert not app.exception, app.exception
    assert ui.MODE == "dark" and ui.SURFACE == "#1a1a19"
