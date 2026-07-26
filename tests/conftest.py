"""Konfigurasi bersama pytest.

Menaruh akar repo di sys.path supaya `import src...` bekerja apa pun cara
pemanggilannya — `pytest`, `python -m pytest`, atau menjalankan satu berkas
langsung. Sebelum ini hanya `python -m pytest` yang jalan (karena Python
menambahkan cwd), sehingga perintah `python tests/test_data.py` di README
selalu gagal dengan ModuleNotFoundError.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def df():
    """Data bersih (dimuat sekali per sesi uji)."""
    from src.data.adapters import load_clean

    return load_clean()


@pytest.fixture(scope="session")
def seq_spike(df):
    """Deret replay skenario 'Gangguan: Silika Spike'."""
    from src.data import replay

    return replay.build_sequence(df, replay.SCENARIOS[1])


@pytest.fixture(scope="session")
def models_siap():
    """Pastikan registry berisi model; latih sekali kalau kosong."""
    from src.models import predict

    if not predict.available_targets():
        from src.models import train

        train.train_all(verbose=False)
    return predict.available_targets()
