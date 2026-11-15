FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "pycryptodome>=3.20,<4" \
    && useradd --no-create-home --uid 10001 ctf

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY chall.py flag.py modulus.py ./

USER ctf
EXPOSE 10201
CMD ["sh", "-c", "ulimit -c 0; exec socat -T 120 TCP-LISTEN:10201,reuseaddr,fork,max-children=30 'EXEC:/usr/bin/timeout -k 5 180 python3 -u /app/chall.py,stderr'"]
