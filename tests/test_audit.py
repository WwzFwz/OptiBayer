"""Uji audit trail: satu penulis untuk Streamlit, REST, dan MCP.

Audit trail adalah artefak compliance — kalau ia salah format atau diam-diam
kehilangan baris, seluruh klaim "keputusan terekam" runtuh. Karena itu di sini
diuji juga MIGRASI berkas versi lama, bukan cuma jalur bahagia.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.advisory import audit
from src.integration.api import app


@pytest.fixture
def log(tmp_path):
    return tmp_path / "advisory_log.csv"


def test_tulis_lalu_baca(log):
    assert audit.append(8, "Silika tinggi", "terima", sumber="react", path=log)
    hasil = audit.read(path=log)
    assert hasil["n_total"] == 1
    baris = hasil["decisions"][0]
    assert baris["judul"] == "Silika tinggi"
    assert baris["keputusan"] == "terima"
    assert baris["sumber"] == "react"
    assert baris["jam_sim"] == "8"


def test_berkas_kosong_aman(log):
    assert audit.read(path=log) == {"n_total": 0, "decisions": []}


def test_keputusan_ngawur_ditolak(log):
    with pytest.raises(ValueError):
        audit.append(1, "x", "mungkin", path=log)


def test_migrasi_format_lama_tidak_menggeser_kolom(log):
    """Berkas 4-kolom milik versi Streamlit lama harus naik ke 5 kolom utuh."""
    log.write_text(
        "waktu,jam_sim,judul,keputusan\n"
        "2026-01-01T00:00:00,3,Judul Lama,terima\n",
        encoding="utf-8")
    audit.append(8, "Judul Baru", "tolak", sumber="react", path=log)

    hasil = audit.read(path=log)
    assert hasil["n_total"] == 2
    lama, baru = hasil["decisions"]
    assert lama["judul"] == "Judul Lama"      # data lama tidak rusak
    assert lama["keputusan"] == "terima"
    assert lama["sumber"] == "streamlit"      # diberi asal yang benar
    assert baru["sumber"] == "react"


def test_batas_limit(log):
    for i in range(5):
        audit.append(i, f"kartu {i}", "terima", path=log)
    assert len(audit.read(limit=2, path=log)["decisions"]) == 2
    assert audit.read(limit=2, path=log)["n_total"] == 5


# ------------------------------------------------------------------ REST
@pytest.fixture
def client(models_siap, tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "LOG_PATH", tmp_path / "advisory_log.csv")
    with TestClient(app) as c:
        yield c


def test_endpoint_mencatat_lalu_terbaca(client):
    r = client.post("/v1/audit/decision", json={
        "hour": 12, "title": "Dosis CaO under-dosing", "decision": "terima"})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    d = client.get("/v1/audit/decisions?limit=5").json()
    assert d["n_total"] == 1
    assert d["decisions"][0]["judul"] == "Dosis CaO under-dosing"
    assert d["decisions"][0]["sumber"] == "react"


def test_endpoint_menolak_keputusan_tak_sah(client):
    r = client.post("/v1/audit/decision",
                    json={"hour": 1, "title": "x", "decision": "ragu"})
    assert r.status_code == 400


def test_endpoint_menolak_judul_kosong(client):
    r = client.post("/v1/audit/decision", json={"hour": 1, "decision": "terima"})
    assert r.status_code == 400


def test_endpoint_tulis_dilindungi_token(client, monkeypatch):
    monkeypatch.setenv("OPTIBAYER_WRITE_TOKEN", "rahasia")
    r = client.post("/v1/audit/decision",
                    json={"hour": 1, "title": "x", "decision": "terima"})
    assert r.status_code == 401
    r = client.post("/v1/audit/decision",
                    json={"hour": 1, "title": "x", "decision": "terima"},
                    headers={"X-Write-Token": "rahasia"})
    assert r.status_code == 200


def test_kontrak_dan_rest_membaca_sumber_yang_sama(client):
    """Playground kontrak (dipakai halaman Integrasi & MCP) harus melihat
    baris yang sama dengan endpoint REST — bukan berkas lain."""
    client.post("/v1/audit/decision",
                json={"hour": 5, "title": "Uji kontrak", "decision": "tolak"})
    lewat_kontrak = client.post("/v1/audit/decisions", json={"limit": 10}).json()
    assert lewat_kontrak["result"]["n_total"] == 1
    assert lewat_kontrak["result"]["decisions"][0]["judul"] == "Uji kontrak"
