# 23 — Status Deploy (serah-terima konteks)

**Ditulis 11 Agustus 2026. Tim GLADIOOL 72.**

Doc 22 menjelaskan *bagaimana* men-deploy. Dokumen ini mencatat *di mana kita
sekarang* dan *keputusan apa yang sudah dibuat* — supaya tidak hanya hidup di
riwayat chat, yang tidak ikut berpindah antar sesi.

---

## Status

**Sudah lolos ke babak final.** Dua pekerjaan tersisa: **deploy backend** dan
**bikin PPT**.

| Komponen | Platform | Status |
|---|---|---|
| Next.js (`frontend/`) | Vercel free (Hobby) | ✅ live di `opti-bayer-23b4.vercel.app` |
| FastAPI (`src/`) | Render free tier (Docker) | 🔨 blocker utama |
| Keep-alive | cron-job.org → `/v1/health` tiap 10 menit | ⬜ belum |

Nama project Vercel kena sufiks acak. Selama alias bersih belum dipasang
(doc 22, bagian A2), **`CORS_ORIGINS` harus memakai URL bersufiks itu.**

---

## Rencana yang dibatalkan, dan alasannya

**HF Spaces Docker — tidak lagi gratis.** Per Juli 2026 Docker SDK di Hugging
Face Spaces ditandai "Paid"; hanya Static Spaces yang tersisa gratis.

**Vercel untuk backend — salah paham yang sudah diluruskan.** Sempat dikira
butuh Docker (berbayar). Kenyataannya Next.js di Vercel berjalan native, tanpa
Docker sama sekali. Yang butuh Docker hanya backend FastAPI.

**Pre-commit artefak model supaya container tidak train saat build — dibatalkan
setelah diukur.** Lihat bagian berikutnya.

---

## Angka hasil pengukuran

### Training saat build tetap dipakai

| Yang diukur | Hasil |
|---|---|
| `python -m src.models.train --quiet` | **27,2 dtk** (laptop lokal) |
| Docker build penuh (layer pip ter-cache) | **114,8 dtk** |

27 detik jauh di bawah ambang risiko build timeout. Melatih saat *start*
justru membuat permintaan pertama juri menunggu ~10 detik. Karena itu
`RUN python -m src.models.train --quiet` (`Dockerfile:35`) dipertahankan.

### Memori

Diukur di dalam container dengan `-m 512m` (mensimulasikan limit Render):

| Titik | RSS |
|---|---|
| idle (baru melayani health check) | 120,9 MiB |
| **setelah replay + 4× pareto + operating-map + active-learning** | **170,9 MiB (33%)** |

**Aman, margin besar** — sisa ~340 MiB dari 512. Patokan yang dipakai: < 350 MB
aman, > 450 MB perlu turunkan populasi/generasi. Tidak perlu mitigasi apa pun.

Doc 22 mencatat 281 MB puncak; angka itu diukur pada proses Python telanjang di
laptop, bukan di dalam container ber-limit. Yang berlaku untuk keputusan Render
adalah 170,9 MiB di atas. Keduanya sama-sama di bawah batas, jadi kesimpulannya
tidak berubah.

### Waktu respons — asumsi awal ternyata KELIRU

Diukur di laptop, container ber-limit, tiap `hour` berbeda supaya tidak kena
cache:

| Endpoint | Laptop | Perkiraan Render (3–10×) |
|---|---|---|
| `/v1/replay/1/hour/8` (muat model) | 1,68 s | 5–17 s |
| `/v1/pareto` dingin (rata-rata 3 jam) | ~0,90 s | 3–9 s |
| `/v1/pareto` dari cache | **0,05 s** | ~0,5 s |
| `/v1/operating-map` | 0,85 s | 3–9 s |
| **`/v1/active-learning`** | **3,46 s** | **10–35 s** |

**NSGA-II bukan masalahnya.** Kekhawatiran awal tertuju ke pareto (2400 evaluasi
surrogate per run), padahal ia hanya 0,9 detik — evaluasi surrogate itu murah.
Endpoint paling lambat justru **`/v1/active-learning`, 3,8× lebih lambat dari
pareto**. Kalau nanti ada yang perlu dioptimasi di Render, itu targetnya —
jangan sentuh `pop`/`gen` di `src/optimize/pareto.py:60` tanpa bukti baru.

### Mitigasi yang dipilih: panaskan cache, jangan turunkan kualitas

`_pareto_hour` di `src/integration/api.py:122` dibungkus `@lru_cache(maxsize=256)`.
Terukur: 0,99 s → **0,05 s**, sekitar **20× lebih cepat**.

Karena itu, mitigasi yang benar bukan mengecilkan populasi NSGA-II (yang
menurunkan kualitas rekomendasi — justru inti nilai jual produk ini), melainkan
**memperluas pinger cron-job.org**: selain `/v1/health`, panggil juga endpoint
skenario yang akan dipresentasikan ke juri. Nol perubahan kode, hasil tetap
kualitas penuh.

⚠️ `lru_cache` hidup di memori proses. Kalau Render sempat spin-down atau
rebuild, cache hilang dan permintaan pertama kembali dingin. Pinger mengurangi
peluang itu, tidak menghapusnya — karena itu video demo cadangan tetap wajib.

---

## Perubahan yang sudah diterapkan (11 Agustus)

### Dockerfile: port mengikuti env var

Render menyuntik `PORT` sendiri (default 10000). Port hardcoded 8000 membuat
service dianggap gagal start.

