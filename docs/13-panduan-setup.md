# 13 — Panduan Setup & Menjalankan Project (untuk anggota tim)

> Target pembaca: anggota tim yang baru clone repo dan mau menjalankan +
> mencoba semua fitur AI RED MUD di laptopnya sendiri.

## 1. Prasyarat

- Python 3.11/3.12 (cek: `python --version`)
- Git
- Internet hanya untuk install & (opsional) LLM cloud — dashboard sendiri offline

## 2. Setup pertama kali (±5 menit)

```bash
git clone <url-repo>
cd antam-hackathon
pip install -r requirements.txt
```

Latih model (sekali saja; otomatis dilatih juga oleh app kalau lupa):

```bash
python -m src.models.train --data data/raw/data.csv
```

Output yang diharapkan: 4 baris `R2=0.93–0.99` + artefak muncul di `models/`.

## 3. Menjalankan dashboard

```bash
python -m streamlit run app/main.py
```

> ⚠ Selalu `python -m streamlit ...` — perintah `streamlit` saja sering tidak
> ada di PATH Windows. Dan JANGAN me-rename `app/main.py` menjadi `app.py`
> (menyebabkan circular import).

Browser terbuka di `http://localhost:8501`. Kalau port bentrok:
`python -m streamlit run app/main.py --server.port 8511`.

## 4. Tur fitur — cara mencoba SEMUANYA

### a. Replay & skenario gangguan (sidebar)
1. Sidebar kiri → **Skenario replay** → pilih *"Gangguan: Silika Spike"*.
2. Tekan **▶ Play** — jam simulasi berjalan; sekitar jam ke-24 silika naik >6%.
3. Perhatikan: KPI *Silika Reaktif* memerah 🔴 → kartu advisory **CRITICAL**
   muncul dengan rekomendasi setpoint + prediksi dampaknya.

### b. Advisory human-in-the-loop
- Di kartu advisory, klik **✔ Terima** atau **✘ Tolak** → keputusan tercatat
  di *Audit Trail* (tab Overview, paling bawah).

### c. Bobot prioritas Pareto (sidebar)
- Geser slider **Recovery / OPEX / Red mud** → rekomendasi setpoint berubah
  mengikuti prioritas (mis. ESG diberatkan → rekomendasi menekan red mud).

### d. Tab Overview
- 4 tren + pita alarm.
- **Regret Meter**: klik *"Hitung regret 8 jam terakhir"* → berapa recovery/OPEX
  yang tertinggal seandainya advisory diikuti (counterfactual dari model).
- **Laporan Serah Terima Shift**: klik *"Buat laporan shift"* → laporan otomatis
  (pakai LLM kalau diset, kalau tidak template).

### e. Tab Digesti & Pra-desilikasi
- **Peta operasi** (heatmap recovery vs suhu×NaOH) dengan marker
  *ANDA DI SINI* vs *REKOMENDASI*.
- **What-if**: geser 5 slider setpoint → prediksi recovery/OPEX/red mud/yield
  berubah live.

### f. Tab Liquor Loop
- **Sankey natrium**: ke mana NaOH bocor (DSP / soda mati / fisik).
- Kartu **dosis CaO**: status over/under-dosing dari kalkulator stoikiometri.

### g. Tab Presipitasi
- Kurva **Ceq** (fisika Misra) + slider A (alumina terlarut) → gap
  supersaturasi = yield yang belum diambil.

### h. Tab Red Mud & CCUS
- **Sankey aluminium** + panel **karbonasi** (paper 2026): ton CO₂, kebutuhan
  air L/S 2:1, status pH vs Permen LHK. Coba ubah **harga karbon** →
  nilai rupiah karbon berubah (coba Rp1.400.000 ≈ harga EU ETS).

### i. Goal-seek (belum ada di UI — via Python)
```python
from src.optimize.goal_seek import cheapest_for_recovery
from src.data.adapters import load_clean
from src.models import predict
row = load_clean().iloc[0]
print(cheapest_for_recovery(predict.composition_of(row), target_recovery=88.0))
```

## 5. Setup LLM (opsional — TANPA LLM pun semua fitur jalan pakai template)

1. Salin `.env.example` → `.env` (file `.env` di-.gitignore, jangan di-commit).
2. Pilih salah satu (semua gratis):

| Backend | Cara | Catatan |
|---|---|---|
| `template` (default) | tidak perlu apa-apa | offline, deterministik |
| `groq` ⭐ | daftar console.groq.com → `GROQ_API_KEY` | tercepat, butuh internet |
| `gemini` | aistudio.google.com/apikey → `GEMINI_API_KEY` | cadangan cloud |
| `ollama` | install ollama.com → `ollama pull qwen2.5:3b` | offline; 3b utk RAM 16GB |

3. Set `LLM_PROVIDER=groq` (misal) di `.env`, restart app.
4. Yang berubah: muncul expander **"🤖 Narasi advisory (LLM)"** + laporan shift
   ditulis LLM. Kalau API gagal, otomatis jatuh ke template (tidak akan crash).

## 6. Menjalankan test (verifikasi setup benar)

```bash
# dari root repo (Windows PowerShell):
$env:PYTHONPATH = (Get-Location).Path
python tests/test_data.py       # fondasi data     -> "M0 OK"
python tests/test_engine.py     # fisika+optimizer -> "M2 OK"
python tests/test_advisory.py   # advisory+replay  -> "M3 (engine) OK"
python tests/test_app.py        # dashboard penuh  -> "APP OK"
```

(Linux/Mac: `export PYTHONPATH=$PWD` lalu perintah python yang sama.)

## 7. Troubleshooting

| Gejala | Solusi |
|---|---|
| `streamlit: not recognized` | pakai `python -m streamlit run ...` |
| `ImportError ... starlette` | `pip install --user --upgrade starlette` (Streamlit baru butuh starlette baru) |
| `circular import ... app` | file entry HARUS `app/main.py`, bukan `app/app.py` |
| `ModuleNotFoundError: src` saat test | set `PYTHONPATH` ke root repo (lihat §6) |
| Dashboard lambat per jam sim | wajar ±1 dtk (NSGA-II per tick); kecilkan `gen/pop` di `src/advisory/context.py` kalau perlu |
| LLM tidak merespons | cek `.env` terbaca (restart app); fallback template otomatis aktif |

## 8. Ganti data (tahap 2 — data asli)

```bash
python -m src.models.train --data data/raw/data_asli.csv
```

Kalau formatnya beda dari CSV sintesis, tambahkan adapter baru di
`src/data/adapters.py` (contoh: `RealDataAdapter`) + mapping header di
`src/schema.py` — modul lain TIDAK perlu disentuh (doc 09).
