# 22 — Deploy (menggantikan doc 16)

> Doc 16 menargetkan Streamlit Community Cloud dan sudah tidak berlaku sejak
> konsol Streamlit dipensiunkan dari `main`. Dokumen ini yang dipakai sekarang.

Tujuan: **juri cukup membuka satu link**, tanpa memasang apa pun.

---

## Pilih jalur dulu — ini menentukan segalanya

| Situasi | Jalur | Kenapa |
|---|---|---|
| **Link dikirim di proposal.** Juri membuka sendiri, kapan saja, tanpa kamu di sana | **A — Vercel + Render + cron** | Tidak ada yang bisa "memanaskan" link sebelum dibuka. Cold start akan dibaca sebagai aplikasi rusak |
| **Tanpa akun / offline** | **E — Docker Compose lokal** | Satu perintah |

Sisa dokumen ini berfokus ke **jalur A**, karena itu kasus yang paling tidak
memaafkan kesalahan.

### Kenapa jalur A dipecah ke dua penyedia

Godaan pertama adalah menaruh frontend dan backend sama-sama di Render, karena
`render.yaml` bisa menyalakan keduanya sekaligus. Jangan. Di free tier keduanya
tidur setelah ~15 menit menganggur, dan kegagalannya berlapis dua:

1. Juri klik link → frontend tidur, bangun 30–60 dtk. **Layar kosong.**
2. Frontend akhirnya render → memanggil backend, yang **juga masih tidur**.
3. Halaman tampil lengkap tetapi seluruh angkanya kosong dengan status
   **"API terputus"**.

Langkah 3 yang mematikan. Juri tidak melihat "sedang bangun" — dia melihat
aplikasi yang terbuka tapi rusak, lalu menutup tab.

Menjaga keduanya tetap hidup dengan ping juga bukan jalan keluar, karena
**jatah 750 jam instance Render dihitung per AKUN, bukan per service.** Satu
bulan ≈ 730 jam. Dua service yang sama-sama dijaga hidup = ~1460 jam: kuota
habis sekitar tanggal 15, lalu Render menangguhkan keduanya sampai bulan
berikutnya. Untuk demo yang kamu tonton sendiri itu tidak apa-apa; untuk
proposal yang dibuka entah kapan, itu persis skenario terburuknya.

Dan ada alasan yang lebih dalam dari sekadar kuota. Seluruh penanganan cold
start yang sudah dibangun di UI — state `menyiapkan`, spanduk "Menyiapkan
server", percobaan ulang otomatis (`frontend/src/lib/store.tsx`) — **hanya
berfungsi kalau frontend hidup untuk menggambarnya.** Frontend yang tidur tidak
punya apa pun untuk menampilkan pesan apa pun.

Karena itu: frontend ke Vercel (tidak pernah tidur, tanpa kuota jam), dan 730
jam Render disisakan utuh untuk satu-satunya hal yang memang butuh Docker.

---

## Arsitektur jalur A

| Komponen | Di mana | Alasan pemilihan |
|---|---|---|
| Next.js (`frontend/`) | **Vercel** free | Tidak pernah tidur. Klik → langsung terbuka |
| FastAPI (`src/`) | **Render** free, Docker | Satu-satunya free tier tersisa yang menjalankan Docker tanpa kartu |
| Keep-alive | **cron-job.org** | Ping `/v1/health` tiap 10 mnt supaya backend tak sempat tidur |

> Syarat free tier berubah cukup sering dan **tanpa pengumuman** — lihat catatan
> HF Spaces di bawah. Konfirmasi sekali di halaman pricing resmi sebelum kamu
> menggantungkan penjurian padanya.

### RAM: 281 MB dari 512 MB (sudah diukur, bukan asumsi)

Kekhawatiran wajar soal Render free adalah 512 MB RAM untuk proses yang menarik
lightgbm + shap + pymoo + scikit-learn sekaligus. Sudah diukur langsung dengan
menembak seluruh jalur berat:

| Titik | RSS |
|---|---|
| baseline interpreter | 18 MB |
| setelah `import src.integration.api` | 117 MB |
| setelah `/v1/replay/1/hour/8` (muat model + shap) | 275 MB |
| setelah pareto + operating-map + active-learning | **281 MB** |

