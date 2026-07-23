# OptiBayer — Bayer Process Advisor + CRO Console (ANTAM Hackathon)

**Solusi:** dashboard monitoring + advisory untuk Control Room Operator (CRO).
Neuro-symbolic digital twin: surrogate ML (LightGBM) + fisika neraca massa +
optimizer multi-objektif (NSGA-II, carbon-aware) + advisory ber-grounding +
pengetahuan expert (Knowledge Pack). Input: komposisi bauksit & kondisi operasi.
Output: rekomendasi setpoint yang **memaksimalkan recovery Al, meminimalkan
OPEX (NaOH/CaO), meminimalkan red mud** — plus kuantifikasi CCUS karbonasi red
mud (23 kg CO₂/ton, paper 2026).

**Dua wajah, satu otak (headless):** inti Python dipakai oleh DUA frontend —
**Streamlit** (cepat, lengkap) dan **Next.js + React** (UI produksi) — keduanya
lewat REST API yang sama (`src/integration/api.py`). Bukti arsitektur
data-agnostic: ganti/ tambah frontend tanpa menyentuh logika.

---

## Menjalankan

### A. Dashboard Streamlit (paling cepat — satu proses)

```bash
pip install -r requirements.txt
python -m streamlit run app/main.py     # buka http://localhost:8501
```

Model dilatih otomatis saat boot pertama (~30 dtk). Pilih skenario
**"Gangguan: Silika Spike"** → tekan ▶ Play untuk alur demo terbaik.

### B. Frontend Next.js + REST API (UI React — butuh 2 proses)

**Terminal 1 — backend API (Python):**
```bash
pip install -r requirements.txt
python -m uvicorn src.integration.api:app --port 8000
# dokumentasi OpenAPI otomatis: http://localhost:8000/docs
```

**Terminal 2 — frontend (Node.js ≥ 18):**
```bash
cd frontend
npm install
npm run dev                              # buka http://localhost:3000
```

Frontend memanggil API di `http://localhost:8000` (indikator "API tersambung"
di kanan atas). Kalau backend belum jalan, muncul instruksi menyalakannya.

### Uji tanpa dashboard (semua engine jalan dari CLI)

```bash
python tests/test_data.py       # M0 fondasi data
python tests/test_engine.py     # M2 fisika + optimizer + regret
python tests/test_advisory.py   # M3 replay + advisory
python tests/test_app.py        # dashboard Streamlit end-to-end (AppTest)
```

### Advisory LLM (opsional, gratis)

Salin `.env.example` → `.env`, set `LLM_PROVIDER`:
`template` (default, offline tanpa AI) · `ollama` (lokal, Qwen) ·
`groq`/`gemini` (free tier) · `openai` (OpenRouter/DashScope — Qwen via cloud).
Tanpa LLM, semua fitur AI tetap jalan dengan ringkasan template.

---

## Fitur (setara penuh di Streamlit & React)

| Halaman | Fitur |
|---|---|
| **Overview** | HexRadar profil kesehatan pabrik (6 metrik + grade S+/S/A/B) · 6 tren live + pita alarm (recovery, OPEX, silika, red mud, **yield, CO₂**) · Regret Meter counterfactual + laporan serah-terima shift · **Korelasi & Scatter** (data historis penuh) · **Audit Trail** keputusan advisory · Analisis AI |
| **Diagram Proses (HMI)** | Sirkuit Bayer SVG live: pipa berwarna, readout digital, lampu status · **3 lapisan analitik** (Operasi / Kebocoran NaOH / Jalur Karbon) · sparkline 12 jam · gauge |
| **Digesti** | Heatmap operating map (✕ sekarang + ★ rekomendasi) · **what-if setpoint** live · Pareto scatter + radar + parallel coordinates · Analisis AI |
| **Liquor Loop** | Sankey natrium (ke mana NaOH bocor) · kartu dosis CaO stoikiometrik · Analisis AI |
| **Presipitasi** | Kurva Ceq + gap supersaturasi interaktif · Analisis AI |
| **Red Mud & CCUS** | **Sankey aluminium** · kalkulator karbonasi (CO₂, air, nilai Rp, pH regulasi) · Analisis AI |
| **Prediction Lab** | Komposisi + setpoint + feed rate/moisture bebas · ML vs kalkulator fisika berdampingan · peringatan ekstrapolasi · sensitivitas + tornado |
| **Knowledge** | Dokumen expert ber-tag · search · chips "dipakai oleh chart" · **tambah dokumen** (multiselect chart) |
| **Integrasi** | Kontrak REST/MCP/MQTT · playground panggil API sungguhan · unduh spec JSON |
| Lintas halaman | KPI stat-tile kontekstual · **advisory bisa di-drag** (dock atas/kanan) + pagination · navigasi rail ikon · Panel Kendali · dark/light · Analisis AI per chart (grounded + sitasi knowledge) · annunciator alarm lintas halaman · mode Play ringan |

---

## Arsitektur (headless, 3 klien di atas 1 inti)

```
                    ┌─ Streamlit CRO Console (app/)
Inti Python ────────┤─ Next.js + React (frontend/)   ── REST API (src/integration/api.py)
(predict/optimize/  └─ MCP server (roadmap)
 mass_balance/       ↑
 advisory/knowledge) data historian / OPC UA (produksi)
```

## Struktur Folder

```
antam-hackathon/
├── docs/                      ← 01–18 (analisis, arsitektur, deploy, laporan teknis)
├── data/raw/data.csv          ← data (jangan diedit; ekspor asli diarsip)
├── data/calculator/           ← kalkulator xlsm (sumber mass_balance)
├── knowledge/                 ← dokumen expert ber-tag (Knowledge Pack)
├── src/
│   ├── schema.py · capability.py
│   ├── data/       adapters · validate · replay · rebuild_targets
│   ├── models/     train · registry · predict · explain (SHAP)
│   ├── physics/    mass_balance · carbonation · precipitation · na_balance
│   ├── optimize/   pareto (NSGA-II carbon-aware) · goal_seek · regret
│   ├── advisory/   context · template · providers (LLM) · knowledge
│   └── integration/ contract · api (FastAPI REST)
├── models/                    ← artefak + metrics.json
├── app/                       ← Streamlit (main.py + ui.py + views/)
├── frontend/                  ← Next.js + React (src/components + lib)
└── tests/                     ← uji per milestone
```

> 📖 Setup 5 menit + tur fitur + troubleshooting: **[docs/13-panduan-setup.md](docs/13-panduan-setup.md)**
> · Deploy (juri dapat link): **[docs/16-tutorial-deploy.md](docs/16-tutorial-deploy.md)**
> · Laporan teknis (metode + diagram): **[docs/17-laporan-teknis.md](docs/17-laporan-teknis.md)**

## Mulai dari mana?

1. `docs/01` konteks bisnis → `docs/06` analisis lengkap → `docs/17` laporan teknis.
2. Jalankan (A) Streamlit atau (B) React, pilih skenario **"Silika Spike"**, ▶ Play.
