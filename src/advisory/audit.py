"""Audit trail keputusan advisory — SATU penulis untuk semua frontend.

LATAR. Fungsi ini dulu tertanam di `app/ui.py::_persist_decision`, sehingga
hanya Streamlit yang benar-benar mencatat keputusan operator. Frontend React
menyimpan keputusan di memori saja (`store.tsx`), jadi setiap refresh
menghapusnya dan halaman Audit Trail di React hanya menampilkan keputusan yang
dibuat di Streamlit. Untuk fitur yang dijual sebagai bahan compliance, itu
lubang nyata — modul ini menutupnya: Streamlit, REST API, dan MCP membaca &
menulis berkas yang sama lewat pintu yang sama.

Sengaja CSV, bukan basis data: audit trail harus bisa dibuka auditor pabrik
dengan Excel tanpa alat khusus, dan harus selamat walau prosesnya mati.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "data" / "processed" / "advisory_log.csv"

# Kolom "sumber" ditambahkan agar terlihat keputusan datang dari konsol mana.
KOLOM = ["waktu", "jam_sim", "judul", "keputusan", "sumber"]
KOLOM_LAMA = ["waktu", "jam_sim", "judul", "keputusan"]

KEPUTUSAN_SAH = ("terima", "tolak")


def _migrasi_bila_perlu(path: Path) -> None:
    """Berkas versi lama (4 kolom) dinaikkan ke skema 5 kolom.

    Tanpa ini, menambahkan baris 5-kolom ke berkas 4-kolom akan menggeser data
    dan merusak audit trail yang justru harus paling bisa dipercaya.
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open(newline="", encoding="utf-8") as f:
        baris = list(csv.reader(f))
    if not baris or baris[0] == KOLOM:
        return
    if baris[0] != KOLOM_LAMA:
        return  # format tak dikenal — jangan diutak-atik
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(KOLOM)
        for r in baris[1:]:
            if r:
                w.writerow([*r[:4], "streamlit"])


def append(hour: int, title: str, decision: str, sumber: str = "streamlit",
           path: Path | None = None) -> bool:
    """Catat satu keputusan. Mengembalikan True kalau tertulis.

    Kegagalan menulis TIDAK boleh mematikan dashboard (operator lebih butuh
    layarnya hidup daripada lognya lengkap), jadi galat ditelan dan dilaporkan
    lewat nilai balik.
    """
    if decision not in KEPUTUSAN_SAH:
        raise ValueError(f"keputusan harus salah satu dari {KEPUTUSAN_SAH}")
    p = path or LOG_PATH
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        _migrasi_bila_perlu(p)
        baru = not p.exists() or p.stat().st_size == 0
        with p.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if baru:
                w.writerow(KOLOM)
            w.writerow([
                datetime.now().isoformat(timespec="seconds"),
                int(hour), str(title), decision, sumber,
            ])
        return True
    except Exception:
        return False


def read(limit: int = 20, path: Path | None = None) -> dict:
    """Baca audit trail terakhir -> {"n_total": int, "decisions": [...]}"""
    p = path or LOG_PATH
    if not p.exists() or p.stat().st_size == 0:
        return {"n_total": 0, "decisions": []}
    try:
        with p.open(newline="", encoding="utf-8") as f:
            baris = list(csv.DictReader(f))
    except Exception:
        return {"n_total": 0, "decisions": []}
    return {"n_total": len(baris), "decisions": baris[-int(limit):]}
