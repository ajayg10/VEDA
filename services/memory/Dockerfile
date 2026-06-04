FROM python:3.11-slim

WORKDIR /app

# Layer 1: Base packages (fast — no large deps)
COPY requirements-base.txt .
RUN pip install --no-cache-dir --timeout 300 -r requirements-base.txt

# Layer 2: Memory-specific heavy packages (cached separately)
# Only re-downloads if requirements-memory.txt changes — not when base changes
COPY requirements-memory.txt .
RUN pip install --no-cache-dir --timeout 300 -r requirements-memory.txt

# Layer 3: Pre-bake the ONNX model into the image
RUN python -c "from fastembed import TextEmbedding; list(TextEmbedding('BAAI/bge-small-en-v1.5').embed(['test']))"

COPY shared/ ./shared/
COPY core/memory.py ./core/memory.py
COPY core/__init__.py ./core/__init__.py
COPY services/memory/ ./services/memory/

RUN useradd -m veda && mkdir -p /data && chown veda:veda /data
VOLUME ["/data"]

EXPOSE 8002

USER veda

ENV DB_PATH=/data/veda.db
ENV FAISS_PATH=/data/veda.faiss
ENV ID_MAP_PATH=/data/veda_id_map.json

CMD ["uvicorn", "services.memory.main:app", "--host", "0.0.0.0", "--port", "8002"]