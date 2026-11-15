FROM python:3.12-alpine

# Jalankan sebagai non-root user demi keamanan Home Server
RUN adduser -D -u 10001 ctfuser

WORKDIR /app
COPY server.py answers.json /app/

USER ctfuser

ENV HOST=0.0.0.0
ENV PORT=13370
ENV MAX_ATTEMPTS=8
ENV IDLE_TIMEOUT=900
ENV PYTHONUNBUFFERED=1

EXPOSE 13370

CMD ["python3", "/app/server.py"]
