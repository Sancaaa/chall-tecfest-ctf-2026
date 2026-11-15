# pwn_mavuika - Binary Exploitation A (Ret2win klasik)
# Base: ubuntu:22.04 (glibc 2.35) - pin via digest sebelum deploy asli (lihat NOTES.md)
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1500 mavuika_pwn

WORKDIR /home/mavuika_pwn
COPY bin/mavuika.c .

# Protections: NX on, canary off, PIE off.
RUN gcc -m64 -fno-stack-protector -no-pie -o mavuika mavuika.c && \
    rm mavuika.c && \
    chown root:mavuika_pwn mavuika && \
    chmod 550 mavuika

USER mavuika_pwn

# flag di-mount read-only lewat docker-compose (:ro), TIDAK di-bake ke image.
# CATATAN: JANGAN pakai opsi "pty" di socat -- pty mem-filter byte lewat line
# discipline terminal dan bikin payload biner (shellcode/alamat raw) nyasar.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:40101,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 120 /home/mavuika_pwn/mavuika'"]
EXPOSE 40101
