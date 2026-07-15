"""Adapter sumber data (P2, doc 09).

Kontrak: setiap adapter mengembalikan DataFrame KANONIK — kolom bernama sesuai
schema.py, semua numerik, sudah bersih. Semua keanehan spesifik sumber
(encoding, delimiter, cacat generator) terkurung DI SINI.

Tahap 2 (data asli): tambah kelas baru dengan kontrak sama, jangan ubah modul lain.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import schema


class SyntheticCSVAdapter:
    """data/raw/data.csv — generator neraca massa Ainin.

    Keanehan yang ditangani di sini (doc 02 + data v2 dari xlsm UPDATED):
    - encoding cp1252, delimiter ';', desimal koma ATAU titik, persen ber-'%'
    - Digestion Efficiency > 100% dan Recovery > 100% (mustahil fisik) -> clip
    - Make-up NaOH / OPEX / dosis CaO negatif -> drop baris
    - kolom pemisah kosong ('KONSENTRASI DLL' / '-----') -> buang
    - v2: kolom rasio 0-1 yang terekspor sebagai persen (NumberFormat 0.00%
      di macro VBA: predesil/wash eff dll) -> dinormalkan kembali ke fraksi;
      kolom persen yang terekspor sebagai fraksi mentah (Precipitation Yield)
      -> dinormalkan ke skala persen. Deteksi otomatis dari rentang nilai,
      jadi data v1 (basis 100 t) dan v2 (skala pabrik 800 t/jam) dua-duanya jalan.
    """

    # kolom bermakna fraksi 0-1; kalau termuat sebagai puluhan berarti persen
    RATIO_COLS = (
        "predesil_eff", "wash_eff", "clarif_eff", "na2co3_conv_eff",
        "causticity", "naoh_carbonation_frac", "free_moisture",
        "feed_moisture_frac", "steam_evap_loss", "steam_flash",
    )

    def __init__(self, path: str | Path = "data/raw/data.csv"):
        self.path = Path(path)

    def load(self) -> pd.DataFrame:
        raw = pd.read_csv(self.path, sep=";", encoding="cp1252", dtype=str)

        rename, unmapped = {}, []
        for col in raw.columns:
            canonical = schema.match_canonical(col)
            if canonical:
                rename[col] = canonical
            else:
                unmapped.append(col)
        df = raw[list(rename)].rename(columns=rename)

        for col in df.columns:
            s = df[col].str.strip().str.rstrip("%").str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(s, errors="coerce")

        # --- normalisasi format v1/v2 (deteksi dari rentang nilai) ---
        for col in self.RATIO_COLS:
            if col in df.columns and df[col].median() > 1.5:
                df[col] = df[col] / 100.0          # 80.0 (%) -> 0.8 (fraksi)
        # HANYA target persen (bukan oksida input — Cr2O3 dkk memang < 1%)
        for col in ("recovery_pct", "precip_yield_pct", "digestion_eff_pct"):
            if col in df.columns and df[col].max() <= 1.5:
                df[col] = df[col] * 100.0          # 0.73 (fraksi) -> 73.0 (%)

        n_clipped_recovery = int((df["recovery_pct"] > 100.0).sum())
        df["recovery_pct"] = df["recovery_pct"].clip(upper=100.0)
        df["digestion_eff_pct"] = df["digestion_eff_pct"].clip(upper=100.0)
        n_before = len(df)
        bad = (
            (df["naoh_makeup_t"] < 0)
            | (df["total_opex"] < 0)
            | (df["cao_addition_t"] < 0)
        )
        df = df[~bad].reset_index(drop=True)

        self.report = {
            "source": str(self.path),
            "rows_raw": n_before,
            "rows_dropped_negative": int(bad.sum()),
            "rows_clipped_recovery": n_clipped_recovery,
            "rows_clean": len(df),
            "columns_mapped": len(rename),
            "columns_unmapped": unmapped,
        }
        return df


def load_clean(path: str | Path = "data/raw/data.csv") -> pd.DataFrame:
    """Jalan pintas standar: sumber default proyek -> DataFrame kanonik."""
    return SyntheticCSVAdapter(path).load()
