# 06 — Analisis: Pivot ke "AI RED MUD" CRO Advisory Dashboard

> Konteks: ide berkembang dari "assay-in → setpoint-out" (doc 03) menjadi **dashboard
> monitoring + advisory untuk Control Room Operator (CRO)**, dengan modul ESG/CCUS
> berbasis paper *direct aqueous carbonation* red mud (Sciencedirect, 2026:
> ~2.3 g CO₂ tersekuestrasi per 100 g red mud, L/S 2:1, pH awal 11–13).

---

## Bagian 1 — Validasi klaim Ainin (first-principles)

### Klaim 1: NaOH = beban OPEX kritis, caustic loss kimiawi & fisik — **BENAR**

Secara prinsip neraca natrium di proses Bayer, NaOH keluar dari loop lewat 3 pintu:

1. **DSP (Desilication Product)** — silika reaktif (kaolinit) larut lalu mengendap
   sebagai sodalit/cancrinite `Na₆[Al₆Si₆O₂₄]·2NaX`. Setiap kg SiO₂ reaktif mengunci
   ±1.2 kg Na₂O **plus** alumina ikut terkunci → kerugian ganda. Ini konsisten dengan
   temuan EDA kita: korelasi silika reaktif vs recovery **−0.91** dan vs OPEX **+0.60**.
2. **Sodium titanate** — TiO₂ bereaksi dengan NaOH. *Nuansa:* pada digesti suhu rendah
   gibbsitik (140–150 °C, tipikal bauksit Indonesia dan sesuai rentang data kita),
   reaktivitas TiO₂ jauh lebih rendah daripada digesti boehmit suhu tinggi (>240 °C).
   Jadi klaim ini benar tapi porsinya kecil untuk kasus kita — jangan dijadikan fokus.
3. **Inklusi fisik** — Na terlarut ikut kelembapan red mud. Dikendalikan oleh
   **wash efficiency & wash water ratio** di mud washing circuit; trade-off-nya nyata:
   makin banyak air cuci → makin sedikit Na hilang, tapi beban evaporasi (energi) naik.

Harga NaOH USD 400–600/ton skala industri: masuk akal (harga spot caustic soda memang
di kisaran itu, fluktuatif). NaOH umumnya 15–25% dari total cash cost refinery alumina —
klaim "komponen biaya material tertinggi" valid.

**Dukungan data:** `NaOH Consumed`, `Net Make-up NaOH`, `Total NaOH OPEX`, `Reactive SiO₂`
bervariasi ✔. `Wash Efficiency` (0.8) dan `Free Moisture` (0.1) **konstan** ✖ — kalau mau
menjadikan mud washing sebagai knob, generator data harus memvariasikannya.

### Klaim 2: Soda mati (Na₂CO₃) & dosis make-up NaOH/CaO yang lagging — **BENAR, dan ini klaim paling bernilai**

Kimia dasarnya:
- Karbonat & organik bawaan bauksit + CO₂ udara di tangki terbuka mengubah NaOH aktif
  → Na₂CO₃ ("soda mati") → **causticity** (NaOH aktif / total soda) turun → daya larut
  digester anjlok.
- Pemulihan lewat kaustisasi: `Na₂CO₃ + Ca(OH)₂ → 2NaOH + CaCO₃↓`.
- **Over-dosing CaO**: kapur berlebih bereaksi dengan aluminat membentuk TCA
  (tricalcium aluminate) → **alumina ikut hilang** + scaling/kerak + limbah padat naik.
- **Under-dosing**: causticity turun perlahan, yield digesti turun, dan operator baru
  tahu setelah hasil titrasi lab (siklus 4–8 jam) → **lagging indicator klasik**.

Ini persis kelas masalah yang di industri diselesaikan dengan **soft sensor**
(virtual analyzer): prediksi causticity/Na₂CO₃ real-time dari variabel proses yang
terukur online, sehingga dosis make-up jadi proaktif, bukan reaktif.

