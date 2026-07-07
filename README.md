# ANTAM Hackathon — 


## Struktur Folder

```
antam-hackathon/
├── README.md                 
├── docs/                      ← semua dokumen analisis & perencanaan
│   ├── 01-analisis-masalah.md      (first-principles: masalah apa yang bernilai)
│   ├── 02-analisis-data.md         (isi data sintesis, kualitas, yang perlu dibersihkan)
│   ├── 03-solusi-dan-arsitektur.md (solusi yang diusulkan + arsitektur teknis)
│   ├── 04-sumber-data-referensi.md (perlu data asli? cari di mana?)
│   └── 05-rencana-kerja.md         (roadmap sampai hari-H hackathon)
├── data/
│   ├── raw/data.csv           ← data sintesis asli (JANGAN diedit)
│   └── processed/             ← hasil cleaning (dibuat oleh src/preprocess)
├── notebooks/                 ← EDA & eksperimen model (Jupyter)
├── src/                       ← kode final (preprocess, training, optimizer)
├── models/                    ← model terlatih (.pkl / .json)
└── app/                       ← dashboard demo (Streamlit)
```

## Mulai dari mana?

1. Baca `docs/01-analisis-masalah.md` → paham konteks bisnisnya.
2. Baca `docs/02-analisis-data.md` → paham data teman kamu.
3. Baca `docs/03-solusi-dan-arsitektur.md` → apa yang mau dibangun.
4. Ikuti `docs/05-rencana-kerja.md`.
