# 14 — Batasan Sistem & Alasannya (jujur, untuk tim + slide)

> Prinsip: setiap batasan ditulis dengan AKAR SEBAB dan MITIGASI-nya. Sebagian
> besar bersumber dari data sintesis — artinya hilang sendiri saat data asli
> tahap 2 datang, ASAL arsitektur kita tetap disiplin (doc 09).
> Gunakan ini juga sebagai bank jawaban saat juri menyerang.

## A. Batasan karena DATA SINTESIS (akar sebab terbesar)

| # | Batasan | Alasan | Dampak | Mitigasi |
|---|---|---|---|---|
| A1 | R² 0.94–0.99 TIDAK membuktikan akurasi dunia nyata | Model mempelajari ulang simulator neraca massa deterministik Ainin — bukan pabrik | Angka absolut prediksi belum bisa dipegang untuk keputusan riil | Diakui terbuka **dan sekarang DIUKUR**: `python -m src.models.verify` melaporkan fidelitas surrogate thd kalkulator (NMAE 0.14–0.74% di kondisi realistis) — lihat docs/21 §3. Sirkularitas terverifikasi: target CSV reproduksi `mass_balance.run` dengan galat 0.000000%. Pipeline retrain 1 perintah; validasi sesungguhnya = data historian tahap 2 |
| A2 | Tidak ada dimensi waktu | Data = 1000 skenario independen, bukan time-series | "Real-time" di demo adalah REPLAY; tidak ada dead-time/inersia proses; anomaly detection = residual sederhana | Replay memutar baris NYATA (bukan karangan); interface Lapis 0 tipis — historian tinggal dicolok; fitur lag masuk roadmap (doc 07) |
| A3 | Skenario gangguan terbatas (hanya silika spike) | Satu-satunya variabel gangguan yang bervariasi kuat di data | Demo tidak bisa menunjukkan gangguan causticity, suhu drift, dll. | Skenario tambahan menyusul kalau Ainin regenerasi data |
| A4 | OPEX satuan abstrak | Generator tidak memakai harga reagen aktual | Angka "hemat X/jam" belum bisa dibaca sebagai rupiah | Konfigurasi harga (NaOH USD 400–600/t) + konversi indikatif; kalibrasi = tahap 2 |

## B. Batasan karena KOLOM KONSTAN di data (doc 06 Bag. 6)

| # | Batasan | Alasan | Dampak | Mitigasi |
|---|---|---|---|---|
| B1 | Soft sensor causticity = kalkulator stoikiometri, BUKAN ML | `causticity`, `na2co3_conv`, `naoh_carbonation` konstan → tidak ada sinyal untuk dilatih | Advisory dosis CaO memakai asumsi eksplisit (mis. 0.85 kg NaOH/kg SiO₂ utk DSP), bukan pola belajar | Capability detection: begitu kolom bervariasi (regenerasi Ainin / data asli), soft sensor ML menyala TANPA ubah kode |
| B2 | Mud washing bukan knob optimasi | `wash_water`, `wash_eff` konstan | Loss fisik NaOH di Sankey = estimasi residual, bukan hasil model | idem B1 |
| B3 | Tidak ada optimasi energi/steam | steam konstan 0.05 | OPEX hanya reagen | Jangan pernah diklaim; roadmap |

## C. Utang teknis — SELESAI (bukti terukur di docs/21)

Bagian ini dulu berisi lima utang. Semuanya sudah ditutup; empat dikerjakan,
satu ditolak justru karena diuji. Rinciannya ada di
**[docs/21-benchmark-model.md](21-benchmark-model.md)**.

