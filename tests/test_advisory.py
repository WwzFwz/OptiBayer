"""Uji M3: replay + konteks advisory + kartu + provider (fallback template)."""

from src.advisory import context, providers, template


def test_replay_membangun_spike(seq_spike):
    s0 = seq_spike.iloc[0]["reactive_sio2_pct"]
    s30 = seq_spike.iloc[30]["reactive_sio2_pct"]
    assert s0 < 4.5 < s30, (s0, s30)


def test_context_menandai_silika_kritis(seq_spike, models_siap):
    ctx = context.build(seq_spike.iloc[30])
    assert ctx["silika_level"] == "critical"


def test_kartu_advisory_terurut_severity(seq_spike, models_siap):
    ctx = context.build(seq_spike.iloc[30])
    cards = template.cards(ctx)
    assert cards
    assert cards[0]["severity"] in ("critical", "serious")
    for c in cards:
        assert c["title"] and c["impact"] and c["action"]


def test_provider_fallback_template(seq_spike, models_siap):
    ctx = context.build(seq_spike.iloc[30])
    text, backend = providers.advise(ctx)
    assert backend == "template"
    assert len(text) > 100


def test_laporan_serah_terima():
    rep, backend = providers.handover_report({
        "hour_start": 0, "hour_end": 8, "recovery_mean": 88.0, "opex_sum": 26000,
        "red_mud_sum": 500, "co2_t": 11.5, "silika_last": 6.8,
        "silika_trend": "naik", "n_advisories": 4, "n_critical": 2,
    })
    assert backend == "template"
    assert "Serah Terima" in rep
