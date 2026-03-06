# ── Analytic AI Backend — Docker Image ───────────────────────
# Python 3.11 slim (stable, not bleeding-edge 3.14)
FROM python:3.11-slim

# System deps for Pillow / Matplotlib / ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer cache optimisation)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend source
COPY . .

# Create runtime directories (ephemeral on Render free tier)
RUN mkdir -p uploads outputs

# Expose the default uvicorn port
EXPOSE 8000

# Health check so Render knows when the container is ready
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start server — $PORT is injected by Render at runtime
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
