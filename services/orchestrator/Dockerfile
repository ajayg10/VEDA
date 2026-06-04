FROM python:3.11-slim

WORKDIR /app

COPY requirements-base.txt .
RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements-base.txt

COPY shared/ ./shared/
COPY core/__init__.py ./core/__init__.py
COPY services/orchestrator/ ./services/orchestrator/

EXPOSE 8000

RUN useradd -m veda
USER veda

CMD ["uvicorn", "services.orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]