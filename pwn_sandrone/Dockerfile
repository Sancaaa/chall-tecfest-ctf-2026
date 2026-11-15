# pwn_sandrone - Binary Exploitation C (Shellcode injection, NX off)
# Base: ubuntu:22.04 (glibc 2.35) - pin via digest sebelum deploy asli (lihat NOTES.md)
# Multi-stage: kompilasi pakai gcc di stage builder lalu buang compiler dari runtime.
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11 AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY bin/sandrone.c .

# Compile DI DALAM image supaya binary selalu match glibc base image ini,
# bukan glibc di mesin dev. Protections: NX off, canary off, PIE off.
RUN gcc -m64 -fno-stack-protector -no-pie -z execstack -o /build/sandrone sandrone.c && \
    rm sandrone.c

FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1500 sandrone_pwn

WORKDIR /home/sandrone_pwn
COPY --from=builder /build/sandrone /home/sandrone_pwn/sandrone

RUN chown root:sandrone_pwn /home/sandrone_pwn/sandrone && \
    chmod 550 /home/sandrone_pwn/sandrone

USER sandrone_pwn

# flag di-mount read-only lewat docker-compose/run.sh (:ro), TIDAK di-bake ke image.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:40301,reuseaddr,fork,max-children=30 'EXEC:/usr/bin/timeout -k 5 60 /home/sandrone_pwn/sandrone'"]
EXPOSE 40301
