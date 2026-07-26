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


def _fmt_interval(ctx: dict, target: str, desimal: int = 1) -> str:
    """Teks interval konformal target, mis. '±0.7 (90%)'. Kosong kalau tak ada.

    Model yang dilatih sebelum fitur konformal ada tidak punya kuantil ini —
    dalam hal itu kita DIAM, bukan menampilkan angka yang tidak dihitung.
    """
    iv = (ctx.get("interval_now") or {}).get(target)
    if not iv:
        return ""
    return f"±{iv['half']:.{desimal}f} (interval {iv['level']:.0%})"


def _fmt_dinamika(ctx: dict) -> str:
    """Sisipan waktu: angka di kartu adalah kondisi MANTAP, bukan seketika.

    Tanpa ini operator wajar membaca "recovery +1.3 pp" sebagai sesuatu yang
    terjadi begitu tombol ditekan — padahal digester & presipitator punya
    inersia berjam-jam (doc 14 A2).
    """
    dyn = ctx.get("dinamika") or {}
    if not dyn.get("tersedia"):
        return ""
    return (f" — nilai MANTAP, terasa mulai ~{dyn['dead_time_jam']:.1f} jam, "
            f"tercapai ~{dyn['t95_jam']:.0f} jam")


def _confidence(ctx: dict, target: str = "recovery_pct", desimal: int = 1) -> str:
    """Label kepercayaan BERBASIS UKURAN: interval konformal + status guard.

    Menggantikan label tangan ("tinggi"/"sedang") yang dulu dipakai di sini —
    doc 14 C1. Urutan informasi: seberapa lebar ketidakpastiannya, lalu apakah
    titik operasinya masih di dalam wilayah yang dikuasai model, lalu apakah
    fisika setuju.
    """
    bagian = []
    iv = _fmt_interval(ctx, target, desimal)
    if iv:
        bagian.append(f"recovery {iv}")

    ood = ctx.get("ood") or {}
    if ood.get("alasan"):
        bagian.append("EKSTRAPOLASI: " + "; ".join(ood["alasan"]))
    elif ood:
        bagian.append("dalam rentang data latih")

    pc = ctx.get("physics_check") or {}
    if pc.get("rows"):
        bagian.append("cocok dgn neraca massa" if pc.get("ok")
                      else "BEDA dari neraca massa: " + ", ".join(pc["gagal_label"]))

    return " · ".join(bagian) if bagian else "—"


