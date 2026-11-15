# Notes — pwn_furina (Binary Exploitation C)

Status: **fungsional, teruji** (local process + Docker container via network).

## Environment build

- Base image: `ubuntu:22.04`, dipin via digest `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11`
- gcc: `11.4.0`, glibc: `2.35`. Binary dikompilasi di dalam Dockerfile.

## Struktur folder

Mengikuti pola [`ctf_xinetd`](https://github.com/152334H/ctf_xinetd) (tanpa `ctf.xinetd`-nya sendiri — kita pakai `docker-compose.yml` + `socat`, bukan xinetd): `bin/` untuk source + binary test lokal (**wajib extract dari container**, lihat `pwn_mavuika/NOTES.md` bagian bug alamat `win()` — berlaku juga di sini karena `solve.py` baca `exe.symbols["win"]` statis); `flag` + scaffolding deploy tetap di dir utama; `dist/` untuk attachment peserta.

## Compile command

```
gcc -m64 -fstack-protector-all -no-pie -o bin/furina bin/furina.c
```

`checksec`: Partial RELRO, **Canary found** (red herring, bug utama bukan stack overflow), NX enabled, No PIE.

## Teknik

OOB array index -> write-what-where -> hijack dispatch-table -> `win(a,b,c)` dengan calling convention benar.

Layout `.bss`: `court.case_notes[4][32]` (128 byte) **langsung diikuti** `court.verdicts[4]` (32 byte, function pointer array) dalam satu struct — dicek via `nm`/`readelf`. Index out-of-bounds di operasi "catat catatan kasus" (`idx * 32` tanpa bounds check) bisa menulis ke memory `court.verdicts`.

`OOB_IDX = 4` (karena `sizeof(case_notes)/NOTE_LEN = 128/32 = 4`) menulis TEPAT di `verdicts[0]`. Tulis 8 byte = alamat `win()` — **statis** karena no-PIE, dibaca dari attachment binary (`exe.symbols["win"]`), **bukan** di-leak program. Lalu panggil "jatuhkan putusan" index 0 dengan `a=0x1337, b=0xC0DE, c=0xF00DBEEF` (argumen yang dicek di dalam `win()`) — argumen dikirim di register `rdi/rsi/rdx` oleh compiler secara normal karena ini **indirect call biasa** (`court.verdicts[idx](a,b,c)`), bukan ROP, jadi calling convention otomatis benar selama kode exploit kita yang panggil fungsinya lewat C.

**Revisi (setelah keputusan kasih attachment ke A/B/C/E/F):** versi awal program ini punya `printf("debug: win @ %p\n", win)` di `main()` sebelum banner — sisa dari asumsi lama "nc-only, tanpa attachment". Dihapus karena redundant (info sama sudah statis dari binary) dan `BINEXP_PLANNING.md` sejak awal sudah menulis intended solution sebagai "temukan index ... hitung offset ... tulis alamat win()" tanpa menyebut leak runtime. Binary di-rebuild, `solve.py` diubah ke `exe.symbols["win"]`, retest end-to-end (local + Docker via network) — hasil identik, OOB_IDX/layout `.bss` tidak berubah.

## Tidak ada isu stack-alignment di sini

Berbeda dari Mavuika/Istaroth: `win()` dipanggil lewat **indirect call normal** (compiler yang generate instruksi `call`-nya), bukan lewat `ret`-hijack — jadi RSP otomatis di-align benar oleh compiler, tidak perlu ret-sled.

## Hosting

- Port: `40401`. Flag dari file `flag` (bind mount `:ro`). Socat tanpa `pty`.
- CMD dibungkus `sh -c "ulimit -c 0; exec socat ..."` biar core dump dimatikan (lihat `CHALLENGE_DAN_HOSTING.md` 2.4, berlaku ke semua 6 soal).

## Cara test ulang

```
docker compose up -d --build
docker cp pwn_furina-furina-1:/home/furina_pwn/furina bin/furina && chmod +x bin/furina
python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40401
python3 solve.py   # test lokal non-Docker, pakai bin/furina yang sama
```

## Attachment peserta

`dist/furina_attachment.zip` = binary `furina` di-`strip --strip-all`. Perilaku runtime identik setelah strip, sudah diverifikasi jalan normal. Rebuild ulang? Extract binary baru dari container, strip, lalu re-zip.

**Catatan:** `bin/furina` sengaja TETAP unstripped (beda dari Istaroth/Columbina) —
`win()` di sini tidak punya decoy/chaff bernama apa pun, jadi `exe.symbols["win"]`
bukan kecurangan: alamat yang dibaca persis sama dengan yang peserta temukan manual
lewat `nm`/`objdump` di `dist/furina_attachment.zip` yang sudah di-strip. Hanya
`dist/` yang perlu di-strip supaya nama fungsi tidak kebocor ke peserta; `bin/`
tidak perlu ikut.
