# Benchmark & kepercayaan model (doc 14 C1–C4)

> Dokumen ini menutup empat utang teknis di doc 14 dengan PENGUKURAN, bukan
> argumen. Semua angka di bawah dibangkitkan ulang oleh kode di repo:
> `python -m src.models.benchmark --out docs/21-benchmark-model.md` (tabel di
> bawah) dan `python -m src.models.verify -n 200` (bagian fidelitas).
> Regenerasi kalau data atau model berubah.

**Ringkasan temuan yang mengubah keputusan:**

| # | Yang diyakini sebelumnya | Yang terukur | Akibatnya |
|---|---|---|---|
| 1 | "LightGBM adalah pilihannya" | LightGBM kalah di 3 dari 4 target | Model dipilih **per target** lewat adu CV |
| 2 | C4: OPEX perlu log-transform | log1p memperburuk (R² 0.945→0.924) | C4 **ditolak dengan bukti**, tidak dikerjakan |
| 3 | Kepercayaan advisory = label tangan | Interval konformal, cakupan teruji 88.8–96.4% | Kartu advisory memuat ±, bukan kata "tinggi" |
| 4 | Guard kotak per-fitur sudah cukup | Titik "sah" bisa bikin fisika keluar OPEX **negatif** | Guard + cek plausibilitas komposisi (jumlah ~100%) |
| 5 | Delta rekomendasi dari selisih prediksi ML | ML kelebihan janji ~22% di titik optimizer | Delta dihitung ulang dengan **neraca massa eksak** |

---

## 1. Kenapa bukan satu model untuk semua? (C2)

Data 997 baris · 5-fold CV · fitur & seed identik untuk semua kandidat.

> Catatan penting: target di data ini dihasilkan ulang oleh kalkulator neraca massa deterministik, jadi angka R² mengukur seberapa setia sebuah model meniru KALKULATOR — bukan akurasi terhadap pabrik nyata (doc 14 A1).

Pola yang muncul konsisten: target yang berasal dari formula fisika yang MULUS
(recovery, red mud, yield) lebih cocok ke ridge-polinomial — pohon memang buruk
meniru permukaan mulus karena hasilnya bertangga. Sebaliknya OPEX yang
bertingkat (biaya reagen dengan patahan) justru paling pas ke gradient boosting.
Karena itu `train.train_one` mengadu semua keluarga per target dan memilih MAE
CV terkecil di antara yang lolos anggaran kecepatan (≤15 µs/prediksi, karena
NSGA-II memanggil surrogate 2400× per jalan — RandomForest tersingkir di sini
meski skornya bagus).

## Recovery Al (%) (`recovery_pct`)

| Model | CV R² | CV MAE | Latih (dtk) | Prediksi (µs/baris) |
|---|---:|---:|---:|---:|
| ridge_poly2 **←dipakai** | 0.9986 | 0.1060 | 0.011 | 1.90 |
| lightgbm | 0.9871 | 0.3249 | 0.125 | 5.47 |
| hist_gbdt | 0.9860 | 0.3364 | 0.350 | 10.75 |
| ridge | 0.9633 | 0.5716 | 0.002 | 0.77 |
| random_forest | 0.9623 | 0.5555 | 2.110 | 36.69 |
| dummy_rata2 | -0.0014 | 3.3100 | 0.000 | 0.02 |

## Total OPEX (/jam) (`total_opex`)

| Model | CV R² | CV MAE | Latih (dtk) | Prediksi (µs/baris) |
|---|---:|---:|---:|---:|
| lightgbm **←dipakai** | 0.9455 | 517.9024 | 0.118 | 5.73 |
| hist_gbdt | 0.9415 | 551.0243 | 0.556 | 12.41 |
| random_forest | 0.9041 | 675.8813 | 2.122 | 32.79 |
| ridge_poly2 | 0.8824 | 1129.2091 | 0.007 | 2.69 |
| ridge | 0.6723 | 1790.4701 | 0.003 | 1.03 |
| dummy_rata2 | -0.0009 | 3008.5267 | 0.000 | 0.03 |

