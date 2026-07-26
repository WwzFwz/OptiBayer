# 22 — Deploy (menggantikan doc 16)

> Doc 16 menargetkan Streamlit Community Cloud dan sudah tidak berlaku sejak
> konsol Streamlit dipensiunkan dari `main`. Dokumen ini yang dipakai sekarang.

Tujuan: **juri cukup membuka satu link**, tanpa memasang apa pun.

---

## Ringkasan arsitektur deploy

Dua service, keduanya punya Dockerfile sendiri:

| Service | Berkas | Port | Isi |
|---|---|---|---|
| `optibayer-api` | `Dockerfile` | 8000 | FastAPI + inti Python. Model dilatih **saat build image**, jadi permintaan pertama tidak menunggu ~10 detik. |
| `optibayer-web` | `frontend/Dockerfile` | 3000 | Next.js. Image tunggal, alamat backend ditentukan saat **runtime**. |

### Kenapa alamat API dibaca saat runtime

`NEXT_PUBLIC_*` ditanam ke bundle JavaScript **saat build**. Artinya kalau
alamat backend dipakai lewat variabel itu, image frontend terkunci ke satu URL
dan harus dibuild ulang setiap kali backend pindah — padahal saat deploy, URL
backend baru diketahui SETELAH backend hidup. Itu urutan yang menyebalkan.

Karena itu `app/layout.tsx` membaca `OPTIBAYER_API_URL` dari environment server
lalu menyuntikkannya ke halaman (`window.__OPTIBAYER_API__`), dan `lib/api.ts`
memakainya lebih dulu sebelum jatuh ke `NEXT_PUBLIC_API_URL`. Terbukti: build
yang sama dijalankan dua kali dengan env berbeda menghasilkan alamat berbeda —
**cukup restart, tidak perlu build ulang**.

Konsekuensi teknis yang perlu diketahui: `await connection()` membuat rute
dirender per permintaan (`ƒ Dynamic`), bukan shell statis. Tanpa itu
`process.env` terbaca saat build dan suntikannya hilang sama sekali.

---

## A. Render (rekomendasi — ada blueprint di repo)

1. Push repo ke GitHub.
2. Render Dashboard → **New → Blueprint** → pilih repo ini. Render membaca
   `render.yaml` dan membuat kedua service.
3. Tunggu `optibayer-api` hidup, salin URL-nya.
4. Di service `optibayer-web`, set env **`OPTIBAYER_API_URL`** = URL backend
   tadi → **Restart** (tidak perlu build ulang).
5. Di service `optibayer-api`, set env **`CORS_ORIGINS`** = URL frontend.
   Tanpa ini browser akan memblokir panggilan lintas domain.
6. Buka URL frontend. Indikator "API tersambung" di kanan atas harus hijau.

**Keamanan saat publik.** `render.yaml` menyalakan `OPTIBAYER_WRITE_TOKEN`
(nilainya dibangkitkan Render). Selama terisi, **`/v1/knowledge/add`** menuntut
header `X-Write-Token` yang sama — endpoint itu menulis BERKAS berisi teks
bebas ke disk server. CORS saja tidak cukup menjaganya: ia hanya mengikat
browser, bukan `curl`.

**`/v1/audit/decision` sengaja TIDAK dijaga token.** Aplikasi ini belum punya
login, jadi token apa pun yang dikirim ke browser ikut terbaca siapa saja yang
membuka halaman — memasangnya di situ hanya keamanan pura-pura, sambil
memastikan tombol Terima/Tolak selalu 401 di konfigurasi ini. Risikonya juga
berbeda kelas: endpoint itu hanya menambah baris berbentuk tetap dengan panjang
dibatasi. Saat autentikasi nyata dipasang (AD/API-key per operator, doc 07),
identitas penekan tombol seharusnya ikut tercatat di kolom `sumber`.

> Catatan free tier: instance tidur setelah ~15 menit menganggur dan butuh
> ~30–60 detik untuk bangun. **Buka link sekali sebelum sesi penjurian** supaya
> sudah panas.

---

## B. Lokal / LAN (paling cepat, tanpa akun)

```bash
docker compose up --build
```

API di `:8000`, UI di `:3000`. Untuk dipakai perangkat lain di jaringan yang
sama, jalankan dengan alamat host:

```bash
OPTIBAYER_API_URL="http://<IP-laptop>:8000" \
CORS_ORIGINS="http://<IP-laptop>:3000" docker compose up --build
```

---

## C. Platform lain

Polanya sama di mana pun (Fly.io, Railway, VPS): dua image, dan tiga variabel.

| Variabel | Di service | Isi |
|---|---|---|
| `OPTIBAYER_API_URL` | web | URL publik backend |
| `CORS_ORIGINS` | api | URL publik frontend (boleh dipisah koma) |
| `OPTIBAYER_WRITE_TOKEN` | api | rahasia acak; wajib kalau instance publik |

Opsional pada api: `LLM_PROVIDER` + kunci API-nya (lihat `.env.example`), dan
`MQTT_HOST` kalau event OT mau diterbitkan ke broker sungguhan.

---

## Checklist H-1 penjurian

- [ ] Buka link frontend, pastikan indikator API hijau
- [ ] Ganti skenario ke **"Gangguan: Silika Spike"**, tekan ▶ Play
- [ ] Salin link satu halaman dalam (mis. `?p=redmud&s=1&h=14`), buka di tab
      baru — harus mendarat persis di sana (deep link)
- [ ] Cek satu kartu advisory memuat interval (mis. "±0.22") dan dasar delta
      "neraca massa eksak"
- [ ] Tekan Terima/Tolak sekali, lalu **refresh** — keputusan harus tetap ada
      di halaman Audit Trail (kalau hilang, backend tidak menerima POST-nya:
      cek `CORS_ORIGINS`)
- [ ] `curl <api>/v1/health` mengembalikan `{"ok":true}`