def cards(ctx: dict) -> list[dict]:
    """Susun kartu advisory dari konteks, urut severity lalu dampak."""
    out: list[dict] = []
    d = ctx["delta_if_followed"]

    # 1) Gangguan silika / peluang setpoint
    fast = bool(ctx.get("fast"))
    if ctx["silika_level"] in ("critical", "warning") or d.get("recovery_pct", 0) > 0.75:
        sev = "critical" if ctx["silika_level"] == "critical" else (
            "serious" if ctx["silika_level"] == "warning" else "warning"
        )
        sio2 = ctx["composition"]["reactive_sio2_pct"]
        title = (
            f"Silika reaktif {sio2:.1f}% — di atas ambang"
            if ctx["silika_level"] != "normal"
            else "Setpoint saat ini belum optimal"
        )
        if fast:
            # mode Play: optimizer dilewati agar tick mulus — jangan
            # menampilkan angka rekomendasi yang tidak dihitung
            out.append({
                "severity": sev,
                "title": title,
                "impact": (
                    f"Prediksi kondisi ini: recovery "
                    f"{ctx['predicted_now']['recovery_pct']:.1f}% "
                    f"{_fmt_interval(ctx, 'recovery_pct')}, OPEX "
                    f"{ctx['predicted_now']['total_opex']:,.0f}/jam"
                ),
                "action": "Tekan ⏸ Pause — rekomendasi setpoint penuh "
                          "(optimizer) dihitung saat berhenti",
                "why": "Mode Play memakai jalur ringan agar replay mulus",
                "confidence": _confidence(ctx),
            })
        else:
            why = "; ".join(
                f"{f['label']} = {f['value']:.1f} ({f['direction']} recovery)"
                for f in ctx["shap_factors"]
            )
            out.append({
                "severity": sev,
                "title": title,
                "impact": (
                    f"Jika rekomendasi diikuti: recovery {d['recovery_pct']:+.1f}%, "
                    f"OPEX {d['total_opex']:+.0f}/jam, red mud {d['red_mud_t']:+.1f} t "
                    f"({ctx.get('delta_basis', 'model')}){_fmt_dinamika(ctx)}"
                ),
                "action": f"Sesuaikan setpoint → {_fmt_knobs(ctx['recommended_knobs'])}",
                "why": why,
                "confidence": _confidence(ctx),
            })

    # 1b) Peringatan kalau perbaikan yang dijanjikan lebih kecil dari
    #     ketidakpastian model sendiri — operator berhak tahu bahwa "naik 0.2%"
    #     pada model dengan interval ±0.7% belum tentu naik sungguhan.
    iv_rec = (ctx.get("interval_now") or {}).get("recovery_pct")
    drec = abs(d.get("recovery_pct", 0.0))
    if iv_rec and 0 < drec < iv_rec["half"]:
        out.append({
            "severity": "info",
            "title": "Keunggulan setpoint ini tipis dibanding ketidakpastian model",
            "impact": (
                f"Perbaikan recovery {drec:.2f} pp ({ctx.get('delta_basis', 'model')}) "
                f"lebih kecil dari interval surrogate ±{iv_rec['half']:.2f} pp "
                f"({iv_rec['level']:.0%})"
            ),
            "action": "Perlakukan sebagai penyetelan halus — setpoint lain yang "
                      "hampir sama baiknya bisa saja sebenarnya lebih unggul",
            "why": "Optimizer memilih pakai surrogate; kalau selisih antar-kandidat "
                   "lebih kecil dari galat surrogate, urutan juaranya belum pasti",
            "confidence": _confidence(ctx),
        })

    # 1c) Guard out-of-distribution (doc 14 C3) — terukur: galat surrogate vs
    #     fisika naik 2-3x saat titik operasi keluar rentang latih.
    ood = ctx.get("ood") or {}
    if ood.get("alasan"):
        out.append({
            "severity": "serious",
            "title": "Rekomendasi berada di luar wilayah data latih",
            "impact": "; ".join(ood["alasan"]),
            "action": "Jangan terapkan langsung — verifikasi dengan kalkulator "
                      "neraca massa & pengalaman shift sebelum menyetel",
            "why": (
                "Uji fidelitas (src/models/verify.py): di luar rentang latih, "
                "galat surrogate terhadap fisika naik dari ~1.7% ke ~3.4% "
                "(p95 4.4% → 23.8%)"
            ),
            "confidence": _confidence(ctx),
        })

    # 1d) Wasit fisika tidak setuju dengan ML pada titik rekomendasi.
    pc = ctx.get("physics_check") or {}
    if pc.get("rows") and not pc.get("ok"):
        detail = "; ".join(
            f"{r['label']}: ML {r['ml']:,.1f} vs fisika {r['fisika']:,.1f}"
            for r in pc["rows"] if not r["ok"]
        )
        out.append({
            "severity": "warning",
            "title": "Surrogate menyimpang jauh dari neraca massa di setpoint ini",
            "impact": detail,
            "action": "Angka yang ditampilkan sudah memakai neraca massa, jadi "
                      "aman dibaca; laporkan ke tim data agar surrogate dilatih ulang "
                      "di daerah operasi ini",
            "why": "Selisih melampaui 2x interval konformal model — ambang "
                   "dikalibrasi dari sebaran selisih di setpoint rekomendasi",
            "confidence": _confidence(ctx),
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
            "confidence": _confidence(ctx),
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
