# 09 — Arsitektur v2 (Engineering View)

> Revisi arsitektur doc 03/06 setelah info kunci: **data asli yang lebih lengkap datang
> di tahap berikutnya**. Prinsip utama v2: *semua yang tahu tentang bentuk data
> dikurung di satu tempat; sisanya bekerja pada skema kanonik.*

## 1. Prinsip arsitektur (kenapa v2 berbeda dari v1)

| # | Prinsip | Wujud konkret |
|---|---|---|
| P1 | **Single source of schema** | `src/schema.py` — satu-satunya file yang tahu nama kolom mentah; sisanya pakai nama kanonik |
| P2 | **Adapter di pintu masuk** | sumber data apa pun (CSV sintesis, CSV asli, historian) → adapter → DataFrame kanonik |
| P3 | **Capability detection** | fitur app menyala/mati otomatis berdasarkan kolom yang tersedia & bervariasi |
| P4 | **Physics terpisah dari ML** | `src/physics/` murni deterministik, unit-testable, tidak butuh data training |
| P5 | **Model = artefak + metadata** | model tersimpan bersama daftar fitur, rentang valid, metrik → app tidak menebak |
| P6 | **Advisory ber-fallback** | strategi LLM dan template deterministik di balik satu interface |

## 2. Struktur kode

```
src/
├── schema.py            # P1: RAW_TO_CANONICAL mapping, ROLE tiap kolom
│                        #     (input | knob | intermediate | target | constant)
├── data/
│   ├── adapters.py      # P2: SyntheticCSVAdapter (cp1252, ';', koma desimal,
│   │                    #     clip/drop cacat) | RealDataAdapter (tahap 2, TBD)
│   │                    #     | HistorianAdapter (produksi, stub saja)
│   ├── validate.py      # range check fisik, kolom wajib, laporan kualitas
│   └── replay.py        # generator baris berurutan + injeksi gangguan
│                        #     (interface tipis — sumber time-series asli tinggal colok)
├── capability.py        # P3: periksa df → {surrogate: on, soft_sensor_causticity:
│                        #     off (kolom konstan), mud_washing_knob: off, ...}
├── models/
│   ├── train.py         # CLI: python -m src.models.train --data <path>
│   │                    #     latih semua target yang capability-nya ON
│   ├── registry.py      # P5: save/load model + {features, ranges, cv_metrics, hash data}
│   └── explain.py       # SHAP (summary global + per-prediksi untuk advisory)
├── physics/
│   ├── carbonation.py   # 23 kg CO2/ton RM, L/S 2:1, estimasi pH (paper 2026)
│   ├── precipitation.py # Ceq (korelasi Misra), gap supersaturasi
│   └── na_balance.py    # neraca Na + kaustisasi stoikiometrik → advisory dosis CaO
├── optimize/
│   ├── pareto.py        # NSGA-II (pymoo); baca bounds dari registry, clamp guardrail
│   └── goal_seek.py     # "recovery ≥ X, OPEX minimum"
└── advisory/
    ├── context.py       # rakit JSON: kondisi sekarang + SHAP + rekomendasi + alarm
    ├── providers.py     # P6: interface tunggal `advise(context) -> Card`, backend
    │                    #     dipilih via env LLM_PROVIDER:
    │                    #     "template" → deterministik, offline, TANPA AI (default)
    │                    #     "ollama"   → LLM lokal GRATIS (Qwen2.5-7B, tool-calling)
    │                    #     "groq"/"gemini" → free-tier cloud (gratis, butuh internet)
    │                    #     "claude"   → hanya jika ada sponsor/credit
    └── template.py      # fallback deterministik, format kartu sama persis

app/
├── app.py               # entry: header pabrik, play/pause replay, routing
└── views/               # 5 tab = 5 modul: overview, digestion, liquor_loop,
                         # precipitation, redmud_ccus — semua baca capability dulu

tests/
└── test_physics.py      # minimal: karbonasi & neraca Na (angka bisa diverifikasi manual)
```

## 3. Kontrak antar-lapis (yang membuatnya benar-benar scalable)

```
[Adapter] ──► DataFrame KANONIK (nama kolom standar, satuan standar, sudah bersih)
                 │  kontrak: validate.py lulus
                 ▼
[capability.py] ──► dict fitur aktif        ← dibaca oleh train.py DAN app
                 │
                 ▼
[train.py] ──► models/*.joblib + metadata.json {features, bounds, metrics}
                 │  kontrak: app/optimizer HANYA percaya metadata, tidak hardcode
                 ▼
[optimize + physics + advisory] ──► RecommendationCard {apa, kenapa, angka, confidence}
                 │
                 ▼
[views/*] render — tidak pernah menyentuh nama kolom mentah
```

Konsekuensi praktis: **ketika data asli tahap 2 datang**, pekerjaan = tulis
`RealDataAdapter` (+update mapping schema) → jalankan `train --data` → capability
menyalakan fitur baru (mis. soft sensor causticity) → dashboard ikut, tanpa disentuh.
Itu demo scalability yang bisa DIBUKTIKAN di depan juri, bukan diklaim.

## 4. Keputusan non-fungsional

| Aspek | Keputusan | Alasan |
|---|---|---|
| Kecepatan optimizer | prediksi batch/vektorized; model GBM (bukan stacking/TabPFN) di loop | NSGA-II ≈ ribuan evaluasi; target < 5 dtk |
| Caching | `st.cache_resource` untuk model, `st.cache_data` untuk hasil optimasi per kondisi | replay men-trigger rerun terus |
| Reproducibility | seed tetap; `metrics.json` + hash data di registry | jawaban juri "kok angkanya beda?" |
| Guardrail | bounds = irisan (rentang data, batas alarm proses di `schema.py`) | rekomendasi tak pernah keluar amplop aman |
| Secrets | `.env` + `python-dotenv`; `.env` di `.gitignore` | sebelum API key pertama dibuat |
| Error handling demo | semua panel punya empty-state ("model belum dilatih / fitur off") | app tidak boleh crash saat capability off |

## 5. Urutan build yang direvisi (menggantikan urutan Fase doc 05, isi sama)

1. `schema.py` + `adapters.py` + `validate.py` (fondasi — ½ hari)
2. `train.py` + `registry.py` (surrogate end-to-end; + model chain per tahap jika sempat)
3. `physics/` (3 kalkulator — bisa paralel dengan #2, tidak saling tunggu)
4. `optimize/` + `advisory/` (template dulu, LLM belakangan)
5. `replay.py` + `app/views/` (urutan tab: overview → liquor loop → digestion → redmud → precipitation)
6. Benchmark notebook (linear vs LGBM vs XGB vs TabPFN) — amunisi pitch, bukan blocker

Definisi selesai per komponen: bisa dijalankan dari CLI/import TANPA dashboard —
dashboard hanyalah view. (Kalau Streamlit bermasalah H-1, demo tetap bisa via notebook.)
