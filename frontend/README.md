# OptiBayer Frontend (Next.js) — antarmuka alternatif

Frontend React/Next.js di atas **REST API OptiBayer** (`src/integration/api.py`).
Klien kedua di samping Streamlit — inti Python sama, hanya wajahnya beda.
UI/UX lebih leluasa: rail ikon kiri, Panel Kendali overlay, panel Advisory
yang bisa **di-drag** ke atas / panel kanan.

> Streamlit TIDAK diganti. Ini opsi UI; keduanya memanggil API yang sama.

## Menjalankan (butuh 2 proses)

```bash
# 1) backend (dari ROOT repo, bukan folder ini)
python -m uvicorn src.integration.api:app --port 8000

# 2) frontend (dari folder frontend/)
npm install          # sekali
npm run dev          # http://localhost:3000
```

Default API di http://localhost:8000. Ubah via `.env.local`
(`NEXT_PUBLIC_API_URL=...`, contoh di `.env.local.example`).

## Status port

- Overview: KPI live, 4 tren + pita alarm (recharts), advisory drag-dock
  (atas/kanan) + Terima/Tolak, jam-aktif, indikator API.
- Halaman lain (Diagram HMI, Digesti, dst.): placeholder — versi lengkap ada
  di Streamlit (http://localhost:8501); porting bertahap.

## Offline-ready

Font sistem (bukan next/font/google), tanpa CDN — build & runtime tidak butuh
internet (jaringan pabrik tertutup).
