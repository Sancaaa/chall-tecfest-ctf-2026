# warmup_pwn_mona - Binary Exploitation Warm-up (buffer overflow -> SIGSEGV -> flag)
# Base: ubuntu:22.04 (glibc 2.35), pin via digest sama seperti pwn_mavuika (konsistensi infra)
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1510 mona_pwn

WORKDIR /home/mona_pwn
COPY bin/mona.c .

# Protections: canary OFF (sengaja, lihat mona.c) -- NX/PIE tidak relevan,
# challenge ini tidak perlu redirect eksekusi, cukup crash lewat return
# address yang rusak.
RUN gcc -m64 -fno-stack-protector -o mona mona.c && \
    rm mona.c && \
    chown root:mona_pwn mona && \
    chmod 550 mona

USER mona_pwn

# flag di-mount read-only lewat docker-compose (:ro), TIDAK di-bake ke image.
# JANGAN pakai opsi "pty" di socat -- payload overflow ini raw bytes ('A' * N),
# pty bisa memfilter/mengubah byte lewat line discipline terminal.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:10110,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 60 /home/mona_pwn/mona'"]
EXPOSE 10110
