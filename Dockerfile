
# Backend OptiBayer: REST API — satu-satunya jalan masuk ke inti Python.
# Frontend Next.js punya image sendiri (frontend/Dockerfile).

FROM python:3.12-slim

# libgomp1 dibutuhkan LightGBM (OpenMP runtime); tanpa ini import gagal.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ARROW_DEFAULT_MEMORY_POOL=system

WORKDIR /app

# Dependensi lebih dulu supaya layer-nya bisa dipakai ulang saat kode berubah.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY data/ ./data/
COPY knowledge/ ./knowledge/
COPY models/metrics.json ./models/

# Latih surrogate SAAT BUILD, bukan saat container start: kalau dilatih saat
# start, permintaan pertama juri menunggu ~10 detik. Training terukur 27 detik,
# jauh di bawah ambang build timeout.
#
# Artefak surrogate_*.joblib SEBENARNYA ikut di-track git (.gitignore punya
# negasi eksplisit `!models/surrogate_*.joblib`). Jadi kalau build di platform
# free tier kena timeout, ada jalan keluar: ganti baris COPY models/metrics.json
# di atas jadi `COPY models/ ./models/` lalu hapus baris RUN train ini.
RUN python -m src.models.train --quiet

# Dokumentasi saja. Port sebenarnya ditentukan env var PORT saat runtime —
# Render menyuntiknya sendiri (default 10000).
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:${PORT:-8000}/v1/health || exit 1

# Bentuk `sh -c` wajib: exec form tidak melakukan ekspansi variabel, sehingga
# ${PORT} akan diteruskan mentah ke uvicorn dan service dianggap gagal start.
CMD ["sh", "-c", "python -m uvicorn src.integration.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
