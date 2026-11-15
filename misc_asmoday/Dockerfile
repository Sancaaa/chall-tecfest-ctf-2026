FROM python:3.12-slim

RUN useradd --no-create-home --uid 10001 ctf \
    && pip install --no-cache-dir "numpy>=2,<3"

WORKDIR /app
# Hanya server.py yang masuk image (lihat .dockerignore): tanpa solver, sample, atau catatan.
COPY server.py .

USER ctf
EXPOSE 13337
CMD ["python", "-u", "server.py"]
