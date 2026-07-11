"""Uji dashboard end-to-end via streamlit AppTest: skrip harus jalan tanpa exception."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest


def main():
    at = AppTest.from_file(str(ROOT / "app" / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception, at.exception
    # KPI + advisory + sidebar hadir
    assert len(at.metric) >= 6, f"metric={len(at.metric)}"
    assert at.sidebar.selectbox[0].value in ("Operasi Normal", "Gangguan: Silika Spike")
    print(f"run-1 OK: {len(at.metric)} metric, exception=None")

    # skenario silika spike + maju ke jam 30 -> harus tetap tanpa exception
    at.sidebar.selectbox[0].set_value("Gangguan: Silika Spike").run()
    assert not at.exception, at.exception
    # slider 'Jam simulasi' = slider ke-2 di sidebar (setelah 'Detik per jam')
    at.sidebar.slider[1].set_value(30).run()
    assert not at.exception, at.exception
    print("run-2 OK: skenario spike jam-30 tanpa exception")
    print("APP OK")


if __name__ == "__main__":
    main()
