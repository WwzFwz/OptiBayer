"""Uji tier event MQTT (doc 07 tier 2) — tanpa broker sama sekali.

Justru itu poin desainnya: alur penerbitan harus bisa dibuktikan di laptop
juri, bukan hanya di jaringan pabrik.
"""

from __future__ import annotations

import json

from src.integration import contract, events


def test_topik_sama_dengan_kontrak():
    """Kontrak & implementasi tidak boleh berbeda diam-diam — halaman
    Integrasi memamerkan daftar topik dari kontrak, dan inilah yang benar-benar
    diterbitkan."""
    dari_kontrak = set(contract.spec_export()["events_mqtt"]["topics"])
    assert dari_kontrak == set(events.TOPIK)


def test_kpi_terbit_ke_topik_jam():
    sink = events.MemorySink()
    bus = events.Bus(sink)
    bus.publish_kpi(jam=8, kpi={"recovery_pct": 91.7})

    assert sink.topik_saja() == [events.TOPIK_KPI]
    _, muatan = sink.terkirim[0]
    assert muatan["jam"] == 8
    assert muatan["kpi"]["recovery_pct"] == 91.7


def test_amplop_selalu_membawa_sumber_jenis_waktu():
    sink = events.MemorySink()
    events.Bus(sink).publish_kpi(1, {})
    _, muatan = sink.terkirim[0]
    for kunci in ("sumber", "jenis", "waktu_utc"):
        assert kunci in muatan, kunci
    assert muatan["waktu_utc"].endswith("+00:00")


def test_kartu_critical_diulang_ke_topik_alarm():
    """Sistem alarm OT harus bisa berlangganan HANYA yang genting."""
    sink = events.MemorySink()
    kartu = [
        {"severity": "critical", "title": "Silika reaktif 6.8%"},
        {"severity": "info", "title": "Potensi CCUS"},
    ]
    events.Bus(sink).publish_advisory(jam=30, cards=kartu)

    topik = sink.topik_saja()
    assert topik.count(events.TOPIK_ADVISORY_ALL) == 2
    assert topik.count(events.TOPIK_ADVISORY_CRITICAL) == 1

    _, genting = next(t for t in sink.terkirim
                      if t[0] == events.TOPIK_ADVISORY_CRITICAL)
    assert genting["kartu"]["severity"] == "critical"


def test_tanpa_kartu_tidak_menerbitkan_apa_pun():
    sink = events.MemorySink()
    events.Bus(sink).publish_advisory(jam=1, cards=[])
    assert sink.terkirim == []


def test_publish_jam_meringkas_dgn_benar():
    sink = events.MemorySink()
    kartu = [{"severity": "critical", "title": "a"},
             {"severity": "warning", "title": "b"}]
    ring = events.Bus(sink).publish_jam(8, {"recovery_pct": 90.0}, kartu)

    assert ring == {"jam": 8, "n_advisory": 2, "n_critical": 1}
    assert events.TOPIK_KPI in sink.topik_saja()


def test_muatan_bisa_diserialisasi_json():
    """Muatan MQTT harus JSON — kalau ada objek aneh, ia baru meledak di
    pabrik, bukan di sini."""
    sink = events.MemorySink()
    events.Bus(sink).publish_jam(
        8, {"recovery_pct": 91.7}, [{"severity": "info", "title": "x"}])
    for _, muatan in sink.terkirim:
        json.loads(json.dumps(muatan, default=str))


def test_default_tanpa_broker_memakai_log(monkeypatch):
    """Demo di laptop tidak boleh menuntut broker."""
    monkeypatch.delenv("MQTT_HOST", raising=False)
    assert isinstance(events.sink_dari_env(), events.LogSink)


def test_log_sink_mencetak_satu_baris_json(capsys):
    events.Bus(events.LogSink()).publish_kpi(3, {"recovery_pct": 88.0})
    keluaran = capsys.readouterr().out.strip()
    assert keluaran.startswith("[event] optibayer/kpi/hourly ")
    json.loads(keluaran.split(" ", 2)[2])


def test_bus_dari_advisory_sungguhan(seq_spike, models_siap):
    """Uji sambungan sungguhan: konteks -> kartu -> event, tanpa dirakit tangan."""
    from src.advisory import context, template

    ctx = context.build(seq_spike.iloc[30], fast=True)
    kartu = template.cards(ctx)
    sink = events.MemorySink()
    ring = events.Bus(sink).publish_jam(30, ctx["predicted_now"], kartu)

    assert ring["n_advisory"] == len(kartu)
    assert len(sink.terkirim) >= len(kartu) + 1  # +1 utk KPI