Sisa ~230 MB. Aman, dengan catatan: lonjakan besarnya terjadi sekali saja saat
model pertama dimuat, bukan tiap permintaan. Kalau backend restart sendiri
tepat saat optimizer dipakai, itu OOM — bukan bug kode.

### Kedua URL sudah bisa ditebak sebelum deploy

Ini menyelesaikan masalah ayam-telur: frontend butuh URL backend, backend butuh
URL frontend untuk CORS. Padahal keduanya ditentukan nama yang **kamu pilih
sendiri**:

| Layanan | Pola URL | Contoh |
|---|---|---|
| Vercel | `https://<nama-project>.vercel.app` | `https://optibayer.vercel.app` |
| Render | `https://<nama-service>.onrender.com` | `https://optibayer-api.onrender.com` |

Tentukan kedua nama itu **di awal**, lalu isi semua env var sekaligus.

> ⚠️ Nama service harus unik se-Render. Kalau `optibayer-api` sudah dipakai
> orang lain, Render menambah sufiks acak — dan nilai yang dipatok di
> `render.yaml` jadi salah alamat. **Selalu cek URL asli di dashboard** sebelum
> menganggap selesai.

---

## A1. Backend ke Render

`render.yaml` sudah berisi definisinya (backend saja — lihat komentar di
berkasnya soal kenapa frontend tidak ada di situ).

### Verifikasi kartu

Render meminta kartu untuk **verifikasi identitas** (otorisasi sementara $1 yang
dilepas kembali), bukan tagihan. Selama **Instance Type = Free**, tidak ada yang
ditagih. Kalau kartunya ditolak berulang, itu biasanya kartu virtual/prabayar
yang tidak mendukung pre-auth USD — pakai kartu kredit terbitan bank, atau kartu
debit yang sudah diaktifkan untuk transaksi internasional.

### Jalur Blueprint (kalau tersedia)

1. Pastikan repo sudah ter-push ke GitHub (`WwzFwz/OptiBayer`).
2. Render Dashboard → **New → Blueprint** → pilih repo ini.
3. Render membaca `render.yaml`, membangun `Dockerfile` di root, dan menyalakan
   `optibayer-api` di region `singapore`.

Kalau repo-mu tidak muncul di daftar, GitHub App Render belum diberi akses:
**Configure account** → pilih akunmu → tambahkan `OptiBayer` ke *Repository
access*. Repo yang baru diganti nama kadang perlu koneksi GitHub dipasang ulang.

### Jalur manual (kalau Blueprint terhalang)

**New → Web Service**, lalu isi sendiri — `render.yaml` tidak dibaca di jalur
ini, jadi env var harus diketik manual:

| Field | Isi |
|---|---|
| Language / Runtime | **Docker** |
| Branch | `main` |
| Region | **Singapore** |
| Root Directory | *(kosong)* |
| Dockerfile Path | `./Dockerfile` |
| Instance Type | **Free** |
| Health Check Path | `/v1/health` |

Root Directory dikosongkan karena `Dockerfile` ada di root dan build-nya butuh
`src/`, `data/`, `requirements.txt` yang juga di root.

Env var (Advanced): `CORS_ORIGINS`, `LLM_PROVIDER=template`, dan
`OPTIBAYER_WRITE_TOKEN` — yang terakhir harus kamu buat sendiri di jalur ini
karena `generateValue: true` cuma berlaku lewat Blueprint:

```powershell
$b = [byte[]]::new(24)
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
($b | ForEach-Object { '{0:x2}' -f $_ }) -join ''
```

### Setelah hidup

Build melatih surrogate (`Dockerfile:30`, ~14 dtk di laptop, lebih lama di
Render) — model ikut di dalam image, tidak dilatih saat start.

```bash
curl https://optibayer-api.onrender.com/v1/health
# {"ok":true,"service":"optibayer","version":"v1-draft"}
```

`OPTIBAYER_WRITE_TOKEN` di-generate otomatis oleh Render (`generateValue: true`)
— tidak perlu kamu isi, tapi salin nilainya dari dashboard kalau mau memakai
`/v1/knowledge/add` dari luar browser.

---

## A2. Frontend ke Vercel

Next.js-nya ada di subdirektori, jadi satu pengaturan wajib diubah:

