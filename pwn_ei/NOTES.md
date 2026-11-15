# Notes — pwn_ei (Binary Exploitation D)

Status: **fungsional, teruji** (local process + Docker container via network).

## Environment build

- Base image: `ubuntu:22.04`, dipin via digest `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11`
- gcc: `11.4.0`, glibc: `2.35`. Binary dikompilasi di dalam Dockerfile.

## Struktur folder

Mengikuti pola [`ctf_xinetd`](https://github.com/152334H/ctf_xinetd) (tanpa `ctf.xinetd`-nya sendiri — kita pakai `docker-compose.yml` + `socat`, bukan xinetd, karena ini dihost sendiri bukan di shared box):

- `bin/` — source (`ei.c`) yang di-`COPY` & dikompilasi di dalam `Dockerfile`. Analog `bin/` di template itu ("put ALL challenge files in bin").
- `flag.txt`, `Dockerfile`, `docker-compose.yml`, `NOTES.md`, `readme`, `solve.py` — tetap di dir utama (scaffolding deploy + secret runtime). `flag.txt` **sengaja tidak** ikut masuk `bin/`: dia bind-mount `:ro` lewat `docker-compose.yml`, bukan di-bake ke image (lihat bagian Hosting).
- `dist/` — yang akan dibagikan ke peserta. Untuk Ei: binary `ei` (+ `ei_attachment.zip`), hasil build Docker (copy dari `bin/ei`).

## Compile command

```
gcc -m64 -fstack-protector-all -no-pie -o bin/ei bin/ei.c
```

`checksec`: Partial RELRO, Canary found, NX enabled, No PIE ("medium standar" — opsi PIE on untuk versi lebih sulit sengaja tidak dipakai, lihat `BINEXP_PLANNING.md`).

## Teknik

Format string exploitation. `printf(input)` langsung tanpa format specifier.

Offset argumen: input kita muncul di posisi **ke-6** vararg printf (dicek dengan probing manual `AAAAAAAA.%1$p.%2$p...%14$p` — nilai `0x4141414141414141` muncul di `%6$p`).

Solver pakai `pwnlib.fmtstr.fmtstr_payload(offset=6, {target_addr: 1}, write_size="short")` untuk `%n`-write 1 byte ke `access_granted`. Alamat target (`0x4040ac`) dibaca dari symbol binary (`exe.sym["access_granted"]`) — program **tidak lagi** nge-print baris `debug: access_granted @ ...` (dihapus 14 Nov; binary dibagikan ke peserta, no-PIE jadi alamat tetap statis).

## Hosting

- Port: `40201`. Flag dari file `flag.txt` (bind mount `:ro`) — **beda dari A/B/C/F/Istaroth yang pakai nama `flag` tanpa ekstensi**, ini sengaja (permintaan author untuk soal ini). Socat tanpa `pty`.
- CMD dibungkus `sh -c "ulimit -c 0; exec socat ..."` biar core dump dimatikan (lihat `CHALLENGE_DAN_HOSTING.md` 2.4, berlaku ke semua 6 soal).

## Cara test ulang

```
docker compose up -d --build
python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40201
```

## Attachment peserta: binary `ei`

Revisi 14 Nov: baris `debug: access_granted @ %p` dihapus dari `ei.c` (lihat `bin/ei.c`), dan binary `ei` sekarang dibagikan ke peserta (`dist/ei` + `dist/ei_attachment.zip`). Peserta harus cari alamat `access_granted` sendiri lewat `nm`/`objdump`/gdb (no-PIE, jadi statis); offset vararg tetap lewat probing live seperti sebelumnya. Binary di `dist/` identik dengan `bin/ei` (sama-sama hasil build Docker ubuntu:22.04). Setelah revisi, sudah diretest ulang lewat container live: offset 6 tetap, payload `AAAA%7$n` + alamat `0x4040ac` mengembalikan flag asli.

**PERINGATAN (ditemukan belakangan, cek Build ID sebelum percaya klaim "identik" di atas):**
`dist/ei` + `dist/ei_attachment.zip` **sudah tidak sinkron** dengan `bin/ei` saat ini
-- Build ID beda (`nm`/`readelf -n` buktinya), karena `bin/ei` di-rebuild lagi setelah
`dist/` terakhir dibuat tapi `dist/` tidak ikut diregenerasi. `deploy_pwn.sh` sekarang
sudah menangani `ei` (`HAS_ATT=1`, `STRIP=0` -- **tanpa** strip, karena peserta memang
dimaksudkan baca nama `access_granted` lewat `nm`), tapi belum dijalankan ulang lewat
Docker/WSL sejak perbaikan ini. **Jangan bagikan `dist/ei*` yang ada sekarang ke
peserta** sampai `deploy_pwn.sh ei` dijalankan ulang dan alamat `access_granted` di
attachment dikonfirmasi cocok dengan yang live di server.

## Bug yang ditemukan & diperbaiki (audit banding vs picoCTF format-string-0/1)

`give_flag()` sempat ter-edit jadi `fopen("flag.txt", "r")` dengan pesan ala picoCTF ("Please create 'flag.txt'...") sementara file di host masih bernama `flag` (tanpa ekstensi) — mismatch, persis kelas bug yang sama dengan yang ditemukan di `pwn_sandrone` (lihat `NOTES.md` sana). **Untuk Ei, nama resminya memang `flag.txt`** (beda dari 5 soal lain yang pakai `flag`) — jadi perbaikannya bukan mengubah kode, melainkan me-rename file host dari `flag` ke `flag.txt` + update mount di `docker-compose.yml` agar cocok dengan `fopen("flag.txt", ...)`, dan pesan error diselaraskan ke gaya kita sendiri ("flag.txt tidak ditemukan di server, lapor panitia."). Sudah direbuild (`--no-cache`) & diretest, local process maupun live container, keduanya balikin flag asli.