## Red Mud Basah (ton) (`red_mud_t`)

| Model | CV R² | CV MAE | Latih (dtk) | Prediksi (µs/baris) |
|---|---:|---:|---:|---:|
| ridge_poly2 **←dipakai** | 0.9997 | 1.1305 | 0.008 | 2.91 |
| ridge | 0.9966 | 3.7129 | 0.004 | 1.25 |
| lightgbm | 0.9910 | 5.9803 | 0.124 | 6.64 |
| hist_gbdt | 0.9908 | 6.1952 | 0.444 | 13.64 |
| random_forest | 0.9752 | 10.2474 | 2.083 | 33.03 |
| dummy_rata2 | -0.0005 | 68.0615 | 0.000 | 0.03 |

## Yield Presipitasi (%) (`precip_yield_pct`)

| Model | CV R² | CV MAE | Latih (dtk) | Prediksi (µs/baris) |
|---|---:|---:|---:|---:|
| random_forest | 1.0000 | 0.0129 | 1.991 | 37.53 |
| hist_gbdt **←dipakai** | 0.9999 | 0.0206 | 0.450 | 12.64 |
| ridge_poly2 | 0.9998 | 0.0371 | 0.007 | 2.48 |
| lightgbm | 0.9995 | 0.0457 | 0.152 | 7.09 |
| ridge | 0.9981 | 0.1064 | 0.003 | 1.11 |
| dummy_rata2 | -0.0003 | 2.4359 | 0.000 | 0.04 |

---

## 2. Interval konformal — kepercayaan yang bisa diuji (C1)

`train.conformal_quantiles()` mengambil |residual| out-of-fold, lalu kuantil
dengan koreksi sampel-hingga `ceil((n+1)·level)/n`. Hasilnya dipakai
`predict.interval()` dan tampil di KPI, kartu advisory, dan Prediction Lab.

**Lebar interval 90% pada model terpasang:**

| Target | Keluarga | ± (90%) | Perbandingan: sebelum pemilihan model (LightGBM) |
|---|---|---:|---:|
| Recovery Al (%) | ridge_poly2 | ±0.219 pp | ±0.736 pp |
| Total OPEX (/jam) | lightgbm | ±1 460 | ±1 460 |
| Red Mud (ton) | ridge_poly2 | ±2.33 t | ±13.01 t |
| Yield Presipitasi (%) | hist_gbdt | ±0.040 pp | ±0.100 pp |

**Cakupan diuji di data held-out**, bukan di residual yang membentuk kuantilnya
(itu tautologis). Kalibrasi hanya dari data latih, cakupan diukur pada 25% data
uji:

| Target | Cakupan terukur | Target nominal |
|---|---:|---:|
| recovery_pct | 89.6% | 90% |
| total_opex | 91.6% | 90% |
| red_mud_t | 88.8% | 90% |
| precip_yield_pct | 96.4% | 90% |

Dijaga oleh `tests/test_model_trust.py::test_cakupan_konformal_pada_data_held_out`.

> **Batas kejujuran.** Data latih saat ini adalah keluaran kalkulator
> deterministik, jadi residual = galat surrogate terhadap KALKULATOR, bukan
> ketidakpastian pabrik. Begitu data historian masuk, kodenya tidak berubah
> tetapi artinya naik kelas jadi ketidakpastian sesungguhnya.

---

## 3. Fidelitas surrogate vs fisika (menjawab A1)

`python -m src.models.verify -n 200`. Metrik = **NMAE**: galat absolut dibagi
rentang target di data latih. MAPE sengaja tidak dipakai sebagai metrik utama —
pada satu titik uji, fisika mengeluarkan OPEX **−605** (mustahil) sehingga
"MAPE 845%" hanya artefak pembagi, bukan kegagalan model.

