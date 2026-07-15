# ANTAM Hackathon — AI RED MUD (Bayer Process Advisor + CRO Console)

**Solusi:** dashboard monitoring + advisory untuk Control Room Operator (CRO).
Neuro-symbolic digital twin: surrogate ML (LightGBM) + fisika neraca massa +
optimizer multi-objektif (NSGA-II, carbon-aware) + advisory ber-grounding.
Input: komposisi bauksit & kondisi operasi. Output: rekomendasi setpoint yang
**memaksimalkan recovery Al, meminimalkan OPEX (NaOH/CaO), meminimalkan red mud**
— plus kuantifikasi CCUS karbonasi red mud (23 kg CO₂/ton, paper 2026).

## Menjalankan

```bash
pip install -r requirements.txt
python -m src.models.train --data data/raw/data.csv   # latih surrogate (sekali)
python -m streamlit run app/main.py                   # buka dashboard
```

Uji tanpa dashboard (semua engine bisa jalan dari CLI, doc 09 §5):

```bash
python tests/test_data.py       # M0 fondasi data
python tests/test_engine.py     # M2 fisika + optimizer + regret
python tests/test_advisory.py   # M3 replay + advisory
python tests/test_app.py        # dashboard end-to-end (AppTest)
```

Advisory LLM opsional & gratis — set env `LLM_PROVIDER`:
`template` (default, offline tanpa AI) · `ollama` (lokal) · `groq`/`gemini`
(free tier, butuh API key di `.env`).

## Struktur Folder

```
antam-hackathon/
├── docs/                      ← analisis & perencanaan
│   ├── 01–05 …                    (fondasi awal; 03 & 05 punya penerus)
│   ├── 06-cro-dashboard-analisis  (validasi klaim + model + inovasi stack)
│   ├── 07-integrasi-produksi      (OPC UA/historian, keamanan OT, roadmap 3 fase)
│   ├── 08-catatan-penting         (living doc: keputusan, TODO, info kunci)
│   ├── 09-arsitektur-v2           (engineering view: schema/adapter/capability)
│   ├── 10-desain-dashboard        (UI/UX CRO console + acceptance test)
│   ├── 11-plan-implementasi       (milestone M0–M5)
│   └── 12-inovasi                 (carbon-aware, regret meter, dst.)
├── data/raw/data.csv          ← data sintesis (JANGAN diedit)
├── src/
│   ├── schema.py                  (satu-satunya pemetaan kolom mentah→kanonik)
│   ├── capability.py              (fitur on/off otomatis dari data)
│   ├── data/       adapters · validate · replay
│   ├── models/     train · registry · predict · explain (SHAP)
│   ├── physics/    carbonation · precipitation (Ceq) · na_balance
│   ├── optimize/   pareto (NSGA-II carbon-aware) · goal_seek · regret
│   └── advisory/   context · template · providers (LLM fleksibel)
├── models/                    ← artefak + metrics.json (hasil train)
├── app/                       ← dashboard Streamlit (main.py + ui.py + views/)
└── tests/                     ← uji per milestone
```

> 📖 **Baru clone repo? Ikuti [docs/13-panduan-setup.md](docs/13-panduan-setup.md)** —
> setup 5 menit, tur semua fitur, setup LLM gratis, troubleshooting.
> Mau di-deploy supaya juri dapat link? **[docs/16-tutorial-deploy.md](docs/16-tutorial-deploy.md)**.

## Mulai dari mana?

1. `docs/01` konteks bisnis → `docs/06` analisis lengkap solusi.
2. `docs/11` plan implementasi (status: M0–M3 selesai, lihat `docs/08`).
3. Jalankan dashboard, pilih skenario **"Gangguan: Silika Spike"**, tekan ▶ Play.
