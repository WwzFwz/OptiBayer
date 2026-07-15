"""Advisory deterministik (fallback P6): kartu APA/KENAPA/LAKUKAN tanpa LLM.

Format kartu SAMA PERSIS dengan output provider LLM, jadi UI tidak peduli
backend mana yang aktif.
"""

from __future__ import annotations

from src import schema
from src.utils import converters

SEVERITY_ORDER = {"critical": 0, "serious": 1, "warning": 2, "info": 3}


def _fmt_knobs(knobs: dict) -> str:
    return ", ".join(
        f"{schema.label(k)}: {v:.1f}" for k, v in knobs.items()
    )


def cards(ctx: dict) -> list[dict]:
    """Susun kartu advisory dari konteks, urut severity lalu dampak."""
    out: list[dict] = []
    d = ctx["delta_if_followed"]

    # 1) Gangguan silika / peluang setpoint
    if ctx["silika_level"] in ("critical", "warning") or d.get("recovery_pct", 0) > 0.75:
        sev = "critical" if ctx["silika_level"] == "critical" else (
            "serious" if ctx["silika_level"] == "warning" else "warning"
        )
        sio2 = ctx["composition"]["reactive_sio2_pct"]
        why = "; ".join(
            f"{f['label']} = {f['value']:.1f} ({f['direction']} recovery)"
            for f in ctx["shap_factors"]
        )
        out.append({
            "severity": sev,
            "title": (
                f"Silika reaktif {sio2:.1f}% — di atas ambang"
                if ctx["silika_level"] != "normal"
                else "Setpoint saat ini belum optimal"
            ),
            "impact": (
                f"Jika rekomendasi diikuti: recovery {d['recovery_pct']:+.1f}%, "
                f"OPEX {d['total_opex']:+.0f}/jam, red mud {d['red_mud_t']:+.1f} t"
            ),
            "action": f"Sesuaikan setpoint → {_fmt_knobs(ctx['recommended_knobs'])}",
            "why": why,
            "confidence": "tinggi" if abs(d["recovery_pct"]) > 0.3 else "sedang",
        })

    # 2) Dosis CaO (kaustisasi soda mati — klaim #2 Ainin, fallback stoikiometri)
    ca = ctx["cao_advisory"]
    if ca["status"] in ("over-dosing", "under-dosing"):
        arah = ("Naikkan" if ca["status"] == "under-dosing" else "Turunkan")
        risiko = (
            "soda mati menumpuk → daya larut digester turun"
            if ca["status"] == "under-dosing"
            else "kapur berlebih → kerak & alumina hilang sebagai TCA"
        )
        cao_liter = converters.ton_to_liters(ca['cao_recommended_t'])
        out.append({
            "severity": "warning",
            "title": f"Dosis CaO {ca['status']} (estimasi stoikiometri)",
            "impact": f"Risiko: {risiko}",
            "action": (
                f"{arah} dosis CaO dari {ca['cao_actual_t']:.2f} → "
                f"{ca['cao_recommended_t']:.2f} t/jam "
                f"≈ **{cao_liter:,.0f} L slurry/jam**"
            ),
            "why": (
                f"Estimasi Na₂CO₃ terbentuk {ca['na2co3_est_t']:.2f} t; "
                "kaustisasi: Na₂CO₃ + Ca(OH)₂ → 2NaOH + CaCO₃"
            ),
            "confidence": "sedang (kalkulator fisika — soft sensor menunggu data bervariasi)",
        })

    # 3) Anomali residual
    if ctx["anomaly_recovery"]:
        act = ctx["actual"].get("recovery_pct", float("nan"))
        prd = ctx["predicted_now"]["recovery_pct"]
        out.append({
            "severity": "serious",
            "title": "Anomali: recovery aktual menyimpang dari prediksi model",
            "impact": f"Aktual {act:.1f}% vs prediksi {prd:.1f}%",
            "action": "Verifikasi assay bauksit & kalibrasi instrumen; cek hasil lab terakhir",
            "why": "Selisih melebihi 3× simpangan residual validasi silang model",
            "confidence": "tinggi",
        })

    # 4) Nilai karbonasi (info ESG)
    cb = ctx["carbonation"]
    out.append({
        "severity": "info",
        "title": "Potensi CCUS red mud (karbonasi akuatik langsung)",
        "impact": (
            f"{cb['red_mud_t']:.1f} t red mud → {cb['co2_sequestered_t']:.2f} t CO₂ "
            f"tersekuestrasi (≈ Rp{cb['carbon_value_idr']:,.0f})"
        ),
        "action": f"Kebutuhan air karbonasi (L/S 2:1): {cb['water_needed_t']:.0f} t",
        "why": "Koefisien paper 2026: 23 kg CO₂/ton RM; pH menuju pita layak Permen LHK 6/2021",
        "confidence": "koefisien literatur",
    })

    out.sort(key=lambda c: SEVERITY_ORDER.get(c["severity"], 9))
    return out


def narrative(ctx: dict) -> str:
    """Ringkasan markdown deterministik — dipakai saat provider LLM off/gagal."""
    lines = []
    for c in cards(ctx)[:3]:
        lines.append(f"**[{c['severity'].upper()}] {c['title']}**")
        lines.append(f"- Dampak: {c['impact']}")
        lines.append(f"- Tindakan: {c['action']}")
        lines.append(f"- Kenapa: {c['why']}")
        lines.append("")
    return "\n".join(lines)
