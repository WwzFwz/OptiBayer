"""Titik masuk untuk platform yang menjalankan `fastapi run` (FastAPI Cloud).

Berkas ini SENGAJA setipis mungkin: tidak ada logika, cuma menyodorkan `app`
di tempat yang dicari CLI `fastapi`. CLI itu memindai `main.py`, `app.py`, atau
`api.py` di root repo; app kita hidup di `src/integration/api.py`, yang tidak
akan pernah ditemukannya.

Jalur Docker (Render/Koyeb/docker-compose) TIDAK melewati berkas ini — lihat
`Dockerfile:37`, yang memanggil `src.integration.api:app` langsung. Jadi kalau
kamu mengubah cara app dibuat, ubah di `src/integration/api.py`; di sini tidak
ada yang perlu disentuh.
"""

from src.integration.api import app

__all__ = ["app"]
