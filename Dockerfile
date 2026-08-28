FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    WEB_CONCURRENCY=4 \
    UVICORN_LIMIT_CONCURRENCY=1000 \
    UVICORN_BACKLOG=2048

WORKDIR /app

RUN groupadd --system --gid 10001 stavarai \
    && useradd --system --uid 10001 --gid stavarai --create-home stavarai

COPY api/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt

COPY --chown=stavarai:stavarai . /app

USER stavarai

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).read()" || exit 1

CMD ["sh", "-c", "exec python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-4} --proxy-headers --forwarded-allow-ips='*' --limit-concurrency ${UVICORN_LIMIT_CONCURRENCY:-1000} --backlog ${UVICORN_BACKLOG:-2048} --timeout-keep-alive 5"]