**Dukungan data:** kolom-kolomnya ADA (`Minimum Causticity`=0.85,
`Spent Liquor Na₂CO₃ conversion efficiency`=0.9, `NaOH affected by carbonation`=0.1)
tapi **semuanya konstan** ✖. Dua opsi:
- **Opsi A (kuat):** minta Ainin memvariasikan 3 kolom ini + kadar karbonat/organik
  bauksit di generator → kita bisa melatih soft sensor causticity betulan.
- **Opsi B (fallback):** modelkan sebagai **kalkulator fisika** (neraca Na + reaksi
  kaustisasi stoikiometrik) di dashboard — tetap bisa memberi advisory dosis CaO
  tanpa ML.

### Klaim 3: Inefisiensi kinetika presipitasi — **BENAR**

Presipitasi adalah tahap paling lambat & penentu yield proses Bayer. Driving force =
supersaturasi `(A − Ceq)`, di mana `Ceq(T, C_caustic)` bisa dihitung dari korelasi
literatur (persamaan Misra untuk kelarutan gibbsite):

```
Ceq/C = exp(6.2106 − 2486.7/T_K + 1.0875·C/1000)   (bentuk umum; kalibrasi ke data)
```

Operator memang tidak "melihat" Ceq — yang terlihat hanya suhu & rasio seed. Alumina
yang gagal mengendap kembali ke hulu sebagai spent liquor kaya-Al → produktivitas
liquor (g Al₂O₃/L per pass) turun → kapasitas pabrik turun tanpa ada alarm apa pun.

**Dukungan data:** `Precipitation Temperature` (50–70 °C), `Seed Ratio` (2–3),
`Precipitation Yield` (bervariasi, ~77–81%) ✔ — cukup untuk memodelkan yield dan
menampilkan **kurva supersaturasi + garis Ceq** sebagai overlay fisika.

### Kesimpulan validasi

**Analisis Ainin benar secara kimia proses dan tepat sasaran secara ekonomi.** Ketiganya
memetakan rapi ke 4 titik kendali yang dia sebut:

| Titik kendali | Klaim terkait | Status data |
|---|---|---|
| Pre-desilication | #1 (DSP), #2 (dosis CaO) | silika ✔, Ca/Si ratio konstan ✖ |
| Digestion | #1, #2 (causticity) | suhu, NaOH conc, efisiensi ✔ |
| Red mud washing | #1 (loss fisik) | wash eff/water konstan ✖ |
| Precipitation | #3 | suhu, seed, yield ✔ |

---

## Bagian 2 — Posisi paper karbonasi dalam produk

Paper direct aqueous carbonation **jangan dijadikan model ML** (doc 01 sudah benar:
tidak ada data pendukung). Jadikan **kalkulator deterministik + panel advisory ESG**:

- Input: `Wet Red Mud Discharge` (prediksi surrogate) + parameter paper.
- Koefisien dari paper: **23 kg CO₂ / ton red mud** (2.3 g/100 g), L/S 2:1,
  pH awal 11–13 → target netralisasi, mass loss 14.19% vs 10.74% (bukti karbonat
  terbentuk), leaching membaik → layak backfill/produk sirkular.
- Output panel: *"Red mud hari ini: X ton → potensi sekuestrasi Y ton CO₂, kebutuhan
  air Z ton (L/S 2:1), estimasi pH akhir → status kepatuhan Permen LHK 6/2021 (pH 7–10)"*.
- Bonus advisory: suhu karbonasi optimal dari kurva paper (temperatur divariasikan
  sistematis pada tekanan konstan).

Ini mengubah red mud dari sekadar "objektif minimasi" menjadi **modul CCUS yang
dikuantifikasi** — pembeda kuat di pitch, biaya implementasi rendah (murni stoikiometri).

---

## Bagian 3 — Arsitektur "AI RED MUD" CRO Console

Prinsip: **otaknya tetap doc 03** (surrogate + NSGA-II + SHAP — jangan dibuang),
yang berubah adalah **kulit dan konteks penyajiannya**: dari form kalkulator menjadi
ruang kontrol yang hidup.

