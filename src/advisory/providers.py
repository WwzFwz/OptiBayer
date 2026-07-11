"""Provider advisory fleksibel (P6, doc 09) — TANPA token berbayar.

Backend dipilih via env `LLM_PROVIDER`:
  template (default) : deterministik, offline, tanpa AI
  ollama             : LLM lokal gratis (mis. qwen2.5:7b) di http://localhost:11434
  groq               : free-tier cloud (env GROQ_API_KEY)
  gemini             : free-tier cloud (env GEMINI_API_KEY)

Semua backend menerima KONTEKS JSON dari context.py — LLM hanya membahasakan
angka yang sudah dihitung model/fisika, tidak mengarang (doc 07). Kegagalan
apa pun jatuh mulus ke template.
"""

from __future__ import annotations

import json
import os

from src.advisory import template

_SYSTEM = (
    "Anda advisor ruang kontrol pabrik alumina (proses Bayer). Tulis advisory "
    "singkat Bahasa Indonesia untuk Control Room Operator berdasarkan HANYA "
    "angka pada konteks JSON — dilarang mengarang angka. Format: maksimal 3 "
    "kartu '[SEVERITY] Judul' berisi Dampak / Tindakan / Kenapa, ≤4 kalimat per kartu."
)


def _ctx_json(ctx: dict) -> str:
    slim = {k: v for k, v in ctx.items() if k != "shap_factors"}
    slim["faktor_utama"] = [
        f"{f['label']}={f['value']:.1f} ({f['direction']} recovery)"
        for f in ctx.get("shap_factors", [])
    ]
    return json.dumps(slim, ensure_ascii=False, default=str)


def _ollama(prompt: str, system: str) -> str:
    import requests

    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
    r = requests.post(
        os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 400},
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


def _groq(prompt: str, system: str) -> str:
    import requests

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={
            "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 500,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _gemini(prompt: str, system: str) -> str:
    import requests

    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": os.environ["GEMINI_API_KEY"]},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


_BACKENDS = {"ollama": _ollama, "groq": _groq, "gemini": _gemini}


def provider_name() -> str:
    return os.environ.get("LLM_PROVIDER", "template").lower()


def advise(ctx: dict) -> tuple[str, str]:
    """-> (markdown_advisory, backend_terpakai). Selalu berhasil (fallback template)."""
    name = provider_name()
    fn = _BACKENDS.get(name)
    if fn is not None:
        try:
            return fn("Konteks operasi:\n" + _ctx_json(ctx), _SYSTEM), name
        except Exception:
            pass  # jatuh ke template
    return template.narrative(ctx), "template"


def handover_report(shift_summary: dict) -> tuple[str, str]:
    """Laporan serah terima shift (I4, doc 12)."""
    name = provider_name()
    fn = _BACKENDS.get(name)
    system = (
        "Tulis laporan serah terima shift pabrik alumina dalam Bahasa Indonesia: "
        "ringkasan kondisi, kejadian penting, advisory yang muncul, dan PR untuk "
        "shift berikutnya. Berdasarkan HANYA data JSON. Maksimal 200 kata."
    )
    if fn is not None:
        try:
            return fn(json.dumps(shift_summary, ensure_ascii=False, default=str), system), name
        except Exception:
            pass
    # fallback deterministik
    s = shift_summary
    lines = [
        f"## Laporan Serah Terima Shift (jam sim {s.get('hour_start', 0)}–{s.get('hour_end', 0)})",
        f"- Recovery rata-rata: {s.get('recovery_mean', 0):.1f}% | OPEX total: {s.get('opex_sum', 0):,.0f}",
        f"- Red mud: {s.get('red_mud_sum', 0):.0f} t | Potensi CO₂ karbonasi: {s.get('co2_t', 0):.1f} t",
        f"- Silika reaktif terakhir: {s.get('silika_last', 0):.1f}% ({s.get('silika_trend', 'stabil')})",
        f"- Advisory aktif: {s.get('n_advisories', 0)} (kritis: {s.get('n_critical', 0)})",
        "- PR shift berikut: pantau tren silika & konfirmasi hasil lab causticity.",
    ]
    return "\n".join(lines), "template"
