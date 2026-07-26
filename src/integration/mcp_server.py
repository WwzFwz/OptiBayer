"""MCP server OptiBayer — digital twin proses Bayer sebagai alat untuk agen AI.

Tier 3 di doc 07 selama ini berstatus "roadmap" di README, padahal
`contract.py` sudah memuat MCP_TOOLS lengkap dengan fungsi yang bisa dipanggil.
Modul ini menutup jarak itu: server MCP sungguhan yang tool-nya DIBANGKITKAN
dari kontrak yang sama dengan REST API & playground dashboard — satu definisi,
tiga antarmuka, nol duplikasi.

Transport: stdio JSON-RPC 2.0 (satu pesan JSON per baris), sesuai transport
stdio MCP. Sengaja TANPA dependensi baru: SDK `mcp` belum tentu terpasang di
mesin juri, sedangkan protokol yang dibutuhkan di sini kecil dan stabil.

Menjalankan (dari akar repo):
    python -m src.integration.mcp_server

Mendaftarkannya di Claude Desktop / Claude Code (contoh):
    {
      "mcpServers": {
        "optibayer": {
          "command": "python",
          "args": ["-m", "src.integration.mcp_server"],
          "cwd": "/path/ke/antam-hackathon"
        }
      }
    }

Semua tool READ-ONLY terhadap pabrik (doc 07 keamanan): agen boleh bertanya
"kalau suhu dinaikkan, apa yang terjadi?", tidak boleh menulis setpoint.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from src.integration import contract  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "optibayer", "version": "1.0.0"}


# --------------------------------------------------------------- skema tool
def _json_type(value: Any) -> dict:
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int | float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        return {"type": "array", "items": _json_type(value[0]) if value else {}}
    if isinstance(value, dict):
        return {
            "type": "object",
            "properties": {k: _json_type(v) for k, v in value.items()},
        }
    return {}


def _input_schema(example: dict) -> dict:
    """Skema JSON untuk sebuah tool, diturunkan dari contoh payload kontrak.

    Contoh payload memang sudah wajib ada di ENDPOINTS (dipakai playground),
    jadi skema tidak perlu ditulis dua kali dan tak mungkin ketinggalan zaman.
    """
    return {
        "type": "object",
        "properties": {k: _json_type(v) for k, v in example.items()},
        "required": [k for k in example if k not in ("wet_feed_t", "moisture_frac",
                                                     "limit", "tags")],
    }


def tools() -> list[dict]:
    """Daftar tool MCP — sumbernya ENDPOINTS yang sama dengan REST API."""
    out = []
    for ep in contract.ENDPOINTS:
        if not ep["playground"] or ep["fn"] is None:
            continue
        out.append({
            "name": f"optibayer_{ep['id']}",
            "description": (
                f"{ep['summary']}. Setara endpoint REST {ep['method']} "
                f"{ep['path']}. Read-only."
            ),
            "inputSchema": _input_schema(ep["example"]),
        })
    return out


# ------------------------------------------------------------- penanganan
def _panggil_tool(nama: str, argumen: dict) -> dict:
    endpoint_id = nama.removeprefix("optibayer_")
    try:
        hasil, ms = contract.call(endpoint_id, argumen or {})
    except StopIteration:
        return _isi_teks(f"Tool tidak dikenal: {nama}", error=True)
    except Exception as e:
        return _isi_teks(f"{type(e).__name__}: {e}", error=True)
    return _isi_teks(json.dumps(
        {"latency_ms": round(ms, 1), "result": hasil},
        ensure_ascii=False, default=str, indent=2))


def _isi_teks(teks: str, error: bool = False) -> dict:
    hasil = {"content": [{"type": "text", "text": teks}]}
    if error:
        hasil["isError"] = True
    return hasil


def tangani(pesan: dict) -> dict | None:
    """Proses satu pesan JSON-RPC; None berarti tidak perlu dibalas (notifikasi)."""
    metode = pesan.get("method")
    pid = pesan.get("id")

    # Notifikasi (tanpa id) tidak boleh dibalas.
    if pid is None and metode and metode.startswith("notifications/"):
        return None

    if metode == "initialize":
        diminta = (pesan.get("params") or {}).get("protocolVersion")
        return _hasil(pid, {
            "protocolVersion": diminta or PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "Digital twin proses Bayer (alumina). Pakai optibayer_predict "
                "untuk prediksi cepat, optibayer_mass_balance untuk perhitungan "
                "fisika eksak sebagai pembanding, optibayer_pareto/goal_seek "
                "untuk mencari setpoint. Semua read-only."
            ),
        })

    if metode == "ping":
        return _hasil(pid, {})

    if metode == "tools/list":
        return _hasil(pid, {"tools": tools()})

    if metode == "tools/call":
        params = pesan.get("params") or {}
        return _hasil(pid, _panggil_tool(params.get("name", ""),
                                         params.get("arguments") or {}))

    if pid is None:
        return None
    return _galat(pid, -32601, f"Metode tidak dikenal: {metode}")


def _hasil(pid, hasil: dict) -> dict:
    return {"jsonrpc": "2.0", "id": pid, "result": hasil}


def _galat(pid, kode: int, pesan: str) -> dict:
    return {"jsonrpc": "2.0", "id": pid, "error": {"code": kode, "message": pesan}}


def serve(masuk=None, keluar=None) -> None:
    """Loop stdio: satu pesan JSON per baris, balasan juga satu baris."""
    masuk = masuk or sys.stdin
    keluar = keluar or sys.stdout
    for baris in masuk:
        baris = baris.strip()
        if not baris:
            continue
        try:
            pesan = json.loads(baris)
        except json.JSONDecodeError:
            keluar.write(json.dumps(_galat(None, -32700, "JSON tidak valid")) + "\n")
            keluar.flush()
            continue

        balasan = tangani(pesan)
        if balasan is not None:
            keluar.write(json.dumps(balasan, ensure_ascii=False, default=str) + "\n")
            keluar.flush()


if __name__ == "__main__":
    serve()
