FROM python:3.11-slim

WORKDIR /app

# Install system tools the executor might shell out to
# (git for git workflows, curl as fallback HTTP tool)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-base.txt .
RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements-base.txt

COPY shared/ ./shared/
COPY core/executor.py ./core/executor.py
COPY core/__init__.py ./core/__init__.py
COPY core/tools/ ./core/tools/
COPY services/executor/ ./services/executor/

EXPOSE 8003

RUN useradd -m veda
USER veda

CMD ["uvicorn", "services.executor.main:app", "--host", "0.0.0.0", "--port", "8003"]