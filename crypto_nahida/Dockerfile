# Pin base image lewat digest saat deploy (lihat CHALLENGE_DAN_HOSTING.md 2.4).
FROM python:3.12-slim

RUN useradd --no-create-home --uid 10001 ctf \
    && pip install --no-cache-dir "pycryptodome>=3.20,<4"

WORKDIR /app
# Hanya server.py yang masuk image (lihat .dockerignore): tanpa solver,
# secrets, capture, atau catatan author. Secrets di-mount read-only saat run.
COPY server.py .

USER ctf
EXPOSE 10501
CMD ["python", "-u", "server.py"]
