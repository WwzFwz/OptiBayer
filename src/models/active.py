"""Active learning — "AI yang tahu apa yang tidak ia ketahui" (doc 12 I9).

PERTANYAAN YANG DIJAWAB. Tahap 2 proyek ini adalah mengambil data pabrik nyata.
Pengambilan data itu mahal: tiap titik uji berarti menggeser setpoint pabrik
sungguhan dan menunggu proses mantap berjam-jam. Jadi pertanyaannya bukan
"berapa banyak data yang kita butuh", melainkan **"titik operasi mana yang
paling berharga diukur lebih dulu"**. Modul ini menjawabnya dari model yang
sudah ada — sistem bukan cuma siap menelan data, tapi ikut memandu
pengambilannya.

SKOR. Sebuah kandidat bernilai tinggi kalau model PALING TIDAK YAKIN di sana.
Dua sumber ketidakpastian dipakai, keduanya sudah tersedia dan terukur:

1. **Ketidaksepakatan ML vs fisika** (`models/verify.verify`) — di titik mana
   surrogate menyimpang paling jauh dari kalkulator deterministik, relatif
   terhadap interval konformalnya sendiri. Inilah sinyal terkuat yang kita
   punya sekarang, karena kalkulator berperan sebagai kebenaran acuan selama
   fase data sintesis.
2. **Kelangkaan tetangga** — seberapa jarang daerah itu terwakili di data
   latih (jarak ke baris terdekat dalam ruang fitur ternormalisasi). Daerah
   jarang = model menebak, bukan mengingat.

Titik yang di luar amplop operasi aman TIDAK pernah disarankan: menyarankan
pabrik keluar batas aman demi mengumpulkan data adalah saran yang salah,
seberapa pun informatifnya secara statistik.

Pakai:
    python -m src.models.active -n 10
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import schema
from src.models import verify

# Bobot skor. Ketidaksepakatan fisika diberi porsi lebih besar karena ia
# mengukur kesalahan yang BISA DIBUKTIKAN, sedangkan kelangkaan hanya proksi.
BOBOT_SELISIH = 0.7
BOBOT_KELANGKAAN = 0.3


def _ruang_ternormalisasi(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = df[list(schema.FEATURES)].to_numpy(dtype=float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < 1e-9] = 1.0          # fitur konstan tidak boleh meledakkan jarak
    return (X - mu) / sd, mu, sd


def _kelangkaan(titik: dict, Z: np.ndarray, mu: np.ndarray,
                sd: np.ndarray) -> float:
    """Jarak ke baris latih TERDEKAT (ruang z-score). Besar = daerah jarang."""
    z = (np.array([float(titik[f]) for f in schema.FEATURES]) - mu) / sd
    return float(np.min(np.linalg.norm(Z - z, axis=1)))


def _kandidat_acak(df: pd.DataFrame, n: int, rng: np.random.Generator) -> list[dict]:
    """Kandidat realistis: komposisi baris nyata (tetap menjumlah 100%),
    knob disapu bebas di dalam amplop operasi aman.

    Komposisi TIDAK diundang acak — bauksit yang oksidanya tidak menjumlah 100%
    tidak akan pernah masuk pabrik, jadi mengusulkannya sebagai titik uji itu
    tidak berarti (lihat temuan di docs/21 §3).
    """
    idx = rng.integers(0, len(df), size=n)
    keluar = []
    for i in idx:
        row = df.iloc[int(i)]
        titik = {c: float(row[c]) for c in schema.INPUTS}
        for k in schema.KNOBS:
            lo, hi = schema.SAFE_BOUNDS[k]
            titik[k] = float(rng.uniform(lo, hi))
        keluar.append(titik)
    return keluar


def skor_titik(titik: dict, Z: np.ndarray, mu: np.ndarray,
               sd: np.ndarray) -> dict:
    """Nilai informasi satu kandidat titik uji."""
    comp = {c: titik[c] for c in schema.INPUTS}
    knobs = {c: titik[c] for c in schema.KNOBS}

    hasil = verify.verify(comp, knobs)
    # rasio = |ML - fisika| / toleransi; >1 berarti sudah di luar yang diakui
    rasio = [r.get("rasio", 0.0) for r in hasil["rows"]] or [0.0]
    selisih = float(max(rasio))

    langka = _kelangkaan(titik, Z, mu, sd)
    return {
        "selisih_fisika": round(selisih, 3),
        "kelangkaan": round(langka, 3),
        "target_paling_meleset": max(
            hasil["rows"], key=lambda r: r.get("rasio", 0.0))["label"]
        if hasil["rows"] else None,
        "knobs": {k: round(v, 2) for k, v in knobs.items()},
        "composition": {c: round(v, 3) for c, v in comp.items()},
    }


def usulkan(n: int = 10, n_kandidat: int = 300, seed: int = 0) -> dict:
    """Usulkan `n` titik uji paling bernilai untuk pengambilan data tahap 2."""
    from src.data.adapters import load_clean

    df = load_clean()
    Z, mu, sd = _ruang_ternormalisasi(df)
    rng = np.random.default_rng(seed)

    baris = [skor_titik(t, Z, mu, sd)
             for t in _kandidat_acak(df, n_kandidat, rng)]

    # normalkan tiap komponen ke 0..1 sebelum digabung, supaya satuan yang
    # berbeda (rasio vs jarak) tidak saling menenggelamkan
    def norm(nilai: list[float]) -> np.ndarray:
        a = np.array(nilai, dtype=float)
        rentang = a.max() - a.min()
        return (a - a.min()) / rentang if rentang > 1e-12 else np.zeros_like(a)

    s = norm([b["selisih_fisika"] for b in baris])
    k = norm([b["kelangkaan"] for b in baris])
    for i, b in enumerate(baris):
        b["skor"] = round(float(BOBOT_SELISIH * s[i] + BOBOT_KELANGKAAN * k[i]), 4)

    baris.sort(key=lambda b: -b["skor"])
    terpilih = baris[:n]

    return {
        "n_kandidat": n_kandidat,
        "n_usulan": len(terpilih),
        "bobot": {"selisih_fisika": BOBOT_SELISIH, "kelangkaan": BOBOT_KELANGKAAN},
        "catatan": (
            "Semua usulan berada DI DALAM amplop operasi aman (schema."
            "SAFE_BOUNDS) dan memakai komposisi bauksit nyata. Skor tinggi = "
            "model paling tidak yakin di sana, jadi mengukurnya paling banyak "
            "menambah pengetahuan per rupiah uji."
        ),
        "usulan": terpilih,
    }


def _cli() -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="Usulkan titik uji paling bernilai (active learning)")
    ap.add_argument("-n", type=int, default=10, help="jumlah usulan")
    ap.add_argument("--kandidat", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rep = usulkan(n=args.n, n_kandidat=args.kandidat)
    if args.json:
        print(json.dumps(rep, indent=2))
        return

    print(f"Usulan {rep['n_usulan']} titik uji teratas "
          f"(dari {rep['n_kandidat']} kandidat)")
    print("skor = 0.7*ketidaksepakatan ML-vs-fisika + 0.3*kelangkaan data\n")
    for i, u in enumerate(rep["usulan"], 1):
        kn = u["knobs"]
        print(f"{i:2d}. skor {u['skor']:.3f} | selisih {u['selisih_fisika']:.2f}x "
              f"| langka {u['kelangkaan']:.2f} | paling meleset: "
              f"{u['target_paling_meleset']}")
        print(f"    suhu {kn['digester_temp_c']}C, NaOH {kn['naoh_conc_gl']} g/L, "
              f"partikel {kn['particle_size_um']} um, "
              f"presip {kn['precip_temp_c']}C, seed {kn['seed_ratio']}")


if __name__ == "__main__":
    _cli()
