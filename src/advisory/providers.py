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

try:  # muat .env kalau ada (python-dotenv); tanpa itu pakai env sistem saja
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

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


def _openai_compat(prompt: str, system: str) -> str:
    """Backend generik utk endpoint OpenAI-compatible — jalur deploy Qwen
    via cloud (OpenRouter, DashScope/Alibaba, vLLM, LM Studio, dll).

    Env: OPENAI_BASE_URL (mis. https://openrouter.ai/api/v1 atau
    https://dashscope-intl.aliyuncs.com/compatible-mode/v1),
    OPENAI_API_KEY, OPENAI_MODEL (mis. qwen/qwen-2.5-7b-instruct:free
    di OpenRouter, atau qwen2.5-7b-instruct di DashScope).
    """
    import requests

    base = os.environ["OPENAI_BASE_URL"].rstrip("/")
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": os.environ.get("OPENAI_MODEL", "qwen2.5-7b-instruct"),
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


_BACKENDS = {"ollama": _ollama, "groq": _groq, "gemini": _gemini,
             "openai": _openai_compat}


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


_EXPLAIN_SYSTEM = (
    "Anda process engineer senior pabrik alumina yang mendampingi Control Room "
    "Operator. Diberikan konteks JSON berisi angka-angka SEBUAH CHART, jawab "
    "dalam Bahasa Indonesia, maksimal 4 kalimat, dengan MENUNJUK angka dari "
    "konteks (mis. 'DSP memakan 34% make-up'). Fokus: apa artinya untuk "
    "operator dan tindakan apa yang relevan. DILARANG memakai angka yang tidak "
    "ada di konteks. Kalau ada pertanyaan user, jawab pertanyaan itu dulu."
)


def _template_explain(context: dict) -> str:
    """Fallback deterministik: ringkasan angka konteks (tanpa LLM)."""
    def _flat(d: dict, prefix: str = "") -> list[tuple[str, object]]:
        items: list[tuple[str, object]] = []
        for k, v in d.items():
            if isinstance(v, dict):
                items += _flat(v, f"{prefix}{k}.")
            elif isinstance(v, (int, float, str)):
                items.append((f"{prefix}{k}", v))
        return items

    lines = ["**Ringkasan angka chart ini:**"]
    for k, v in _flat(context)[:10]:
        vv = f"{v:,.2f}" if isinstance(v, float) else str(v)
        lines.append(f"- {k}: {vv}")
    lines.append("")
    lines.append(
        "_Analisis naratif butuh LLM — aktifkan gratis via `.env` "
        "(`LLM_PROVIDER=groq`, lihat docs/13 §5)._"
    )
    return "\n".join(lines)


def explain_chart(chart_title: str, context: dict, question: str = "",
                  tags: list[str] | None = None) -> tuple[str, str]:
    """Analisis AI untuk satu chart -> (markdown, backend). Selalu berhasil.

    Konteks = HANYA angka milik chart tsb (grounding ketat per-chart);
    `tags` menarik dokumen Knowledge Pack pabrik yang relevan (AI wajib
    mengutip nama dokumen); pertanyaan bebas user opsional.
    """
    from src.advisory import knowledge

    name = provider_name()
    fn = _BACKENDS.get(name)
    if fn is not None:
        prompt = f"Chart: {chart_title}\nKonteks angka:\n" + json.dumps(
            context, ensure_ascii=False, default=str
        )
        prompt += knowledge.as_prompt_block(tags)
        if question.strip():
            prompt += f"\n\nPertanyaan operator: {question.strip()}"
        try:
            return fn(prompt, _EXPLAIN_SYSTEM), name
        except Exception:
            pass
    text = _template_explain(context)
    refs = knowledge.for_tags(tags)
    if refs:
        text += ("\n\n**Knowledge pabrik terkait:** "
                 + ", ".join(f"`{d['name']}`" for d in refs)
                 + " (lihat halaman Knowledge)")
    return text, "template"


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
