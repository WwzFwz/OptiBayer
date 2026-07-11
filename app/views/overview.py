"""Tab 1 — Overview: tren + pita alarm, log kejadian, regret meter, handover."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app import ui
from src.advisory import providers
from src.optimize import regret
from src.physics import carbonation


def render(seq: pd.DataFrame, hour: int):
    hist = seq.iloc[: hour + 1]
    x = hist.index

    c1, c2 = st.columns(2)
    c1.plotly_chart(
        ui.trend(x, hist["recovery_pct"], "Recovery", band=(85, 100),
                 color=ui.SERIES[0], title="Recovery Al (%)"),
        width="stretch",
    )
    c2.plotly_chart(
        ui.trend(x, hist["total_opex"], "OPEX", band=(0, 2500),
                 color=ui.SERIES[2], title="Total OPEX (/jam)"),
        width="stretch",
    )
    c3, c4 = st.columns(2)
    c3.plotly_chart(
        ui.trend(x, hist["reactive_sio2_pct"], "Silika", band=(0, 5.5),
                 color=ui.SERIES[4], title="Silika Reaktif Feed (%) — musuh utama"),
        width="stretch",
    )
    c4.plotly_chart(
        ui.trend(x, hist["red_mud_t"], "Red mud", band=(0, 75),
                 color=ui.SERIES[1], title="Red Mud Basah (ton)"),
        width="stretch",
    )

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("⏱ Regret Meter — nilai yang tertinggal")
        st.caption(
            "Counterfactual 8 jam terakhir: seandainya setpoint mengikuti advisory "
            "(dihitung ulang dari model, bukan klaim)."
        )
        if st.button("Hitung regret 8 jam terakhir"):
            with st.spinner("Me-replay counterfactual..."):
                rg = regret.shift_regret(hist.tail(8))
            d = rg["delta"]
            m1, m2, m3 = st.columns(3)
            m1.metric("Δ Recovery", f"{d['recovery_pct']:+.2f}%")
            m2.metric("Δ OPEX (8 jam)", f"{d['total_opex']:+,.0f}")
            m3.metric("Δ Red Mud", f"{d['red_mud_t']:+.1f} t")
            if d["recovery_pct"] > 0 or d["total_opex"] < 0:
                st.warning(
                    f"Dengan setpoint advisory: recovery rata-rata "
                    f"{rg['counterfactual']['recovery_pct']:.1f}% "
                    f"(aktual {rg['actual']['recovery_pct']:.1f}%). "
                    "Selisih ini adalah nilai yang bisa diambil.", icon="💸",
                )
            else:
                st.success("Operasi 8 jam terakhir sudah dekat optimal.", icon="✅")

    with right:
        st.subheader("📝 Laporan Serah Terima Shift")
        st.caption(f"Digenerate otomatis (backend: {providers.provider_name()}).")
        if st.button("Buat laporan shift"):
            last8 = hist.tail(8)
            co2 = carbonation.assess(float(last8["red_mud_t"].sum())).co2_sequestered_t
            log = st.session_state.get("advisory_log", [])
            summary = {
                "hour_start": int(last8.index[0]),
                "hour_end": int(last8.index[-1]),
                "recovery_mean": float(last8["recovery_pct"].mean()),
                "opex_sum": float(last8["total_opex"].sum()),
                "red_mud_sum": float(last8["red_mud_t"].sum()),
                "co2_t": co2,
                "silika_last": float(last8["reactive_sio2_pct"].iloc[-1]),
                "silika_trend": (
                    "naik" if last8["reactive_sio2_pct"].iloc[-1]
                    > last8["reactive_sio2_pct"].iloc[0] + 0.3 else "stabil"
                ),
                "n_advisories": len(log),
                "n_critical": sum(1 for l in log if "silika" in l["title"].lower()),
                "keputusan_operator": log[-5:],
            }
            with st.spinner("Menulis laporan..."):
                report, backend = providers.handover_report(summary)
            st.markdown(report)
            st.caption(f"backend: {backend}")

    st.divider()
    st.subheader("📋 Audit Trail Keputusan Operator")
    log = st.session_state.get("advisory_log", [])
    if log:
        st.dataframe(pd.DataFrame(log), width="stretch", hide_index=True)
    else:
        st.caption("Belum ada keputusan advisory yang dicatat di sesi ini.")