| # | Dulu | Status sekarang | Bukti |
|---|---|---|---|
| C1 | "Confidence" advisory heuristik ("tinggi"/"sedang") | ✅ **Selesai** — interval konformal per target; kartu advisory memuat "recovery ±0.22 (interval 90%)" | Cakupan di data held-out 88.8–96.4% (nominal 90%); dijaga `tests/test_model_trust.py` |
| C2 | Belum ada benchmark model | ✅ **Selesai** — 6 keluarga diadu per target, `python -m src.models.benchmark` | Ternyata LightGBM kalah di 3 dari 4 target; model kini dipilih PER TARGET lewat CV (docs/21 §1) |
| C3 | Belum ada deteksi out-of-distribution | ✅ **Selesai** — `predict.ood_report()` dipakai optimizer, advisory, DAN Lab (dulu hanya layar Lab) | Galat naik 2–8× di luar rentang latih; guard juga memeriksa jumlah oksida ~100% (docs/21 §3) |
| C4 | OPEX perlu log-transform | ❌ **Ditolak dengan bukti** — log1p memperburuk (R² 0.945→0.924, MAE 518→607); asumsi "rentang 167–4260" berasal dari data v1, data v2 skew-nya negatif | docs/21 §5 |
| C5 | Goal-seek belum ada di UI | ✅ **Selesai** — form "Cari setpoint termurah" di Prediction Lab React, hasilnya langsung dimuat ke slider | `frontend/src/components/pages/Lab.tsx` |

### Yang muncul saat mengerjakannya (tidak ada di daftar awal)

| Temuan | Kenapa penting |
|---|---|
| **Winner's curse optimizer** — selisih ML vs fisika di setpoint rekomendasi jauh lebih besar daripada di titik acak (melampaui interval pada 6–25% kasus) | Angka delta yang dilihat operator kini dihitung ulang dengan neraca massa eksak. ML sempat melebih-lebihkan perbaikan recovery ~22% (docs/21 §4) |
| **Guard kotak per-fitur memberi rasa aman palsu** — titik yang "sah" per fitur bisa membuat kalkulator fisika mengeluarkan OPEX negatif | Guard OOD ditambah cek plausibilitas komposisi (semua baris latih berjumlah 99.97–100.02%) |
| **Klaim kecepatan surrogate**: terukur ~5× lebih cepat dari fisika, bukan ribuan kali | Supaya tidak ada angka karangan di pitch. Nilai ML yang sebenarnya: bisa dilatih pada data historian yang tak punya rumus tertutup |

## D. Batasan METODOLOGIS yang melekat (tetap ada meski data asli datang)

| # | Batasan | Alasan | Cara menyikapi |
|---|---|---|---|
| D1 | Kurva Ceq belum terkalibrasi pabrik | Korelasi Misra generik dari literatur | Dipakai sebagai OVERLAY ARAH (gap supersaturasi), bukan angka absolut; kalibrasi butuh data liquor asli |
| D2 | Koefisien karbonasi dari satu paper | 2.3 g CO₂/100 g RM adalah hasil eksperimen red mud tertentu; red mud ANTAM bisa berbeda komposisi | Ditampilkan sebagai potensi ber-sitasi; validasi = uji lab red mud sendiri |
| D3 | Ambang alarm & advisory di-set manual | Silika 5.5/6.3%, pita CaO ±15% = pilihan engineering, bukan hasil belajar | Wajar di industri (alarm limit memang di-set engineer); bisa dikaji ulang dengan data historis alarm |
| D4 | Steady-state, bukan kontrol dinamis | Rekomendasi per kondisi, bukan MPC | Fase 3 roadmap (doc 07); advisory human-in-the-loop memang desain yang dituju untuk fase awal |
| D5 | Rekomendasi optimal MENURUT MODEL | Semua optimizer surrogate mewarisi error modelnya | Guardrail bounds + (C3) OOD guard + human-in-the-loop sebagai lapisan pertahanan |

## Kalimat pembuka bagian batasan di pitch

> *"Kami tahu persis di mana sistem ini belum bisa dipercaya — dan kami
> mendesainnya agar setiap batasan itu hilang dengan data, bukan dengan
> menulis ulang kode. Tabel A–B hilang saat data asli masuk; tabel C adalah
> pekerjaan berjam-jam, bukan berbulan; tabel D kami kelola dengan guardrail
> dan human-in-the-loop."*
