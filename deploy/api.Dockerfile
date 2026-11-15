FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 RUNTIME_DIR=/data
WORKDIR /app
COPY apps/api/requirements.txt .
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/* \
    && pip install -r requirements.txt && useradd --create-home --uid 10001 haiti && mkdir -p /data/evidence && chown -R haiti:haiti /data
COPY --chown=haiti:haiti apps/api/ .
USER haiti
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
