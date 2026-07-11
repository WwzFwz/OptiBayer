# 14 — Batasan Sistem & Alasannya (jujur, untuk tim + slide)

> Prinsip: setiap batasan ditulis dengan AKAR SEBAB dan MITIGASI-nya. Sebagian
> besar bersumber dari data sintesis — artinya hilang sendiri saat data asli
> tahap 2 datang, ASAL arsitektur kita tetap disiplin (doc 09).
> Gunakan ini juga sebagai bank jawaban saat juri menyerang.

## A. Batasan karena DATA SINTESIS (akar sebab terbesar)

| # | Batasan | Alasan | Dampak | Mitigasi |
|---|---|---|---|---|
| A1 | R² 0.94–0.99 TIDAK membuktikan akurasi dunia nyata | Model mempelajari ulang simulator neraca massa deterministik Ainin — bukan pabrik | Angka absolut prediksi belum bisa dipegang untuk keputusan riil | Diakui terbuka; pipeline retrain 1 perintah (`train --data`); validasi sesungguhnya = data historian tahap 2 |
| A2 | Tidak ada dimensi waktu | Data = 1000 skenario independen, bukan time-series | "Real-time" di demo adalah REPLAY; tidak ada dead-time/inersia proses; anomaly detection = residual sederhana | Replay memutar baris NYATA (bukan karangan); interface Lapis 0 tipis — historian tinggal dicolok; fitur lag masuk roadmap (doc 07) |
| A3 | Skenario gangguan terbatas (hanya silika spike) | Satu-satunya variabel gangguan yang bervariasi kuat di data | Demo tidak bisa menunjukkan gangguan causticity, suhu drift, dll. | Skenario tambahan menyusul kalau Ainin regenerasi data |
| A4 | OPEX satuan abstrak | Generator tidak memakai harga reagen aktual | Angka "hemat X/jam" belum bisa dibaca sebagai rupiah | Konfigurasi harga (NaOH USD 400–600/t) + konversi indikatif; kalibrasi = tahap 2 |

## B. Batasan karena KOLOM KONSTAN di data (doc 06 Bag. 6)

| # | Batasan | Alasan | Dampak | Mitigasi |
|---|---|---|---|---|
| B1 | Soft sensor causticity = kalkulator stoikiometri, BUKAN ML | `causticity`, `na2co3_conv`, `naoh_carbonation` konstan → tidak ada sinyal untuk dilatih | Advisory dosis CaO memakai asumsi eksplisit (mis. 0.85 kg NaOH/kg SiO₂ utk DSP), bukan pola belajar | Capability detection: begitu kolom bervariasi (regenerasi Ainin / data asli), soft sensor ML menyala TANPA ubah kode |
| B2 | Mud washing bukan knob optimasi | `wash_water`, `wash_eff` konstan | Loss fisik NaOH di Sankey = estimasi residual, bukan hasil model | idem B1 |
| B3 | Tidak ada optimasi energi/steam | steam konstan 0.05 | OPEX hanya reagen | Jangan pernah diklaim; roadmap |

## C. Batasan karena BELUM DIKERJAKAN (utang teknis, bukan mustahil)

| # | Batasan | Alasan | Dampak | Rencana |
|---|---|---|---|---|
| C1 | "Confidence" advisory masih heuristik | Conformal prediction (MAPIE) belum dipasang | Label tinggi/sedang = aturan tangan, bukan jaminan statistik | ±1 jam kerja; prioritas #1 upgrade |
| C2 | Belum ada tabel benchmark model | Notebook linear vs LGBM vs XGB vs TabPFN belum dibuat | "Kenapa LightGBM?" baru dijawab argumen, belum bukti | ±2 jam; prioritas #2 |
| C3 | Belum ada deteksi out-of-distribution | Cek komposisi vs rentang training belum dipasang | Optimizer/prediksi bisa dieksploitasi di daerah data jarang (jebakan klasik surrogate optimization) | ±30 menit (bounds sudah ada di registry); prioritas #3 |
| C4 | Model OPEX terlemah (R² 0.936) | Rentang target sangat lebar (167–4260), belum di-log-transform | Prediksi OPEX kurang presisi di ujung rentang | ±15 menit |
| C5 | Goal-seek belum ada di UI | Prioritas layar diberikan ke advisory & Pareto | Hanya bisa via Python (doc 13 §4i) | Tambah form kecil kalau sempat |

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
