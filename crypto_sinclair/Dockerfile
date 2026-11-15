FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --no-create-home --uid 10001 ctf

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY ["chall(sinclair).py", "flag.py", "keygen.py", "./"]

USER ctf
EXPOSE 10401
CMD ["sh", "-c", "ulimit -c 0; exec socat -T 200 TCP-LISTEN:10401,reuseaddr,fork,max-children=30 'EXEC:/usr/bin/timeout -k 5 185 python3 -u \"/app/chall(sinclair).py\",stderr'"]
