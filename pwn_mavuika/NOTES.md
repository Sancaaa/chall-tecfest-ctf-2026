# Notes — pwn_mavuika (Binary Exploitation B)

Status: **fungsional, teruji** (local process + Docker container via network, berkali-kali, reliable).

## Environment build

- Base image: `ubuntu:22.04`, dipin via digest `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11`
- gcc: `11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)`, glibc: `2.35`
- Binary dikompilasi di dalam Dockerfile.

## Struktur folder

Mengikuti pola [`ctf_xinetd`](https://github.com/152334H/ctf_xinetd) (tanpa `ctf.xinetd`-nya sendiri — kita pakai `docker-compose.yml` + `socat`, bukan xinetd, karena ini dihost sendiri bukan di shared box):

- `bin/` — source (`mavuika.c`) yang di-`COPY` & dikompilasi di dalam `Dockerfile`, plus binary test lokal (**wajib** di-extract dari container, lihat bug di bawah — JANGAN compile manual).
- `flag`, `Dockerfile`, `docker-compose.yml`, `NOTES.md`, `readme`, `solve.py` — tetap di dir utama. `flag` **sengaja tidak** ikut masuk `bin/`.
- `dist/` — yang dibagikan ke peserta (`mavuika_attachment.zip`).

## Compile command

```
gcc -m64 -fno-stack-protector -no-pie -o bin/mavuika bin/mavuika.c
```

`checksec`: Partial RELRO, No canary, **NX enabled**, No PIE.

## Teknik

Ret2win klasik. `win()` **statis** karena no-PIE — alamatnya dibaca dari attachment binary (`exe.symbols["win"]` di pwntools, atau `nm`/`objdump` manual), **bukan** di-leak oleh program. Offset ke return address = 72 byte (`buf[64]` di `rbp-0x40` + 8 byte saved RBP, dicek via `objdump`).

**Revisi (setelah keputusan kasih attachment ke A/B/C/E/F):** versi awal program ini punya `printf("debug: win @ %p\n", win)` di `vuln()` — sisa dari asumsi lama "semua binexp nc-only, tanpa attachment" (lihat `CHALLENGE_DAN_HOSTING.md` 2.4 versi sebelumnya). Setelah attachment dipastikan ada, leak itu jadi redundant (info yang sama sudah bisa didapat statis dari binary) dan bertentangan dengan intended solution yang dari awal sudah tertulis di `BINEXP_PLANNING.md`: "temukan alamat win() (statis karena no-PIE)". Baris `printf` debug itu **dihapus** dari source, binary di-rebuild dari awal (gcc/glibc sama seperti sebelumnya), `solve.py` diubah ke `exe.symbols["win"]`, dan retest end-to-end (local process + Docker container via network) — hasil identik, OFFSET tidak berubah (`sub $0x40,%rsp` dicek ulang via objdump, tetap 0x40).

## Bug penting yang ditemukan saat testing — WAJIB dibaca kalau mau ubah source/compile flags

Ret2win **langsung** ke `win()` (tanpa gadget tambahan) ternyata **SIGSEGV** saat dites lawan container Ubuntu 22.04 (meski 100% jalan kalau dites lokal di WSL/Kali pakai glibc lebih baru). Root cause (dikonfirmasi via `strace`+`gdb` di dalam container):

- `ret` langsung ke `win()` TIDAK melalui instruksi `call` biasa, jadi RSP di `win()` **misaligned 8 byte** dari yang diharapkan konvensi ABI x86-64 (normal: `call` push 8 byte dulu, lalu callee `push rbp` balikin ke 16-aligned; ret2win langsung skip langkah push dari `call` itu).
- `win()` -> `fopen()` -> `malloc()` -> `_int_malloc()` (inisialisasi tcache pertama kali) pakai instruksi SSE `movaps` yang **wajib** operand 16-byte aligned -> `#GP` -> `SIGSEGV`.
- Ini bug klasik "stack alignment ret2win" yang memang flaky antar versi glibc (sebagian build tidak kena karena code path pertamanya tidak kebetulan lewat `movaps` di titik itu).

**Fix:** sisipkan 1 gadget `ret` polos sebelum alamat `win()` di payload (`payload = padding + p64(ret_gadget) + p64(win_addr)`), supaya RSP bergeser 8 byte ekstra dan align lagi. Di `solve.py`, gadget dicari otomatis lewat `exe.search(asm("ret"), executable=True)` — **penting pakai `executable=True`**, kalau tidak, `search()` bisa ketemu byte `0xc3` di section non-executable (misal kebetulan ada di `.rodata`) dan crash.

## Bug baru: binary test lokal yang di-compile manual bisa punya alamat `win()` SALAH

Ditemukan saat restrukturisasi folder jadi `bin/`+`dist/`: `exe.symbols["win"]` di `solve.py` dibaca dari binary **lokal** (`bin/mavuika`). Kalau binary itu di-compile manual pakai gcc di WSL/Kali (rolling release, versi gcc berubah-ubah), alamat `win()` yang dihasilkan **bisa berbeda** dari binary yang benar-benar jalan di container (gcc 11.4.0 Ubuntu 22.04, versi yang di-pin). Contoh nyata yang kejadian: gcc 15.2.0 (WSL) menaruh `win` di `0x4011b6`, sedangkan gcc 11.4.0 (container) menaruhnya di `0x401256` — solver yang pakai alamat dari WSL langsung SIGSEGV lawan container asli (padahal lolos sempurna lawan proses lokal WSL-nya sendiri, karena dua-duanya konsisten memakai binary WSL yang sama).

**Fix & aturan wajib ke depan:** binary test lokal (`bin/mavuika`) **selalu di-extract dari container yang sudah dibuild**, tidak pernah di-compile manual di host:

```
docker compose up -d --build
docker cp pwn_mavuika-mavuika-1:/home/mavuika_pwn/mavuika bin/mavuika
chmod +x bin/mavuika
```

Ini menjamin byte-identik dengan yang dilawan peserta. Berlaku juga untuk Furina/Istaroth/Columbina — lihat NOTES.md masing-masing.

**Catatan:** `bin/mavuika` sengaja TETAP unstripped (beda dari Istaroth/Columbina) —
`win()` di sini tidak punya decoy/chaff bernama apa pun, jadi `exe.symbols["win"]`
bukan kecurangan: alamat yang dibaca persis sama dengan yang peserta temukan manual
lewat `nm`/`objdump` di `dist/mavuika_attachment.zip` yang sudah di-strip. Hanya
`dist/` yang perlu di-strip (sudah, lihat bagian "Attachment peserta") supaya nama
fungsi tidak kebocor ke peserta; `bin/` tidak perlu ikut, karena tidak ada apa pun
yang disembunyikan di baliknya untuk soal ini.

## Hosting

- Port: `40101`. Flag dibaca dari file `flag` (bind mount `:ro`).
- Socat CMD **tanpa** opsi `pty` (lihat catatan di `pwn_sandrone/NOTES.md` — masalah yang sama berlaku di semua 6 soal).
- CMD dibungkus `sh -c "ulimit -c 0; exec socat ..."` biar core dump dimatikan (lihat `CHALLENGE_DAN_HOSTING.md` 2.4) — berlaku ke semua 6 soal, dicek: `ulimit -c` = 0 di container, crash paksa tidak hasilkan file `core*`.

## Cara test ulang

**Paling simpel: jalankan `deploy_pwn.sh mavuika` dari WSL** — otomatis rebuild
Docker, extract `bin/mavuika` (unstripped), lalu bungkus `dist/*.zip` dari salinan
yang di-strip terpisah.

Manual (debug langkah per langkah):
```
docker compose up -d --build
docker cp pwn_mavuika-mavuika-1:/home/mavuika_pwn/mavuika bin/mavuika && chmod +x bin/mavuika
python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40101
python3 solve.py   # test lokal non-Docker, pakai bin/mavuika yang sama
```

## Attachment peserta

`dist/mavuika_attachment.zip` = binary `mavuika` di-`strip --strip-all` (symbol `win`/`vuln` dibuang dari attachment peserta; source asli tetap pakai nama itu untuk maintenance). Perilaku runtime identik setelah strip, sudah diverifikasi jalan normal. Rebuild ulang? Extract binary baru dari container (lihat bagian bug di atas), strip, lalu re-zip.