1. <https://vercel.com/new> → import repo `OptiBayer`.
2. **Root Directory → `frontend`.** Kalau dilewat, Vercel tidak menemukan
   `package.json` dan build gagal.
3. Framework preset terdeteksi otomatis sebagai Next.js. Biarkan.
4. **Environment Variables** → tambahkan:

| Nama | Isi |
|---|---|
| `OPTIBAYER_API_URL` | `https://optibayer-api.onrender.com` |

5. Deploy. Nama project menentukan domainnya — pastikan cocok dengan yang sudah
   diisikan ke `CORS_ORIGINS` di Render.

> **Domainnya jelek?** Vercel menurunkan nama dari repo (`OptiBayer` →
> `opti-bayer`) dan menambah sufiks acak kalau sudah dipakai orang lain, mis.
> `opti-bayer-23b4.vercel.app`. Tidak perlu deploy ulang: **Settings → Domains →
> Add Domain** → ketik nama yang kamu mau. Domain lama tetap hidup sebagai alias,
> jadi tidak ada link yang mati. **Yang dipakai sekarang:
> `https://optibayer.vercel.app`.**

> **Mengubah env var di Vercel butuh Redeploy**, bukan restart — env terikat ke
> deployment, jadi nilai baru tidak dipakai sampai **Deployments → ⋯ →
> Redeploy**. Beda dari Render yang cukup Save lalu restart sendiri. Pastikan
> juga centang **Production** aktif; kalau hanya Preview, domain utama tetap
> memakai nilai lama.

Alamat API dibaca **saat runtime** lewat `frontend/src/app/layout.tsx:30`, bukan
ditanam ke bundle. Artinya kalau backend pindah, cukup ubah env var lalu
redeploy — tanpa perubahan kode. (`NEXT_PUBLIC_API_URL` tetap dihormati sebagai
cadangan di `lib/api.ts`.)

> Catatan `output: "standalone"`: mode itu dibutuhkan image Docker frontend,
> tetapi tidak relevan bagi Vercel yang punya pipeline sendiri. Karena itu di
> `frontend/next.config.ts` mode tersebut kini hanya aktif bila
> `BUILD_STANDALONE=1` — env yang di-set oleh `frontend/Dockerfile`. Vercel
> membangun tanpa env itu dan memakai jalur normalnya.

---

## A3. Pinger — di mana persisnya, dan kenapa wajib

**Pinger bukan bagian dari aplikasimu.** Dia layanan cron eksternal yang
memanggil URL backend dari luar, dengan jadwal tetap, supaya Render tidak pernah
menganggap backend menganggur. Tidak ada kode yang perlu ditulis; yang dipanggil
adalah `/v1/health` yang sudah ada (`src/integration/api.py:73`) — murah, tanpa
efek samping, tanpa auth.

Di Render ini **wajib, bukan optimasi**: tanpa pinger, instance tidur setelah 15
menit dan permintaan pertama juri menunggu 30–60 detik.

### Pilihan yang disarankan: cron-job.org (gratis)

1. Daftar di <https://cron-job.org> (gratis, tanpa kartu).
2. **Create cronjob**:

| Field | Isi |
|---|---|
| Title | `optibayer keepalive` |
| URL | `https://optibayer-api.onrender.com/v1/health` |
| Schedule | Every **10 minutes** |
| Request method | `GET` |

3. Aktifkan notifikasi kegagalan lewat email. Ini bonus penting: pinger jadi
   merangkap **monitoring**. Kalau backend mati diam-diam tiga minggu setelah
   proposal dikirim, kamu tahu — bukan juri yang menemukannya.

UptimeRobot (interval minimum 5 menit di paket gratis) bekerja sama baiknya.

> Interval 10 menit tidak menambah pemakaian kuota. Jam instance terpakai selama
> service **bangun**, bukan per permintaan — ping yang lebih sering tidak
> membuatnya lebih boros, dan ping yang lebih jarang dari 15 menit membuat
> seluruh usaha ini sia-sia.

### Alternatif: GitHub Actions (sudah disiapkan di repo)

Berkas `.github/workflows/keepalive.yml` sudah ada, tinggal diaktifkan dengan
mengisi repository variable `KEEPALIVE_URL`. Kelebihannya: ikut terversion di
repo. **Tapi dua jebakannya nyata**, dan keduanya menyerang justru pada skenario
proposal:

