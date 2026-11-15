# Notes — pwn_sandrone (Binary Exploitation A)

Status: **fungsional, teruji** (local process + Docker container via network, berkali-kali, reliable). Narasi/gimmick belum ditambahkan (sengaja, lihat permintaan di chat) — tinggal di-custom manual.

## Revisi besar 14 Nov — badchar-free XOR payload encoding jadi teknik inti

**Alasan revisi:** dibandingkan ulang dengan Furina (sama-sama label "Medium" di `BINEXP_PLANNING.md`), versi lama sandrone jauh lebih mekanis begitu leak `buf` dikasih — satu tembakan `shellcode + padding + alamat`, tanpa insight tambahan (beda dengan Furina yang butuh reverse 2 menu handler + hitung index aritmatika + chaining). Supaya difficulty-nya sebanding, teknik intinya diganti jadi **badchar-free XOR shellcode encoding**, mengikuti metode kombinatorial di makalah "Badchar-Free XOR Payload Encoding in Binary Exploitation" (Justin Sepvian, ITB, 2026) — lihat `WRITEUP.md` bagian 5 buat rujukan lengkap & penjelasan teori (set theory + GF(2^8) + Principle of Inclusion-Exclusion).

**Source (`bin/sandrone.c`) sekarang punya DUA channel input di `vuln()`:**
1. **"payload diagnostik"** — `fgets()` lalu `strcpy()` ke buffer `payload`. Badchar muncul **natural** dari cara kerja fungsi ini (bukan filter buatan): `strcpy` berhenti di byte NUL (`0x00`) pertama, `fgets` berhenti di `\n` (`0x0a`). Shellcode yang mau dieksekusi WAJIB lewat channel ini, jadi wajib di-encode dulu.
2. **"kontrol overflow"** — `read()` mentah, TIDAK disanitasi. Dipakai buat overflow return address asli. Ini sengaja dipisah dari channel 1 karena alamat stack (buf/payload) hampir pasti mengandung byte NUL di 2 byte teratas — kalau overflow ini juga lewat `strcpy`, byte NUL di tengah alamat bakal motong return-address overwrite-nya sendiri (lihat WRITEUP.md bagian 3 buat penjelasan kenapa ini masalah berbeda dari badchar di shellcode).

**Layout stack (`frame[192]` dibagi manual lewat pointer, BUKAN dua `char[]` terpisah):**
```c
char frame[128 + 64];
char *payload = frame;        // frame[0..127]   -> alamat LEBIH RENDAH
char *buf     = frame + 128;  // frame[128..191] -> alamat LEBIH TINGGI
```
Sengaja satu array: dua `char[]` lokal terpisah urutannya bergantung heuristik gcc (percobaan pertama, `payload[128]` dideklarasi sebelum `buf[64]`, malah ditaruh gcc di alamat LEBIH TINGGI dari `buf` — kebalik dari yang diinginkan). Kalau `payload` ada di alamat lebih tinggi dari `buf`, overflow `read(fd, buf, 256)` (nulis maju/naik alamat dari `buf`) bakal **menimpa balik** `payload` yang baru diisi channel 1 — race antar 2 channel. Dengan satu array + pointer manual, urutan byte dijamin standar C (index naik = alamat naik), jadi `payload` (index rendah) tidak pernah kesentuh overflow yang mulai dari `buf` (index tinggi).

**Offset (dicek via `objdump -d bin/sandrone --disassemble=vuln`, bukan ditebak):**
- `buf = rbp-0x50`, `payload = buf - 0x80` (frame dimulai di `rbp-0xd0`, `buf = frame+0x80`).
- Return address: `buf` ke saved RBP = `0x50` (80 byte) + 8 byte saved RBP = **88 byte** sebelum return address. (Beda dari versi lama yang offsetnya 72 — frame lebih besar sekarang karena ada `payload`+`net_buf` tambahan.)

