FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY core/__init__.py ./core/__init__.py
COPY services/orchestrator/ ./services/orchestrator/

EXPOSE 8000

RUN useradd -m veda
USER veda

CMD ["uvicorn", "services.orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]