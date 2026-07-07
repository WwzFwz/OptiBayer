# 01 — Analisis Masalah (First-Principles)

## Mulai dari prinsip dasar: di mana uang & risiko di pabrik alumina?

Proses Bayer mengubah bauksit menjadi alumina lewat 4 tahap:
**digesti** (larutkan Al dengan NaOH panas) → **klarifikasi** (pisahkan residu = red mud)
→ **presipitasi** (endapkan Al(OH)₃ dengan seed) → **kalsinasi** (bakar jadi Al₂O₃).

Dari prinsip dasar, hanya ada 3 tuas nilai (value lever) di pabrik seperti ini:

| Tuas | Kenapa penting | Di data kita |
|---|---|---|
| **1. Recovery Al** | Setiap % Al yang tidak ter-recover = bijih terbuang ke red mud. Recovery di data: 78–97% → selisih 19 poin itu uang besar | `Alumunium Recovery Rate`, `Alumunium Lost in Red Mud` |
| **2. Biaya reagen (OPEX)** | NaOH adalah biaya operasional terbesar proses Bayer. Silika reaktif "memakan" NaOH (membentuk sodalit/DSP) — kerugian ganda: NaOH hilang + Al ikut hilang | `NaOH Consumed`, `Total NaOH OPEX`, `TOTAL OPEX` |
| **3. Red mud (ESG)** | 1–1.5 ton red mud per ton alumina, pH 11–13.5, limbah B3. Makin banyak Na & Al yang lolos ke red mud, makin mahal netralisasinya (lihat paper Abdul et al. 2024 tentang red mud Indonesia) | `Wet Red Mud Discharge`, `Alumunium Lost in Red Mud` |

**Ketiga tuas ini saling tarik-menarik.** Contoh: menaikkan suhu & konsentrasi NaOH menaikkan
recovery, tapi menaikkan OPEX. Bauksit dengan silika reaktif tinggi butuh strategi berbeda dari
bauksit bersih. Inilah masalah optimasi multi-objektif yang nyata.

## Masalah operasional yang sebenarnya

Komposisi bauksit **berubah-ubah setiap pengiriman** (di data: Al₂O₃ 49–63%, silika reaktif
1.5–8%) dan **tidak bisa dikendalikan** operator. Yang bisa dikendalikan hanyalah parameter
proses. Hari ini, penyesuaian setpoint umumnya berdasarkan pengalaman operator + trial-error —
lambat dan tidak optimal.

> **Rumusan masalah:**
> *"Diberikan komposisi bauksit yang masuk hari ini, berapa setpoint proses (suhu digester,
> konsentrasi NaOH, ukuran gerus, suhu presipitasi, rasio seed) yang menghasilkan kombinasi
> terbaik antara recovery, OPEX, dan volume red mud?"*

Ini persis ide teman kamu ("dari input komposisi X, buat dapat recovery 88%, berapa suhu &
konsentrasi yang perlu disesuaikan") — dan itu memang solusi yang tepat untuk data ini.
Istilah industrinya: **process digital twin + setpoint optimizer / advisory system**.

## Kenapa ini cocok untuk tema hackathon?

Tema "mineral processing" ANTAM mencakup: recovery improvement ✔, flowsheet/process
optimization ✔, tailing & water management ✔ (red mud + konsumsi air ada di data),
AI & data analytics ✔, ESG ✔. Satu solusi menyentuh 5 sub-tema sekaligus.

## Kenapa BUKAN solusi lain?

- **"AI pengolahan red mud"** (mis. optimasi dealkalisasi/karbonasi seperti di paper):
  ide bagus, tapi **data kalian tidak mendukungnya** — tidak ada kolom pH red mud, dosis CO₂,
  komposisi limbah kaya-Ca, dll. Harus bikin data sintesis baru dari nol. Cukup jadikan
  red mud sebagai **salah satu objektif** (minimalkan Al & Na yang hilang ke red mud) —
  narasi ESG-nya tetap dapat, tanpa keluar dari data yang ada.
- **Prediksi saja tanpa optimasi**: kurang "wow". Prediksi hanyalah komponen; nilai jualnya
  ada di *rekomendasi tindakan* (prescriptive, bukan sekadar predictive).
