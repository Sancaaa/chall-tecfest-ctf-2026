# Build attachment Rhinedottir enigma maCChine. Jalankan dari folder ini:
#   docker build --target out    --output type=local,dest=dist  .   # binary peserta
#   docker build --target author --output type=local,dest=build .   # author.json + binary tak ter-strip
# Hasil: dist/rhinedottir (ELF x86-64, static, stripped).
#
# Dua pass: pass 1 menghasilkan alamat call site, pass 2 mengisi tabel harapan
# (EXP) dan memverifikasi tata letak kode tidak bergeser. JANGAN compile manual
# di host: alamat call site ikut menentukan hasil enkripsi.
#
# Base image sama dengan pwn_* (Ubuntu 22.04, dipin via digest).
FROM ubuntu@sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11 AS build

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev binutils python3 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY machine.py gen.py flag.txt ./
COPY src/rhinedottir.c src/

ENV CFLAGS="-O2 -static -no-pie -fcf-protection=none -fno-ipa-icf -fno-asynchronous-unwind-tables -fno-ident -Wl,--build-id=none"

RUN python3 gen.py --tables src/tables.h --author author.json --flag flag.txt && \
    gcc $CFLAGS -o rd1 src/rhinedottir.c && \
    nm rd1 | grep -E ' k_[abc]_ret$' | sort > sites.txt && \
    python3 gen.py --tables src/tables.h --author author.json --flag flag.txt --sites sites.txt && \
    gcc $CFLAGS -o rd2 src/rhinedottir.c && \
    nm rd2 | grep -E ' k_[abc]_ret$' | sort | cmp - sites.txt && \
    objcopy -O binary -j .text rd1 t1.bin && objcopy -O binary -j .text rd2 t2.bin && cmp t1.bin t2.bin && \
    mkdir -p /out && cp rd2 /out/rhinedottir.unstripped && \
    strip --strip-all -o /out/rhinedottir rd2 && \
    cp author.json sites.txt /out/

FROM scratch AS out
COPY --from=build /out/rhinedottir /rhinedottir

FROM scratch AS author
COPY --from=build /out/author.json /out/sites.txt /out/rhinedottir.unstripped /
