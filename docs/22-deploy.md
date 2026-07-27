# 22 — Deploy (menggantikan doc 16)

> Doc 16 menargetkan Streamlit Community Cloud dan sudah tidak berlaku sejak
> konsol Streamlit dipensiunkan dari `main`. Dokumen ini yang dipakai sekarang.

Tujuan: **juri cukup membuka satu link**, tanpa memasang apa pun.

---

## Pilih jalur dulu — ini menentukan segalanya

Dua situasi di bawah kelihatan mirip tapi menuntut arsitektur berbeda:

| Situasi | Jalur | Kenapa |
|---|---|---|
| **Link dikirim di proposal.** Juri membuka sendiri, kapan saja, tanpa kamu di sana | **A — Vercel + HF Spaces + pinger** | Tidak ada yang bisa "memanaskan" link sebelum dibuka. Cold start akan dibaca sebagai aplikasi rusak |
| **Demo langsung.** Kamu buka linknya sendiri di depan juri | **D — Render blueprint** | Cukup buka link 1 menit sebelum mulai. Setup paling singkat |
| **Tanpa akun / offline** | **E — Docker Compose lokal** | Satu perintah |

Sisa dokumen ini berfokus ke **jalur A**, karena itu kasus yang paling tidak
memaafkan kesalahan.

### Kenapa jalur A ada

Di Render free tier, kedua service tidur setelah ~15 menit menganggur. Untuk
link yang dibuka juri tanpa persiapan, kegagalannya berlapis dua:

1. Juri klik link → frontend tidur, bangun 30–60 dtk. Layar kosong.
2. Frontend akhirnya render → memanggil backend, yang **juga masih tidur**.
3. Halaman tampil lengkap tetapi seluruh angkanya kosong dengan status
   **"API terputus"**.

Langkah 3 yang mematikan. Juri tidak melihat "sedang bangun" — dia melihat
aplikasi yang terbuka tapi rusak, lalu menutup tab. Jalur A menghapus kedua
lapisan itu: Vercel tidak pernah tidur, dan pinger menjaga backend tetap hidup.

---

## Arsitektur jalur A

| Komponen | Di mana | Alasan pemilihan |
|---|---|---|
| Next.js (`frontend/`) | **Vercel** free | Tidak pernah tidur. Klik → langsung terbuka |
| FastAPI (`src/`) | **HF Spaces** (Docker) | 16 GB RAM (isu OOM 512 MB lenyap), tanpa kuota jam bulanan |
| Keep-alive | **cron-job.org** | Ping `/v1/health` tiap 10 mnt supaya backend tak sempat tidur |

> Syarat free tier ketiga layanan ini berubah cukup sering. Angka kuota di
> dokumen ini layak dikonfirmasi sekali di halaman pricing resmi sebelum kamu
> menggantungkan penjurian padanya.

### Kedua URL sudah bisa ditebak sebelum deploy

Ini menyelesaikan masalah ayam-telur yang bikin repot di jalur Render: frontend
butuh URL backend, backend butuh URL frontend untuk CORS. Padahal keduanya
ditentukan oleh nama yang **kamu pilih sendiri**:

| Layanan | Pola URL | Contoh |
|---|---|---|
| Vercel | `https://<nama-project>.vercel.app` | `https://optibayer.vercel.app` |
| HF Spaces | `https://<user>-<nama-space>.hf.space` | `https://wwzfwz-optibayer-api.hf.space` |

Jadi tentukan kedua nama itu **di awal**, lalu isi semua env var sekaligus —
tidak perlu bolak-balik menunggu satu service hidup dulu.

> ⚠️ Untuk HF, pakai domain **`.hf.space`**, bukan `huggingface.co/spaces/...`.
> Yang kedua adalah halaman pembungkus ber-iframe, bukan endpoint API. Salah
> pilih di sini menghasilkan gejala "API terputus" yang membingungkan.

---

## A1. Backend ke Hugging Face Spaces

HF Space adalah **repo git tersendiri** di huggingface.co. Kodenya kamu push ke
sana; HF membangun `Dockerfile` di root repo.

### Konfigurasi Space ada di frontmatter README

HF membaca pengaturan Space dari blok YAML di baris pertama `README.md`. Karena
kita mem-push repo ini apa adanya, `README.md` repo ini yang akan dibaca — dan
tanpa frontmatter, Space tidak akan tahu dirinya Docker Space.

Menempelkan frontmatter itu ke `README.md` di `main` akan membuat GitHub
merender tabel YAML di puncak README — jelek untuk repo yang ikut dinilai.
Karena itu pakai **branch terpisah**:

```bash
git checkout -b hf-space
```

Tambahkan blok ini di **baris paling atas** `README.md` (sebelum judul `#`):

```yaml
---
title: OptiBayer API
emoji: 🏭
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 8000
pinned: false
---
```

`app_port: 8000` penting: default HF adalah 7860, sedangkan `Dockerfile` kita
mendengarkan di 8000. Mendeklarasikannya di sini berarti **Dockerfile tidak
perlu diubah sama sekali** — image yang sama tetap dipakai docker-compose lokal.

