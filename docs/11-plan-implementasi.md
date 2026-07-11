# 11 — Plan Implementasi (menggantikan urutan doc 05; isi doc 05 tetap valid)

> Basis: arsitektur v2 (doc 09) + desain dashboard (doc 10). Tim 2 orang,
> target ±5–6 hari efektif. Aturan potong: **fitur dipotong dari bawah tiap
> milestone, milestone tidak pernah dilompati** — setiap akhir milestone proyek
> selalu dalam keadaan bisa didemokan.

## Milestone 0 — Fondasi data (½ hari) 🔴 wajib
| Deliverable | File | Definisi selesai |
|---|---|---|
| Schema & role kolom | `src/schema.py` | mapping raw→kanonik + role (input/knob/intermediate/target/constant) |
| Adapter sintesis | `src/data/adapters.py` | load cp1252/`;`/koma → DataFrame kanonik bersih; cacat (eff>100%, make-up negatif) tertangani DI SINI saja |
| Validasi + capability | `src/data/validate.py`, `src/capability.py` | laporan kualitas; dict fitur on/off |
| Test cepat | `tests/test_data.py` | 1000→N baris bersih, tidak ada NaN di kolom model |

## Milestone 1 — Otak ML (1 hari) 🔴 wajib
| Deliverable | File | Definisi selesai |
|---|---|---|
| Training CLI | `src/models/train.py` | `python -m src.models.train --data <path>` → 3–4 model (recovery, OPEX, red mud, precip yield) |
| Registry | `src/models/registry.py` | artefak + metadata {features, bounds, cv_metrics, data_hash} |
| Evaluasi | `models/metrics.json` | 5-fold CV R²/MAE tercatat |
| SHAP | `src/models/explain.py` | summary global (PNG utk slide) + fungsi per-prediksi (utk advisory) |

**Gate:** SHAP menunjukkan silika reaktif dominan negatif → model konsisten kimia. Kalau tidak, berhenti & investigasi.

## Milestone 2 — Fisika + Optimizer (1 hari) 🔴 wajib
| Deliverable | File | Definisi selesai |
|---|---|---|
| Kalkulator karbonasi | `src/physics/carbonation.py` | input ton RM → CO₂, air L/S 2:1, pH; angka dicek manual vs paper |
| Ceq presipitasi | `src/physics/precipitation.py` | kurva Ceq(T,C) + gap supersaturasi |
| Neraca Na | `src/physics/na_balance.py` | breakdown loss utk Sankey + advisory dosis CaO stoikiometrik |
| NSGA-II | `src/optimize/pareto.py` | Pareto 3-objektif < 5 dtk; bounds dari registry + guardrail |
| Goal-seek | `src/optimize/goal_seek.py` | "recovery ≥ X termurah" |
| Uji fisik | — | skenario silika 2% vs 7% → rekomendasi berbeda & masuk akal (**divalidasi Ainin**) |

## Milestone 3 — Dashboard inti (1½ hari) 🔴 wajib
Urutan di dalam milestone (potong dari bawah):
1. `src/data/replay.py` + header global + KPI row (stat tiles + sparkline)
2. Kartu advisory (pakai `advisory/template.py` dulu — TANPA LLM) + injeksi gangguan silika
3. Tab Overview: 4 trend + pita alarm + log kejadian
4. Tab Liquor Loop: **Sankey Na** + kartu dosis make-up
5. Tab Digesti: **heatmap operating map** + what-if
6. Tab Red Mud CCUS: Sankey Al + panel karbonasi + meter pH
7. Tab Presipitasi: kurva Ceq + gap supersaturasi

**Gate (= demo minimum):** poin 1–4 jalan → alur "gangguan → alarm → advisory → angka" utuh.

## Milestone 4 — Pembeda / inovasi (1–1½ hari) 🟡 kuat, bukan wajib
Urutan sesuai taruhan doc 12 (potong dari bawah):
1. **I2 Carbon-aware optimization**: objektif ke-4 NSGA-II = ekonomi CO₂
   (kalkulator karbonasi × harga karbon IDXCarbon) — perluasan `optimize/pareto.py`
2. **I1 Regret Meter**: replay ulang shift dengan setpoint rekomendasi →
   kartu "selisih Rp / red mud / CO₂ kalau advisory diikuti" di tab Overview
3. LLM advisory + **I4 Shift-Handover Report** (`advisory/llm.py`, Claude API,
   key via `.env`) + fallback template; tombol Tolak + alasan (human-in-the-loop)
4. Conformal prediction (MAPIE) → interval kepastian di kartu advisory
5. Benchmark notebook: linear vs LightGBM vs XGBoost vs TabPFN → tabel utk slide
   (distilasi TabPFN→LGBM hanya kalau TabPFN menang)
6. (Jika data regenerasi Ainin datang) soft sensor causticity → capability menyala
7. (Stretch) I3 Ore Blending Advisor (LP scipy) / model chain per tahap (doc 06 Bag. 8)

## Milestone 5 — Demo & pitch (1 hari) 🔴 wajib
1. Deploy Streamlit Community Cloud + uji di laptop lain; lokal sebagai cadangan
2. Uji 5 acceptance test desain (doc 10 §5) — perbaiki yang ❌
3. Skrip demo 3 babak: (a) pabrik normal — tunjukkan glanceability; (b) injeksi
   silika spike — alarm → advisory → terima → KPI membaik; (c) tab CCUS — cerita
   ESG + paper karbonasi
4. Slide: klaim Ainin → demo live → arsitektur data-agnostic (doc 09: "data asli
   tahap 2 tinggal ganti adapter") → roadmap integrasi (doc 07)

## Pembagian kerja
| Orang | Fokus |
|---|---|
| Kamu (informatika) | M0, M1, M3, M4 (pipeline + app) |
| Ainin (proses) | validasi fisik M2, regenerasi data (doc 08 TODO), koefisien karbonasi & Ceq, narasi pitch |

## Risiko eksekusi teratas
| Risiko | Mitigasi |
|---|---|
| Waktu habis di UI | M3 urutannya sudah potong-dari-bawah; gate = poin 4 |
| Streamlit rewel saat replay | semua komponen bisa jalan dari CLI/notebook (doc 09 §5) |
| API LLM down saat demo | template fallback dibuat DULU (M3), LLM belakangan (M4) |
| Data regenerasi tidak datang | capability off → panel tampil sebagai kalkulator fisika; tidak ada janji ML causticity |
