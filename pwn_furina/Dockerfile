# pwn_furina - Binary Exploitation D (OOB write-what-where -> GOT/dispatch-table hijack)
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1500 furina_pwn

WORKDIR /home/furina_pwn
COPY bin/furina.c .

# Protections: NX on, PIE off, canary on (red herring).
RUN gcc -m64 -fstack-protector-all -no-pie -o furina furina.c && \
    rm furina.c && \
    chown root:furina_pwn furina && \
    chmod 550 furina

USER furina_pwn

# CATATAN: JANGAN pakai opsi "pty" di socat -- lihat NOTES.md.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:40401,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 120 /home/furina_pwn/furina'"]
EXPOSE 40401
