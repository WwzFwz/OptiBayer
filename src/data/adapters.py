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

    Keanehan yang ditangani di sini (doc 02):
    - encoding cp1252, delimiter ';', desimal koma, nilai persen ber-suffix '%'
    - Digestion Efficiency > 100% (mustahil fisik) -> clip ke 100
    - Make-up NaOH / OPEX / dosis CaO negatif -> drop baris
    - kolom pemisah kosong 'KONSENTRASI DLL' -> buang
    """

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
            "rows_clean": len(df),
            "columns_mapped": len(rename),
            "columns_unmapped": unmapped,
        }
        return df


def load_clean(path: str | Path = "data/raw/data.csv") -> pd.DataFrame:
    """Jalan pintas standar: sumber default proyek -> DataFrame kanonik."""
    return SyntheticCSVAdapter(path).load()
