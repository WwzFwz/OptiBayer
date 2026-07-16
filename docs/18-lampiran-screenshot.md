# 18 — Lampiran Screenshot (struktur siap isi)

> Cara pakai: jalankan app (`python -m streamlit run app/main.py`), ikuti
> **[cara ambil]** di tiap butir untuk menyetel kondisi layar, ganti
> placeholder `<screenshot: ...>` dengan gambarnya. **Teks penjelasan sudah
> bahasa laporan — tinggal salin apa adanya di atas tiap gambar.**
> Urutan mengikuti alur cerita demo, bukan urutan menu.

---

## A. Tampilan Umum

**A1 — Konsol utama (Overview, kondisi normal).**
Halaman pertama yang dilihat operator. Baris KPI di atas menjawab "pabrik
sehat atau tidak?" dalam lima detik: setiap kartu memuat titik status
berwarna, nilai terkini, dan panah perubahan yang arahnya sudah
memperhitungkan makna (kenaikan OPEX ditandai merah karena memburuk).
`[cara ambil]` skenario **Operasi Normal**, jam simulasi ±8, halaman Overview.
<screenshot: overview kondisi normal — KPI hijau + banner onboarding>

**A2 — Mode terang.**
Seluruh antarmuka termasuk chart dan diagram memiliki palet terang tersendiri
(bukan sekadar latar diputihkan) untuk ruangan presentasi yang terang.
`[cara ambil]` sidebar → seksi Tampilan → aktifkan **Mode terang**.
<screenshot: halaman yang sama dalam mode terang>

**A3 — Tombol Bantuan.**
Panduan penggunaan selalu dapat dijangkau dari pojok kanan atas: alur demo
tiga langkah, fungsi tiap halaman, dan arti warna status.
`[cara ambil]` klik tombol **? Bantuan** di kanan atas hingga popover terbuka.
<screenshot: popover bantuan terbuka>

