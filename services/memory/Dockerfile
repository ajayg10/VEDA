FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during image build.
# This makes the image larger (~300MB) but means zero delay at
# container startup — no runtime download needed.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY shared/ ./shared/
COPY core/memory.py ./core/memory.py
COPY core/__init__.py ./core/__init__.py
COPY services/memory/ ./services/memory/

# /data is the mount point for the named volume.
# FAISS index and SQLite DB persist here across container restarts.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8002

RUN useradd -m veda
USER veda

ENV DB_PATH=/data/veda.db
ENV FAISS_PATH=/data/veda.faiss
ENV ID_MAP_PATH=/data/veda_id_map.json

CMD ["uvicorn", "services.memory.main:app", "--host", "0.0.0.0", "--port", "8002"]