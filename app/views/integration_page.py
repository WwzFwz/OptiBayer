"""Halaman Integrasi — kontrak antarmuka + playground hidup.

Bukan mock: playground memanggil FUNGSI INTI YANG SAMA (in-process) dengan
yang kelak dibungkus REST/MCP, jadi integrator melihat request/response
sebenarnya. Desain 3 tier & alasan arsitekturnya: doc 07.
"""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app import ui
from src.integration import contract


def render() -> None:
    st.subheader("Integrasi — kontrak antarmuka & playground")
    st.caption(
        "Inti OptiBayer headless: dashboard ini hanyalah salah satu klien. "
        "Tiga tier integrasi (doc 07): **REST API** read-only untuk sistem "
        "pabrik/BI · **event MQTT** untuk mendorong advisory ke jaringan OT · "
        "**MCP server** agar LLM agent/copilot ANTAM memakai digital twin ini "
        "sebagai tools. Playground di bawah memanggil mesin yang sama persis — "
        "tanpa proses server baru."
    )

    # ---------- tabel kontrak ----------
    st.markdown("**Kontrak endpoint (v1, read-only)**")
    rows = [{"Method": e["method"], "Path": e["path"],
             "Fungsi": e["summary"], "Konsumen": e["consumer"],
             "Playground": "✓" if e["playground"] else "— (butuh historian)"}
            for e in contract.ENDPOINTS]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with st.expander("Tools MCP (agent-ready) & topik event MQTT"):
        c1, c2 = st.columns(2)
        c1.markdown("**MCP tools**\n" + "\n".join(
            f"- `{t['name']}` → `{t['maps_to']}`" for t in contract.MCP_TOOLS))
        c2.markdown(
            "**Topik MQTT (outbound)**\n"
            "- `optibayer/advisory/critical`\n"
            "- `optibayer/advisory/all`\n"
            "- `optibayer/kpi/hourly`"
        )

    st.download_button(
        "Unduh spesifikasi kontrak (JSON)",
        data=json.dumps(contract.spec_export(), indent=2, ensure_ascii=False),
        file_name="optibayer_integration_contract_v1.json",
        mime="application/json", icon=":material/download:",
    )

    st.divider()

    # ---------- playground ----------
    st.markdown("**Playground — coba panggil kontraknya**")
    st.caption(
        "Pilih endpoint, edit payload JSON, panggil. Respons & latensi berasal "
        "dari fungsi inti sungguhan (bukan data statis)."
    )
    ids = [e["id"] for e in contract.ENDPOINTS if e["playground"]]
    sel = st.selectbox(
        "Endpoint", ids, key="itg_ep",
        format_func=lambda i: next(
            f"{e['method']} {e['path']}" for e in contract.ENDPOINTS
            if e["id"] == i),
    )
    ep = next(e for e in contract.ENDPOINTS if e["id"] == sel)
    payload_text = st.text_area(
        "Payload (JSON)", json.dumps(ep["example"], indent=2),
        height=220, key=f"itg_payload_{sel}",
    )
    if st.button("Panggil endpoint", type="primary",
                 icon=":material/send:", key="itg_call"):
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as e:
            st.error(f"JSON tidak valid: {e}")
        else:
            try:
                with st.spinner("Memanggil fungsi inti..."):
                    result, ms = contract.call(sel, payload)
                st.session_state["itg_result"] = (sel, result, ms)
            except Exception as e:  # tampilkan apa adanya utk integrator
                st.error(f"Gagal: {type(e).__name__}: {e}")
    cached = st.session_state.get("itg_result")
    if cached and cached[0] == sel:
        _, result, ms = cached
        st.caption(f"Respons dalam **{ms:.0f} ms** (in-process)")
        st.json(result, expanded=2)

    st.caption(
        "Catatan: wrapper REST (Flask) & MCP server mengiterasi kontrak yang "
        "sama (`src/integration/contract.py`) — implementasinya PASCA-demo "
        "(catatan dependensi starlette/fastapi di doc 07)."
    )
