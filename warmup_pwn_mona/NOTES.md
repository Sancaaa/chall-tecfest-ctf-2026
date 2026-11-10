# Notes — warmup_pwn_mona

Status: **fungsional, teruji** (local process via WSL gcc 15.2.0; dan lewat Docker
container via network, beberapa kali koneksi TCP terpisah ke `127.0.0.1:10110`,
semua balas flag dengan benar). `bin/mona` di-extract dari container (`docker cp`),
bukan hasil compile WSL manual, mengikuti aturan di `pwn_mavuika/NOTES.md`.
`dist/mona_attachment.zip` sudah di-rebuild dari binary itu + source `mona.c`.

## Revisi v2 (2026-11-08) — pola disamakan dengan format-string-0.c

Atas permintaan Sanca, struktur disamakan dengan `format-string-0.c` (referensi di
folder parent):

- Flag dibaca **sekali** ke buffer global `char flag[FLAGSIZE]` di **awal banget**
  `main()`, sebelum hal lain terjadi. Kalau `flag.txt` tidak ada di direktori kerja,
  program langsung bilang "flag.txt tidak ditemukan..." dan exit -- ketauan dari
  awal, bukan nanti pas sudah coba di-crash.
- Nama file diganti dari `flag` -> **`flag.txt`** (lebih jelas), termasuk mount path
  di `docker-compose.yml` (`./flag.txt:/home/mona_pwn/flag.txt:ro`).
- Signal handler **langsung diberi nama `win`** (`signal(SIGSEGV, win)`) dan cuma
  nge-print buffer `flag` yang sudah dibaca di awal (bukan buka file lagi di dalam
  handler -- `fopen`/`fgets` memang bukan async-signal-safe, pola lama yang buka
  file di dalam handler kurang tepat untuk ditiru ke depan).
- `dist/mona_attachment.zip` sekarang membundel **binary + `mona.c`** (source ikut
  dibagikan peserta) -- ini warm-up, jadi intended solution boleh langsung kelihatan
  dari source: ada `vuln()` yang `read()` 1024 byte ke `buf[64]` tanpa cek, dan ada
  `signal(SIGSEGV, win)` yang bikin jelas "kalau program ini crash, kamu menang".

## Konsep

Peserta overflow `buf[64]` dengan payload panjang (misal 200 byte `A`) sampai
menimpa saved RBP + return address milik `vuln()`. Saat `vuln()` `ret`, CPU coba
lompat ke `0x4141414141414141` (non-canonical address) -> `SIGSEGV`. Kernel
memanggil `win()` sebagai handler -> `win()` print buffer `flag` yang sudah dibaca
di awal `main()` -> `_exit(0)`.

Canary **sengaja dimatikan** (`-fno-stack-protector`) supaya overflow benar-benar
nembus ke return address dan crash lewat jalur `ret` di atas (bukan keburu
`__stack_chk_fail` -> `SIGABRT` duluan, yang tidak kita tangani).

## Kenapa reliable (tidak bergantung ASLR)

`0x4141414141414141` punya bit 63 = 0 tapi bit-bit tinggi lain tidak konsisten dengan
sign-extension yang disyaratkan canonical address x86-64 -> selalu general protection
fault terlepas dari base ASLR apapun. Beda dari bug "ret2win alignment" di
`pwn_mavuika/NOTES.md` (itu soal `movaps` butuh stack 16-byte aligned); di sini kita
TIDAK pernah benar-benar mengeksekusi apapun di alamat itu, jadi isu alignment itu
tidak relevan.

## Compile

```
gcc -m64 -fno-stack-protector -o bin/mona bin/mona.c
```

`checksec`: No canary, PIE default (tidak relevan untuk challenge ini).

## Test lokal (tanpa Docker)

```
mkdir -p /tmp/monatest && cp bin/mona flag.txt /tmp/monatest/ && cd /tmp/monatest
python3 -c "import subprocess; p=subprocess.run(['./mona'], input=b'A'*200, stdout=subprocess.PIPE, timeout=5); print(p.stdout.decode())"
```

Dites juga skenario `flag.txt` sengaja dihapus sementara -- program langsung bilang
"flag.txt tidak ditemukan..." tanpa perlu dikirim input apapun, sebelum "=== Mona's
Astrology..." sekalipun. Sesuai desain (cek di awal `main()`).

## Hasil test Docker (2026-11-08, setelah revisi v2)

- `docker compose up -d --build` sukses, container `Up` normal.
- Beberapa koneksi TCP terpisah (bukan 1 koneksi dipakai ulang) ke
  `127.0.0.1:10110`, masing-masing kirim `b"A"*200` -> semua balas flag dengan benar.
- `docker exec ... ulimit -c` = `0` di dalam container; container tetap `Up` setelah
  beberapa kali crash berturut-turut.
- Binary `bin/mona` di-extract ulang dari container via `docker cp` lalu
  `dist/mona_attachment.zip` di-rebuild dari situ + `mona.c` (byte-identik dengan
  yang jalan di server, bukan hasil compile WSL manual).

## TODO sebelum deploy

- [x] Host-side port sudah diset ke `40111` (skema 5 digit K-CC-W-I: kategori 4
      Pwn, slot 01, digit-4=1 warm-up) di `docker-compose.yml` — tidak bentrok
      dengan soal lain (lihat `ARSITEKTUR_INFRA_DAN_ANCAMAN.md` bagian 3a untuk
      pemetaan port penuh). Port internal container (`10110`, dipakai di Dockerfile
      /socat) tidak berubah.
- [ ] Set `Deployment Status = Deployed` di CSV setelah dipasang di instance lomba
