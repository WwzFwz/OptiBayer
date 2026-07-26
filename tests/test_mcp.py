"""Uji MCP server: handshake, daftar tool, dan pemanggilan tool sungguhan.

Termasuk satu uji END-TO-END yang menyalakan server sebagai PROSES TERPISAH
lewat stdio — supaya yang dibuktikan adalah protokolnya, bukan sekadar fungsi
Python yang kebetulan bisa dipanggil.
"""

from __future__ import annotations

import json
import subprocess
import sys

from src.integration import contract, mcp_server
from tests.conftest import ROOT


def kirim(pesan: dict) -> dict | None:
    return mcp_server.tangani(pesan)


def test_handshake_initialize():
    r = kirim({"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18"}})
    assert r["id"] == 1
    assert r["result"]["protocolVersion"] == "2025-06-18"
    assert r["result"]["serverInfo"]["name"] == "optibayer"
    assert "tools" in r["result"]["capabilities"]


def test_notifikasi_tidak_dibalas():
    assert kirim({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_daftar_tool_mengikuti_kontrak():
    r = kirim({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    nama = {t["name"] for t in r["result"]["tools"]}
    diharapkan = {f"optibayer_{e['id']}" for e in contract.ENDPOINTS
                  if e["playground"] and e["fn"] is not None}
    assert nama == diharapkan, "daftar tool harus persis mengikuti kontrak"
    for t in r["result"]["tools"]:
        assert t["description"]
        assert t["inputSchema"]["type"] == "object"


def test_panggil_tool_predict(models_siap):
    r = kirim({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
               "params": {"name": "optibayer_predict",
                          "arguments": {"composition": contract.EXAMPLE_COMPOSITION,
                                        "knobs": contract.EXAMPLE_KNOBS}}})
    assert not r["result"].get("isError")
    isi = json.loads(r["result"]["content"][0]["text"])
    assert isi["result"]["recovery_pct"] > 0


def test_panggil_tool_mass_balance(models_siap):
    r = kirim({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
               "params": {"name": "optibayer_mass_balance",
                          "arguments": {"composition": contract.EXAMPLE_COMPOSITION,
                                        "knobs": contract.EXAMPLE_KNOBS}}})
    isi = json.loads(r["result"]["content"][0]["text"])
    assert isi["result"]["total_opex"] > 0


def test_tool_tak_dikenal_menghasilkan_isError():
    r = kirim({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
               "params": {"name": "optibayer_ngawur", "arguments": {}}})
    assert r["result"]["isError"] is True


def test_argumen_salah_tidak_mematikan_server(models_siap):
    r = kirim({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
               "params": {"name": "optibayer_predict", "arguments": {}}})
    assert r["result"]["isError"] is True
    # server harus tetap melayani permintaan berikutnya
    assert kirim({"jsonrpc": "2.0", "id": 7, "method": "ping"})["result"] == {}


def test_metode_tak_dikenal():
    r = kirim({"jsonrpc": "2.0", "id": 8, "method": "tidak/ada"})
    assert r["error"]["code"] == -32601


def test_stdio_end_to_end(models_siap):
    """Nyalakan server sebagai proses nyata dan bicara JSON-RPC lewat pipa."""
    permintaan = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    masukan = "\n".join(json.dumps(p) for p in permintaan) + "\n"

    proc = subprocess.run(
        [sys.executable, "-m", "src.integration.mcp_server"],
        input=masukan, capture_output=True, text=True, cwd=str(ROOT), timeout=300,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]

    balasan = [json.loads(b) for b in proc.stdout.strip().splitlines() if b.strip()]
    # dua permintaan ber-id -> dua balasan; notifikasi tidak dibalas
    assert len(balasan) == 2, balasan
    assert balasan[0]["result"]["serverInfo"]["name"] == "optibayer"
    assert balasan[1]["result"]["tools"]
