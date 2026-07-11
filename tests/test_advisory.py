"""Uji M3: replay + konteks advisory + kartu + provider (fallback template)."""

import time

from src.advisory import context, providers, template
from src.data import replay
from src.data.adapters import load_clean


def main():
    df = load_clean()
    seq = replay.build_sequence(df, replay.SCENARIOS[1])
    s0 = seq.iloc[0]["reactive_sio2_pct"]
    s30 = seq.iloc[30]["reactive_sio2_pct"]
    assert s0 < 4.5 < s30, (s0, s30)
    print(f"seq {len(seq)} baris; silika jam0={s0:.1f}% -> jam30={s30:.1f}% (spike OK)")

    t0 = time.time()
    ctx = context.build(seq.iloc[30])
    dt = time.time() - t0
    assert ctx["silika_level"] == "critical"
    print(f"context {dt:.1f} dtk; silika_level={ctx['silika_level']}")

    cards = template.cards(ctx)
    assert cards and cards[0]["severity"] in ("critical", "serious")
    for c in cards[:3]:
        print(f"[{c['severity']}] {c['title']}")

    text, backend = providers.advise(ctx)
    assert backend == "template" and len(text) > 100
    rep, b = providers.handover_report({
        "hour_start": 0, "hour_end": 8, "recovery_mean": 88.0, "opex_sum": 26000,
        "red_mud_sum": 500, "co2_t": 11.5, "silika_last": 6.8,
        "silika_trend": "naik", "n_advisories": 4, "n_critical": 2,
    })
    assert b == "template" and "Serah Terima" in rep
    print("provider fallback template OK; handover OK")
    print("M3 (engine) OK")


if __name__ == "__main__":
    main()
