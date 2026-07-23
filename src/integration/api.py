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


@app.get("/v1/operating-map", tags=["frontend"],
         summary="Grid recovery = f(suhu digester × NaOH) + marker rekomendasi")
def operating_map(scenario_id: int, hour: int, n: int = 20) -> dict:
    import numpy as np
    import pandas as pd

    from src import schema
    from src.models import predict
    from src.optimize import pareto

    seq = _sequence(scenario_id)
    row = seq.iloc[max(0, min(hour, len(seq) - 1))]
    comp = predict.composition_of(row)
    knobs = predict.knobs_of(row)
    reco = pareto.pick(pareto.pareto(comp))
    tb = schema.SAFE_BOUNDS["digester_temp_c"]
    nb_ = schema.SAFE_BOUNDS["naoh_conc_gl"]
    temps = np.linspace(*tb, n)
    naohs = np.linspace(*nb_, n)
    tt, nn = np.meshgrid(temps, naohs)
    kdf = pd.DataFrame({
        "particle_size_um": knobs["particle_size_um"],
        "digester_temp_c": tt.ravel(),
        "naoh_conc_gl": nn.ravel(),
        "precip_temp_c": knobs["precip_temp_c"],
        "seed_ratio": knobs["seed_ratio"],
    })
    z = predict.predict_frame(predict.frame(comp, kdf))["recovery_pct"]
    return {
        "temps": [round(float(t), 1) for t in temps],
        "naohs": [round(float(x), 0) for x in naohs],
        "z": z.round(2).values.reshape(n, n).tolist(),
        "now": {"t": round(knobs["digester_temp_c"], 1),
                "naoh": round(knobs["naoh_conc_gl"], 0)},
        "reco": {"t": round(float(reco["digester_temp_c"]), 1),
                 "naoh": round(float(reco["naoh_conc_gl"]), 0)},
        "composition": {k: round(float(v), 3) for k, v in comp.items()},
        "knobs_now": {k: round(float(v), 2) for k, v in knobs.items()},
        "bounds": {k: schema.SAFE_BOUNDS[k] for k in schema.KNOBS},
        "knob_labels": {k: schema.label(k) for k in schema.KNOBS},
    }


@app.get("/v1/pareto", tags=["frontend"],
         summary="Pareto NSGA-II utk komposisi jam tertentu (+ radar knob)")
def pareto_hour(scenario_id: int, hour: int) -> dict:
    from src import schema
    from src.models import predict
    from src.optimize import pareto

    seq = _sequence(scenario_id)
    row = seq.iloc[max(0, min(hour, len(seq) - 1))]
    comp = predict.composition_of(row)
    knobs = predict.knobs_of(row)
    pf = pareto.pareto(comp)
    picked = pareto.pick(pf)
    cols = list(schema.KNOBS) + ["recovery_pct", "net_opex", "red_mud_t"]
    return {
        "solutions": pf[cols].round(3).to_dict(orient="records"),
        "picked": {k: round(float(picked[k]), 3) for k in cols},
        "bounds": {k: schema.SAFE_BOUNDS[k] for k in schema.KNOBS},
        "now_knobs": {k: round(v, 3) for k, v in knobs.items()},
        "labels": {k: schema.label(k) for k in schema.KNOBS},
    }


@app.get("/v1/ceq", tags=["frontend"],
         summary="Kurva Ceq presipitasi (korelasi Misra) + gap supersaturasi")
def ceq_curve(a_gl: float = 130.0, caustic_gl: float = 150.0,
              t_now: float = 60.0) -> dict:
    from src.physics import precipitation

    temps, ceqs = precipitation.ceq_curve(caustic_gl)
    return {
        "temps": [round(float(t), 1) for t in temps],
        "ceq": [round(float(c), 2) for c in ceqs],
        "a_gl": a_gl,
        "t_now": t_now,
        "ceq_now": round(float(precipitation.ceq(t_now, caustic_gl)), 2),
        "gap": round(precipitation.supersaturation_gap(a_gl, t_now, caustic_gl), 2),
    }


@app.get("/v1/knowledge", tags=["frontend"],
         summary="Daftar dokumen Knowledge Pack + chart pemakainya")
def knowledge_list() -> dict:
    from src.advisory import knowledge

    docs = knowledge.load_all()
    return {
        "docs": [{
            "name": d["name"], "tags": d["tags"], "status": d["status"],
            "body": d["body"], "used_by": knowledge.charts_for_doc(d),
        } for d in docs],
        "charts": {k: v["label"] for k, v in knowledge.CHART_TAGS.items()},
    }


@app.get("/v1/correlation", tags=["frontend"],
         summary="Korelasi fitur vs target + scatter (analisis data historis penuh)")
def correlation(target: str = "recovery_pct", feature: str = "reactive_sio2_pct") -> dict:
    import numpy as np

    from src import schema
    from src.data.adapters import load_clean

    df = load_clean()
    corr = []
    for f in schema.FEATURES:
        r = float(np.corrcoef(df[f], df[target])[0, 1])
        corr.append({"feature": f, "label": schema.label(f), "r": round(r, 3)})
    corr.sort(key=lambda x: abs(x["r"]), reverse=True)
    # scatter untuk satu fitur terpilih (subsample utk ringan)
    sub = df.sample(min(300, len(df)), random_state=1)
    scatter = [{"x": round(float(a), 2), "y": round(float(b), 2)}
               for a, b in zip(sub[feature], sub[target])]
    return {
        "target": target, "target_label": schema.label(target),
        "feature": feature, "feature_label": schema.label(feature),
        "corr": corr, "scatter": scatter,
        "features": [{"key": f, "label": schema.label(f)} for f in schema.FEATURES],
        "targets": [{"key": t, "label": schema.label(t)} for t in schema.TARGETS],
    }


