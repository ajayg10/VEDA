FROM python:3.11-slim

# Set working directory inside container.
# All subsequent COPY and RUN commands are relative to this.
WORKDIR /app

# Install deps first — Docker caches this layer separately.
# If only source code changes, this layer is reused → faster rebuilds.
COPY requirements-base.txt .
RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements-base.txt

# Copy only what this service needs.
# Build context is the project root (set in docker-compose.yml).
COPY shared/ ./shared/
COPY core/planner.py ./core/planner.py
COPY core/__init__.py ./core/__init__.py
COPY services/planner/ ./services/planner/

EXPOSE 8001

# Run as non-root user — security best practice.
# Never run production containers as root.
RUN useradd -m veda
USER veda

CMD ["uvicorn", "services.planner.main:app", "--host", "0.0.0.0", "--port", "8001"]