"""Inersia proses & dead-time — menjawab "rekomendasi Anda berlaku seketika?"

MASALAH YANG DIJAWAB (doc 14 A2). Data latih adalah 1000 skenario steady-state
yang saling bebas, tanpa sumbu waktu sama sekali. Akibatnya seluruh model —
surrogate maupun kalkulator neraca massa — menjawab pertanyaan "kalau kondisi
MANTAP begini, hasilnya berapa?", bukan "berapa lama sampai ke sana". Dashboard
yang menampilkan lompatan seketika dari setpoint lama ke recovery baru
menjanjikan sesuatu yang tidak pernah terjadi di pabrik: digester punya volume,
liquor punya waktu tinggal, presipitator butuh jam untuk mengendap.

APA YANG MODUL INI *BUKAN*. Ini BUKAN model yang dipelajari dari data — tidak
mungkin, datanya memang tidak punya waktu. Ini model rekayasa orde-1 +
dead-time (bentuk paling standar untuk respons proses kimia), dengan tetapan
waktu yang DIPILIH INSINYUR dari volume & laju alir tipikal, bukan hasil fit.
Setiap keluaran wajib ditandai demikian di UI. Begitu data historian nyata
datang, `tetapan_dari_data()` menggantikan tebakan ini dengan hasil identifikasi
— dan sisa kodenya tidak berubah.

MODEL. Untuk perubahan setpoint step pada t=0, respons keluaran:

    y(t) = y0                                   untuk t < L      (dead-time)
    y(t) = y0 + (y1 - y0)·(1 - exp(-(t-L)/T))   untuk t >= L

dengan L = dead-time (jam) dan T = tetapan waktu (jam). Sesudah 1T tercapai
63% perubahan, 3T sekitar 95%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Tetapan waktu per target, dalam JAM. Angka-angka ini adalah pilihan
# engineering dari orde besaran unit Bayer (waktu tinggal digester ~1 jam,
# sirkuit presipitasi berjam-jam, kolam red mud paling lambat), BUKAN hasil
# belajar dari data. Diletakkan di satu tempat supaya gampang diganti begitu
# data historian memberi angka sebenarnya.
TETAPAN_DEFAULT: dict[str, tuple[float, float]] = {
    # target            (dead-time L, tetapan waktu T)
    "recovery_pct":     (0.5, 1.5),
    "total_opex":       (0.25, 1.0),
    "red_mud_t":        (0.75, 2.5),
    "precip_yield_pct": (1.0, 4.0),
}

# Dipakai kalau target tak dikenal — konservatif (lambat), supaya sistem tidak
# pernah menjanjikan respons lebih cepat daripada yang bisa dibuktikan.
TETAPAN_CADANGAN = (1.0, 3.0)

SUMBER_TETAPAN = "asumsi engineering (belum dikalibrasi data historian)"


@dataclass
class Respons:
    """Lintasan satu target dari nilai awal ke nilai mantap."""

    target: str
    awal: float
    mantap: float
    dead_time_jam: float
    tetapan_jam: float
    sumber: str = SUMBER_TETAPAN
    titik: list[dict] = field(default_factory=list)

    @property
    def t95_jam(self) -> float:
        """Kapan 95% perubahan tercapai — angka yang dipakai operator."""
        return self.dead_time_jam + 3.0 * self.tetapan_jam


def nilai_pada(awal: float, mantap: float, t_jam: float,
               dead_time_jam: float, tetapan_jam: float) -> float:
    """Nilai target pada jam ke-t setelah setpoint diubah di t=0."""
    if t_jam <= dead_time_jam:
        return float(awal)
    if tetapan_jam <= 0:
        return float(mantap)
    sisa = math.exp(-(t_jam - dead_time_jam) / tetapan_jam)
    return float(awal + (mantap - awal) * (1.0 - sisa))


def tetapan(target: str) -> tuple[float, float]:
    return TETAPAN_DEFAULT.get(target, TETAPAN_CADANGAN)


def respons(target: str, awal: float, mantap: float, *,
            horizon_jam: float | None = None, langkah: float = 0.25) -> Respons:
    """Lintasan lengkap satu target — bahan chart "kapan terasa".

    `horizon_jam` default = t95 dibulatkan ke atas, supaya chart selalu memuat
    seluruh cerita tanpa ekor datar yang panjang.
    """
    L, T = tetapan(target)
    r = Respons(target=target, awal=float(awal), mantap=float(mantap),
                dead_time_jam=L, tetapan_jam=T)
    batas = horizon_jam if horizon_jam is not None else math.ceil(r.t95_jam)
    n = max(2, int(round(batas / max(langkah, 1e-6))) + 1)
    r.titik = [
        {"jam": round(i * langkah, 3),
         "nilai": round(nilai_pada(awal, mantap, i * langkah, L, T), 4)}
        for i in range(n)
    ]
    return r


def respons_banyak(awal: dict[str, float], mantap: dict[str, float],
                   **kw) -> dict[str, Respons]:
    """Lintasan untuk semua target yang punya nilai awal DAN nilai mantap."""
    return {t: respons(t, awal[t], mantap[t], **kw)
            for t in mantap if t in awal}


def ringkasan(awal: dict[str, float], mantap: dict[str, float]) -> dict:
    """Ringkasan siap-tampil: berapa lama sampai terasa & sampai selesai.

    Dipakai kartu advisory supaya kalimat "recovery +1.3 pp" tidak dibaca
    operator sebagai "sekarang juga".
    """
    hasil = respons_banyak(awal, mantap)
    if not hasil:
        return {"tersedia": False, "sumber": SUMBER_TETAPAN}

    paling_lambat = max(hasil.values(), key=lambda r: r.t95_jam)
    return {
        "tersedia": True,
        "sumber": SUMBER_TETAPAN,
        "dead_time_jam": round(min(r.dead_time_jam for r in hasil.values()), 2),
        "t95_jam": round(paling_lambat.t95_jam, 2),
        "target_paling_lambat": paling_lambat.target,
        "per_target": {
            t: {"dead_time_jam": r.dead_time_jam, "tetapan_jam": r.tetapan_jam,
                "t95_jam": round(r.t95_jam, 2),
                "awal": round(r.awal, 3), "mantap": round(r.mantap, 3)}
            for t, r in hasil.items()
        },
    }


def tetapan_dari_data(df, kolom_waktu: str = "timestamp") -> dict:
    """Titik masuk identifikasi tetapan waktu dari data historian NYATA.

    Sengaja belum diimplementasikan: data saat ini tidak punya sumbu waktu
    (doc 14 A2), jadi mengarang prosedur identifikasi di atas data steady-state
    hanya akan menghasilkan angka yang terlihat ilmiah tapi tidak berarti.
    Fungsi ini ada sebagai KONTRAK: begitu historian tersedia, isinya diganti
    (identifikasi step-response / ARX) dan pemanggil di UI tidak perlu berubah.
    """
    raise NotImplementedError(
        "Identifikasi tetapan waktu butuh data time-series pabrik. "
        "Sampai itu ada, sistem memakai TETAPAN_DEFAULT dan menandainya "
        f"sebagai '{SUMBER_TETAPAN}' di setiap tampilan."
    )
