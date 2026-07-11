# 10 — Desain Web App Dashboard (UI/UX)

> Prinsip: dashboard CRO yang bagus bukan yang paling ramai chart-nya, tapi yang
> menjawab 3 pertanyaan operator dalam <10 detik: **(1) pabrik sehat atau tidak?
> (2) kalau tidak, kenapa? (3) saya harus berbuat apa?** Semua keputusan desain
> di bawah diturunkan dari 3 pertanyaan itu.

## 1. Pengguna & konteks pakai

| Aspek | Realita | Konsekuensi desain |
|---|---|---|
| Siapa | CRO, shift 8–12 jam, bukan data scientist | Bahasa Indonesia, istilah pabrik, nol jargon ML di permukaan |
| Layar | Monitor workstation / wall display, dilihat dari jarak 2–3 m | Angka besar, kontras tinggi, tema gelap (standar HMI — mengurangi silau ruang kontrol) |
| Mode baca | *Glance* berkala, bukan eksplorasi | Status harus terbaca tanpa klik; detail baru muncul saat di-drill |
| Kepercayaan | Skeptis terhadap "AI kotak hitam" | Setiap rekomendasi wajib bawa: kenapa (SHAP), angka dampak, confidence, dan tombol tolak |

## 2. Sistem visual (mengikuti metode dataviz — warna dihitung, bukan dikira)

### Tema & permukaan (dark, ala HMI/SCADA)
- Permukaan chart: `#1a1a19` · latar halaman: `#0d0d0d`
- Teks utama `#ffffff` · sekunder `#c3c2b7` · sumbu/label redup `#898781`
- Gridline hairline `#2c2c2a` — grid & sumbu harus resesif, data yang menonjol

### Warna STATUS — khusus & tidak boleh dipakai untuk hal lain
| Status | Hex | Pemakaian |
|---|---|---|
| Normal/good | `#0ca30c` | KPI dalam pita aman, delta membaik |
| Warning | `#fab219` | Mendekati batas (mis. causticity < 0.87) |
| Serious | `#ec835a` | Keluar pita, belum kritis |
| Critical | `#d03b3b` | Alarm — silika spike, recovery anjlok |

Aturan keras: status **selalu ikon + label + warna**, tidak pernah warna saja;
dan warna status tidak pernah dipakai sebagai warna seri chart biasa.

### Warna SERI (kategorikal, urutan tetap — jangan diacak/di-cycle)
Slot dark-mode: 1 biru `#3987e5` · 2 aqua `#199e70` · 3 kuning `#c98500` ·
4 hijau `#008300` · 5 violet `#9085e9` … Maks 5–6 seri per chart; lebih → gabung "Lainnya".

### Warna MAGNITUDO (heatmap operating map)
**Satu hue biru, terang→gelap** (`#cde2fb` → `#0d366b`). BUKAN rainbow/jet/viridis —
heatmap magnitudo pakai satu hue. Titik operasi saat ini & titik rekomendasi
ditandai marker + label, bukan warna tambahan.

### Anti-pattern yang DILARANG di app ini
- Dual axis (dua skala y) → pecah jadi dua chart kecil bertumpuk
- Pie chart & gauge dekoratif → stat tile / meter satu-hue
- Angka di setiap titik line chart → direct label selektif di ujung seri
- Warna teks memakai warna seri → teks selalu ink token, identitas dibawa mark

## 3. Komposisi halaman

### Kerangka global (semua tab)
```
┌──────────────────────────────────────────────────────────────────┐
│ AI RED MUD · Pabrik Alumina    Shift 2 · Jam sim 14:00  ▶⏸ 1×    │ ← header + replay
├──────────────────────────────────────────────────────────────────┤
│ [Recovery 87.6% ▲] [OPEX/jam 3.3k ▼] [Causticity 0.85 ●]         │ ← KPI row (stat tiles:
│ [Red Mud 64 t ▲]   [CO₂ capture 1.5 t ●]                         │   nilai+delta+sparkline)
├──────────────────────────────────────────────────────────────────┤
│ ⚠ ADVISORY (selalu terlihat, maks 3, urut dampak Rp/jam)         │
│ ┌ CRITICAL · Silika reaktif naik 3.9→6.8%                      ┐ │
│ │ Dampak: recovery −4.1% ≈ −Rp XX/jam bila tanpa tindakan      │ │
│ │ Rekomendasi: suhu digester 141→146 °C, NaOH 150→156 g/L      │ │
│ │ Kenapa: [3 faktor SHAP]  · Confidence: TINGGI · [Detail][Tolak]│ │
│ └──────────────────────────────────────────────────────────────┘ │
├───────────┬──────────┬─────────────┬──────────────┬─────────────┤
│ Overview  │ Digesti  │ Liquor Loop │ Presipitasi  │ Red Mud CCUS│ ← tab = stasiun
└───────────┴──────────┴─────────────┴──────────────┴─────────────┘
```