- **Scheduled workflow dinonaktifkan otomatis setelah ~60 hari tanpa aktivitas
  repo.** Proposal yang mengendap dua bulan akan kehilangan pinger-nya persis
  saat masih dibutuhkan.
- **Hanya gratis kalau repo publik.** Di repo privat, setiap run dibulatkan ke
  atas ke 1 menit; ping tiap 10 menit ≈ 4.300 menit/bulan, jauh melewati jatah
  2.000 menit.

Karena itu cron-job.org yang direkomendasikan, dan workflow ini disediakan
sebagai cadangan.

---

## Kandidat yang gugur, dan kenapa

Dicatat supaya tidak dievaluasi ulang dari nol. Semuanya **diuji langsung**, bukan
dibaca dari halaman pricing. Status per **27 Juli 2026**:

| Kandidat | Status | Sebab |
|---|---|---|
| **HF Spaces** | ❌ | Docker **dan** Gradio SDK menuntut langganan PRO/kredit di cpu-basic. Hanya Static Space (HTML/JS, tanpa Python) yang gratis. Diubah tanpa pengumuman — dokumentasi Docker Spaces sampai kini tidak menyebutnya |
| **Railway** | ❌ | Free tier permanen sudah tidak ada, tinggal kredit trial |
| **Koyeb** | ❌ | Setelah diakuisisi Mistral (Feb 2026), **pendaftaran baru ke tier gratis ditutup**; fokus dialihkan ke inferensi AI dan enterprise |
| **FastAPI Cloud** | ❌ | Lihat catatan `libgomp` di bawah — bukan soal kartu, tapi pustaka sistem |
| **Vercel Python Function** | ❌ | Batas bundle serverless 250 MB. scipy + scikit-learn + lightgbm + shap + pymoo + pandas sudah 400–600 MB |
| **Fly.io / Cloud Run** | ❌ | Menuntut kartu di depan |
| **Bekukan data, buang backend** | ❌ | Halaman monitoring bisa distatiskan, tapi `/v1/sensitivity`, `/v1/operating-map`, `/v1/pareto`, `/v1/active-learning` menghitung dari input yang juri ketik sendiri. Membekukannya membuat Prediction Lab jadi pajangan — justru bagian yang paling membuktikan klaim proposal |
| **Render free** | ✅ | Docker penuh, 512 MB cukup (terukur 281 MB), region Singapore |

### Jebakan `libgomp` — kenapa platform "Python murni" tidak cukup

FastAPI Cloud sempat berhasil di-deploy sepenuhnya: build lulus, app hidup,
`/v1/health`, `/v1/spec`, `/v1/replay/{id}`, dan `/v1/knowledge` semua 200. Yang
gagal hanya endpoint yang menyentuh model, dengan:

```
OSError: libgomp.so.1: cannot open shared object file
  ← lightgbm/libpath.py: ctypes.cdll.LoadLibrary(lib_lightgbm.so)
  ← joblib.load(surrogate_total_opex.joblib)
```

`lib_lightgbm.so` menautkan OpenMP secara **dinamis**. Itu paket sistem
(`apt install libgomp1`), bukan paket Python — tidak bisa dipasang lewat
`requirements.txt` maupun `pyproject.toml`. `Dockerfile:9` memasangnya sejak
awal, jadi seluruh jalur Docker aman; yang tidak aman adalah platform yang
membangun environment Python sendiri dan tidak memberi kendali atas image dasar.

Kegagalannya juga **senyap dan menyesatkan**: `registry.available()` hanya
mengembalikan daftar kosong kalau artefak tidak ada, sehingga `/v1/model/health`
sempat membalas `200` dengan `{"targets":{}}` — terlihat sehat padahal tidak ada
satu pun model yang termuat.

> **Aturan praktis:** kalau sebuah platform tidak memakai `Dockerfile` kita, uji
> `/v1/replay/1/hour/8` — bukan `/v1/health` — sebelum menyatakan deploy berhasil.
> Endpoint itu yang pertama kali memuat model.

Kalau suatu saat LightGBM harus dilepas supaya bisa jalan di platform non-Docker,
biayanya sudah terukur di `models/metrics.json`: hanya `total_opex` yang
memakainya, dan penggantinya (`hist_gbdt`, murni scikit-learn yang membawa
OpenMP di dalam wheel) memberi **R² 0.9454 → 0.9416**. Tiga target lain sudah
scikit-learn sejak awal.

