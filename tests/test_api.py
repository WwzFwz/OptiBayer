"""Uji REST API (src/integration/api.py) — kontrak yang dipakai frontend Next.js.

Sebelumnya API sama sekali tidak punya tes: setiap perubahan bentuk respons
baru ketahuan saat frontend rusak di layar. Tes ini memakai TestClient FastAPI
(tanpa menyalakan server sungguhan) sehingga bisa jalan di CI.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.integration.api import app


@pytest.fixture(scope="module")
def client(models_siap):
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_spec_memuat_endpoint_dan_mcp(client):
    spec = client.get("/v1/spec").json()
    assert spec["endpoints"]
    assert spec["mcp_tools"]


def test_replay_sequence(client):
    data = client.get("/v1/replay/1").json()
    assert data["n"] > 0
    assert len(data["hours"]) == data["n"]
    assert "recovery_pct" in data["hours"][0]


def test_replay_scenario_tak_dikenal_404(client):
    assert client.get("/v1/replay/9").status_code == 404


def test_replay_hour_lengkap(client):
    d = client.get("/v1/replay/1/hour/8?fast=false").json()
    assert d["kpi"]["recovery_pct"] > 0
    assert d["cards"]
    # lapisan kepercayaan ikut terkirim ke frontend
    assert d["interval"]["recovery_pct"]["half"] > 0
    assert "ok" in d["ood"]
    assert "ok" in d["physics_check"]
    assert d["delta_basis"] == "neraca massa eksak"


def test_replay_hour_di_luar_rentang_404(client):
    assert client.get("/v1/replay/1/hour/9999").status_code == 404


def test_pareto_membawa_kepercayaan(client):
    d = client.get("/v1/pareto?scenario_id=1&hour=8").json()
    assert d["solutions"]
    assert d["picked"]["recovery_pct"] > 0
    assert d["ood"]["ok"] in (True, False)
    assert d["physics_check"]["rows"]


def test_operating_map(client):
    d = client.get("/v1/operating-map?scenario_id=1&hour=8&n=8").json()
    assert len(d["temps"]) == 8
    assert len(d["z"]) == 8 and len(d["z"][0]) == 8


def test_model_health(client):
    d = client.get("/v1/model/health").json()
    assert d["targets"]
    for t, blok in d["targets"].items():
        assert blok["half_90"] is not None, t
        assert blok["conformal"]
    assert "kalkulator" in d["catatan"]


def test_sensitivity_dengan_guard(client, df):
    from src.models import predict as P

    row = df.iloc[0]
    payload = {"composition": P.composition_of(row), "knobs": P.knobs_of(row),
               "target": "recovery_pct", "n": 5}
    d = client.post("/v1/sensitivity", json=payload).json()
    assert d["curves"]
    assert d["ood"]["ok"] is True
    assert d["interval"]["recovery_pct"]["half"] > 0


def test_ceq_dan_knowledge(client):
    ceq = client.get("/v1/ceq?a_gl=130&caustic_gl=150&t_now=60").json()
    assert ceq["ceq_now"] > 0
    kn = client.get("/v1/knowledge").json()
    assert kn["docs"] and kn["charts"]


def test_knowledge_add_menolak_isi_kosong(client):
    r = client.post("/v1/knowledge/add", json={"name": "x", "body": ""})
    assert r.status_code == 400


def test_knowledge_add_menolak_dokumen_raksasa(client):
    from src.integration.api import MAX_DOC_CHARS

    r = client.post("/v1/knowledge/add",
                    json={"name": "besar", "body": "a" * (MAX_DOC_CHARS + 1)})
    assert r.status_code == 413


def test_gerbang_token_tulis(client, monkeypatch):
    """Kalau OPTIBAYER_WRITE_TOKEN diisi, endpoint tulis wajib menyertakannya."""
    monkeypatch.setenv("OPTIBAYER_WRITE_TOKEN", "rahasia")
    r = client.post("/v1/knowledge/add", json={"name": "a", "body": "b"})
    assert r.status_code == 401
    r = client.post("/v1/knowledge/add", json={"name": "a", "body": "b"},
                    headers={"X-Write-Token": "salah"})
    assert r.status_code == 401


def test_regret_window(client):
    d = client.get("/v1/regret?scenario_id=1&hour=8").json()
    assert d["actual"] and d["counterfactual"]
    assert d["handover"]
