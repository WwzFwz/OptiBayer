"""Kontrak integrasi OptiBayer — SATU sumber untuk semua antarmuka.

Desain 3 tier di doc 07: REST API, event MQTT, MCP server. File ini adalah
persiapannya yang bisa dikirim sekarang: definisi endpoint/tool sebagai DATA
(path, skema ringkas, contoh payload, fungsi inti yang dipanggil), sehingga:

- Halaman "Integrasi" di dashboard me-render tabel kontrak + playground
  (panggilan in-process — mesin yang sama, tanpa proses server baru).
- Wrapper Flask (REST) dan MCP server tinggal iterasi ENDPOINTS yang sama —
  tidak ada duplikasi definisi. (Wrapper TIDAK dipasang pra-demo: bentrok
  dependensi starlette/fastapi tercatat di doc 07.)

Semua operasi READ-ONLY terhadap pabrik (doc 07 keamanan).
"""

from __future__ import annotations

import time

from src import schema

# contoh komposisi/knob (≈ rata-rata data v2) — payload siap-edit di playground
EXAMPLE_COMPOSITION = {
    "al2o3_pct": 56.0, "reactive_sio2_pct": 4.7, "fe2o3_pct": 18.5,
    "tio2_pct": 1.6, "cao_pct": 0.9, "mgo_pct": 0.6, "na2o_pct": 0.15,
    "k2o_pct": 0.3, "cr2o3_pct": 0.08, "others_pct": 17.17,
}
EXAMPLE_KNOBS = {
    "particle_size_um": 62.0, "digester_temp_c": 145.0,
    "naoh_conc_gl": 150.0, "precip_temp_c": 60.0, "seed_ratio": 2.5,
}


def _op_predict(p: dict) -> dict:
    from src.models import predict
    return predict.predict_one(p["composition"], p["knobs"])


def _op_mass_balance(p: dict) -> dict:
    from src.physics import mass_balance
    return mass_balance.run_dict(
        p["composition"], p["knobs"],
        wet_feed_t=float(p.get("wet_feed_t", 1000.0)),
        moisture_frac=float(p.get("moisture_frac", 0.2)),
    )


def _op_pareto(p: dict) -> dict:
    from src.optimize import pareto
    pf = pareto.pareto(p["composition"])
    picked = pareto.pick(pf)
    return {
        "n_solutions": int(len(pf)),
        "picked_balanced": {k: round(float(v), 4) for k, v in picked.items()},
        "solutions_top10": pf.head(10).round(4).to_dict(orient="records"),
    }


def _op_goal_seek(p: dict) -> dict:
    from src.optimize import goal_seek
    res = goal_seek.cheapest_for_recovery(
        p["composition"], float(p["target_recovery"])
    )
    return res if res else {"feasible": False,
                            "note": "target recovery tak tercapai utk komposisi ini"}


def _op_knowledge(p: dict) -> dict:
    from src.advisory import knowledge
    docs = knowledge.for_tags(p.get("tags") or [])
    return {"n_docs": len(docs), "docs": [
        {"name": d["name"], "tags": d["tags"], "status": d["status"],
         "chars": len(d["body"])} for d in docs]}


def _op_audit(p: dict) -> dict:
    from src.advisory import audit
    return audit.read(limit=int(p.get("limit", 20)))


ENDPOINTS: list[dict] = [
    {
        "id": "predict", "method": "POST", "path": "/v1/predict",
        "summary": "Prediksi 4 target dari komposisi + setpoint (surrogate ML)",
        "consumer": "HMI, BI, what-if eksternal",
        "example": {"composition": EXAMPLE_COMPOSITION, "knobs": EXAMPLE_KNOBS},
        "fn": _op_predict, "playground": True,
    },
    {
        "id": "mass_balance", "method": "POST", "path": "/v1/mass-balance",
        "summary": "Neraca massa deterministik (port formula xlsm) — cross-check ML",
        "consumer": "engineering, validasi",
        "example": {"composition": EXAMPLE_COMPOSITION, "knobs": EXAMPLE_KNOBS,
                    "wet_feed_t": 1000.0, "moisture_frac": 0.2},
        "fn": _op_mass_balance, "playground": True,
    },
    {
        "id": "pareto", "method": "POST", "path": "/v1/optimize/pareto",
        "summary": "Pareto NSGA-II carbon-aware utk satu komposisi feed",
        "consumer": "advisory eksternal, planner",
        "example": {"composition": EXAMPLE_COMPOSITION},
        "fn": _op_pareto, "playground": True,
    },
    {
        "id": "goal_seek", "method": "POST", "path": "/v1/optimize/goal-seek",
        "summary": "Setpoint OPEX-minimum dengan recovery >= target",
        "consumer": "planner produksi",
        "example": {"composition": EXAMPLE_COMPOSITION, "target_recovery": 88.0},
        "fn": _op_goal_seek, "playground": True,
    },
    {
        "id": "knowledge", "method": "GET", "path": "/v1/knowledge?tags=",
        "summary": "Dokumen pengetahuan expert ber-tag (Knowledge Pack)",
        "consumer": "copilot lain, portal SOP",
        "example": {"tags": ["naoh", "kaustisasi"]},
        "fn": _op_knowledge, "playground": True,
    },
    {
        "id": "audit", "method": "GET", "path": "/v1/audit/decisions",
        "summary": "Audit trail keputusan advisory (persisten)",
        "consumer": "compliance, pelaporan",
        "example": {"limit": 20},
        "fn": _op_audit, "playground": True,
    },
    {
        "id": "advisory", "method": "POST", "path": "/v1/advisory/context",
        "summary": "Kartu advisory utk satu kondisi operasi penuh",
        "consumer": "notifikasi, mobile",
        "example": {"note": "butuh baris kondisi lengkap (historian) — "
                            "tersedia pada service penuh"},
        "fn": None, "playground": False,
    },
]

MCP_TOOLS: list[dict] = [
    {"name": f"optibayer_{e['id']}", "description": e["summary"],
     "maps_to": e["path"]}
    for e in ENDPOINTS if e["playground"]
]


def call(endpoint_id: str, payload: dict) -> tuple[dict, float]:
    """Jalankan operasi kontrak in-process -> (hasil, latensi_ms)."""
    ep = next(e for e in ENDPOINTS if e["id"] == endpoint_id)
    if not ep["playground"] or ep["fn"] is None:
        raise ValueError(f"endpoint '{endpoint_id}' belum tersedia di playground")
    t0 = time.perf_counter()
    result = ep["fn"](payload)
    return result, (time.perf_counter() - t0) * 1000.0


def spec_export() -> dict:
    """Spesifikasi ringkas (OpenAPI-gaya) + daftar tool MCP — utk tim IT."""
    return {
        "service": "OptiBayer Integration Contract",
        "version": "v1-draft",
        "security": "API-key/AD; READ-ONLY terhadap pabrik (doc 07)",
        "endpoints": [
            {k: e[k] for k in ("method", "path", "summary", "consumer")}
            | {"example_payload": e["example"]}
            for e in ENDPOINTS
        ],
        "mcp_tools": MCP_TOOLS,
        "events_mqtt": {
            "broker": "TBD (jaringan OT)",
            "topics": ["optibayer/advisory/critical",
                       "optibayer/advisory/all", "optibayer/kpi/hourly"],
        },
        "feature_names": {"composition": schema.INPUTS, "knobs": schema.KNOBS},
    }