---

## Urutan pengerjaan (± 30 menit)

1. Tentukan dua nama: project Vercel dan service Render. Tulis kedua URL-nya.
2. A1 — Render, tunggu build, **cek URL asli di dashboard**.
3. `curl <api>/v1/health` sampai hijau, lalu **`curl <api>/v1/replay/1/hour/8`** —
   ini yang pertama memuat model, dan satu-satunya yang membuktikan backend
   benar-benar berfungsi (lihat jebakan `libgomp`).
4. A2 — deploy Vercel dengan `OPTIBAYER_API_URL`.
5. Kalau domain Vercel ternyata beda dari tebakan, perbarui `CORS_ORIGINS` di
   Render lalu **restart** (tidak perlu build ulang).
6. Buka URL Vercel, pastikan indikator "API tersambung" hijau.
7. A3 — pasang pinger, jalankan sekali manual untuk memastikan 200.
8. Jalankan checklist di bawah.

### Status saat ini

| Komponen | Keadaan |
|---|---|
| Frontend | ✅ **live** di <https://optibayer.vercel.app> |
| Backend | ⏳ menunggu verifikasi kartu Render |
| Pinger | ⏳ belum dipasang |

---

## Variabel lingkungan (berlaku di platform mana pun)

| Variabel | Di service | Isi | Wajib? |
|---|---|---|---|
| `OPTIBAYER_API_URL` | web | URL publik backend | ✅ |
| `CORS_ORIGINS` | api | URL publik frontend (boleh dipisah koma) | ✅ |
| `OPTIBAYER_WRITE_TOKEN` | api | rahasia acak (Render meng-generate sendiri) | ✅ kalau publik |
| `LLM_PROVIDER` + kuncinya | api | lihat `.env.example`; default `template` (offline) | — |
| `MQTT_HOST` | api | kalau event OT mau diterbitkan ke broker sungguhan | — |

---

## Keamanan saat publik

Isi `OPTIBAYER_WRITE_TOKEN`. Selama terisi, **`/v1/knowledge/add`** menuntut
header `X-Write-Token` yang sama (`src/integration/api.py:506`) — endpoint itu
menulis BERKAS berisi teks bebas ke disk server. CORS saja tidak cukup
menjaganya: ia hanya mengikat browser, bukan `curl`.

**`/v1/audit/decision` sengaja TIDAK dijaga token.** Aplikasi ini belum punya
login, jadi token apa pun yang dikirim ke browser ikut terbaca siapa saja yang
membuka halaman — memasangnya di situ hanya keamanan pura-pura, sambil
memastikan tombol Terima/Tolak selalu 401 di konfigurasi ini. Risikonya juga
berbeda kelas: endpoint itu hanya menambah baris berbentuk tetap dengan panjang
dibatasi. Saat autentikasi nyata dipasang (AD/API-key per operator, doc 07),
identitas penekan tombol seharusnya ikut tercatat di kolom `sumber`.

---

## Batasan yang harus kamu tahu sebelum kirim proposal

**Penyimpanan bersifat sementara.** Render free tidak memberi disk persisten.
Keputusan Terima/Tolak di Audit Trail dan entri Knowledge Pack yang ditambahkan
lewat UI **hilang setiap kali container di-restart atau di-rebuild**. Dalam satu
sesi penjurian semuanya bekerja normal — refresh tetap menampilkan keputusan
tadi — tetapi jangan menjanjikan persistensi jangka panjang di proposal. Kalau
itu perlu, langkah berikutnya adalah database eksternal (mis. Postgres gratis di
Neon/Supabase), bukan menambah disk.

**Jangan membuat service free lain di akun Render yang sama.** Margin kuotanya
cuma ~20 jam sebulan; apa pun yang ikut bangun memakannya.

**Pinger mengurangi cold start, bukan menghapusnya.** Kalau pinger mati atau
platform memaksa rebuild, permintaan pertama tetap lambat. Karena itu:

- Sertakan **GIF demo + screenshot** di proposal, jangan hanya link. Semua
  platform gratis bisa mendadak suspend, dan proposal mungkin dibuka tiga
  minggu lagi. Kalau link bermasalah, juri tetap sudah melihat produknya. Ini
  asuransi paling murah yang ada.
