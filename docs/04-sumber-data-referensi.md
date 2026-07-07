# 04 — Perlu Data Asli? Cari di Mana?

## Jawaban singkat

**Data operasional pabrik Bayer yang asli TIDAK tersedia publik** — itu rahasia dagang
setiap pabrik (Chalco, Alcoa, ANTAM, semua). Kamu tidak akan menemukannya di Kaggle atau
Google Dataset Search, jadi berhenti mencarinya; itu bukan kegagalanmu.

Strategi yang benar untuk hackathon (dan yang dilakukan industri juga):
**pakai data sintesis, tapi KALIBRASI dan VALIDASI rentangnya dengan angka dari literatur.**
Kredibilitas kalian datang dari sitasi, bukan dari dataset curian.

## Sumber untuk kalibrasi & sitasi (urut prioritas)

### 1. Paper yang sudah kamu punya (paling relevan — pakai ini!)
Abdul, Isworo, Mahaputra, Pintowantoro (2025), *Int. J. Environ. Sci. Technol.* 22:5159–5178 —
review red mud Indonesia dengan data internal PT Indonesia Chemical Alumina (Tayan).
Angka yang bisa dipakai untuk validasi:
- Digesti: 140–142 °C, NaOH ±105–175 g/L, ±90 menit → **cocok dengan rentang data sintesis**
- Bauksit Indonesia: 37.55–47% Al₂O₃, 16.83–30.12% SiO₂ total, 8.27–13.56% Fe₂O₃
- Red mud: 1–1.5 s/d 1–2 ton per ton alumina; pabrik 152 ribu ton/thn → 193 ribu ton red mud (2022)
- Biaya penanganan red mud: ±13 USD/ton red mud; 3 USD/ton alumina
- Washing red mud: Na 150 g/L → 15 g/L; moisture ±25%
- Regulasi: Permen LHK No. 6/2021 (pH tailing 7–10, air limbah 6–9)

### 2. Laporan publik ANTAM & pemerintah
- **Laporan Tahunan & Laporan Keberlanjutan ANTAM** (antam.com → Investor Relations):
  produksi & penjualan bauksit/alumina, proyek SGAR Mempawah, komitmen ESG. Untuk
  konteks bisnis di pitch deck, bukan untuk training.
- **Kementerian ESDM** (esdm.go.id, satu data ESDM): statistik produksi mineral nasional.
- **Booklet/statistik Ditjen Minerba**: cadangan bauksit per provinsi.

### 3. Data agregat industri global
- **International Aluminium Institute** (international-aluminium.org/statistics):
  produksi alumina dunia, intensitas energi proses Bayer — gratis, resmi.
- **USGS Mineral Commodity Summaries** (bauxite & alumina): harga, cadangan, produksi.

### 4. Literatur untuk parameter proses (kalau perlu memperbaiki generator)
- Husaini et al. (2014) — komposisi bauksit Tayan.
- Damayanti & Khareunissa (2017) — karakteristik red mud Tayan.
- Hind et al. (1999) — kimia proses Bayer (klasik, banyak angka operasional).

## Data tambahan yang layak DIBUAT/dicari sebelum hari-H

| Kebutuhan | Sumber | Effort |
|---|---|---|
| Harga NaOH & CaO aktual (USD/ton) agar OPEX bermakna | harga pasar publik (mis. caustic soda ±350–450 USD/ton) | 30 menit |
| Perbaiki generator: efisiensi digesti dibatasi ≤100%, tanpa OPEX negatif | minta teman regenerate | 1 jam |
| (Opsional) tambah noise pengukuran ±1–2% ke data agar model tidak "terlalu sempurna" | script sendiri | 30 menit |
| (Opsional) versi data dengan komposisi bauksit sesuai rentang Indonesia (Al₂O₃ 37–47%) | regenerate | 1 jam |

> Catatan: rentang Al₂O₃ di data sintesis (49–63%) lebih tinggi dari bauksit tercuci
> Indonesia menurut literatur (37–47%). Tidak fatal untuk demo, tapi kalau sempat,
> minta teman menyesuaikan — juri dari ANTAM akan menangkap detail seperti ini.
