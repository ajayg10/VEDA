FROM python:3.11-slim

WORKDIR /app

# Install system tools + Docker CLI for sandboxed execution
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-base.txt .
RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements-base.txt

COPY shared/ ./shared/
COPY core/ ./core/
COPY services/executor/ ./services/executor/

EXPOSE 8003

CMD ["uvicorn", "services.executor.main:app", "--host", "0.0.0.0", "--port", "8003"]