- UI sudah menampilkan state "menyiapkan server" — **bukan** "API terputus" —
  selama backend belum pernah menjawab (`frontend/src/lib/store.tsx`). Aplikasi
  yang bilang "tunggu sebentar" dibaca sebagai sedang bekerja; yang bilang
  "terputus" dibaca sebagai rusak. Kondisi teknisnya identik, kesimpulan
  jurinya berbeda.

---

## E. Lokal / LAN (paling cepat, tanpa akun)

```bash
docker compose up --build
```

API di `:8000`, UI di `:3000`. API menyala lebih dulu, `healthcheck`-nya lulus,
baru frontend dinyalakan (`depends_on: service_healthy`) — jadi tidak ada
jendela waktu di mana UI terbuka tapi backend belum siap. Model dilatih saat
build image (~14 dtk), bukan saat start.

### Kalau portnya bentrok

Sangat mungkin terjadi — 3000 adalah port paling ramai di laptop pengembang.

```bash
WEB_PORT=3200 API_PORT=8100 docker compose up --build
```

`CORS_ORIGINS` mengikuti `WEB_PORT` **otomatis**, dan ini bukan kenyamanan
belaka: kalau keduanya tidak seiring, halaman tetap terbuka normal tetapi
seluruh datanya kosong dengan status "API terputus" — gagal senyap yang mudah
disangka backend mati padahal backend sehat.

### Untuk perangkat lain di jaringan yang sama

```bash
OPTIBAYER_API_URL="http://<IP-laptop>:8000" \
CORS_ORIGINS="http://<IP-laptop>:3000" docker compose up --build
```

---

## Troubleshooting

Gejala paling umum: **halaman terbuka normal, semua data kosong, status "API
terputus".** Backend hampir selalu sehat; yang salah biasanya CORS atau alamat.
Periksa berurutan:

```bash
# 1. Backend hidup?
curl https://optibayer-api.onrender.com/v1/health

# 2. CORS mengizinkan domain frontend? Baris access-control-* harus muncul.
curl -H "Origin: https://optibayer.vercel.app" -D - -o /dev/null \
     https://optibayer-api.onrender.com/v1/health | grep -i access-control

# 3. Alamat yang benar-benar dipakai halaman (jalankan di console browser):
#    window.__OPTIBAYER_API__
```

- Kosong di langkah 2 → `CORS_ORIGINS` salah/belum ter-restart. Harus **persis**
  sama termasuk `https://` dan tanpa garis miring di akhir.
- `undefined` di langkah 3 → `OPTIBAYER_API_URL` belum ter-set di frontend, atau
  deploy-nya belum dijalankan ulang setelah env diubah.
- Permintaan pertama lambat lalu normal → instance sempat tidur. Cek riwayat
  eksekusi pinger; kemungkinan ada jeda >15 menit.
- Backend restart sendiri saat Prediction Lab dipakai → OOM. Cek tab Metrics di
  Render; lihat angka RAM terukur di atas sebagai pembanding.

---

## Checklist H-1 penjurian

- [ ] Buka link frontend dari **jaringan lain** (mis. data seluler, mode samaran)
      — memastikan tidak ada yang lolos hanya karena cache browsermu
- [ ] Indikator API hijau
- [ ] Ganti skenario ke **"Gangguan: Silika Spike"**, tekan ▶ Mulai Simulasi
- [ ] Salin link satu halaman dalam (mis. `?p=redmud&s=1&h=14`), buka di tab
      baru — harus mendarat persis di sana (deep link)
- [ ] Cek satu kartu advisory memuat interval (mis. "±0.22") dan dasar delta
      "neraca massa eksak"
- [ ] Tekan Terima/Tolak sekali, lalu **refresh** — keputusan harus tetap ada
      di halaman Audit Trail (kalau hilang, backend tidak menerima POST-nya:
      cek `CORS_ORIGINS`)
- [ ] `curl <api>/v1/health` mengembalikan `{"ok":true}`
- [ ] Riwayat eksekusi pinger menunjukkan 200 berturut-turut
- [ ] Dashboard Render: sisa jam instance bulan ini masih wajar
- [ ] GIF demo + screenshot sudah terlampir di proposal sebagai cadangan
