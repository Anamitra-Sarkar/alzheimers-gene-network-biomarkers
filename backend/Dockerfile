# syntax=docker/dockerfile:1
# Backend container for AD Gene-Network Biomarker API
# Fail-closed release gate is preserved: model only loads when
# MODEL_RELEASE_APPROVED=true and APPROVED_ARTIFACT_REVISION is set.
# No secrets are baked into this image.

# ---- builder stage: install deps ----
FROM python:3.11-slim AS builder
WORKDIR /app

# System deps for scipy/numpy wheels if needed + security updates
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt ./requirements.txt
# requirements.txt is at repo root; for Docker build context at repo root use backend/ fails.
# So we support both: if building with context=backend, this will be empty and we fall back.
# Preferred build: docker build -f backend/Dockerfile .   (context = repo root)
# Alternative: docker build backend/

# Install Python deps to a venv-like location
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---- runtime stage ----
FROM python:3.11-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 10001 appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
# When build context is repo root, these paths are correct
COPY backend/ ./backend/
COPY data_pipeline/ ./data_pipeline/
# Also copy top-level requirements for reference (not needed at runtime)
COPY requirements.txt ./requirements.txt
COPY pyproject.toml ./pyproject.toml

# Create artifacts dir (mounted or empty by default; app fail-closes if missing)
RUN mkdir -p artifacts && chown appuser:appuser artifacts

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Fail-closed defaults: release gate OFF unless caller explicitly sets these.
# Do NOT set MODEL_RELEASE_APPROVED=true here; leave unset so container starts in abstention mode.
ENV MODEL_RELEASE_APPROVED="" \
    APPROVED_ARTIFACT_REVISION="" \
    MODEL_ARTIFACT_PATH="artifacts/model.joblib" \
    DEMO_MODE=""

EXPOSE 8000

# Healthcheck uses the honest /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).read() or sys.exit(1)" || exit 1

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