```dockerfile
CMD ["sh", "-c", "python -m uvicorn src.integration.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Bentuk `sh -c` **wajib**: exec form tidak melakukan ekspansi variabel, sehingga
`${PORT}` diteruskan mentah ke uvicorn. `HEALTHCHECK` ikut memakai
`${PORT:-8000}`. `EXPOSE 8000` dibiarkan — sifatnya hanya dokumentasi.

Endpoint `/v1/health` sudah ada; tidak perlu bikin `/healthz` baru.

### Dockerfile: komentar yang salah sudah diperbaiki

Komentar lama menyatakan artefak `.joblib` "tidak ikut di git". Itu keliru —
`.gitignore` punya negasi eksplisit `!models/surrogate_*.joblib`, artinya
artefak surrogate **sengaja di-track** (dibutuhkan jalur non-Docker seperti
FastAPI Cloud, yang tidak punya langkah training).

Jangan jalankan `git rm --cached` pada berkas itu — membatalkan keputusan tim.

Konsekuensi berguna: kalau build di Render kena timeout, ada **fallback** —
ganti `COPY models/metrics.json ./models/` jadi `COPY models/ ./models/`, lalu
hapus baris `RUN python -m src.models.train`.

### Rujukan baris yang sudah usang, diperbarui

`Dockerfile:30` → `Dockerfile:35` di `.gitignore` dan `docs/22-deploy.md`
(baris training bergeser setelah komentar diperbaiki). Estimasi "~14 dtk" di
doc 22 diganti angka terukur 27 dtk.

---

## Yang TIDAK perlu diubah

**CORS tidak butuh edit kode.** `src/integration/api.py` sudah membaca env var
`CORS_ORIGINS` (dipisah koma, default dev lokal). Cukup set env var di Render
— jangan hardcode domain ke source.

---

## Langkah berikutnya

1. ✅ Ukur MEM USAGE + waktu respons — **selesai, semua aman** (lihat di atas)
2. ✅ Build ulang & tes lokal — **`PORT` terbukti dihormati**: dijalankan dengan
   `-e PORT=10000 -p 8000:10000`, log menunjukkan `Uvicorn running on
   http://0.0.0.0:10000` dan `/v1/health` menjawab lewat port 8000.
   (Uji dengan `PORT=8000` tidak sah — Dockerfile lama pun menghasilkan 8000.)
3. ⬜ Push ke `main` — **stage manual, jangan `git add -A`**, lihat di bawah
4. ⬜ Bikin akun Render via **Sign in with GitHub** (bukan email)
5. ⬜ New Web Service → Docker → branch `main` → region Singapore →
   instance **Free** → Health Check Path `/v1/health`
6. ⬜ Set `CORS_ORIGINS` = `https://opti-bayer-23b4.vercel.app,http://localhost:3000`
7. ⬜ Set `OPTIBAYER_API_URL` di Vercel, lalu **redeploy** frontend
8. ⬜ cron-job.org: ping `/v1/health` tiap 10 menit
   (6 ping/jam × 24 × 30 masih di bawah kuota 750 jam/bulan).
   Tambahkan job kedua yang memanggil endpoint skenario demo supaya
   `lru_cache` ikut panas — lihat bagian mitigasi di atas.
9. ⬜ **Rekam video demo 2-3 menit sebagai backup** — kalau backend down saat
   juri mengakses, video ini penyelamat

---

## Kendala signup Render

Signup sebelumnya **kartu ditolak**. Dugaan penyebab: deploy lewat **Blueprint**
(`render.yaml`) yang memilih instance berbayar, ATAU kartu Indonesia ditolak
Stripe.

**Mitigasi**: jangan pakai Blueprint dulu. Bikin Web Service manual lewat
dashboard dan pilih instance **Free** secara eksplisit. Kalau tetap diminta
kartu: pakai Jenius / Bank Jago / Wise virtual card, dan pastikan transaksi
internasional aktif di mobile banking.

---

## Platform lain yang sudah dicek (per Agustus 2026)

| Platform | Keadaan |
|---|---|
| **Fly.io** | Free tier dihapus sejak 2024, wajib kartu |
| **Koyeb** | Free Starter ditutup untuk user baru setelah diakuisisi Mistral AI awal 2026 |
| **Railway** | $5 trial sekali + $1/bulan; bisa habis 1-2 minggu. Opsi darurat jangka pendek |
| **Cloudflare Tunnel + laptop** | Gratis total, tanpa kartu. **Plan B kalau Render buntu.** Kelemahan: laptop harus nyala |

Lihat juga doc 22 bagian "Kandidat yang gugur" — khususnya jebakan `libgomp`
yang membuat platform "Python murni" tidak cukup untuk LightGBM.

---

## Catatan repo

### ⚠️ Working tree penuh noise CRLF — jangan `git add -A`

Per 11 Agustus, `git status` menampilkan **142 file modified**. Diperiksa satu
per satu dengan `git diff --ignore-cr-at-eol`: hanya **3 file yang isinya
benar-benar berubah** (`Dockerfile`, `.gitignore`, `docs/22-deploy.md`). Sisanya
— seluruh `frontend/`, `src/`, `tests/`, semua docs — murni konversi akhir baris
LF→CRLF dari editor Windows, nol baris isi berubah.

Stage manual supaya diff commit tetap terbaca:

```bash
git add Dockerfile .gitignore docs/22-deploy.md docs/23-status-deploy.md
git commit -m "fix(deploy): port ikut env var PORT + luruskan komentar artefak model"
git restore .   # buang 139 file noise CRLF
```

Kalau ini berulang, pertimbangkan `git config core.autocrlf input` atau
`.gitattributes` dengan `* text=auto eol=lf`.

### Menjalankan ulang training bikin 9 file "modified"

Normal, bisa di-discard
(`git restore models/`). Yang berubah hanya `us_per_prediksi` — benchmark
mikrodetik, noise tergantung beban laptop. `cv_r2` dan `cv_mae` identik persis,
artinya training deterministik dan reproducible.
