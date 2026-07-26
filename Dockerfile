# Backend OptiBayer: REST API (default) atau dashboard Streamlit.
# Satu image, dua peran — dipilih lewat `command` di docker-compose.yml.

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
COPY app/ ./app/
COPY data/ ./data/
COPY knowledge/ ./knowledge/
COPY models/metrics.json ./models/
COPY .streamlit/ ./.streamlit/

# Latih surrogate SAAT BUILD, bukan saat container start: artefak .joblib tidak
# ikut di git (lihat .gitignore), dan kalau dilatih saat start, permintaan
# pertama juri akan menunggu ~10 detik.
RUN python -m src.models.train --quiet

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "src.integration.api:app", \
     "--host", "0.0.0.0", "--port", "8000"]