```bash
git commit -am "chore(hf): frontmatter Space"
```

### Push dan set secret

1. Buat Space di <https://huggingface.co/new-space> → SDK **Docker** → template
   **Blank** → visibility **Public**.
2. Sambungkan dan push branch tadi sebagai `main`-nya Space:

```bash
git remote add hf https://huggingface.co/spaces/<user>/<nama-space>
git push hf hf-space:main --force
```

3. Di Space → **Settings → Variables and secrets**, tambahkan:

| Nama | Jenis | Isi |
|---|---|---|
| `CORS_ORIGINS` | Variable | `https://<nama-project>.vercel.app` |
| `OPTIBAYER_WRITE_TOKEN` | **Secret** | string acak, mis. `openssl rand -hex 24` |

4. Tunggu build (melatih surrogate saat build, lihat `Dockerfile:30`), lalu uji:

```bash
curl https://<user>-<nama-space>.hf.space/v1/health
# {"ok":true,"service":"optibayer","version":"v1-draft"}
```

### Memperbarui backend nanti

Branch `hf-space` cuma berbeda satu blok frontmatter dari `main`:

```bash
git checkout hf-space && git merge main && git push hf hf-space:main
```

---

## A2. Frontend ke Vercel

Next.js-nya ada di subdirektori, jadi satu pengaturan wajib diubah:

1. <https://vercel.com/new> → import repo `antham-hackathon-nyukses`.
2. **Root Directory → `frontend`.** Kalau dilewat, Vercel tidak menemukan
   `package.json` dan build gagal.
3. Framework preset terdeteksi otomatis sebagai Next.js. Biarkan.
4. **Environment Variables** → tambahkan:

| Nama | Isi |
|---|---|
| `OPTIBAYER_API_URL` | `https://<user>-<nama-space>.hf.space` |

5. Deploy. Nama project menentukan domainnya — pastikan cocok dengan yang sudah
   kamu isikan ke `CORS_ORIGINS` di HF.

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

## A3. Pinger — di mana persisnya

**Pinger bukan bagian dari aplikasimu.** Dia layanan cron eksternal yang
memanggil URL backend dari luar, dengan jadwal tetap, supaya penyedia hosting
tidak pernah menganggap backend menganggur. Tidak ada kode yang perlu ditulis;
yang dipanggil adalah endpoint `/v1/health` yang sudah ada
(`src/integration/api.py:73`) — murah, tanpa efek samping, tanpa auth.

### Pilihan yang disarankan: cron-job.org (gratis)

1. Daftar di <https://cron-job.org> (gratis, tanpa kartu).
2. **Create cronjob**:

| Field | Isi |
|---|---|
| Title | `optibayer keepalive` |
| URL | `https://<user>-<nama-space>.hf.space/v1/health` |
| Schedule | Every **10 minutes** |
| Request method | `GET` |

3. Aktifkan notifikasi kegagalan lewat email. Ini bonus penting: pinger jadi
   merangkap **monitoring**. Kalau backend mati diam-diam tiga minggu setelah
   proposal dikirim, kamu tahu — bukan juri yang menemukannya.

UptimeRobot (interval minimum 5 menit di paket gratis) bekerja sama baiknya
kalau kamu sudah punya akun di sana.

### Alternatif: GitHub Actions (sudah disiapkan di repo)

Berkas `.github/workflows/keepalive.yml` sudah ada, tinggal diaktifkan dengan
mengisi repository variable `KEEPALIVE_URL`. Kelebihannya: ikut terversion di
repo. **Tapi dua jebakannya nyata**, dan keduanya menyerang justru pada skenario
proposal:

- **Scheduled workflow dinonaktifkan otomatis setelah ~60 hari tanpa aktivitas
  repo.** Proposal yang mengendap dua bulan akan kehilangan pinger-nya persis
  saat masih dibutuhkan.
- **Hanya gratis kalau repo publik.** Di repo privat, setiap run dibulatkan ke
  atas ke 1 menit; ping tiap 10 menit ≈ 4.300 run/bulan ≈ 4.300 menit,
  jauh melewati jatah 2.000 menit/bulan.

Karena itu cron-job.org yang direkomendasikan, dan workflow ini disediakan
sebagai cadangan bila kamu memang lebih suka semuanya di dalam repo.

---

## Urutan pengerjaan (± 30 menit)

1. Tentukan dua nama: project Vercel dan Space HF. Tulis kedua URL-nya.
2. A1 — push backend ke HF, isi `CORS_ORIGINS` + `OPTIBAYER_WRITE_TOKEN`.
3. `curl .../v1/health` sampai hijau.
4. A2 — deploy Vercel dengan `OPTIBAYER_API_URL`.
5. Buka URL Vercel, pastikan indikator "API tersambung" hijau.
6. A3 — pasang pinger, jalankan sekali secara manual untuk memastikan 200.
7. Jalankan checklist di bawah.

---

## Variabel lingkungan (berlaku di platform mana pun)

