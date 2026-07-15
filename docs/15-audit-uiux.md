# 15 — Audit UI/UX (2026-07-15, diperbarui malam)

## Update status (pasca paket navigasi & tema)
- ✅ 🔴3 latency: segmented control hanya merender halaman aktif → rerun ringan
- ✅ 🟡5 onboarding: banner + tombol "Mulai demo Silika Spike"
- ✅ 🟡6 feedback aksi: Terima hijau / Tolak merah + ikon; terkunci jadi badge
  DITERIMA/DITOLAK setelah diputuskan (anti klik ganda)
- ✅ 🟡7 (sebagian) navigasi silang: advisory → "Lihat peta operasi";
  sidebar → "Muat jam ini → Prediction Lab". PFD klik-stasiun masih roadmap
  (bisa via st.plotly_chart on_select + ui.goto — ±2 jam)
- ✅ toggle dark/light penuh (CSS) + dipisah ke seksi "Tampilan" di sidebar
- ✅ jam simulasi 46:00 → "Hari 2 · 22:00 · Shift 3"
- Masih terbuka: 🔴1 redundansi Sankey/what-if (butuh keputusan tim),
  🔴2 sentralisasi ambang alarm, 🟡4 label mata uang OPEX, 🟡8 layar 1366px,
  🟡9 bahasa campur

> Diaudit terhadap acceptance test doc 10 §5 + praktik konsol CRO.
> Skala: 🔴 perlu sebelum demo · 🟡 bagus kalau sempat · 🟢 sudah beres.

## Yang SUDAH beres di iterasi ini 🟢
- Emoji → Material Icons monokrom di tab + label pendek (baris tab seimbang,
  kesan industrial, tidak "murahan").
- WebGL dihapus sebagai dependensi (Scattergl→Scatter): chart identik, jalan
  di browser/GPU apa pun — robust untuk laptop juri.
- Konsistensi satuan v2: semua caption/kartu kini ton/jam skala pabrik.
- Overlay yang MENJAWAB masalah (bukan hiasan): prediksi-vs-aktual + anomali
  (membuat fitur anomaly detection terlihat), counterfactual regret (bukti
  nilai advisory), Pareto explorer scatter+parallel-coordinates (memilih
  trade-off), radar setpoint (apa yang diubah & seberapa jauh, sekali pandang).

## Temuan yang MASIH terbuka

| # | Temuan | Kenapa masalah | Saran |
|---|---|---|---|
| 🔴1 | **Redundansi konten**: Sankey Al/Na ada di Overview-sub3 DAN tab Liquor/RedMud; heatmap+what-if (Digesti) tumpang tindih dgn sensitivitas (Prediction Lab) | Operator bingung "sumber kebenaran" yang mana; maintenance ganda | Satu rumah per visual: Sankey → tab stasiun saja (Overview-sub3 cukup regret+handover); what-if slider Digesti bisa dilepas (arahkan ke Prediction Lab) |
| 🔴2 | **Ambang alarm tersebar** (BANDS di overview.py, argumen status_of di main.py, threshold pfd.py, SILIKA_* di context.py) | Nilai bisa saling beda diam-diam → KPI hijau tapi tren merah | Satu modul `src/alarms.py`; semua view mengimpor darinya |
| 🔴3 | **Latency per tick ±1 dtk** (NSGA-II tiap ganti jam) tanpa indikator di mode Play | Terasa "nge-lag" saat demo Play | Turunkan gen/pop khusus mode playing, atau hitung advisory hanya saat pause/di jam alarm |
| 🟡4 | **OPEX tanpa mata uang** ("24,671 /jam") | Juri pasti tanya "itu rupiah? dolar?" | Label "USD (asumsi)" + tooltip harga NaOH 400–600 USD/t (doc 08 TODO lama) |
| 🟡5 | **Onboarding kosong**: user baru tidak tahu harus pilih skenario Spike | Momen demo terbaik tersembunyi di sidebar | Banner sekali-tampil: "Coba skenario Silika Spike ▶" |
| 🟡6 | **Keputusan advisory kurang feedback**: klik Terima → toast sekilas, kartu tidak berubah | Operator tak yakin aksinya tercatat | Setelah klik: disable tombol + badge "tercatat ✓" di kartu |
| 🟡7 | **Navigasi silang belum ada**: advisory menyebut setpoint tapi tak bisa lompat ke peta operasi; PFD belum klik-ke-tab | Ekstra klik & mencari-cari | `st.page_link`/anchor antar tab (atau tombol "lihat di Digesti") |
| 🟡8 | **Layar sempit (≤1366px)**: 6 KPI + 5 slider sidebar wrap tidak rapi | Laptop panitia sering 1366×768 | Uji di 1366px; KPI jadi 3+3, sidebar pakai expander |
| 🟡9 | **Bahasa campur** (Washed Bauxite vs istilah ID; "Filtration" vs "Klarifikasi") | Kesan kurang rapi utk juri non-teknis | Pilih satu: istilah proses EN (standar pabrik) + narasi ID, konsisten |
| 🟢10 | Teks readout PFD 9–10px | Lolos di monitor, gagal dari 2 m (acceptance #5) | Sudah cukup utk demo laptop; naikkan kalau pakai proyektor |

## Ide visual lanjutan (galeri ECharts, disaring "menjawab problem")

| Ide | Menjawab apa | Cara di stack kita |
|---|---|---|
| ✅ Parallel coordinates (SUDAH dipasang) | memilih solusi Pareto multi-dimensi | plotly Parcoords |
| ✅ Radar setpoint (SUDAH) | "apa yang kuubah & seberapa jauh" | plotly Scatterpolar |
| 3D surface recovery=f(T,NaOH) | intuisi bentuk permukaan respon (lanjutan heatmap) | plotly Surface — toggle di Digesti, ~1 jam |
| Sunburst OPEX | "ke mana uang" 2 level: NaOH/CaO → jenis kebocoran | plotly Sunburst dari na_balance, ~1 jam |
| Liquid-fill gauge causticity | wow-factor HMI | butuh `streamlit-echarts` (dependensi baru — JANGAN sebelum demo) |
| Bar race / animasi timeline | tidak menjawab problem CRO | ❌ skip |
