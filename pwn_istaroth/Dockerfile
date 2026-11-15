# pwn_istaroth - Binary Exploitation F (Multi-stage ROP & shell)
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev socat && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -M -u 1500 istaroth_pwn

WORKDIR /home/istaroth_pwn
COPY bin/istaroth.c bin/catflag.c .

# Protections: NX on, canary OFF (lihat NOTES.md - disengaja, canary+ret2libc
# butuh leak canary juga lewat side-channel yang bikin desain menumpuk skill;
# fokus Hard di soal ini adalah PIE-defeat dua-leak (libc + string PIE) +
# bangun ROP chain ret2libc beneran), PIE on. TIDAK ADA win() siap pakai --
# target akhirnya system() dari libc yang dibagikan di attachment (lihat
# NOTES.md v2 dan deploy_pwn.sh: NEEDS_LIBC sekarang 1 untuk soal ini).
RUN gcc -O0 -m64 -fno-stack-protector -pie -fPIE -o istaroth istaroth.c && \
    gcc -O0 -m64 -fno-stack-protector -no-pie -o catflag catflag.c && \
    rm istaroth.c catflag.c && \
    chown root:istaroth_pwn istaroth catflag && \
    chmod 550 istaroth && \
    chmod 550 catflag

USER istaroth_pwn

# CATATAN: JANGAN pakai opsi "pty" di socat -- lihat NOTES.md.
CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:40601,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 180 /home/istaroth_pwn/istaroth'"]
EXPOSE 40601
