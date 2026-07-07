# 03 — Solusi yang Diusulkan & Arsitektur Teknis

## Nama kerja: **Bayer Process Advisor** (digital twin + setpoint optimizer)

> Operator memasukkan hasil assay bauksit yang baru datang → sistem merekomendasikan
> setpoint proses + menampilkan prediksi recovery, OPEX, dan red mud + trade-off-nya.

Ini solusi *prescriptive analytics* (memberi tindakan), bukan sekadar *predictive*
(memberi angka). Persis ide teman kamu, ditambah lapisan optimasi & ESG.

## Arsitektur: 3 lapis

```
[Input: assay bauksit + batas operasional]
        │
        ▼
┌─────────────────────────────────────────────┐
│ LAPIS 1 — SURROGATE MODEL (ML)              │
│ f(komposisi, setpoint) → recovery           │
│ g(komposisi, setpoint) → TOTAL OPEX         │
│ h(komposisi, setpoint) → red mud & Al loss  │
│ Algoritma: Gradient Boosting (XGBoost/LGBM) │
│ + SHAP untuk explainability                 │
└─────────────────────────────────────────────┘
        │  dipanggil ribuan kali oleh ↓
┌─────────────────────────────────────────────┐
│ LAPIS 2 — OPTIMIZER                         │
│ Cari setpoint (5 knob) yang optimal:        │
│  max recovery, min OPEX, min red mud        │
│ s.t. 140≤T≤150, 140≤NaOH≤160, dll           │
│ Algoritma: NSGA-II (pymoo) → Pareto front,  │
│ atau Optuna kalau mau single-objective      │
└─────────────────────────────────────────────┘
        │
┌─────────────────────────────────────────────┐
│ LAPIS 3 — DASHBOARD (Streamlit)             │
│ • form input assay bauksit                  │
│ • kartu rekomendasi setpoint                │
│ • prediksi recovery/OPEX/red mud vs baseline│
│ • kurva Pareto (geser slider "prioritas     │
│   biaya vs recovery vs ESG")                │
│ • SHAP: "kenapa rekomendasinya begini"      │
└─────────────────────────────────────────────┘
```

## Detail teknis per lapis

### Lapis 1 — Model prediksi
- **Fitur (input)**: 10 kolom komposisi + 5 kolom knob = 15 fitur. Buang 14 kolom konstan.
  Jangan pakai kolom antara (mis. `NaOH Consumed`) sebagai fitur — itu *hasil*, bukan
  *penyebab* (data leakage).
- **Target**: 3 model terpisah → `Recovery Rate`, `TOTAL OPEX`, `Wet Red Mud Discharge`
  (opsional: `Alumunium Lost in Red Mud`).
- **Validasi**: 5-fold CV, laporkan R² dan MAE. Dengan data dari simulator, R² akan tinggi
  (>0.95) — wajar, jelaskan kenapa.
- **Explainability**: SHAP summary plot. Cek apakah model menemukan "silika reaktif =
  musuh utama" (korelasi −0.91 di EDA) — ini bukti model konsisten dengan kimia proses.

### Lapis 2 — Optimizer
- Variabel keputusan: particle size, suhu digester, konsentrasi NaOH, suhu presipitasi,
  seed ratio (5 dimensi, kecil — NSGA-II selesai dalam detik).
- Komposisi bauksit = parameter tetap (given).
- Output: Pareto front recovery-vs-OPEX-vs-red-mud → user memilih titik operasinya.
- Mode kedua (ide teman kamu): *goal seeking* — "saya mau recovery 88%, cari setpoint
  termurah yang mencapainya" (constraint recovery ≥ 88%, minimize OPEX).

### Lapis 3 — Demo
- Streamlit cukup; satu file `app/app.py`. Jangan buang waktu bikin backend terpisah.
- Skenario demo yang kuat: bandingkan 2 bauksit — silika rendah (2%) vs tinggi (7%) —
  tunjukkan sistem merekomendasikan setpoint berbeda dan jelaskan kenapa.

## Narasi ESG (pembeda dari tim lain)

Red mud adalah limbah B3 dan isu terbesar industri alumina Indonesia (lihat
`04-sumber-data-referensi.md`). Setiap ton Al & Na yang gagal ter-recover berakhir di
red mud → menaikkan pH & biaya netralisasi → memperberat kolam penampungan.
Jadi optimizer kalian bukan hanya "menghemat OPEX", tapi juga **mengurangi volume dan
bahaya red mud dari hulu** — pencegahan, bukan pengobatan. Kutip regulasi
Permen LHK No. 6/2021 (tailing boleh dibuang hanya jika pH 7–10) untuk memperkuat urgensi.

## Batasan yang diakui jujur (tulis di slide!)

1. Model dilatih dari data sintesis (simulator neraca massa) — angka absolutnya belum
   terkalibrasi ke pabrik nyata; **pipeline-nya siap di-retrain dengan data historian**.
2. Steady-state, bukan dinamis — rekomendasi per batch/pengiriman bijih, bukan kontrol
   real-time (untuk itu perlu time-series + MPC, kerjaan riset lanjutan).
3. OPEX hanya mencakup reagen (NaOH + CaO), belum energi.
