# 02 — Analisis Data Sintesis (`data/raw/data.csv`)

1000 baris × 51 kolom. Format: delimiter `;`, desimal koma (`62,78%`), encoding **cp1252**
(bukan UTF-8 — karakter `–` rusak jadi `�`). Satu baris = satu skenario operasi pabrik
(kemungkinan basis: per 100 ton bauksit kering).

## Struktur logis kolom (ini kunci memahami datanya)

### A. INPUT — komposisi bauksit (10 kolom, TIDAK bisa dikendalikan operator)
| Kolom | Rentang | Catatan |
|---|---|---|
| Kadar Al₂O₃ | 49–63% | sumber aluminium |
| Reactive SiO₂ | 1.5–8% | **musuh utama** — memakan NaOH & Al (bentuk sodalit) |
| Fe₂O₃, TiO₂, CaO, MgO, Na₂O, K₂O, Cr₂O₃ | kecil | inert, lolos ke red mud |
| Others | 2.7–34.5% | sisa penyeimbang ke 100% |

### B. KNOB — parameter proses (5 kolom variabel, BISA dikendalikan → ini yang dioptimasi)
| Kolom | Rentang | Tahap |
|---|---|---|
| Bauxite Particle size | 50–75 µm | penggerusan |
| Suhu Digester | 140–150 °C | digesti |
| Target NaOH Solution Concentration | 140–160 g/L | digesti |
| Precipitation Temperature | 50–70 °C | presipitasi |
| Seed Alumino Hydrate Ratio | 2–3 | presipitasi |

(Rentang ini konsisten dengan literatur: digesti gibbsite 105–150 °C, NaOH 105–250 g/L —
paper Abdul et al. menyebut 140–142 °C untuk pabrik di Indonesia. Bagus, generatornya realistis.)

### C. OUTPUT — hasil neraca massa (target prediksi)
- **`Alumunium Recovery Rate (From Feed)`**: 78–97% ← target utama
- **`TOTAL OPEX`** (= NaOH OPEX + CaO OPEX): 167–4260 per jam ← target kedua
- **`Wet Red Mud Discharge`**: 36–96 ton & **`Alumunium Lost in Red Mud`**: 1.5–7.2 ← target ESG
- Sisanya (konsumsi NaOH/CaO/air, evaporasi, seed, dll) = variabel antara neraca massa

### D. KONSTANTA — 14 kolom bernilai tunggal (buang saat modeling, tidak ada sinyal)
Ca/Si ratio=1.2, pre-desilication eff=0.8, L/S=3, steam=0.05, clarification eff=0.98,
wash water=2.5, wash eff=0.8, causticity=0.85, dst. + 1 kolom kosong (`KONSENTRASI DLL` —
hanya pemisah visual).

## Temuan penting dari profiling

1. **Silika reaktif adalah driver terkuat recovery: korelasi −0.91.** Suhu digester +0.24,
   ukuran partikel −0.28, konsentrasi NaOH +0.13. Ini sesuai kimia proses — cerita yang
   bagus untuk juri (model belajar hal yang benar secara fisika).
2. **Silika juga driver OPEX (+0.60)** — konsisten dengan konsumsi NaOH oleh DSP.

## ⚠ Cacat data yang HARUS dibersihkan

| Masalah | Jumlah | Tindakan |
|---|---|---|
| Digestion Efficiency > 100% (max 101.18%) | 64 baris | fisik mustahil → clip ke 100% atau drop |
| `Net Make-up NaOH` negatif (min −0.23) | beberapa | mustahil → investigasi/drop |
| `Total NaOH OPEX` negatif (min −114.8) | beberapa | ikut baris di atas → drop |
| `CaO Addition` negatif (min −0.105) | beberapa | idem |
| Encoding cp1252 + desimal koma + `%` string | semua | normalisasi saat load |

Cara load yang benar:
```python
df = pd.read_csv('data/raw/data.csv', sep=';', encoding='cp1252')
# lalu strip '%', ganti ',' → '.', to_numeric
```

## Apakah data ini cukup? (jawaban jujur)

**Cukup untuk membangun prototipe hackathon, dengan satu kelemahan yang harus diakui:**
data ini dihasilkan dari rumus neraca massa deterministik + randomisasi, sehingga model ML
pada dasarnya "mempelajari kembali simulator teman kamu". Itu **bukan masalah** untuk
proof-of-concept — justru begitulah industri membangun digital twin (surrogate model dari
simulator, lalu di-retrain dengan data historian pabrik asli). Yang penting:
**katakan ini terang-terangan ke juri** dan tunjukkan arsitektur kalian data-agnostic.

Yang TIDAK ada di data (jangan janjikan fitur yang butuh ini):
- dimensi waktu (bukan time-series → tidak bisa klaim "real-time anomaly detection")
- data energi/steam yang bervariasi (steam konstan 0.05 → tidak bisa optimasi energi)
- harga reagen aktual (OPEX satuannya abstrak)
- karakteristik red mud (pH, mineralogi) → tidak bisa modelkan pengolahan red mud