```
┌────────────────────────────────────────────────────────────────┐
│ LAPIS 0 — PLANT REPLAY (simulasi stream)                       │
│ data.csv 1000 baris → diputar sebagai "shift feed" 1 baris/    │
│ beberapa detik (+injeksi gangguan: silika spike, causticity    │
│ drift) → dashboard terasa live/real-time                       │
└────────────────────────────────────────────────────────────────┘
        │
┌────────────────────────────────────────────────────────────────┐
│ LAPIS 1 — MODEL                                                │
│ a. Surrogate LightGBM/XGBoost: recovery, TOTAL OPEX, red mud   │
│    (+precipitation yield sebagai target ke-4)                  │
│ b. Soft sensor (jika data di-regenerate): causticity, Na₂CO₃   │
│ c. Anomaly: residual |aktual − prediksi| > ambang → alarm      │
│ d. SHAP untuk "kenapa"                                         │
└────────────────────────────────────────────────────────────────┘
        │
┌────────────────────────────────────────────────────────────────┐
│ LAPIS 2 — FISIKA (tanpa ML, kredibel & bebas data)             │
│ a. Kalkulator karbonasi red mud (koefisien paper: 23 kg CO₂/t) │
│ b. Kurva Ceq presipitasi (korelasi Misra) + supersaturasi      │
│ c. Neraca Na & kaustisasi stoikiometrik → advisory dosis CaO   │
└────────────────────────────────────────────────────────────────┘
        │
┌────────────────────────────────────────────────────────────────┐
│ LAPIS 3 — OPTIMIZER & ADVISORY                                 │
│ a. NSGA-II (pymoo): Pareto recovery×OPEX×red mud               │
│ b. Goal-seek: "recovery ≥88% termurah"                         │
│ c. LLM advisory (Claude API): terjemahkan JSON {kondisi, SHAP, │
│    rekomendasi optimizer, alarm} → kartu bahasa operator:      │
│    "APA yang terjadi / KENAPA / LAKUKAN apa" — grounded pada   │
│    angka model, bukan mengarang                                │
└────────────────────────────────────────────────────────────────┘
        │
┌────────────────────────────────────────────────────────────────┐
│ LAPIS 4 — CRO CONSOLE (Streamlit, 4 stasiun + overview)        │
└────────────────────────────────────────────────────────────────┘
```

### Layout dashboard (5 tab, mengikuti titik kendali Ainin)

1. **Overview (landing CRO)** — KPI tiles: recovery %, OPEX/jam, causticity, red mud
   t/jam, potensi CO₂ capture t/hari. Trend 24 "jam" terakhir + pita alarm.
   **Kartu advisory AI** teratas (maks 3, ranked by dampak Rp/jam).
2. **Digestion & Pre-desilication** — heatmap operating map: recovery = f(suhu digester
   × konsentrasi NaOH) dari surrogate, dengan titik operasi saat ini + titik rekomendasi
   optimizer di-overlay. Slider silika untuk melihat peta bergeser.
3. **Liquor Loop (NaOH & CaO)** — **Sankey natrium**: NaOH segar + recycle → digesti →
   {DSP loss, loss fisik red mud, soda mati, kembali sebagai spent liquor}. Panel dosis
   make-up: rekomendasi vs aktual, indikator over/under-dosing.
4. **Precipitation** — kurva konsentrasi Al vs waktu/suhu dengan garis `Ceq(T,C)`;
   gap supersaturasi = "uang yang belum diambil". Rekomendasi suhu & seed ratio.
5. **Red Mud & CCUS** — **Sankey aluminium** (feed → produk / hilang ke red mud /
   recycle) + panel karbonasi: tonase RM → CO₂ tersekuestrasi, pH, status Permen LHK,
   narasi circular economy (backfill).

Dua Sankey (Na dan Al) = visual paling kuat untuk cerita OPEX & recovery — juri melihat
"ke mana uang bocor" dalam satu gambar.

### Pilihan model — dan kenapa

