# 08 — Catatan Penting & Masa Depan (living document)

> Tambahkan catatan baru di atas, beri tanggal. Ini tempat parkir keputusan, utang
> teknis, dan ide masa depan supaya tidak hilang di kepala/chat.

## ⭐ Info kunci kompetisi

**2026-07-11 — Data sintesis BUKAN acuan final.** Di tahap selanjutnya panitia akan
memberikan data sebenarnya yang lebih lengkap. Konsekuensi desain (WAJIB, bukan opsional):

1. **Jangan hardcode nama kolom** di seluruh kode — semua daftar fitur/target lewat satu
   file konfigurasi (mis. `src/schema.py` / `features.yaml`). Ganti dataset = edit config
   + retrain, bukan tulis ulang kode.
2. **Training satu perintah**: `python src/train.py --data <path>` → model baru dalam
   hitungan menit begitu data asli datang. Ini kalimat pitch yang kuat.
3. **Isolasi pembersihan khusus data sintesis** (clip digestion eff >100%, drop make-up
   negatif) di satu modul terpisah — jangan tersebar, karena data asli punya cacat berbeda.
4. **Capability detection di app**: panel/model aktif otomatis berdasarkan kolom yang
   tersedia & bervariasi. Contoh: kalau data asli punya causticity yang bervariasi →
   soft sensor (klaim #2 Ainin) menyala sendiri tanpa ubah kode dashboard.
5. **Replay engine = interface tipis** — kalau data asli ternyata time-series
   bertimestamp, tinggal ganti sumber feed, bukan rombak dashboard.
6. Jangan menghabiskan waktu menyempurnakan akurasi di data sintesis — dia hanya
   scaffolding. Prioritas: pipeline & dashboard yang siap menelan data apa pun.

## ⚠️ Insiden data v2 & perbaikannya (2026-07-15)

**Temuan:** data.csv v2 (ekspor macro VBA xlsm UPDATED, skala pabrik 1000 t/jam
basah / moisture 20% / 800 kering) **tidak konsisten antar-kolom dalam satu
baris** — korelasi silika vs recovery = +0.01 (harusnya ≈ −0.91), semua model
R² negatif. Akar masalah di macro: `Application.Calculation = xlCalculationManual`
+ hanya satu pass `wsCalc.Calculate` per sheet, padahal workbook punya referensi
melingkar spent-liquor yang butuh iterative calculation — nilai output disalin
SEBELUM konvergen, jadi tercampur sisa iterasi baris sebelumnya.

**Perbaikan di repo:** `src/data/rebuild_targets.py` menghitung ulang seluruh
kolom output dari kolom input memakai `src/physics/mass_balance.py` (port
literal formula workbook, tervalidasi <0.11% pada data v1), format & posisi
kolom dipertahankan persis. Ekspor asli disimpan sebagai
`data/raw/data_v2_ekspor_asli.csv` (bukti). Hasil: 997/1000 baris valid,
R² kembali 0.95–0.999, SHAP gate lulus (silika dominan, corr −0.908).

**PR untuk Ainin (perbaikan di sisi Excel, untuk ekspor berikutnya):**
1. File > Options > Formulas > centang **Enable iterative calculation**.
2. Di macro, ganti loop `wsCalc.Calculate` per sheet dengan beberapa kali
   `Application.Calculate` sampai sel monitor stabil, SEBELUM menyalin baris.
3. Verifikasi cepat setelah export: korelasi kolom silika vs recovery harus
   kuat negatif (≈ −0.9). Kalau ≈ 0, ekspornya masih tercampur.

**Perubahan teknis ikutan (data v2):** adapter kini otomatis mendeteksi
format v1/v2 (persen vs fraksi, clip recovery >100%); `mass_balance.run()`
& Prediction Lab mendukung what-if **feed rate & moisture** (Dashboard!C6/C7,
linear terhadap dry feed — permintaan tim); `na_balance` berbasis
`feed_rate_t` dari data; scaling lama `/150` di pareto dihapus (data sudah
skala pabrik).

## Keputusan yang sudah diambil (dan alasannya)

| Tanggal | Keputusan | Alasan |
|---|---|---|
| 2026-07-11 | Arsitektur config-driven / schema-agnostic (6 aturan di atas) | Tahap berikutnya dapat data asli yang lebih lengkap |
| 2026-07-11 | Bentuk solusi: **web app Streamlit** (bukan Dash/React) | Tim 2 orang; otak semua di Python; UI 1–1.5 hari (doc 06 Bag. 7) |
| 2026-07-11 | Model utama: **LightGBM/XGBoost**, bukan DL/stacking berat | Tabular 1000 baris; SHAP auditable; inference cepat untuk NSGA-II (doc 06 Bag. 8) |
| 2026-07-11 | Paper karbonasi → **kalkulator deterministik**, bukan ML | Tidak ada data training; koefisien paper: 23 kg CO₂/ton RM, L/S 2:1 |
| 2026-07-11 | Fitur causticity & mud washing = fallback fisika dulu | Kolom masih konstan di data.csv — menunggu regenerasi Ainin |
| 2026-07-11 | Demo "real-time" = replay + injeksi gangguan, dibilang jujur | Data tidak punya dimensi waktu |
| 2026-07-11 | 3 taruhan inovasi: carbon-aware optimization, regret meter, shift-handover report (doc 12) | Pembeda nyata & murah; RL/multi-agent DITOLAK (risiko > nilai) |
| 2026-07-11 | LLM = provider fleksibel via env (`template`/`ollama`/`groq`/`gemini`), TANPA token berbayar | Tidak ada budget API; laptop 16 GB RAM cukup utk Qwen2.5-7B Q4 lokal; Groq/Gemini free-tier utk demo lebih ngebut kalau ada internet |

## Transformasi frontend (2026-07-22)

**FastAPI REST + Next.js/React sebagai frontend KEDUA** — Streamlit tetap utuh.
Inti headless + kontrak (`src/integration/api.py`, doc 19). 9 halaman React
setara PENUH dgn Streamlit (0 fitur berkurang): Overview (HexRadar profil
kesehatan, 6 tren + yield/CO₂, regret+handover, korelasi+scatter, audit trail),
Diagram HMI 3 lapisan + sparkline, Digesti (heatmap ✕/★ + what-if + Pareto +
parallel coords), Liquor (Sankey Na + dosis CaO), Presipitasi (Ceq), Red Mud
(Sankey Al + karbonasi), Lab (ML vs fisika + ekstrapolasi + sensitivitas +
tornado), Knowledge (+ tambah dokumen), Integrasi (playground). Advisory
bisa di-drag (dock atas/kanan) + pagination. Verifikasi: tsc bersih, next
build sukses, semua endpoint 200. **Bonus:** perbaikan `regret.shift_series`
(tak pernah masuk main) sekaligus memperbaiki regret meter Streamlit.
Dependensi: fastapi 0.115→0.139 (Streamlit aman), + node ≥18 utk frontend.

## Status implementasi (2026-07-11)

**M0–M3 + sebagian M4 SELESAI & teruji** (semua test di `tests/` hijau):
- M0: schema/adapter/validate/capability — 1000→N baris bersih, capability benar
- M1: 4 surrogate LightGBM (R² CV 0.94–0.99), SHAP gate lulus (silika dominan −)
- M2: karbonasi + Ceq + neraca Na; NSGA-II carbon-aware 1.5 dtk; goal-seek; uji silika 2% vs 7% lulus
- M3: replay 96 jam + skenario silika spike (baris NYATA ber-silika tinggi, bukan karangan);
  advisory template; dashboard 5 tab jalan tanpa exception (AppTest)
- M4 sebagian: carbon-aware (I2) ✔, regret meter (I1) ✔, handover report (I4) ✔,
  provider LLM fleksibel ✔ · BELUM: conformal, benchmark TabPFN, notebook symbolic regression
- ⚠ Environment: `starlette` di-upgrade ke 1.3.1 di user site utk Streamlit baru —
  bentrok dengan pin `fastapi 0.115.5` (proyek lain di laptop yang pakai fastapi bisa
  kena; solusi bersih = venv per proyek)

## TODO penting (di luar rencana kerja doc 05)

- [ ] **Minta Ainin regenerasi data**: variasikan causticity, Na₂CO₃ conversion,
  NaOH carbonation, wash water/efficiency; perbaiki digestion eff >100% & make-up negatif
- [ ] Pastikan `.env` masuk `.gitignore` SEBELUM ada API key Claude ter-commit
- [ ] Benchmark model di notebook: baseline linear vs LightGBM vs XGBoost vs TabPFN →
  tabel bukti bahwa pilihan model empiris, bukan default (amunisi jawaban juri)
- [ ] Siapkan fallback template advisory non-LLM (kalau API down saat demo)
- [ ] Konfigurasi harga reagen (NaOH USD 400–600/t) supaya OPEX bisa tampil indikatif Rp/USD
- [ ] Enhancement (kalau waktu ada): model chain per tahap — Model A digestion eff +
  Model B precipitation yield + neraca massa deterministik; end-to-end tetap sebagai
  cross-check (doc 06 Bag. 8, "digital twin modular")

## Knowledge Pack (2026-07-15)

**Keputusan:** pengetahuan expert ANTAM dijadikan sumber kecerdasan ke-3
(setelah data historian & fisika) via **Knowledge Pack tier-1**: folder
`knowledge/*.md` ber-header `tags:`, loader `src/advisory/knowledge.py`,
disuntikkan ke prompt tombol "Analisis AI" per chart (AI wajib mengutip nama
dokumen), halaman Knowledge di app utk lihat/upload. Konten awal = **MOCK**
(ditandai `status:` di tiap file) — arsitektur yang dinilai, isi tinggal
diganti expert. TANPA vector DB: volume SOP/catatan pakar puluhan halaman,
pencocokan tag cukup & auditable.

**Jalur upgrade tier-2 (bila ANTAM punya ribuan halaman, mis. jurnal riset):**
ganti isi `knowledge.py` dengan embeddings + vector store lokal (FAISS/Chroma),
chunking + sitasi per-potongan, kurasi berperan (hanya expert menambah),
versioning — SEMUA pemanggil (`explain_chart`, advisory) tidak berubah karena
kontraknya tetap `for_tags()/as_prompt_block()`. Estimasi 1-2 hari + dependensi
baru; JANGAN sebelum demo.

## Ide masa depan (pasca-hackathon / kalau menang)

- Soft sensor causticity dilatih dari data historian + LIMS nyata (klaim #2 Ainin penuh)
- Uncertainty (quantile/conformal) + drift monitoring + MLflow (checklist doc 07)
- Fitur lag/rolling → model dinamis; jangka panjang: MPC di presipitasi
- Modul karbonasi diperluas: optimasi suhu karbonasi dari data eksperimen sendiri,
  integrasi dengan sumber CO₂ flue gas pabrik (bukan CO₂ murni seperti di paper)
- Multi-site: arsitektur sama untuk pabrik feronikel/smelter lain ANTAM

## Pertanyaan juri yang sudah disiapkan jawabannya

1. "Datanya sintesis, valid?" → doc 05 Fase 5
2. "Kok R² tinggi?" → surrogate dari simulator; justru alasan butuh pilot data ANTAM
3. "Scalable ke sistem kami?" → doc 07 (ganti Lapis 0 saja; roadmap 3 fase)
4. "Keamanannya?" → doc 07 bagian keamanan (read-only, DMZ, human-in-the-loop)
5. "Kenapa bukan deep learning / model canggih?" → doc 06 Bag. 8 + benchmark notebook