KPI tile = **stat tile** (angka besar + delta + sparkline 24 jam + titik status
ikon-label), bukan bar chart satu batang, bukan gauge.

### Tab 1 — Overview (default; menjawab "pabrik sehat?")
- Trend 4 panel kecil bertumpuk (recovery, OPEX, causticity, red mud) — **pita alarm**
  sebagai band abu translusen + garis batas; pelanggaran diberi marker status.
- Log kejadian replay (gangguan terinjeksi muncul di sini) + riwayat advisory.

### Tab 2 — Digesti & Pra-desilikasi (menjawab "di mana titik operasi optimal?")
- **Heatmap operating map**: recovery = f(suhu × konsentrasi NaOH) dari surrogate,
  sequential biru; marker "ANDA DI SINI" vs "REKOMENDASI"; slider silika menggeser peta.
- Panel what-if: ubah knob → prediksi live + delta vs sekarang.

### Tab 3 — Liquor Loop / NaOH & CaO (menjawab "ke mana uang bocor?")
- **Sankey natrium**: NaOH segar + recycle → digesti → {DSP, loss fisik red mud,
  soda mati, kembali via spent liquor}. Node loss diberi warna status serious/critical,
  aliran sehat memakai seri biru/aqua — jangan pelangi.
- Kartu dosis make-up: rekomendasi vs aktual NaOH & CaO, indikator over/under.

### Tab 4 — Presipitasi (menjawab "berapa yield yang belum diambil?")
- Kurva konsentrasi Al vs suhu + garis `Ceq(T,C)`; area gap supersaturasi diarsir =
  "uang yang belum diambil" (label eksplisit dalam ton & Rp-indikatif).
- Rekomendasi suhu & seed ratio + confidence.

### Tab 5 — Red Mud & CCUS (cerita ESG)
- **Sankey aluminium**: feed → produk / hilang ke red mud / recycle.
- Panel karbonasi (kalkulator paper): tonase RM → CO₂ tersekuestrasi, kebutuhan air
  L/S 2:1, estimasi pH, badge status kepatuhan Permen LHK 6/2021 (pH 7–10).
- **Meter** (bukan gauge dekoratif) untuk pH: track satu-hue dengan penanda batas regulasi.

## 4. Interaksi
- Hover/tooltip di semua chart (crosshair di line, per-sel di heatmap, per-flow di Sankey).
- Filter dalam SATU baris di atas chart (rentang jam sim, skenario gangguan) — bukan tersebar.
- Advisory: klik "Detail" → SHAP per-prediksi + trajectory "jika diterapkan"; klik
  "Tolak" → minta alasan singkat (data pembelajaran + bukti human-in-the-loop).
- Empty state setiap panel: "fitur nonaktif — kolom X tidak tersedia/konstan di data"
  (capability detection, doc 09) — app tidak pernah crash/blank.

## 5. Definisi "benar-benar membantu" (dipakai sebagai acceptance test)
1. Dari layar default, orang awam bisa menjawab "pabrik sehat?" dalam ≤5 detik. ✅/❌
2. Saat gangguan silika diinjeksi, jalur *alarm → penjelasan → rekomendasi → dampak Rp*
   selesai tanpa berpindah tab. ✅/❌
3. Setiap rekomendasi menampilkan kenapa + angka dampak + confidence + cara menolak. ✅/❌
4. Tidak ada chart yang butuh penjelasan lisan saat demo — judul chart = kalimat
   temuan ("Silika memakan recovery"), bukan nama variabel. ✅/❌
5. Semua teks terbaca dari 2 m pada layar 1080p (uji: zoom browser 67%). ✅/❌