| Kebutuhan | Model | Alasan |
|---|---|---|
| Surrogate 4 target | LightGBM/XGBoost | 1000 baris tabular; DL akan overfit & lambat di-iterate. R² tinggi wajar (data dari simulator) — katakan jujur |
| Optimasi setpoint | NSGA-II (pymoo) | 5 dimensi, multi-objektif, Pareto dalam hitungan detik |
| Goal-seek | Optuna/scipy | mode "target recovery X, OPEX minimum" |
| Explainability | SHAP | jembatan kepercayaan operator; verifikasi model belajar kimia yang benar |
| Soft sensor causticity | LightGBM (**butuh regenerasi data**) | jawaban langsung untuk klaim #2 Ainin |
| Anomaly | Residual threshold (bukan autoencoder) | sederhana, bisa dijelaskan, cukup untuk demo |
| Advisory NL | Claude API, prompt ber-grounding JSON | inovasi presentasional; TANPA ML tambahan |
| Karbonasi & Ceq | Stoikiometri/korelasi literatur | kredibel, tidak butuh data training |

**Yang sengaja TIDAK dipakai:** LSTM/time-series forecasting (data bukan deret waktu
sungguhan — replay hanyalah penyajian), reinforcement learning (tidak ada environment
dinamis), computer vision (tidak ada citra). Jangan biarkan juri menggiring ke sana.

---

## Bagian 4 — Permintaan ke Ainin (regenerasi data, prioritas)

