# pwn_columbina - Binary Exploitation E (Heap: UAF-write -> tcache poisoning
# -> function pointer hijack. v2 -- lihat NOTES.md, bukan lagi sekadar
# "UAF + reuse-by-size")
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1500 columbina_pwn

WORKDIR /home/columbina_pwn
COPY bin/columbina.c .

# Protections: NX on, canary on, PIE off (disengaja, lihat NOTES.md -- fokus Hard
# soal ini murni mekanisme UAF, bukan ditumpuk lagi sama defeat-PIE).
RUN gcc -O0 -m64 -fstack-protector-all -no-pie -o columbina columbina.c && \
    rm columbina.c && \
    chown root:columbina_pwn columbina && \
    chmod 550 columbina

USER columbina_pwn

# CATATAN: JANGAN pakai opsi "pty" di socat -- lihat NOTES.md.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:40501,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 120 /home/columbina_pwn/columbina'"]
EXPOSE 40501