**Decoder stub — teknik JMP/CALL/POP (Erickson, *Hacking: The Art of Exploitation*):** posisi-independen tanpa immediate/alamat mentah. Percobaan pertama pakai `lea rsi, [rip+label]` (RIP-relative) GAGAL — meski offset-nya kecil, x86-64 selalu encode `lea reg,[rip+disp32]` dengan field 4-byte, dan nilai kecil berarti 3 byte tertinggi dari disp32 itu `0x00` (zero-padding) → otomatis kena badchar. Fix: `call` MUNDUR ke label dekat (`call decoder` yang definisinya di ATAS instruksi call-nya) menghasilkan `rel32` NEGATIF (two's complement) — byte tertinggi jadi `0xFF`, bukan `0x00`. `pop rsi` setelah itu mengambil return-address yang di-push `call`, yaitu persis alamat byte tepat sesudah instruksi `call` = awal shellcode terenkode. Stub final: 26 byte, diverifikasi 0 badchar (lihat `solve.py`).

**Key search:** `Algorithm 1` dari paper (set-based filtration, bukan brute force 256 key) — lihat implementasi di `solve.py`. Untuk `shellcraft.amd64.linux.cat("flag.txt") + shellcraft.amd64.linux.exit(0)` (51 byte, 32 byte unik) vs `B={0x00,0x0a}`: 196 key valid dari 256, dipakai key terkecil (`0x03`).

**Hasil test:** 5x run lawan container live, ASLR beda tiap koneksi, 100% dapat flag (`python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40301`), juga lolos sebagai proses lokal. Binary di-build ulang via `deploy_pwn.sh` (WSL kali-linux, `docker compose build --no-cache`), bukan compile manual.

## Environment build (dicatat untuk reproduksi)

- Base image: `ubuntu:22.04`, dipin via digest `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11`
- gcc di dalam image: `11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3)`
- glibc di dalam image: `2.35 (Ubuntu GLIBC 2.35-0ubuntu3.15)`
- Arch: x86-64
- Binary **dikompilasi di dalam Dockerfile** (bukan di-copy dari mesin dev) supaya glibc selalu match persis dengan yang di-deploy.

## Struktur folder

Mengikuti pola [`ctf_xinetd`](https://github.com/152334H/ctf_xinetd) (tanpa `ctf.xinetd`-nya sendiri — kita pakai `docker-compose.yml` + `socat`, bukan xinetd, karena ini dihost sendiri bukan di shared box):

- `bin/` — source (`sandrone.c`) yang di-`COPY` & dikompilasi di dalam `Dockerfile`, plus binary hasil test lokal (lihat catatan "Binary test lokal" di bawah).
- `flag`, `Dockerfile`, `docker-compose.yml`, `NOTES.md`, `readme`, `solve.py` — tetap di dir utama. `flag` **sengaja tidak** ikut masuk `bin/`: bind-mount `:ro`, bukan di-bake ke image.
- `dist/` — yang dibagikan ke peserta (`sandrone_attachment.zip`, lihat bagian Attachment).

## Compile command

```
gcc -m64 -fno-stack-protector -no-pie -z execstack -o bin/sandrone bin/sandrone.c
```

## Binary test lokal — WAJIB extract dari container, JANGAN compile lokal manual

Ditemukan saat merger struktur folder: compile ulang `sandrone.c` pakai gcc lokal (WSL/Kali, versi berubah-ubah karena rolling release) **bisa menghasilkan binary yang berbeda byte-nya** dari yang benar-benar jalan di container (gcc 11.4.0 Ubuntu 22.04 yang di-pin). Soal ini kebetulan tidak kena dampak (alamat `buf` di-leak live tiap koneksi, tidak pernah dibaca statis dari binary) — tapi Mavuika/Furina/Istaroth/Columbina (yang baca `exe.symbols["win"]` secara statis) **kena**, lihat NOTES.md masing-masing. Supaya konsisten dan aman ke depannya, binary test lokal (`bin/sandrone`) **selalu di-extract langsung dari container yang sudah dibuild**, bukan di-compile manual:

```
docker compose up -d --build
docker cp pwn_sandrone-sandrone-1:/home/sandrone_pwn/sandrone bin/sandrone
chmod +x bin/sandrone
```

Verifikasi `checksec`: Partial RELRO, **No canary**, **NX disabled**, **No PIE**.

## Teknik

~~Shellcode injection klasik tanpa constraint lain~~ — **digantikan** per revisi 14 Nov (lihat bagian atas): sekarang shellcode injection + **badchar-free XOR payload encoding** (dua channel, decoder stub JMP/CALL/POP, key search ala paper). Mekanisme leak tetap sama (lihat paragraf di bawah), cuma payload-nya sekarang harus di-encode dulu sebelum lewat channel yang disanitasi.

Alamat `buf` di-leak langsung oleh program (`debug: buf @ 0x...`) supaya peserta tidak perlu tahu/disable ASLR — binary tetap NX off + no PIE, tapi stack tetap kena ASLR normal (PIE cuma soal alamat *kode* binary, bukan stack).

**Catatan (dicek ulang setelah keputusan kasih attachment ke A/B/C/E/F):** beda dari Mavuika/Furina (yang leak `win()`-nya sempat salah, dihapus — lihat `NOTES.md` masing-masing), leak `buf` di sini **tetap wajib ada**, attachment atau tidak. Alasannya beda: `win()` di Mavuika/Furina ada di code segment yang statis tanpa PIE (bisa dibaca dari binary), sedangkan `buf` di sini ada di **stack**, yang basenya selalu diacak ASLR kernel terlepas dari PIE/attachment — tidak pernah tercatat sebagai alamat tetap di file binary manapun. Komentar di source awalnya salah menyebut alasannya "karena tidak ada attachment"; sudah diperbaiki jadi menyebut ASLR stack sebagai alasan sebenarnya.

## Hal yang ditemukan saat testing (penting buat siapa pun yang edit hosting-nya)

- **Dockerfile/CMD socat JANGAN pakai opsi `pty`** (`pty,stderr,setsid,sigint,sane,echo=0` ala template `bof.zip`). PTY punya line-discipline terminal yang bisa memfilter/mengubah byte tertentu dari payload biner (shellcode) — exploit yang 100% jalan lewat proses lokal langsung EOF/gagal total lewat koneksi network kalau pakai `pty`. Fix: CMD cuma `EXEC:/usr/bin/timeout ... /path/binary` polos, tanpa `pty`. (Makin krusial sekarang: channel 2/"kontrol overflow" butuh raw byte termasuk NUL tertulis utuh, PTY bisa merusak itu juga.)
- Shellcode target (`solve.py`) pakai `shellcraft.amd64.linux.cat("flag.txt") + shellcraft.amd64.linux.exit(0)` — ditambah `exit(0)` secara eksplisit karena shellcraft `cat()` default-nya (pakai `sendfile`) tidak exit sendiri setelah selesai, lanjut "jatuh" ke byte sampah berikutnya dan crash (tidak masalah buat ambil flag karena flag sudah ter-print duluan, tapi exit(0) bikin koneksi tutup bersih tanpa SIGSEGV di log). Shellcode ini sekarang di-XOR-encode dulu (lihat bagian "Revisi besar" di atas) sebelum dikirim lewat channel 1 — bukan dikirim mentah lagi.
- **Percobaan gagal yang sengaja dicatat:** decoder stub pertama pakai `lea rsi, [rip+label]` buat self-reference posisi-independen — GAGAL karena `lea reg,[rip+disp32]` selalu pakai field displacement 4 byte, dan nilai kecil bikin 3 byte teratasnya `0x00` (zero-padding), otomatis kena badchar sendiri dari instruksi decoder-nya. Fix: teknik `JMP/CALL/POP` klasik (`call` MUNDUR ke label di atasnya → `rel32` negatif → byte tertinggi `0xFF`, bukan `0x00`).

## Bug kritis yang ditemukan & diperbaiki (tidak ada hubungannya dengan apapun di atas)

File flag di folder ini ternyata bernama **`flag.txt`**, bukan `flag` — mismatch dengan `docker-compose.yml` (`./flag:/home/sandrone_pwn/flag:ro`) dan binary (`fopen`/`cat` syscall minta nama file persis `flag`). Akibatnya: Docker bikin `./flag` otomatis sebagai **direktori kosong** di host karena source bind mount tidak ketemu (perilaku standar Docker kalau path bind mount belum ada) — jadi bukan error nyata saat container start, cuma silently salah isi. Exploit tetap jalan penuh (shellcode berhasil inject & eksekusi, proses exit 0 bersih), tapi `cat("flag")` di dalam shellcode gagal baca (`EISDIR`) dan tidak mencetak apapun → solver EOF tanpa flag, kelihatan seperti exploit gagal padahal sebenarnya exploit-nya 100% berhasil, cuma targetnya salah.

**Fix:** hapus direktori kosong `flag/`, `mv flag.txt flag` (isi sama, sudah dicocokkan ke Flag CSV), `docker compose down && up --build` supaya bind mount Docker re-resolve ke file yang benar (restart/recreate container saja tidak cukup kalau mount point sudah "ter-cache" sebagai direktori). Retest lokal + lawan container — keduanya sukses dapat flag asli.

**Kenapa ini kelewat sebelumnya:** entah kapan tepatnya file ini kena rename/ketukar jadi `.txt` (kemungkinan sisa dari konvensi `flag.txt` yang disebut di `BINEXP_PLANNING.md` baris 7 — tapi 5 soal lain semua konsisten pakai `flag` tanpa ekstensi). Pelajaran: kalau mau cek ulang soal lain di masa depan, jangan cuma percaya status "sudah ditest" dari dokumentasi — re-run `solve.py` lawan container yang baru di-recreate dari awal (bukan container lama yang mungkin sudah "kebetulan benar" dari state sebelumnya).

## Hosting

- Port: `40301`
- CMD dibungkus `sh -c "ulimit -c 0; exec socat ..."` biar core dump dimatikan (lihat `CHALLENGE_DAN_HOSTING.md` 2.4, berlaku ke semua 6 soal). Diverifikasi: `ulimit -c` di container = 0, crash paksa (overflow asal-asalan) tidak menghasilkan file `core*` di manapun, container utama tetap `Up` setelah 1 koneksi crash.
- Flag dibaca dari file `flag` (relatif cwd proses), di-mount read-only lewat `docker-compose.yml` (`:ro`) — **tidak** di-bake ke image.
- `docker-compose.yml` sudah termasuk hardening dari `CHALLENGE_DAN_HOSTING.md` 2.4: `cap_drop: ALL`, `no-new-privileges`, `pids_limit`, `mem_limit`, `cpus`.
- **Catatan tambahan untuk isolasi** (lihat `BINEXP_PLANNING.md` checklist): karena ini genuine arbitrary code execution (shellcode bebas, bukan cuma reuse fungsi existing), pertimbangkan tambahan isolasi per koneksi (nsjail/pwn.red jail) di infra produksi — `docker-compose.yml` saat ini baru level hardening container biasa.

## Cara test ulang

Pakai `deploy_pwn.sh` (WAJIB dari WSL, lihat header script-nya buat alasan):

```bash
wsl.exe -d kali-linux -- bash "/mnt/d/Universitas Udayana/UKM-KS/Tecart/2026/TecFest/Challenge & Competition/deploy_pwn.sh" sandrone
```

Lalu solve:

```
python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40301
python3 solve.py   # test lokal non-Docker, pakai bin/sandrone yang sama (butuh WSL/Linux + pwntools)
```

(Dicek ulang 14 Nov, 5x run lawan container live dengan ASLR berbeda tiap koneksi — 100% dapat flag.)

## Attachment peserta

`dist/sandrone_attachment.zip` = binary `sandrone` di-`strip --strip-all` dari hasil compile ini (symbol table dibuang, perilaku runtime identik — sudah dites ulang jalan normal setelah strip). Regenerasi sekarang otomatis lewat `deploy_pwn.sh` (lihat "Cara test ulang" di atas) — tidak perlu `docker cp`/`strip`/`zip` manual lagi. Solver (`solve.py`) tidak bergantung ke symbol table binary sama sekali (semua offset dihardcode dari hasil `objdump`, lihat bagian "Revisi besar" di atas) — jadi stripping aman, tidak mempengaruhi exploit.