@app.post("/v1/sensitivity", tags=["frontend"],
          summary="Sweep tiap knob + tornado utk komposisi/setpoint manual (Lab)")
def sensitivity(payload: dict = Body(...)) -> dict:
    import numpy as np
    import pandas as pd

    from src import schema
    from src.models import predict

    comp = payload["composition"]
    knobs = payload["knobs"]
    target = payload.get("target", "recovery_pct")
    n = int(payload.get("n", 21))

    curves: dict[str, list] = {}
    deltas: dict[str, float] = {}
    for k in schema.KNOBS:
        lo, hi = schema.SAFE_BOUNDS[k]
        xs = np.linspace(lo, hi, n)
        kdf = pd.DataFrame({kk: np.full(n, knobs[kk]) for kk in schema.KNOBS})
        kdf[k] = xs
        ys = predict.predict_frame(predict.frame(comp, kdf))[target]
        curves[k] = [{"x": round(float(x), 2), "y": round(float(y), 3)}
                     for x, y in zip(xs, ys)]
        deltas[k] = round(float(ys.iloc[-1] - ys.iloc[0]), 3)

    # peringatan ekstrapolasi (out-of-domain vs rentang data latih)
    wb = predict.within_bounds(comp, knobs, target)
    out_of_bounds = [schema.label(f) for f, ok in wb.items() if not ok]

    return {
        "target": target,
        "curves": curves,
        "deltas": deltas,
        "current": {k: round(float(knobs[k]), 2) for k in schema.KNOBS},
        "labels": {k: schema.label(k) for k in schema.KNOBS},
        "out_of_bounds": out_of_bounds,
    }


@app.post("/v1/knowledge/add", tags=["frontend"],
          summary="Tambah dokumen Knowledge Pack (nama, tag, isi) — langsung dipakai AI")
def knowledge_add(payload: dict = Body(...)) -> dict:
    import re

    from src.advisory import knowledge

    name = (payload.get("name") or "").strip()
    body = (payload.get("body") or "").strip()
    if not name or not body:
        raise HTTPException(400, "name & body wajib diisi")

    # tag: gabungan tag chart terpilih + tag bebas
    tags: list[str] = []
    for cid in payload.get("charts", []):
        spec = knowledge.CHART_TAGS.get(cid)
        if spec:
            for t in spec["tags"]:
                if t not in tags:
                    tags.append(t)
    for t in payload.get("extra_tags", []):
        t = str(t).strip()
        if t and t not in tags:
            tags.append(t)

    safe = re.sub(r"[^A-Za-z0-9._-]", "-", name.lower())
    dest = knowledge.KNOWLEDGE_DIR / f"{safe}.md"
    knowledge.KNOWLEDGE_DIR.mkdir(exist_ok=True)
    dest.write_text(
        f"tags: {', '.join(tags)}\n"
        f"status: ditulis via dashboard — menunggu review\n\n{body}\n",
        encoding="utf-8",
    )
    return {"ok": True, "saved": f"{safe}.md", "tags": tags}


@app.get("/v1/integration/contract", tags=["frontend"],
         summary="Kontrak integrasi (endpoint + MCP tools + MQTT)")
def integration_contract() -> dict:
    return contract.spec_export()


@app.get("/v1/regret", tags=["frontend"],
         summary="Regret meter 8 jam: aktual vs counterfactual + deret + handover")
def regret_window(scenario_id: int, hour: int) -> dict:
    from src.advisory import providers
    from src.optimize import regret

    seq = _sequence(scenario_id)
    lo = max(0, hour - 7)
    window = seq.iloc[lo:hour + 1]
    rg = regret.shift_regret(window)
    series = regret.shift_series(window)
    co2 = float(window["red_mud_t"].sum() * 0.023)
    stats = {
        "hour_start": int(lo), "hour_end": int(hour),
        "recovery_mean": float(window["recovery_pct"].mean()),
        "opex_sum": float(window["total_opex"].sum()),
        "red_mud_sum": float(window["red_mud_t"].sum()),
        "co2_t": co2,
        "silika_last": float(window["reactive_sio2_pct"].iloc[-1]),
        "silika_trend": ("naik" if window["reactive_sio2_pct"].iloc[-1]
                         > window["reactive_sio2_pct"].iloc[0] else "turun/stabil"),
        "n_advisories": 0, "n_critical": 0,
    }
    report, backend = providers.handover_report(stats)
    return {
        "actual": rg["actual"],
        "counterfactual": rg["counterfactual"],
        "delta": rg["delta"],
        "series": series.round(3).to_dict(orient="records"),
        "handover": report,
        "handover_backend": backend,
    }


@app.post("/v1/explain", tags=["frontend"],
          summary="Analisis AI satu chart (grounded + knowledge ber-sitasi)")
def explain(payload: dict = Body(...)) -> dict:
    from src.advisory import providers

    text, backend = providers.explain_chart(
        payload.get("title", "Chart"),
        payload.get("context", {}),
        payload.get("question", ""),
        payload.get("tags"),
    )
    return {"text": text, "backend": backend}


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
        "al_balance": {
            "feed_t": float(row.get("al_feed_t", 0.0)),
            "recycled_t": float(row.get("al_recycled_t", 0.0)),
            "lost_redmud_t": float(row.get("al_lost_redmud_t", 0.0)),
            "hydrate_t": float(row.get("hydrate_t", 0.0)),
        },
    }
