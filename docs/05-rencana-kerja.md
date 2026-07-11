# 05 — Rencana Kerja

> ⚠ **Update 2026-07-11:** urutan kerja digantikan oleh **doc 11 (plan implementasi
> ber-milestone)**. Isi teknis di sini (preprocessing, model, jawaban juri) masih valid.

Estimasi total: ±4–6 hari kerja efektif untuk tim 2 orang. Prioritas dari atas ke bawah —
kalau waktu habis, potong dari bawah (Pareto & SHAP boleh dikorbankan, dashboard tidak).

## Fase 1 — Data & EDA (½–1 hari)
- [ ] `src/preprocess.py`: load cp1252, sep `;`, bersihkan `%` dan desimal koma
- [ ] Drop 14 kolom konstan + kolom kosong `KONSENTRASI DLL`
- [ ] Bersihkan cacat: clip digestion efficiency ke 100%, drop baris OPEX/make-up negatif
- [ ] Simpan hasil ke `data/processed/clean.parquet` (atau csv)
- [ ] `notebooks/01-eda.ipynb`: distribusi, korelasi, scatter recovery vs silika reaktif
      (grafik "silika = musuh" ini nanti masuk slide)

## Fase 2 — Model surrogate (1 hari)
- [ ] `src/train.py`: 3 model XGBoost/LightGBM → recovery, TOTAL OPEX, red mud
- [ ] Fitur = 10 komposisi + 5 knob SAJA (hindari leakage dari kolom antara)
- [ ] 5-fold CV, catat R²/MAE → `models/metrics.json`
- [ ] SHAP summary plot per model → simpan PNG untuk slide

## Fase 3 — Optimizer (1 hari)
- [ ] `src/optimize.py`: NSGA-II (pymoo) — variabel: 5 knob dalam rentang data;
      objektif: max recovery, min OPEX, min red mud
- [ ] Mode goal-seek: "target recovery X% → setpoint ter-murah" (Optuna/scipy)
- [ ] Uji dengan 2 skenario: bauksit silika 2% vs 7% → pastikan rekomendasi berbeda & masuk akal

## Fase 4 — Dashboard demo (1 hari)
- [ ] `app/app.py` (Streamlit): input assay → rekomendasi setpoint + prediksi + Pareto slider
- [ ] Tampilkan delta vs "setpoint rata-rata" (baseline): "+3.2% recovery, −8% OPEX"
- [ ] Panel "kenapa?" (SHAP force plot sederhana)

## Fase 5 — Pitch (½–1 hari)
- [ ] Slide: masalah (3 tuas nilai) → solusi → demo → ESG → roadmap ke data pabrik nyata
- [ ] Siapkan jawaban untuk pertanyaan juri yang PASTI keluar:
  1. *"Datanya sintesis, memangnya valid?"* → rentang dikalibrasi literatur (140–142 °C,
     NaOH 105–175 g/L, Abdul et al. 2025); arsitektur data-agnostic, tinggal retrain
     dengan data historian ANTAM.
  2. *"Bedanya dengan yang operator sudah lakukan?"* → konsisten, kuantitatif, multi-objektif,
     dan menangkap interaksi non-linear antar 15 variabel yang tidak bisa di-tuning manual.
  3. *"Kok R² tinggi banget?"* → karena surrogate dari simulator; di data nyata pasti turun,
     dan itu justru alasan butuh pilot dengan data ANTAM.

## Pembagian tugas yang disarankan
- **Kamu (informatika)**: Fase 1, 2, 4 (pipeline ML + dashboard)
- **Teman (pembuat data/paham proses)**: validasi fisik hasil optimizer (Fase 3),
  perbaikan generator data, narasi proses di pitch
