# OptiBayer — Bayer Process Advisor + CRO Console (ANTAM Hackathon)

**Solusi:** dashboard monitoring + advisory untuk Control Room Operator (CRO).
Neuro-symbolic digital twin: surrogate ML + fisika neraca massa + optimizer
multi-objektif (NSGA-II, carbon-aware) + advisory ber-grounding + pengetahuan
expert (Knowledge Pack). Input: komposisi bauksit & kondisi operasi.
Output: rekomendasi setpoint yang **memaksimalkan recovery Al, meminimalkan
OPEX (NaOH/CaO), meminimalkan red mud** — plus kuantifikasi CCUS karbonasi red
mud (23 kg CO₂/ton, paper 2026).

**Inti headless, klien berganti tanpa menyentuh logika.** Seluruh kecerdasan ada
di `src/` dan diakses lewat SATU kontrak (`src/integration/contract.py`) yang
melahirkan tiga antarmuka sekaligus: REST API, server MCP untuk agen AI, dan
halaman playground. Klaim ini bukan retorika — konsol Streamlit yang dulu jadi
UI utama sudah dipensiunkan dari `main` **tanpa mengubah satu baris pun di
`src/`**. Arsipnya lengkap di branch `feat/old-ada-streamlit`.

UI saat ini: **Next.js + React** (`frontend/`).

---

## Menjalankan

### A. Frontend Next.js + REST API (2 proses)

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

### B. Docker — satu perintah (paling ringkas untuk juri)

```bash
docker compose up --build     # API :8000 + React :3000
```

Model dilatih saat build image, jadi permintaan pertama tidak menunggu.

### Uji

```bash
python -m pytest                 # semua (~1 menit)
python -m pytest tests/test_model_trust.py   # interval, guard OOD, wasit fisika
```

Kalau ingin membuktikan mutu model sendiri:

```bash
python -m src.models.benchmark   # adu keluarga model per target
python -m src.models.verify      # fidelitas surrogate vs fisika + kecepatan
```

### Agen AI (MCP) — digital twin sebagai alat

```bash
python -m src.integration.mcp_server
```

Tool-nya dibangkitkan dari kontrak yang sama dengan REST API
(`src/integration/contract.py`), jadi tidak ada definisi ganda. Contoh
pendaftaran di Claude Desktop/Code ada di docstring modulnya. Semua read-only.

### Advisory LLM (opsional, gratis)

Salin `.env.example` → `.env`, set `LLM_PROVIDER`:
`template` (default, offline tanpa AI) · `ollama` (lokal, Qwen) ·
`groq`/`gemini` (free tier) · `openai` (OpenRouter/DashScope — Qwen via cloud).
Tanpa LLM, semua fitur AI tetap jalan dengan ringkasan template.

---

## Fitur

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

## Kepercayaan angka (yang membedakan dari dashboard biasa)

Setiap angka yang dilihat operator membawa tiga pemeriksaan — semuanya terukur,
bukan label yang ditulis tangan. Bukti & metodologi: **[docs/21](docs/21-benchmark-model.md)**.

| Lapisan | Apa yang dijawab | Wujudnya di layar |
|---|---|---|
| **Interval konformal** | Selebar apa ketidakpastian model? | "recovery 91.7% ±0.22 (interval 90%)" — cakupan diuji di data held-out: 88.8–96.4% |
| **Guard OOD** | Apakah kondisi ini masih dikuasai model? | Strip peringatan bila keluar rentang latih atau komposisi tak menjumlah ~100% |
| **Wasit fisika** | Apakah neraca massa setuju? | Delta rekomendasi dihitung ULANG dengan kalkulator eksak; kartu menandai "neraca massa eksak" |

Model dipilih **per target** lewat adu validasi silang, bukan preferensi:
recovery & red mud → ridge-polinomial, OPEX → LightGBM, yield → HistGB.

## Arsitektur (headless — klien boleh berganti, inti tidak)

```
                    ┌─ Next.js + React (frontend/) ── REST API (src/integration/api.py)
Inti Python ────────┤─ MCP server (agen AI)        ── src/integration/mcp_server.py
(predict/optimize/  └─ [arsip] Streamlit CRO Console  → branch feat/old-ada-streamlit
 mass_balance/       ↑
 advisory/knowledge) data historian / OPC UA (produksi)
```

## Struktur Folder

```
antam-hackathon/
├── docs/                      ← 01–22 (analisis, arsitektur, benchmark, deploy, laporan)
├── data/raw/data.csv          ← data (jangan diedit; ekspor asli diarsip)
├── data/calculator/           ← kalkulator xlsm (sumber mass_balance)
├── knowledge/                 ← dokumen expert ber-tag (Knowledge Pack)
├── src/
│   ├── schema.py · capability.py
│   ├── data/       adapters · validate · replay · rebuild_targets
│   ├── models/     train (pilih keluarga + konformal) · registry · predict
│   │               explain (SHAP agnostik) · verify (wasit fisika) · benchmark
│   ├── physics/    mass_balance · carbonation · precipitation · na_balance
│   ├── optimize/   pareto (NSGA-II carbon-aware) · goal_seek · regret
│   ├── advisory/   context · template · providers (LLM) · knowledge
│   └── integration/ contract · api (FastAPI REST) · mcp_server
├── models/                    ← artefak + metrics.json
├── frontend/                  ← Next.js + React (src/components + lib)
└── tests/                     ← uji per milestone
```

> 🔬 Bukti mutu model (benchmark, interval, fidelitas): **[docs/21-benchmark-model.md](docs/21-benchmark-model.md)**
> · Batasan yang diakui terbuka: **[docs/14-batasan.md](docs/14-batasan.md)**
> 📖 Setup 5 menit + tur fitur + troubleshooting: **[docs/13-panduan-setup.md](docs/13-panduan-setup.md)**
> · 🚀 Deploy (juri dapat link): **[docs/22-deploy.md](docs/22-deploy.md)** — Vercel + HF Spaces + pinger untuk link proposal, blueprint `render.yaml` untuk demo terpandu
> · Laporan teknis (metode + diagram): **[docs/17-laporan-teknis.md](docs/17-laporan-teknis.md)**
> · 🗺️ **Diagram arsitektur visual (Mermaid): [docs/20-diagram-arsitektur.md](docs/20-diagram-arsitektur.md)**

## Mulai dari mana?

1. `docs/01` konteks bisnis → `docs/06` analisis lengkap → `docs/17` laporan teknis.
2. Jalankan (A) React atau (B) Docker, pilih skenario **"Silika Spike"**, ▶ Play.
