"""Uji toggle tema: app harus render tanpa exception di dark DAN light."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest


def main():
    at = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=180)
    at.run()
    assert not at.exception, at.exception
    # toggle "Mode terang" = toggle pertama di sidebar
    at.sidebar.toggle[0].set_value(True).run()
    assert not at.exception, at.exception

    from app import ui
    assert ui.MODE == "light" and ui.SURFACE == "#fcfcfb", (ui.MODE, ui.SURFACE)
    print("light mode OK (palet chart ikut)")

    at.sidebar.toggle[0].set_value(False).run()
    assert not at.exception, at.exception
    assert ui.MODE == "dark" and ui.SURFACE == "#1a1a19"
    print("dark mode OK — THEME OK")


if __name__ == "__main__":
    main()
