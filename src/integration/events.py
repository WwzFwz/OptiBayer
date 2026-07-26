"""Tier 2 doc 07: aliran event ke jaringan OT (MQTT) — kini nyata.

Selama ini `contract.spec_export()` menjanjikan tiga topik MQTT sebagai
rencana, tanpa ada yang menerbitkannya. Modul ini menutup jarak itu dengan
tetap memegang dua batasan yang membuatnya aman dikirim sekarang:

1. **Transport bisa diganti.** Broker MQTT tidak ada di laptop juri dan tidak
   boleh jadi syarat demo. Default-nya `LogSink` (mencetak event) dan
   `MemorySink` (untuk uji); `MqttSink` baru dipakai kalau broker dikonfigurasi.
   Karena itu seluruh alur bisa diuji tanpa broker sama sekali.
2. **Satu arah, keluar saja.** Sistem MENERBITKAN pengamatan; ia tidak pernah
   menerima perintah dan tidak pernah menulis setpoint (doc 07 keamanan).
   Jaringan OT hanya perlu membuka satu arah.

Topik mengikuti daftar di `contract.spec_export()["events_mqtt"]["topics"]`
supaya kontrak dan implementasi tidak bisa berbeda diam-diam.

Pakai:
    from src.integration import events
    bus = events.Bus()                       # default: cetak ke log
    bus.publish_kpi(jam=8, kpi={...})
    bus.publish_advisory(jam=8, cards=[...])
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

TOPIK_ADVISORY_CRITICAL = "optibayer/advisory/critical"
TOPIK_ADVISORY_ALL = "optibayer/advisory/all"
TOPIK_KPI = "optibayer/kpi/hourly"

TOPIK = (TOPIK_ADVISORY_CRITICAL, TOPIK_ADVISORY_ALL, TOPIK_KPI)


# ------------------------------------------------------------------ sinks
class Sink(Protocol):
    """Tujuan penerbitan event. Sengaja sekecil ini supaya mudah diganti."""

    def kirim(self, topik: str, muatan: dict) -> None: ...


@dataclass
class MemorySink:
    """Menyimpan event di memori — dipakai uji & mode kering."""

    terkirim: list[tuple[str, dict]] = field(default_factory=list)

    def kirim(self, topik: str, muatan: dict) -> None:
        self.terkirim.append((topik, muatan))

    def topik_saja(self) -> list[str]:
        return [t for t, _ in self.terkirim]


@dataclass
class LogSink:
    """Mencetak event sebagai satu baris JSON — cukup untuk demo & debugging."""

    prefix: str = "[event]"

    def kirim(self, topik: str, muatan: dict) -> None:
        print(f"{self.prefix} {topik} {json.dumps(muatan, ensure_ascii=False, default=str)}",
              flush=True)


class MqttSink:
    """Penerbit MQTT sungguhan. `paho-mqtt` diimpor SAAT DIPAKAI saja.

    Dengan begitu repo tidak menambah dependensi wajib hanya demi jalur yang
    baru hidup di lingkungan pabrik.
    """

    def __init__(self, host: str, port: int = 1883, *,
                 username: str | None = None, password: str | None = None,
                 client_id: str = "optibayer", qos: int = 1):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as e:  # pragma: no cover - bergantung lingkungan
            raise RuntimeError(
                "MqttSink butuh paket `paho-mqtt` (pip install paho-mqtt). "
                "Untuk demo tanpa broker, pakai LogSink/MemorySink."
            ) from e

        self.qos = qos
        self._client = mqtt.Client(client_id=client_id)
        if username:
            self._client.username_pw_set(username, password or "")
        self._client.connect(host, port)
        self._client.loop_start()

    def kirim(self, topik: str, muatan: dict) -> None:  # pragma: no cover
        self._client.publish(
            topik, json.dumps(muatan, ensure_ascii=False, default=str),
            qos=self.qos)

    def close(self) -> None:  # pragma: no cover
        self._client.loop_stop()
        self._client.disconnect()


def sink_dari_env() -> Sink:
    """Pilih transport dari environment — default aman (tanpa broker).

    MQTT_HOST kosong  -> LogSink (demo/laptop)
    MQTT_HOST terisi  -> MqttSink (pabrik)
    """
    host = os.environ.get("MQTT_HOST", "").strip()
    if not host:
        return LogSink()
    return MqttSink(
        host,
        int(os.environ.get("MQTT_PORT", "1883")),
        username=os.environ.get("MQTT_USERNAME") or None,
        password=os.environ.get("MQTT_PASSWORD") or None,
    )


# -------------------------------------------------------------------- bus
def _sekarang() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Bus:
    """Penerbit event OptiBayer."""

    def __init__(self, sink: Sink | None = None, *, sumber: str = "optibayer"):
        self.sink = sink or sink_dari_env()
        self.sumber = sumber

    def _amplop(self, jenis: str, muatan: dict) -> dict:
        """Setiap event dibungkus sama: gampang dilacak di jaringan OT."""
        return {
            "sumber": self.sumber,
            "jenis": jenis,
            "waktu_utc": _sekarang(),
            **muatan,
        }

    def publish_kpi(self, jam: int, kpi: dict) -> dict:
        muatan = self._amplop("kpi_hourly", {"jam": int(jam), "kpi": kpi})
        self.sink.kirim(TOPIK_KPI, muatan)
        return muatan

    def publish_advisory(self, jam: int, cards: list[dict]) -> list[dict]:
        """Terbitkan kartu advisory.

        Semua kartu masuk topik `all`; yang ber-severity critical DIULANG ke
        topik `critical` supaya sistem alarm OT bisa berlangganan hanya ke
        yang genting tanpa menyaring sendiri.
        """
        terbit: list[dict] = []
        for kartu in cards:
            muatan = self._amplop("advisory", {"jam": int(jam), "kartu": kartu})
            self.sink.kirim(TOPIK_ADVISORY_ALL, muatan)
            if kartu.get("severity") == "critical":
                self.sink.kirim(TOPIK_ADVISORY_CRITICAL, muatan)
            terbit.append(muatan)
        return terbit

    def publish_jam(self, jam: int, kpi: dict, cards: list[dict]) -> dict:
        """Satu jam penuh: KPI + seluruh advisory-nya."""
        self.publish_kpi(jam, kpi)
        advisory = self.publish_advisory(jam, cards)
        return {"jam": jam, "n_advisory": len(advisory),
                "n_critical": sum(1 for c in cards
                                  if c.get("severity") == "critical")}