| Variabel | Di service | Isi | Wajib? |
|---|---|---|---|
| `OPTIBAYER_API_URL` | web | URL publik backend | ✅ |
| `CORS_ORIGINS` | api | URL publik frontend (boleh dipisah koma) | ✅ |
| `OPTIBAYER_WRITE_TOKEN` | api | rahasia acak | ✅ kalau publik |
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

**Penyimpanan bersifat sementara.** HF Spaces (dan Render free) tidak memberi
disk persisten. Keputusan Terima/Tolak di Audit Trail dan entri Knowledge Pack
yang ditambahkan lewat UI **hilang setiap kali container di-restart atau
di-rebuild**. Dalam satu sesi penjurian semuanya bekerja normal — refresh tetap
menampilkan keputusan tadi — tetapi jangan menjanjikan persistensi jangka
panjang di proposal. Kalau itu perlu, langkah berikutnya adalah database
eksternal (mis. Postgres gratis di Neon/Supabase), bukan menambah disk.

**Pinger mengurangi cold start, bukan menghapusnya.** Kalau pinger mati atau
platform memaksa rebuild, permintaan pertama tetap lambat. Karena itu:

- Sertakan **GIF demo + screenshot** di proposal, jangan hanya link. Semua
  platform gratis bisa mendadak suspend, dan proposal mungkin dibuka tiga
  minggu lagi. Kalau link bermasalah, juri tetap sudah melihat produknya. Ini
  asuransi paling murah yang ada.
- Pastikan UI menampilkan state "menyiapkan server" — **bukan** "API terputus" —
  selama backend belum menjawab. Aplikasi yang bilang "tunggu sebentar" dibaca
  sebagai sedang bekerja; yang bilang "terputus" dibaca sebagai rusak. Kondisi
  teknisnya identik, kesimpulan jurinya berbeda.

---

## D. Render (cadangan — blueprint ada di repo)

Setup paling singkat, cocok untuk demo yang kamu pandu sendiri. `render.yaml`
mendefinisikan kedua service sekaligus.

1. Push repo ke GitHub.
2. Render Dashboard → **New → Blueprint** → pilih repo ini.
3. Tunggu `optibayer-api` hidup, salin URL-nya.
4. Di `optibayer-web`, set `OPTIBAYER_API_URL` = URL backend → **Restart**
   (tidak perlu build ulang).
5. Di `optibayer-api`, set `CORS_ORIGINS` = URL frontend.

Nama service harus unik se-Render. Kalau `optibayer-web` sudah dipakai orang
lain, Render menambah sufiks acak — dan nilai yang sudah dipatok di
`render.yaml:29` serta `render.yaml:48` jadi salah alamat. Selalu cek URL asli
di dashboard sebelum menganggap selesai.

Dua batasan free tier yang perlu diterima: tidur setelah ~15 menit (buka link
sekali sebelum sesi), dan **RAM 512 MB** untuk backend yang menarik lightgbm +
shap + pymoo dalam satu proses — belum pernah diukur, jadi pantau tab Metrics
setelah deploy pertama. Kalau backend restart sendiri saat optimizer dipakai,
itu OOM, bukan bug kode.

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
curl https://<backend>/v1/health

# 2. CORS mengizinkan domain frontend? Baris access-control-* harus muncul.
curl -H "Origin: https://<frontend>" -D - -o /dev/null \
     https://<backend>/v1/health | grep -i access-control

# 3. Alamat yang benar-benar dipakai halaman (jalankan di console browser):
#    window.__OPTIBAYER_API__
```

- Kosong di langkah 2 → `CORS_ORIGINS` salah/belum ter-restart. Harus **persis**
  sama termasuk `https://` dan tanpa garis miring di akhir.
- `undefined` di langkah 3 → `OPTIBAYER_API_URL` belum ter-set di frontend, atau
  deploy-nya belum dijalankan ulang setelah env diubah.
- Di HF, URL backend memakai `huggingface.co/spaces/...` alih-alih `.hf.space` →
  ganti; yang pertama bukan endpoint API.

---

## Checklist H-1 penjurian

- [ ] Buka link frontend dari **jaringan lain** (mis. data seluler, mode samaran)
      — memastikan tidak ada yang lolos hanya karena cache browsermu
- [ ] Indikator API hijau
- [ ] Ganti skenario ke **"Gangguan: Silika Spike"**, tekan ▶ Play
- [ ] Salin link satu halaman dalam (mis. `?p=redmud&s=1&h=14`), buka di tab
      baru — harus mendarat persis di sana (deep link)
- [ ] Cek satu kartu advisory memuat interval (mis. "±0.22") dan dasar delta
      "neraca massa eksak"
- [ ] Tekan Terima/Tolak sekali, lalu **refresh** — keputusan harus tetap ada
      di halaman Audit Trail (kalau hilang, backend tidak menerima POST-nya:
      cek `CORS_ORIGINS`)
- [ ] `curl <api>/v1/health` mengembalikan `{"ok":true}`
- [ ] Riwayat eksekusi pinger menunjukkan 200 berturut-turut
- [ ] GIF demo + screenshot sudah terlampir di proposal sebagai cadangan