| Populasi sampel | recovery | OPEX | red mud | yield |
|---|---:|---:|---:|---:|
| perturbasi data nyata (±5%, komposisi tetap 100%) | 0.46% | 0.74% | 0.18% | 0.14% |
| undian dalam kotak rentang per-fitur | 2.53% | 0.97% | 9.49% | 0.12% |
| ekstrapolasi (kotak dilebarkan +25%) | 3.58% | 2.78% | 13.90% | 0.28% |

Dua pelajaran:

1. **Guard OOD terbukti perlu.** Galat naik 2–8× begitu titik operasi keluar
   rentang latih. Itulah dasar kartu peringatan ekstrapolasi di advisory.
2. **Guard kotak per-fitur saja TIDAK cukup.** Undian di dalam kotak sudah
   memburuk tajam untuk red mud (9.5%) karena komposisi hasil undian tidak
   menjumlah 100% — semua baris latih berjumlah 99.97–100.02%, undian median
   101.5%. Karena itu `predict.ood_report()` menambahkan cek plausibilitas
   komposisi, bukan hanya cek rentang.

Dari 200 titik ekstrapolasi, 5 di antaranya membuat kalkulator fisika sendiri
mengeluarkan nilai mustahil dan dikeluarkan dari statistik (dilaporkan terpisah
sebagai `n_tak_masuk_akal`).

**Kecepatan** (dasar klaim di pitch — jangan mengarang angka): fisika ≈86 µs per
evaluasi, surrogate ≈17 µs per baris dalam mode batch → sekitar **5×** lebih
cepat. Bukan ribuan kali. Nilai sesungguhnya dari surrogate bukan kecepatan
ekstrem, melainkan bahwa ia bisa dilatih ulang pada data historian nyata yang
TIDAK punya rumus tertutup.

---

## 4. Wasit fisika & winner's curse

Karena fisika hanya ~86 µs, setiap rekomendasi dicek ulang olehnya sebelum
sampai ke operator (`models/verify.py::verify`).

Awalnya ambang ketidaksepakatan dipasang di 1× interval konformal. Terukur pada
64 setpoint rekomendasi lintas dua skenario, selisih melampaui 1× pada 6–25%
kasus **padahal modelnya sehat** — sebabnya setpoint yang diperiksa bukan titik
acak melainkan pilihan optimizer, yang secara sistematis berdiri di tempat
surrogate paling optimistis (*winner's curse*). Ambang lalu dikalibrasi ke **2×**
(p90 terukur 1.0–2.0×) supaya kartu peringatan hanya menyala di kasus menonjol.

Obat sesungguhnya bukan menaikkan ambang, melainkan **skor ulang**: NSGA-II tetap
mencari dengan surrogate (butuh 2400 evaluasi), tetapi angka yang dilihat
operator dihitung ulang dengan neraca massa eksak. Contoh terukur pada skenario
spike jam 8:

| | recovery | OPEX | red mud |
|---|---:|---:|---:|
| janji versi ML | +1.578 pp | −3 591 | −9.91 t |
| **neraca massa eksak (dipakai UI)** | **+1.293 pp** | **−2 378** | **−8.07 t** |

Surrogate melebih-lebihkan perbaikan recovery sekitar 22%. Kartu advisory
menandai dasar angkanya dengan teks "neraca massa eksak".

---

## 5. C4 (log-transform OPEX) — diuji lalu DITOLAK

doc 14 C4 mengasumsikan OPEX perlu log-transform karena "rentang sangat lebar
167–4260". Angka itu berasal dari data v1. Pada data v2 yang dipakai sekarang,
rentangnya 1 875–28 437 dengan skew **negatif** (−1.86) — dan log1p justru
memperburuk:

| | CV R² | CV MAE |
|---|---:|---:|
| target apa adanya | **0.9455** | **517.90** |
| log1p | 0.9243 | 607.22 |

Di ujung bawah rentang (10% terendah) log1p hanya menang tipis (MAE 1 835 vs
1 871) — tidak sepadan dengan kemunduran menyeluruh. **C4 ditutup sebagai
ditolak**, dan usaha dialihkan ke wasit fisika di bagian 4, yang menyelesaikan
masalah sesungguhnya (angka OPEX yang dipegang operator kini eksak).