1. **Variasikan** `NaOH affected by carbonation` (mis. 0.05–0.20, dipengaruhi kadar
   organik/karbonat bauksit — tambah 1 kolom input "karbonat bauksit"),
   `Spent Liquor Na₂CO₃ conversion efficiency`, `Minimum Causticity` → soft sensor
   causticity + optimasi dosis CaO jadi hidup (klaim #2).
2. **Variasikan** `Wash Water Ratio` & `Red Mud Wash Efficiency` → mud washing jadi
   knob ke-6/7 (klaim #1, loss fisik).
3. Perbaiki cacat: digestion efficiency >100%, make-up NaOH negatif (doc 02).
4. (Opsional) tambah pH red mud sebagai fungsi Na loss → panel karbonasi makin nyata.

Tanpa regenerasi pun produk tetap jalan (fallback kalkulator fisika), tapi #1–#2
mengubah dua klaim Ainin dari "narasi" menjadi "fitur ML yang didemokan".

---

## Bagian 5 — Urutan pengerjaan (revisi doc 05)

Fase 1–3 doc 05 **tetap** (preprocess, surrogate, optimizer). Fase 4 diganti:

- **4a. Replay engine** (½ hari): loop baris data + state di `st.session_state`,
  tombol play/pause/kecepatan, injeksi 2 skenario gangguan (silika spike; causticity
  drift jika data baru tersedia).
- **4b. Console 5 tab** (1–1.5 hari): urutan prioritas kalau waktu habis —
  Overview + advisory → Sankey Na/Al (plotly) → heatmap operating map →
  panel karbonasi → panel Ceq presipitasi.
- **4c. LLM advisory** (½ hari): satu fungsi `advise(context_json) → markdown card`,
  dengan fallback template non-LLM (kalau API down saat demo!).
- **Fase 5 pitch**: alur cerita = klaim Ainin (masalah nyata, 3 poin) → CRO console
  (live demo gangguan silika → alarm → advisory → operator terima rekomendasi →
  KPI membaik) → panel CCUS karbonasi (paper 2026) → roadmap historian ANTAM.

## Bagian 6 — Kecukupan data per fitur (matriks jujur)

| Fitur | Data cukup? | Keterangan / fallback |
|---|---|---|
| Surrogate recovery, OPEX, red mud | ✅ Cukup | 1000 baris, input & target bervariasi |
| Heatmap operating map (T × NaOH) | ✅ Cukup | digenerate dari surrogate, bukan dari data mentah |
| Optimizer NSGA-II + goal-seek | ✅ Cukup | hanya butuh surrogate di atas |
| Sankey Na & Al | ✅ Cukup | semua kolom neraca massa ada per baris |
| SHAP explainability | ✅ Cukup | ikut surrogate |
| Model presipitasi (yield vs T, seed) | ✅ Cukup | `Precipitation Yield` bervariasi |
| Kurva Ceq supersaturasi | ⚠️ Bukan dari data | dari korelasi literatur (Misra) — sah, labeli "physics overlay" |
| Panel karbonasi CCUS | ⚠️ Bukan dari data | kalkulator deterministik dari koefisien paper — sah, kutip papernya |
| **Soft sensor causticity / dosis CaO (ML)** | ❌ **KURANG** | `Causticity`, `Na₂CO₃ conv`, `carbonation` konstan → minta Ainin variasikan; fallback: kalkulator stoikiometri |
| **Optimasi mud washing** | ❌ **KURANG** | `Wash Water`, `Wash Efficiency` konstan → minta divariasikan; fallback: tampilkan sebagai monitoring saja, bukan knob |
| Anomaly detection "real-time" | ❌ Tidak ada dimensi waktu | disimulasikan via replay + injeksi gangguan — jujur ke juri: "streaming-ready, demo pakai replay" |
| Optimasi energi/steam | ❌ KURANG (steam konstan) | JANGAN dijanjikan sama sekali |
| OPEX dalam Rupiah/USD nyata | ⚠️ Satuan abstrak | tambah konfigurasi harga (NaOH USD 400–600/t) untuk konversi indikatif |

Aturan main di pitch: fitur ❌ tanpa regenerasi data **tidak diklaim sebagai ML** —
disajikan sebagai kalkulator fisika atau roadmap. Juri menghargai kejujuran ini.

## Bagian 7 — Bentuk solusi & interface

**Bentuknya: web app** — diakses CRO lewat browser di workstation ruang kontrol
(atau wall display), tanpa instalasi, bisa multi-user. Bukan desktop app, bukan mobile.

Pilihan stack, urut dari yang paling realistis untuk 2 orang × ~5 hari:

| Opsi | Stack | Waktu UI | Kapan dipilih |
|---|---|---|---|
| **A (rekomendasi)** | **Streamlit** (1 proses Python, `app/app.py`) | ~1–1.5 hari | Model & advisory = nilai jual utama; UI cukup rapi dengan tema gelap + plotly |
| B | Plotly Dash | ~2 hari | Kalau butuh layout multi-panel lebih bebas dari Streamlit |
| C | FastAPI + React/Next.js | ~4+ hari | Hanya jika ada anggota ke-3 khusus frontend; tampang paling "SCADA" tapi makan waktu model |

Alasan A: seluruh otak (pandas, LightGBM, pymoo, SHAP) sudah Python — Streamlit
menghilangkan kebutuhan API layer & frontend terpisah. Replay engine cukup
`st.session_state` + auto-refresh. Deploy demo: **Streamlit Community Cloud** (gratis,
juri dapat link) + jalankan lokal saat presentasi sebagai cadangan koneksi.

Sentuhan supaya terasa "control room", bukan notebook:
- Tema gelap ala HMI/SCADA, KPI tiles besar di atas, pita alarm merah/kuning.
- Header: nama pabrik, shift, jam simulasi, tombol play/pause replay.
- Kartu advisory AI selalu terlihat (sticky) — itu produknya, chart hanyalah konteks.

## Bagian 8 — Apakah model ini "bagus" & scalable ke sistem nyata?

### Model: ya, ini pilihan yang benar — bukan kompromi hackathon

Fakta industri yang penting dipahami (dan disampaikan ke juri): refinery alumina/smelter
besar yang sudah punya sistem serupa (advanced process control, soft sensor) **memakai
kelas model yang sama** — gradient boosting / regresi terkalibrasi untuk data tabular
proses, BUKAN deep learning. Alasannya struktural, tidak berubah saat data membesar:

- Data proses = tabular, fitur puluhan, baris 10³–10⁶ → GBM tetap state-of-the-art.
- Operator & process engineer harus bisa percaya → SHAP pada GBM jauh lebih mudah
  diaudit daripada neural net.
- Retraining harian/mingguan di CPU biasa → murah dioperasikan di pabrik.
- Lapis fisika kita (Ceq, neraca Na, karbonasi) = **hybrid/grey-box modeling** —
  persis arah industri sekarang (ML dibatasi oleh hukum kekekalan massa).

Jadi jawaban untuk juri: *"model kami bukan yang paling canggih, tapi yang paling
tepat — kelas model yang sama dengan yang beroperasi di refinery komersial."*

### Perlu stacking / pretrained / model bertingkat?

**Stacking meta-learner: TIDAK untuk sekarang.** Di data sintesis, R² sudah mendekati
plafon — stacking hanya menambah kompleksitas, memperlambat inference (NSGA-II memanggil
model ribuan kali), dan merusak keterbacaan SHAP. Di data nyata pun gain tipikal stacking
cuma 1–2%; peluru yang lebih besar ada di fitur (lag) dan uncertainty.

**Pretrained model: hampir tidak ada yang relevan untuk tabular proses** — kecuali satu:
**TabPFN v2** (foundation model transformer untuk tabular kecil ≤10k baris, zero-shot).
Layak masuk **benchmark notebook** sebagai pembanding (talking point menarik untuk juri:
"kami uji foundation model tabular terbaru, GBM tetap menang/setara + lebih cepat +
auditable"), tapi bukan model utama: inference lambat untuk loop optimizer, SHAP sulit.
Pretrained lain (LLM) hanya untuk lapis advisory — sudah direncanakan.

**Model bertingkat / beberapa model yang berinteraksi: YA — dalam bentuk yang tepat.**
Bentuk yang tepat bukan stacking, melainkan **dekomposisi mengikuti flowsheet**
(model chain per unit proses), dan datanya MENDUKUNG karena kolom antara per tahap ada:

```
                    ┌─ Model A: Digestion Efficiency        ← bervariasi di data ✔
                    │   f(particle size, suhu, NaOH conc, silika)
input bauksit ──────┤
                    ├─ Model B: Precipitation Yield         ← bervariasi di data ✔
                    │   f(suhu presipitasi, seed ratio, beban Al liquor)
                    │
                    └─ NERACA MASSA deterministik (fisika, bukan ML)
                        merangkai A + B + konstanta klarifikasi/washing
                        → recovery, OPEX, red mud
```

Keunggulan dibanding satu model end-to-end gepeng:
1. **"Belajar proses, bukan cuma data"** — struktur rantai = struktur fisik pabrik;
   ML hanya mengisi bagian yang memang empiris (kinetika), sisanya hukum kekekalan massa.
2. Tiap model kecil bisa diperiksa process engineer per tahap (digesti sendiri,
   presipitasi sendiri) — cocok dengan 4 tab dashboard.
3. What-if per stasiun: "kalau digestion eff naik 2%, recovery total jadi berapa?"
4. Saat data nyata datang, tiap tahap bisa di-retrain terpisah dengan data lab tahapnya.

Risiko: error menjalar sepanjang rantai → mitigasi: **tetap latih model end-to-end
sebagai cross-check** (selisih rantai vs end-to-end = indikator kesehatan model).

**Urutan kerja yang aman:** end-to-end dulu (Fase 2 doc 05, demo terjamin) → rantai
per tahap sebagai enhancement kalau waktu ada. Istilah untuk pitch: *"digital twin
modular mengikuti flowsheet, hybrid fisika-ML"* — ini pembeda nyata dari tim lain
yang pasti bawa satu XGBoost gepeng.

### Innovation stack — supaya tidak terdengar "template XGBoost"

Kekhawatiran yang sah: "GBM + dashboard" akan dibawa banyak tim. Jawabannya BUKAN
mengganti regressor dengan deep learning gimmick (transformer di 1000 baris = bahan
serangan juri), melainkan 3 lapisan inovasi yang genuinely baru DAN defensible:

1. **TabPFN v2 — tabular foundation model (Nature, 2025).** Pretrained transformer
   yang melakukan in-context learning untuk data tabular kecil — SOTA di bawah
   ~10k baris, tanpa training (zero-shot fit). Pemakaian cerdas: **TabPFN sebagai
   "guru"** (akurasi + uncertainty), lalu **distill ke LightGBM sebagai "murid"**
   untuk inference cepat di loop NSGA-II. Kalimat pitch: *"kami memakai foundation
   model untuk data tabular — kelas model 2025 — dan mendistilasinya agar layak
   real-time."* Fallback aman: kalau TabPFN tidak menang di benchmark, tabelnya
   tetap jadi bukti rigor.

2. **Conformal prediction — jaminan ketidakpastian bebas-distribusi.** Setiap
   prediksi/rekomendasi membawa interval dengan coverage terjamin secara matematis
   (mis. 90%), bukan sekadar angka titik. Library: MAPIE, ±1 jam kerja di atas model
   yang ada. Ini riset UQ paling praktis 5 tahun terakhir dan langsung berdampak ke
   kepercayaan operator ("recovery akan naik 3.1–4.4%, kepastian 90%").

3. **Agentic advisory — CRO copilot dengan tool-use.** Bukan LLM yang mengarang teks,
   tapi **agent yang memanggil tools digital twin**: operator bertanya bebas
   ("kalau silika naik ke 7% shift depan, apa yang harus kusiapkan?") → Claude
   memanggil surrogate / optimizer / kalkulator fisika / SHAP sebagai function call,
   lalu menjawab dengan angka hasil tool — grounded, bukan halusinasi. Ini pola
   agentic AI 2025–2026 dan jadi momen demo paling "wow" yang tetap jujur.

**Satu kalimat identitas sistem:** *"Neuro-symbolic digital twin — model statistik
(foundation model tabular + GBM terdistilasi) dikawinkan dengan fisika neraca massa,
dibungkus agentic advisory dengan jaminan ketidakpastian conformal."*
Setiap kata di kalimat itu bisa dibuktikan saat ditanya. Prioritas implementasi:
#2 paling murah → #3 paling berdampak di demo → #1 sebagai benchmark dulu, distilasi
hanya kalau menang.

### Yang benar-benar berubah saat integrasi ke sistem ANTAM

Scalability TIDAK berarti ganti model. Yang berubah ada di pinggir:

```
DCS pabrik (Yokogawa/Honeywell/ABB)
   │  OPC UA
   ▼
Plant Historian (PI / AVEVA / TimescaleDB)     ← menggantikan LAPIS 0 (replay)
   │  connector + validasi data
   ▼
[LAPIS 1–3 kita: surrogate + fisika + optimizer + advisory]  ← TIDAK berubah
   │  REST API / dashboard
   ▼
CRO console + LIMS (data lab masuk sebagai ground truth retraining)
```

Karena arsitektur kita berlapis, **satu-satunya komponen yang diganti adalah sumber
data** — replay dicabut, connector historian dicolok. Ini kalimat kunci pitch:
*"streaming-ready & data-agnostic: yang kami demokan dengan replay, di pabrik tinggal
disambungkan ke historian lewat OPC UA."*

Komponen yang HARUS ditambah untuk produksi (masuk roadmap, jangan dibangun sekarang):

| Kebutuhan produksi | Solusi | Kenapa penting |
|---|---|---|
| Ketidakpastian prediksi | Quantile LightGBM / conformal prediction | Advisory tanpa error bar tidak akan dipercaya operator |
| Drift data & konsep | Monitoring residual + retraining terjadwal (MLflow registry) | Bijih & kondisi pabrik berubah; model harus ikut |
| Dinamika waktu | Fitur lag/rolling dari historian (steady-state → dinamis) | Data nyata punya dead-time & inersia proses |
| Validasi rekomendasi | Guardrail hard-constraint (batas alarm DCS) + human-in-the-loop | Rekomendasi tidak boleh keluar amplop operasi aman |
| Keamanan | Advisory open-loop dulu (tidak menulis ke DCS) | Tanpa sertifikasi kontrol; deploy cepat, risiko nol |

### Roadmap integrasi 3 fase (untuk slide)

1. **Fase 1 — Shadow mode (0–3 bln):** sistem membaca historian, memberi advisory,
   TIDAK mengendalikan apa pun; akurasi dibandingkan hasil lab → membangun kepercayaan.
2. **Fase 2 — Advisory resmi (3–9 bln):** soft sensor causticity tervalidasi vs LIMS;
   rekomendasi setpoint dipakai CRO dengan approval supervisor; KPI penghematan diukur.
3. **Fase 3 — Closed-loop / APC (9+ bln):** setpoint terpilih ditulis balik ke DCS
   dalam amplop aman — hanya jika Fase 2 terbukti.

Fase 1 nyaris tanpa risiko bagi ANTAM — itulah kenapa proposal ini realistis
untuk benar-benar diintegrasikan, bukan sekadar demo.

## Bagian 9 — Keamanan (cybersecurity OT + keselamatan proses)

Dua dimensi berbeda yang sering dicampur — pisahkan di pitch:

### A. Keamanan siber (OT security)

Prinsip desain kita sudah aman secara arsitektur, tinggal dieksplisitkan:

1. **Read-only terhadap pabrik.** Fase 1–2 sistem HANYA membaca historian, tidak pernah
   menulis ke DCS. Dalam kerangka Purdue model, aplikasi duduk di Level 3/3.5 (DMZ),
   akses via akun OPC UA read-only → kompromi aplikasi ≠ kompromi kontrol pabrik.
2. **Autentikasi & role:** login via Active Directory/SSO perusahaan; role terpisah —
   CRO (lihat), supervisor (approve rekomendasi), engineer (retrain model).
3. **Audit trail:** setiap advisory yang tampil + keputusan operator (terima/tolak)
   dicatat — kebutuhan compliance sekaligus data pembelajaran.
4. **Secrets & data:** API key via environment variable (JANGAN hardcode/commit —
   pastikan `.env` masuk `.gitignore` sejak sekarang); TLS untuk semua koneksi;
   data historian terenkripsi at-rest.
5. **Khusus LLM advisory:** (a) input prompt = JSON terstruktur dari model kita sendiri,
   bukan teks bebas user → permukaan prompt-injection minimal; (b) untuk produksi,
   data operasional pabrik bersifat rahasia → opsi deployment via VPC/Bedrock/on-prem,
   atau redaksi angka sensitif; (c) fallback template deterministik bila API tak
   tersedia. Untuk demo hackathon aman: data 100% sintetis.

### B. Keselamatan proses (safety) — lebih penting bagi juri pabrik

1. **Guardrail hard-constraint:** semua rekomendasi optimizer di-clamp ke amplop
   operasi aman (rentang alarm DCS, mis. suhu digester 140–150 °C) SEBELUM ditampilkan —
   bukan sekadar rentang data training.
2. **Human-in-the-loop:** sistem tidak pernah mengeksekusi; manusia yang memutuskan.
   Ini bukan kelemahan — ini fitur yang membuat deployment Fase 1 berisiko nol.
3. **Ketidakpastian ditampilkan:** rekomendasi dengan confidence rendah (input di luar
   distribusi training) diberi label "low confidence — verifikasi lab" alih-alih
   disembunyikan.

Satu kalimat untuk slide: *"Sistem ini read-only, human-in-the-loop, dan ter-guardrail —
jalur adopsi paling aman untuk AI di lingkungan OT."*

## Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Juri: "ini kan cuma replay, bukan real-time" | Jujur: arsitektur streaming-ready; historian pabrik tinggal colok di Lapis 0 |
| LLM ngawur saat demo | Grounding ketat + fallback template deterministik |
| Scope melebar (5 tab × fitur) | Otak (surrogate+optimizer) selesai dulu; tab dipotong dari belakang |
| Angka karbonasi dipertanyakan | Kutip paper eksplisit: 2.3 g/100 g, L/S 2:1, mass loss 14.19% vs 10.74% |
