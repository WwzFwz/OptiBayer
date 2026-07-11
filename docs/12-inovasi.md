# 12 — Strategi Inovasi ("bring something genius on the table")

> Prinsip: inovasi yang menang = kombinasi baru yang menyelesaikan sakit nyata dan
> bisa didemokan + dipertanggungjawabkan. Bukan model paling eksotis.
> Lapisan dasar (TabPFN-distill, conformal, agentic copilot) ada di doc 06 Bag. 8.

## Menu inovasi — dinilai dampak vs biaya implementasi

| # | Ide | Kenapa genius / baru | Biaya | Dampak demo |
|---|---|---|---|---|
| I1 | **Counterfactual Regret Meter** | Di akhir shift, sistem me-replay shift yang sama dengan setpoint rekomendasi → "kalau advisory diikuti: +Rp X, −Y ton red mud". Membuktikan nilai dengan ANGKA, bukan klaim. Tidak ada dashboard industri umum yang punya ini | Rendah (surrogate sudah ada; tinggal jalankan 2 lintasan) | ⭐⭐⭐ momen pitch pamungkas |
| I2 | **Carbon-aware optimization** | Objektif ke-4 di NSGA-II: nilai ekonomi CO₂. Red mud bukan lagi murni biaya — via karbonasi (paper 2026) ia jadi sink CO₂ bernilai kredit karbon (harga dari bursa karbon IDXCarbon / pajak karbon RI). Optimizer menimbang OPEX vs recovery vs **ekonomi karbon** — belum ada yang menggabungkan Bayer optimization dengan CCUS economics | Rendah (kalkulator karbonasi × harga karbon = 1 fungsi objektif baru) | ⭐⭐⭐ pembeda tema ESG paling tajam |
| I3 | **Ore Blending Advisor** | Semua tim akan "mengatur pabrik terhadap bijih". Genius-nya: **atur bijihnya juga** — optimasi pencampuran stockpile (LP sederhana) supaya silika feed stabil di bawah ambang sebelum masuk pabrik. Praktik nyata refinery, hampir pasti tak terpikir tim lain | Sedang (LP dengan scipy; stockpile = sampling baris data) | ⭐⭐ menunjukkan kedalaman pemahaman industri |
| I4 | **Auto Shift-Handover Report** | Agent menulis laporan serah terima shift otomatis: kejadian, advisory diterima/ditolak, kondisi liquor, PR untuk shift berikut. Sakit nyata setiap pabrik, 30 menit/shift | Rendah (LLM + konteks yang sudah dirakit advisory) | ⭐⭐ "wow" yang related bagi orang operasi |
| I7 | **Symbolic regression — "AI yang menemukan rumus pabrik"** | Alih-alih black-box, sistem MENURUNKAN persamaan yang bisa dibaca manusia dari data mentah (PySR/gplearn). Momen demo unik: karena data sintesis dibuat dari rumus neraca massa Ainin, AI akan **menemukan kembali persamaan itu** — dan Ainin bisa mengonfirmasi live di depan juri: "ya, itu rumus saya." Tidak ada tim lain yang bisa meniru momen ini. Di data nyata tahap 2, output-nya = rumus empiris pabrik yang jadi aset permanen process engineer | Sedang (gplearn pure-Python aman; PySR lebih kuat tapi butuh Julia) | ⭐⭐⭐ momen paling memorable + tak tertiru |
| I8 | **Mode "Flight Simulator" operator** | Balik produknya: bukan cuma menasihati operator, tapi MELATIH operator. Replay skenario gangguan → operator trainee memutuskan setpoint → sistem menilai vs optimizer + menunjukkan selisih Rp. Komponen 100% sudah ada (replay + surrogate + regret meter), hanya beda mode. Menjawab keresahan manajemen: kompetensi operator = bottleneck nyata; dan mematahkan narasi "AI menggantikan operator" | Rendah (mode baru di atas komponen existing) | ⭐⭐⭐ reframing yang tak terpikir tim lain |
| I9 | **Active learning — "AI yang tahu apa yang tidak ia ketahui"** | Sistem menunjuk titik operasi/uji lab mana yang paling bernilai diambil berikutnya (uncertainty sampling dari conformal/ensemble) → relevan langsung ke tahap 2 (data asli): bukan cuma siap menelan data, tapi MEMANDU pengambilan datanya | Rendah–sedang | ⭐⭐ jawaban elegan untuk "roadmap data" |
| I5 | Multi-agent (agent per stasiun yang bernegosiasi) | Terdengar keren, tapi sulit dipertanggungjawabkan + rawan demo gagal | Tinggi | ⭐ (risiko > nilai) — TIDAK dipilih |
| I6 | RL untuk setpoint | Tidak ada environment dinamis nyata; juri ML akan membongkar | Tinggi | ❌ TIDAK dipilih |

## Taruhan yang DIPILIH (komit, masuk plan)

1. **I2 Carbon-aware optimization** — termurah, paling tajam untuk tema. Narasi:
   *"Optimizer kami menimbang tiga mata uang: Rupiah (OPEX), ton alumina (recovery),
   dan ton CO₂ (karbonasi red mud → kredit karbon)."*
2. **I1 Regret Meter** — penutup demo: bukan "percayalah AI kami", tapi
   *"inilah selisih uangnya, dihitung dari data shift barusan."*
3. **I4 Shift-Handover Report** — output agentic copilot yang paling nyata gunanya.

4. **I7 Symbolic regression** — dikerjakan sebagai NOTEBOOK terpisah (bukan fitur app,
   jadi nol risiko ke demo utama): jalankan gplearn/PySR pada recovery & OPEX →
   simpan rumus yang ditemukan + verifikasi Ainin → 1 slide + 1 layar demo cadangan.
   Kalau berhasil menemukan kembali rumus generator, jadikan PEMBUKA pitch.
5. **I8 Flight Simulator** — tampilkan minimal sebagai toggle mode di replay
   (sembunyikan advisory → operator isi setpoint → skor vs optimizer). Kalau waktu
   mepet: cukup 1 slide "mode latihan" dengan screenshot mock.

I3 (blending) & I9 (active learning) = stretch/slide roadmap jika M0–M3 selesai lebih cepat.

## Narasi besar yang mengikat semuanya (untuk pitch)

**"Dari reaktif → proaktif → regeneratif."**
- *Reaktif* (status quo): tunggu lab, tunggu yield jatuh, red mud = beban.
- *Proaktif* (dashboard + advisory + optimizer): lihat sebelum terjadi, dosis presisi.
- *Regeneratif* (carbon-aware + karbonasi): limbah paling bermasalah industri alumina
  dijadikan sink karbon yang ikut dihitung optimizer — pabrik menawar ulang
  keseimbangannya setiap jam, termasuk keseimbangan karbonnya.

Identitas satu kalimat (doc 06): *neuro-symbolic digital twin dengan agentic advisory* —
dan tiga taruhan di atas adalah buktinya yang kelihatan di layar, bukan jargon.

## Aturan keselamatan inovasi (supaya berani ≠ ceroboh)

1. Setiap inovasi punya fallback yang sudah jadi (regret meter gagal → tetap ada Pareto;
   LLM down → template; TabPFN kalah → benchmark tetap tampil).
2. Tidak ada inovasi yang boleh menggeser gate M0–M3 (doc 11) — pembeda dibangun
   DI ATAS fondasi yang jalan, bukan menggantikannya.
3. Setiap klaim "baru" diuji dengan pertanyaan juri tersulit: "apa bedanya dengan X?"
   — jawaban harus spesifik (tertulis di doc ini sebelum dipakai di slide).
