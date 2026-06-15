FROM python:3-alpine
RUN apk add --no-cache docker-cli && pip install --no-cache-dir watchdog
COPY scripts/caddy_sites_watcher.py /app/caddy_sites_watcher.py
CMD ["python", "/app/caddy_sites_watcher.py"]
