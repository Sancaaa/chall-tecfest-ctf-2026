# pwn_ei - Binary Exploitation B (Format string exploitation)
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1500 ei_pwn

WORKDIR /home/ei_pwn
COPY bin/ei.c .

# Protections: NX on, canary on, PIE off ("medium standar", lihat BINEXP_PLANNING.md).
RUN gcc -m64 -fstack-protector-all -no-pie -o ei ei.c && \
    rm ei.c && \
    chown root:ei_pwn ei && \
    chmod 550 ei

USER ei_pwn

# CATATAN: JANGAN pakai opsi "pty" di socat -- lihat NOTES.md.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:40201,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 120 /home/ei_pwn/ei'"]
EXPOSE 40201
