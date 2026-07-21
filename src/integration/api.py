"""REST API OptiBayer — Tier 1 doc 07, kini NYATA (Fase A transformasi).

Wrapper tipis di atas kontrak (`contract.py`): rute dibangkitkan dari
ENDPOINTS yang sama dengan halaman Integrasi & (kelak) MCP server — nol
duplikasi definisi. Streamlit TIDAK tersentuh: ini klien/antarmuka kedua
di atas inti headless yang sama.

Jalankan (dari root repo):
    python -m uvicorn src.integration.api:app --port 8000

Dokumentasi OpenAPI otomatis: http://localhost:8000/docs
Semua operasi READ-ONLY terhadap pabrik (doc 07 keamanan).
"""

from __future__ import annotations

import os

# harus SEBELUM pandas/pyarrow ter-import (lihat catatan app/main.py)
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.integration import contract


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # warm-up: muat model surrogate saat boot (bukan saat request pertama)
    # supaya klien tidak pernah merasakan cold-load ~7 dtk
    try:
        ep = next(e for e in contract.ENDPOINTS if e["id"] == "predict")
        contract.call("predict", ep["example"])
    except Exception:
        pass  # tanpa model pun API tetap boot; endpoint akan melapor 400
    yield


app = FastAPI(
    lifespan=_lifespan,
    title="OptiBayer API",
    version="v1-draft",
    description=(
        "Digital twin proses Bayer sebagai service: prediksi surrogate ML, "
        "optimasi NSGA-II carbon-aware, neraca massa deterministik, knowledge "
        "pack, dan audit trail. Satu kontrak dengan halaman Integrasi "
        "dashboard & MCP tools (src/integration/contract.py)."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v1/health", tags=["meta"])
def health() -> dict:
    return {"ok": True, "service": "optibayer", "version": "v1-draft"}


@app.get("/v1/spec", tags=["meta"], summary="Spesifikasi kontrak lengkap")
def spec() -> dict:
    return contract.spec_export()


# ---------- rute dari kontrak (satu sumber dengan playground & MCP) ----------
def _register(ep: dict) -> None:
    path = ep["path"].split("?")[0]

    def handler(payload: dict = Body(
        default={}, description="Kosongkan utk memakai contoh payload kontrak"
    )) -> dict:
        try:
            result, ms = contract.call(ep["id"], payload or ep["example"])
        except Exception as e:  # kontrak read-only: aman diteruskan ke klien
            raise HTTPException(status_code=400,
                                detail=f"{type(e).__name__}: {e}")
        return {"ok": True, "latency_ms": round(ms, 1), "result": result}

    handler.__name__ = f"op_{ep['id']}"
    app.post(path, summary=ep["summary"], tags=["contract"])(handler)


for _ep in contract.ENDPOINTS:
    if _ep["playground"]:
        _register(_ep)


# ---------- rute khusus frontend Next.js (di luar kontrak playground) ----------
@lru_cache(maxsize=4)
def _sequence(scenario_id: int):
    from src.data import replay
    from src.data.adapters import load_clean

    return replay.build_sequence(load_clean(), replay.SCENARIOS[scenario_id])


@app.get("/v1/replay/{scenario_id}", tags=["frontend"],
         summary="Deret jam replay utk chart tren (scenario 0=normal, 1=spike)")
def replay_sequence(scenario_id: int) -> dict:
    from src.data import replay

    if scenario_id not in (0, 1):
        raise HTTPException(404, "scenario_id harus 0 (normal) atau 1 (spike)")
    seq = _sequence(scenario_id)
    cols = ["recovery_pct", "total_opex", "red_mud_t",
            "reactive_sio2_pct", "precip_yield_pct"]
    return {
        "scenario": replay.SCENARIOS[scenario_id],
        "n": len(seq),
        "hours": seq[cols].round(3).to_dict(orient="records"),
    }


@app.get("/v1/replay/{scenario_id}/hour/{hour}", tags=["frontend"],
         summary="Kondisi satu jam: KPI + kartu advisory (+ konteks penuh)")
def replay_hour(scenario_id: int, hour: int, fast: bool = True) -> dict:
    from src.advisory import context as adv_context
    from src.advisory import template
    from src.physics import carbonation

    if scenario_id not in (0, 1):
        raise HTTPException(404, "scenario_id harus 0 (normal) atau 1 (spike)")
    seq = _sequence(scenario_id)
    if not 0 <= hour < len(seq):
        raise HTTPException(404, f"hour di luar rentang 0..{len(seq) - 1}")

    row = seq.iloc[hour]
    ctx = adv_context.build(row, fast=fast)
    cards = template.cards(ctx)
    co2 = carbonation.assess(float(row["red_mud_t"])).co2_sequestered_t
    kpi = {
        "recovery_pct": round(float(row["recovery_pct"]), 2),
        "total_opex": round(float(row["total_opex"]), 0),
        "reactive_sio2_pct": round(float(row["reactive_sio2_pct"]), 2),
        "red_mud_t": round(float(row["red_mud_t"]), 1),
        "co2_capture_t": round(co2, 2),
        "precip_yield_pct": round(float(row["precip_yield_pct"]), 2),
    }
    return {
        "hour": hour,
        "fast": fast,
        "kpi": kpi,
        "silika_level": ctx["silika_level"],
        "cards": cards,
        "recommended_knobs": ctx["recommended_knobs"],
        "delta_if_followed": ctx["delta_if_followed"],
        "na_balance": ctx["na_balance"],
        "carbonation": ctx["carbonation"],
    }
