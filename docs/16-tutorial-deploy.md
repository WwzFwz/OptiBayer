# 16 — Tutorial Deploy (Streamlit Community Cloud + opsi lain)

> Target: juri bisa membuka dashboard lewat LINK, tanpa install apa pun.
> Waktu setup ±15 menit, gratis. Repo sudah siap deploy (requirements.txt ✔,
> auto-train saat boot ✔, data ikut repo ✔, .env di-gitignore ✔).

## A. Deploy ke Streamlit Community Cloud (rekomendasi utama)

1. **Pastikan `main` terbaru sudah di-push** — cloud membaca langsung dari GitHub.
2. Buka **https://share.streamlit.io** → *Sign in with GitHub* (akun pemilik repo
   `WwzFwz/antham-hackathon-nyukses`). Kalau repo private, izinkan akses
   private repo saat OAuth (atau jadikan public sementara).
3. Klik **New app** → isi:
   - Repository: `WwzFwz/antham-hackathon-nyukses`
   - Branch: `main`
   - Main file path: **`app/main.py`**
   - (Advanced settings) Python version: **3.12**
4. **Secrets** (pengganti `.env` di cloud — JANGAN commit `.env`):
   klik *Advanced settings → Secrets*, isi format TOML:
   ```toml
   LLM_PROVIDER = "groq"
   GROQ_API_KEY = "gsk_xxxxxxxx"
   ```
   Secrets otomatis tersedia sebagai environment variable, jadi `providers.py`
   langsung membacanya tanpa ubah kode. Kosongkan bila mau backend `template`.
5. Klik **Deploy**. Boot pertama ±2–4 menit (install requirements + auto-train
   4 model LightGBM dari data — muncul spinner "Model belum ada — melatih...").
6. Dapat URL `https://<nama-app>.streamlit.app` → tempel di slide/QR code.

### Update setelah deploy
`git push origin main` → cloud otomatis rebuild dalam ±1 menit. Tidak ada
langkah lain.

### Gotcha Community Cloud (baca sebelum hari-H!)
| Gotcha | Dampak | Mitigasi |
|---|---|---|
| **App tidur** setelah ±12 jam tanpa pengunjung | Juri klik link → menunggu cold-boot ±2 menit | Buka URL-nya 15 menit SEBELUM presentasi |
| RAM 1 GB | Cukup utk app kita (train 1000 baris ±30 dtk) — jangan tambah dependensi berat | Uji setelah tiap deploy |
| Ollama TIDAK jalan di cloud | Backend lokal hanya utk laptop | Di cloud pakai `groq`/`gemini`/`template` |
| Repo private butuh otorisasi | Deploy gagal diam-diam | Cek permission GitHub saat setup |
| File besar memperlambat boot | zip/xlsm root sudah di-.gitignore ✔ | Jangan commit dataset raksasa ke main |

## B. Opsi cadangan 1 — LAN venue (tanpa internet publik)

Kalau internet venue jelek tapi ada Wi-Fi lokal, jalankan di laptopmu dan
biarkan juri membuka lewat jaringan yang sama:

```bash
python -m streamlit run app/main.py --server.address 0.0.0.0 --server.port 8501
```

Streamlit mencetak **Network URL** (mis. `http://192.168.x.x:8501`) — bagikan
itu. Firewall Windows akan bertanya sekali: pilih *Allow access*.

## C. Opsi cadangan 2 — full lokal (jaring pengaman terakhir)

```bash
python -m streamlit run app/main.py
```
Presentasi lewat layar sendiri/HDMI. Selalu siapkan ini walau cloud jalan —
tak ada demo yang boleh bergantung pada Wi-Fi venue.

## Checklist H-1 demo

- [ ] Buka URL cloud → app bangun & render normal (dark + light mode)
- [ ] Uji alur inti di CLOUD: skenario Silika Spike → Play → advisory muncul →
      Terima → audit trail terisi
- [ ] Tombol "Analisis AI" menjawab (backend groq) — kalau kuota habis,
      fallback template tetap tampil (bukan error)
- [ ] Laptop lokal: server jalan + model terlatih (cadangan C siap)
- [ ] QR code URL cloud di slide penutup