**A4 — Panel Kendali (sidebar).**
Pemisahan peran yang disengaja: navigasi halaman berada di atas layar
("sedang melihat apa"), sedangkan sidebar berisi kendali ("sedang mengatur
apa") — skenario replay, kecepatan, bobot prioritas optimasi, dan tema.
`[cara ambil]` sidebar terbuka penuh, halaman bebas.
<screenshot: sidebar panel kendali lengkap>

---

## B. Alur Inti: Gangguan → Advisory → Keputusan

**B1 — Alarm silika spike.**
Saat pengiriman bauksit ber-silika tinggi masuk (disimulasikan dari baris
data nyata), KPI Silika Reaktif berubah merah dan kartu advisory CRITICAL
muncul otomatis — lengkap dengan rekomendasi setpoint, dampak yang
terkuantifikasi, dan alasan dari model (SHAP).
`[cara ambil]` skenario **Gangguan: Silika Spike**, geser jam simulasi ke ±30.
<screenshot: KPI silika merah + kartu advisory CRITICAL>

**B2 — Kartu advisory dari dekat.**
Setiap kartu menjawab tiga pertanyaan operator: APA yang terjadi, LAKUKAN
apa (setpoint konkret), dan KENAPA (faktor terkuat menurut model) — beserta
tombol keputusan dan pintasan ke peta operasi.
`[cara ambil]` crop/zoom satu kartu CRITICAL dari kondisi B1.
<screenshot: satu kartu advisory utuh dengan tombol Terima/Tolak/Lihat peta>

**B3 — Keputusan terkunci & audit trail.**
Setelah operator menekan Terima/Tolak, kartu terkunci menjadi badge dan
keputusan tercatat permanen (file CSV yang bertahan lintas restart) —
human-in-the-loop yang dapat diaudit.
`[cara ambil]` klik **Terima** pada satu kartu; lalu Overview → sub-tab
*Regret, Handover & Audit* untuk tabelnya.
<screenshot: badge DITERIMA pada kartu + tabel audit trail>

---

## C. Overview — Analisis

**C1 — Tren dengan prediksi model & penanda anomali.**
Garis putus-putus adalah prediksi model di atas data aktual; berlian merah
menandai jam ketika keduanya menyimpang melebihi tiga simpangan residual —
beginilah deteksi anomali dibuat terlihat, bukan sekadar diklaim.
`[cara ambil]` Overview → sub-tab *Tren Historis*, skenario spike, jam ≥30.
<screenshot: chart recovery dengan garis prediksi + marker anomali>

**C2 — Korelasi & scatter.**
Analisis seluruh data historis: fitur mana yang paling menggerakkan tiap
target. Silika reaktif tampil sebagai pendorong negatif terkuat recovery
(r ≈ −0,91) — bukti model mempelajari kimia proses yang benar.
`[cara ambil]` Overview → sub-tab *Korelasi & Scatter*, target Recovery.
<screenshot: bar korelasi + scatter silika vs recovery dengan trendline>

**C3 — Regret Meter.**
Counterfactual delapan jam terakhir: seandainya setpoint mengikuti
rekomendasi, berapa recovery/OPEX yang tidak hilang. Area yang diarsir di
antara dua garis adalah "nilai yang tertinggal di meja".
`[cara ambil]` sub-tab *Regret, Handover & Audit* → klik **Hitung regret
8 jam terakhir** (skenario spike agar selisihnya terlihat).
<screenshot: metrik regret + kurva aktual vs counterfactual>

**C4 — Laporan serah terima shift otomatis.**
Ringkasan shift (kondisi, kejadian, keputusan operator, PR shift berikut)
dibuat otomatis — menghemat pekerjaan rutin ±30 menit per shift.
`[cara ambil]` sub-tab yang sama → klik **Buat draf laporan serah-terima**.
<screenshot: laporan shift yang tergenerasi>

---

## D. Diagram Proses (HMI) — Hero Visual

**D1 — Lapisan Operasi.**
Peta sirkuit Bayer bergaya panel HMI: pipa berwarna per jenis aliran, kotak
readout digital dengan nilai live, dan lampu status di tiap stasiun —
gambaran besar pabrik dalam satu layar.
`[cara ambil]` halaman Diagram Proses, lapisan **Operasi**.
<screenshot: diagram penuh lapisan operasi + sparkline 12 jam + gauge>

**D2 — Lapisan Kebocoran NaOH.**
Peta yang sama berganti cerita: jalur kebocoran NaOH menyala berlapis warna
(terkunci DSP, soda mati, hilang fisik, terselamatkan) dengan persentase
dari make-up, sementara aliran lain diredupkan — menjawab "ke mana tiap ton
NaOH pergi" dalam satu pandangan.
`[cara ambil]` lapisan **Kebocoran NaOH** (skenario spike agar angkanya besar).
<screenshot: diagram lapisan kebocoran NaOH>

**D3 — Lapisan Jalur Karbon (CCUS).**
Rute red mud menuju karbonasi menyala hijau dengan potensi CO₂ per jam dan
nilai rupiah kredit karbonnya — cerita ESG yang terlihat, bukan diceritakan.
`[cara ambil]` lapisan **Jalur Karbon (CCUS)**.
<screenshot: diagram lapisan jalur karbon>

---

## E. Digesti — Optimasi Setpoint

**E1 — Peta operasi.**
Permukaan respon recovery terhadap suhu digester × konsentrasi NaOH untuk
komposisi feed saat ini; tanda ✕ "ANDA DI SINI" versus ★ "REKOMENDASI"
menunjukkan ke mana optimizer meminta operator bergeser dan mengapa.
`[cara ambil]` halaman Digesti (skenario spike jam ±30 agar jarak ✕→★ jauh).
<screenshot: heatmap peta operasi dengan dua penanda>

**E2 — Radar setpoint.**
Kelima parameter dalam satu bentuk: selisih siluet biru (sekarang) dan hijau
(rekomendasi) memperlihatkan apa yang perlu diubah dan seberapa jauh.
`[cara ambil]` expander **Radar setpoint** di halaman yang sama.
<screenshot: radar biru vs hijau>

**E3 — Kurva Pareto & parallel coordinates.**
Enam puluh solusi optimal yang saling tawar-menawar (tidak ada yang unggul
di semua tujuan). Pada tampilan parallel coordinates, juri/operator dapat
menyeret rentang pada sumbu mana pun — misalnya "hanya recovery > 88%" —
dan melihat setpoint mana yang tersisa.
`[cara ambil]` expander **Kurva Pareto** → klik hitung; ambil dua gambar
(tab scatter, tab parallel coordinates dengan satu filter terseret).
<screenshot: pareto scatter dengan bintang PILIHAN>
<screenshot: parallel coordinates dengan filter aktif>

**E4 — What-if cepat.**
Geser setpoint untuk feed jam ini dan prediksi keempat target berubah
seketika — sarana operator menguji intuisi sebelum memutuskan.
`[cara ambil]` panel **What-if cepat**, geser satu slider dari nilai awal.
<screenshot: slider + empat metrik delta>

---

## F. Liquor Loop — Ekonomi NaOH

**F1 — Sankey Natrium.**
Aliran uang terbesar pabrik: dari make-up dan recycle, berapa yang kembali
dan berapa yang bocor lewat tiga pintu (DSP karena silika, soda mati karena
karbonasi, fisik terikut red mud).
`[cara ambil]` halaman Liquor Loop.
<screenshot: sankey natrium + empat metrik kebocoran>

**F2 — Advisory dosis CaO.**
Dosis kapur pembanding dihitung stoikiometrik (Na₂CO₃ + Ca(OH)₂ → 2NaOH +
CaCO₃) dan dibandingkan dengan dosis aktual — status over/under-dosing
beserta risikonya masing-masing.
`[cara ambil]` kartu **Dosis Make-up** di halaman yang sama.
<screenshot: kartu dosis CaO dengan status>

**F3 — Analisis AI per chart.**
Setiap visual kunci memiliki tombol Analisis AI: jawaban dihitung hanya dari
angka chart tersebut ditambah dokumen pengetahuan pabrik yang relevan, dan
wajib mengutip nama dokumen sumbernya — bukan chatbot generik.
`[cara ambil]` expander **Analisis AI** di bawah Sankey → ketik pertanyaan
(mis. "mana kebocoran terbesar?") → Analisis. (Aktifkan LLM via `.env`
agar jawabannya naratif; tanpa itu tampil ringkasan angka.)
<screenshot: jawaban analisis AI dengan sitasi dokumen knowledge>

---

## G. Presipitasi

**G1 — Kurva ekuilibrium & gap supersaturasi.**
Jarak antara alumina terlarut dan garis kelarutan ekuilibrium (korelasi
Misra) adalah tenaga pendorong pengendapan — "yield yang belum diambil"
yang tidak terlihat oleh operator tanpa alat ini.
`[cara ambil]` halaman Presipitasi.
<screenshot: kurva Ceq dengan titik operasi + metrik gap>

---

## H. Red Mud & CCUS

**H1 — Sankey aluminium + kalkulator karbonasi.**
Berapa aluminium yang gagal terambil dan ikut terbuang, lalu sisi baliknya:
red mud sebagai bahan baku sekuestrasi CO₂ (23 kg/ton, kondisi paper) dengan
kebutuhan air, nilai rupiah karbon, dan status pH terhadap baku mutu
Permen LHK 6/2021.
`[cara ambil]` halaman Red Mud & CCUS; coba juga ubah harga karbon.
<screenshot: sankey aluminium + panel karbonasi + status pH>

---

## I. Prediction Lab — Eksperimen Bebas

**I1 — Input komposisi & laju umpan.**
Sembilan oksida diatur bebas (sisa otomatis digenapkan ke 100%), berikut
laju umpan basah dan kadar air — mensimulasikan pengiriman bauksit apa pun
pada skala pabrik berapa pun.
`[cara ambil]` halaman Prediction Lab, bagian atas.
<screenshot: grid komposisi + feed rate/moisture>

**I2 — Dua mesin berdampingan: ML vs fisika.**
Prediksi model pembelajaran mesin dan hasil kalkulator neraca massa (port
dari Excel pabrik) ditampilkan bersisian dengan selisihnya — saling
mengecek, inti dari konsep digital twin.
`[cara ambil]` bagian **Prediksi Real-Time** di halaman yang sama.
<screenshot: kolom ML vs kolom kalkulator + delta>

**I3 — Peringatan ekstrapolasi.**
Bila input berada di luar rentang data latih, sistem berterus terang bahwa
prediksi ML-nya kurang dapat dipercaya — kejujuran yang menjaga kepercayaan
operator.
`[cara ambil]` set silika reaktif ke nilai ekstrem (mis. 12%).
<screenshot: banner peringatan ekstrapolasi>

**I4 — Sensitivitas & ranking pengaruh.**
Lima kurva "apa-jika" per parameter plus tornado ranking: parameter mana
yang paling menggerakkan target untuk komposisi yang sedang diuji.
`[cara ambil]` bagian **Simulasi What-If Parameter**.
<screenshot: lima kurva sensitivitas + tornado>

---

## J. Knowledge — Pengetahuan Expert

**J1 — Daftar dokumen dan pemakaiannya.**
Pengetahuan pakar tersimpan sebagai dokumen ber-tag; setiap dokumen
menampilkan chart mana saja yang memakainya — pemetaan lentur yang berubah
otomatis saat tag diubah.
`[cara ambil]` halaman Knowledge, buka satu dokumen (mis. caustic-loss).
<screenshot: dokumen terbuka dengan chips "Dipakai oleh">

**J2 — Menambah pengetahuan dari dashboard.**
Expert dapat menulis langsung: pilih chart tujuan dari daftar (tag terisi
otomatis), dan dokumen baru langsung dipakai AI tanpa restart.
`[cara ambil]` form **Atau tulis langsung** dengan multiselect chart terisi.
<screenshot: form tulis langsung + multiselect chart>
