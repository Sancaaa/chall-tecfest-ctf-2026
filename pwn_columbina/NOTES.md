# Notes — pwn_columbina (Binary Exploitation F)

Status: **v2.1 (tcache poisoning + panjang opsi 5 dibatasi), fungsional &
teruji** (local process via ld-linux+libc yang dipin, DAN 5x+4x koneksi
network berturut-turut ke container Docker asli setelah fix v2.1, semua
balas flag yang sama, alamat heap berbeda tiap koneksi; chaff/opsi "7" dites
manual tetap balas flag salah tanpa eksploitasi; NULL-deref sengaja [slot
belum pernah dibuat] dan slot-index invalid juga dites -- crash bersih/
ditolak rapi, tidak ada core dump, container tetap `Up`).

## Kerentanan v2 yang diperbaiki (v2.1, ditemukan via blackbox test)

Blackbox test independen (`TESTING_PWN/pwn_columbina/WRITEUP_columbina.md`,
dites terhadap binary v2 yang SAMA yang sudah diklaim "fix dan berhasil")
menemukan jalan pintas balik ke teknik v1: **opsi 5 ("Tulis entri Luonnotar")
masih mengizinkan `panjang` sampai 40 byte**, jadi solve 4-langkah sederhana
berikut tetap berhasil tanpa fragmen ke-3, tanpa UAF-write (opsi 3), tanpa
leak, tanpa hitung safe-linking apa pun -- murni "v1 lama":

```
1. Catat fragmen slot 0
2. Lepas fragmen slot 0 (UAF, tidak di-NULL-kan)
3. Tulis entri Luonnotar (panjang=40) -> tcache LIFO balikin chunk YANG SAMA
   -> tulis p64(win) langsung di offset 32 (otoritas) dalam SATU panggilan
4. Uji otoritas slot 0 -> win() terpanggil
```

**Root cause:** saya cuma MENAMBAH primitive baru (UAF-write opsi 3) tanpa
MENUTUP primitive lama (opsi 5 masih bisa menulis sampai offset 32 langsung
pada SATU chunk yang baru direuse) -- exploit v2 yang saya desain memang
berhasil, tapi tidak PERLU dipakai, karena jalan yang lebih pendek masih
terbuka. Ini persis kelas kesalahan yang disebut di diskusi difficulty
review sebelum revisi v2: "tambah primitive, bukan tutup primitive lama".

**Fix (v2.1):** `panjang` di opsi 5 dibatasi maks **16 byte** (dulu 40,
divalidasi `len > 16` bukan `len > sizeof(struct eksistensi)`). 16 byte
cukup buat 2 langkah LEGIT teknik v2 (0 byte konsumsi chunk C, 8 byte tulis
alamat `win()` ke `target` yang sudah diracun) tapi TIDAK PERNAH cukup
menjangkau offset 32 (`otoritas`) dalam satu tulisan mentah dari offset 0 --
jalan pintas v1 sekarang ditolak server dengan `"panjang invalid."`
(dikonfirmasi dites lagi dengan panjang 17/32/40, semua ditolak).

**Pelajaran buat desain heap-chall serupa di masa depan:** setelah menambah
primitive baru yang lebih "susah" (butuh leak/safe-linking/dst.), WAJIB
cek ulang apakah primitive LAMA yang lebih mudah masih mencapai tujuan yang
sama tanpa primitive baru itu -- bukan cuma verifikasi "exploit yang saya
desain berhasil", tapi juga "exploit yang lebih pendek TIDAK berhasil".

## Kenapa direvisi dari v1 (v1 -> v2, sebelum temuan di atas)

v1 (UAF + reuse-by-size) cuma butuh: free satu chunk, malloc ulang chunk SAMA
UKURAN (tcache LIFO otomatis balikin chunk yang sama persis), tulis penuh.
TIDAK ada leak apa pun (PIE off), dan TIDAK pernah menyentuh mekanisme
`fd`/safe-linking tcache sama sekali (cuma 1 chunk pernah ada di bin itu,
field metadata-nya tidak pernah relevan ke exploit). Hasil diskusi difficulty
review menyimpulkan ini **Medium**, setara Furina/Sandrone (0 leak, logic bug
lurus), bukan Hard.

**v2** menambah SATU bug baru: **"Ukir ulang nama fragmen" (opsi 3) tidak
mengecek apakah fragmen itu sudah dilepas (di-free) atau belum** -- UAF-WRITE
lewat pointer dangling, bukan cuma UAF lewat reuse-by-size. Ini memungkinkan
**tcache poisoning** beneran: korupsi field `next` (fd) sebuah chunk yang
masih nangkring di freelist SEBELUM dia di-pop ulang oleh malloc, lewat
formula **safe-linking** (`mangled = (chunk_addr >> 12) ^ target`, wajib ada
sejak glibc >= 2.32) yang harus dihitung peserta sendiri pakai alamat heap
yang di-leak program (opsi "1. Catat fragmen" sekarang print alamat chunk-nya
-- pola yang sama dipakai Sandrone buat leak stack). Hasilnya: `malloc()`
bisa "dipaksa" mengembalikan alamat ARBITRARY (bukan cuma reuse chunk yang
sama), dipakai buat menulis langsung ke field `otoritas` milik fragmen LAIN
yang masih hidup -- genuinely menuntut pemahaman internal tcache glibc,
bukan cuma "reuse chunk, tulis field".

## Environment build

- Base image: `ubuntu:22.04`, dipin via digest
  `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11`
- gcc: `11.4.0`, glibc: `2.35` (dipin spesifik via digest karena heap
  exploitation sensitif ke versi glibc -- termasuk apakah safe-linking aktif,
  lihat `CHALLENGE_DAN_HOSTING.md` 2.4). Binary dikompilasi di dalam Dockerfile.

## Struktur folder

Sama seperti v1 (`bin/` source+test lokal, `flag.txt`/scaffolding di dir
utama, `dist/` attachment peserta berisi binary+libc+ld).

## Compile command

```
gcc -O0 -m64 -fstack-protector-all -no-pie -o bin/columbina bin/columbina.c
```

`checksec`: Partial RELRO, Canary found, NX enabled, **No PIE** (disengaja --
lihat `BINEXP_PLANNING.md`: biar soal ini fokus ke mekanisme heap/tcache
doang, bukan ditumpuk sama defeat-PIE juga; dipertahankan di v2, lihat diskusi
difficulty review -- 1 leak heap + safe-linking math sudah cukup buat level
Hard tanpa perlu nambah PIE-defeat lagi).

## Teknik (desain v2) -- WAJIB 3 fragmen, bukan 2

`struct eksistensi` size = 40 byte: `nama[24]` (offset 0), `jiwa` (offset 24),
`otoritas` (offset 32) -- tidak berubah dari v1.

**Kenapa butuh 3 fragmen (A, B, C), bukan cuma 2 (sacrificial + target):**
glibc `tcache` punya array `counts[]` TERPISAH dari `entries[]` (pointer ke
head freelist). `tcache_get()` (dipanggil tiap `malloc()`) cuma mengambil
dari tcache kalau `counts[tc_idx] > 0` -- **tidak peduli apakah `entries[]`
nonzero/sudah diracun atau belum.** Kalau cuma 1 chunk yang di-free (count=1),
pop PERTAMA (buat "konsumsi" chunk itu) langsung menghabiskan count jadi 0 --
pop KEDUA (yang seharusnya mengembalikan alamat `target` hasil racun) jadi
SKIP tcache sama sekali (count=0), balik ke alokasi normal, alamat racun kita
tidak pernah terpakai. **Percobaan pertama persis kena bug ini saat
development** (lihat histori test) -- exploit "jalan tanpa crash" tapi flag
tidak keluar, karena write landing di alamat lain yang tidak relevan.

**Fix: free DUA chunk sacrificial (A lalu C) sebelum korupsi**, supaya
`count` mulai dari 2:

1. Catat A (slot 0, sacrificial #1), B (slot 1, **TARGET** -- tetap hidup
   sepanjang exploit), C (slot 2, sacrificial #2) -> program print alamat
   heap ketiganya ("bersemayam di %p").
2. Lepas A -> `entries=A, A.next=mangle(A,NULL), count=1`.
3. Lepas C (SETELAH A -- urutan LIFO penting) -> `entries=C` (C jadi HEAD,
   bukan A), `C.next=mangle(C,A)`, `count=2`.
4. **UAF-WRITE** (bug baru v2): "ukir ulang nama" slot 2 (C, **SUDAH
   di-free**, tapi `fragmen[2]` tidak di-NULL-kan -> dangling, sama seperti
   bug UAF lama tapi sekarang dipakai buat WRITE bukan cuma "reuse") dengan 8
   byte = `PROTECT_PTR(C_addr, target) = (C_addr>>12) XOR target`, dengan
   `target = &B->otoritas` (addr B hasil leak + 32). Ini menimpa field
   `next` chunk C **sebelum** dia di-pop ulang oleh malloc manapun.
5. "Tulis entri Luonnotar" **#1**, panjang=**0** -> `malloc(0x28)` cek
   `count=2>0` -> pop C (count jadi 1) -> `entries` jadi
   `REVEAL_PTR(C.next)` = `target` (matematika safe-linking:
   `(C>>12) XOR [(C>>12) XOR target] = target`, XOR self-invers). Konsumsi
   C, sengaja TIDAK nulis apa pun (`panjang=0`).
6. "Tulis entri Luonnotar" **#2**, panjang=**8** -> `malloc(0x28)` cek
   `count=1>0` (**masih lolos** karena count start dari 2, bukan 1 -- INI
   LANGKAH YANG GAGAL KALAU CUMA ADA 1 CHUNK SACRIFICIAL**) -> pop `target`
   (tcache beneran balikin alamat ARBITRARY ini sebagai "chunk" hasil
   `malloc()`) -> tulis 8 byte alamat `win()` -> landing TEPAT di field
   `B->otoritas` (karena `target == &B->otoritas` persis).
7. "Uji otoritas" slot 1 (B) -> `fragmen[1]->otoritas(fragmen[1])` sekarang
   `== win()` -> flag.

Alamat `win()` di-leak langsung dari attachment binary (no-PIE, statis) --
TIDAK perlu leak PIE/libc apa pun untuk BAGIAN INI (beda dari Istaroth v2,
yang butuh leak libc buat `system()`). Satu-satunya leak yang dibutuhkan di
sini adalah alamat HEAP (buat hitung mangle), bukan alamat kode.

## Chaff flag (tidak berubah dari v1)

Menu opsi **"7. Marrow sintetis (pengganti darurat)"** selalu print flag
salah (`TecFest26{false_moon_marrow_is_not_columbina}`) **tanpa butuh
eksploitasi apapun** -- menjebak enumerasi membabi-buta/AI yang coba semua
opsi dan declare "berhasil" di string pertama yang mirip flag. String literal
ini tetap ada di binary walau sudah di-strip (strip cuma hapus symbol table,
bukan string di `.rodata`) -- peserta yang `strings` attachment akan tetap
lihat flag salah ini, by design, sama seperti v1.

## Gotcha penting saat nulis solver (atau kalau mau ubah manual)

Saat kirim payload raw (opsi 3 "ukir ulang nama" ATAU opsi 5 "tulis entri
Luonnotar"), **jangan** pakai `sendlineafter`/`sendline` (otomatis nambah
`\n` di akhir). C code-nya baca RAW persis N byte pakai `read()`, newline
ekstra dari `sendline` akan ketinggalan di buffer socket dan "nyasar" jadi
input menu berikutnya. Solusi: `io.recvuntil(prompt); io.send(payload_raw)`.

Untuk opsi 5 ("tulis entri Luonnotar"), `panjang` SEKARANG bisa `0`
(ditambahkan di v2, dulu selalu fix 40 byte) -- dipakai khusus buat langkah
"konsumsi tanpa menulis" di teknik tcache poisoning (langkah 5 di atas).
Kalau `panjang=0`, program **tidak** nge-print prompt `"entri (N byte, raw):
"` dan **tidak** memanggil `read()` sama sekali (lihat source: `if (len > 0)
{ ... }`) -- jangan kirim byte apa pun setelah `panjang=0`, langsung lanjut
ke menu choice berikutnya.

## Hosting

- Port: `40501`. Flag dari file `flag` (bind mount `:ro`). Socat tanpa `pty`.
- CMD dibungkus `sh -c "ulimit -c 0; exec socat ..."` (sama seperti v1).

## Cara test ulang

**Catatan infra (14-15 Nov):** `deploy_pwn.sh` dijalankan lewat WSL
(`kali-linux`) gagal dengan `docker: 'compose' is not a docker command'` /
`Failed to initialize: protocol not available` -- WSL kali-linux punya
install `docker` CLI sendiri yang terpisah dari Docker Desktop (tidak ada
plugin compose, tidak konek ke daemon Desktop). **Workaround yang terbukti
jalan:** jalankan bagian `docker compose`/`docker cp`/`docker exec` langsung
dari **Git Bash (Windows)**, bukan `wsl.exe`, dan HANYA pakai WSL untuk
`nm`/`strip`/`zip` (butuh binutils Linux asli, lihat alasan di header
`deploy_pwn.sh`) lewat script kecil terpisah yang di-pass path lengkap
(hindari nested quoting `wsl.exe -- bash -c "..."` dari Git Bash, gampang
pecah -- tulis ke file `.sh` dulu, baru `wsl.exe -d kali-linux -- bash
/path/ke/file.sh`).

```bash
# dari Git Bash, di folder pwn_columbina/
docker compose down && docker compose build --no-cache && docker compose up -d
docker cp pwn_columbina-columbina-1:/home/columbina_pwn/columbina bin/columbina
LIBC=$(docker exec pwn_columbina-columbina-1 readlink -f /lib/x86_64-linux-gnu/libc.so.6)
LD=$(docker exec pwn_columbina-columbina-1 readlink -f /lib64/ld-linux-x86-64.so.2)
docker cp pwn_columbina-columbina-1:$LIBC bin/libc.so.6
docker cp pwn_columbina-columbina-1:$LD bin/ld-linux-x86-64.so.2
# lalu dari WSL: nm (freeze ADDR_WIN ke addrs.py) -> strip bin/columbina in-place -> zip dist/
python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40501
python3 solve.py   # test lokal non-Docker, pakai bin/columbina + bin/libc.so.6 + bin/ld-linux-x86-64.so.2
```

**Hasil test (2026-11-15, revisi v2):**
- Lokal (via `ld-linux-x86-64.so.2 --library-path . ./columbina`): berhasil,
  flag `TecFest26{body_soul_authority_columbina_returns}`.
- Remote (5x koneksi berturut-turut ke container Docker asli port 40501,
  masing-masing heap/ASLR baru): **5/5 berhasil**, flag identik, alamat heap
  berbeda tiap koneksi.
- Chaff (opsi 7): tetap print flag salah tanpa eksploitasi, dites manual.
- NULL-deref (slot belum pernah dibuat, opsi 4): koneksi putus bersih
  (SIGSEGV internal container), **container tetap `Up`**.
- Slot index invalid (opsi 4, `idx=99`): ditolak rapi (`"slot invalid."`),
  tidak crash.
- `ulimit -c` terkonfirmasi `0` di dalam container, TIDAK ada file `core*`
  yang numpuk setelah crash paksa.

**Debugging note penting (supaya tidak keulang kalau re-desain lagi):**
Percobaan pertama teknik ini (versi 2 fragmen: 1 sacrificial + 1 target,
tanpa fragmen ke-3) **tidak crash tapi JUGA tidak berhasil** -- "uji
otoritas" tetap panggil `otoritas_fana` default, bukan `win()`. Root cause:
`count` cuma 1 setelah SATU kali free, jadi pop KEDUA (yang seharusnya ambil
`target` hasil racun) skip tcache sama sekali karena `count=0`. Simtom
"tidak crash, tidak berhasil" ini KHAS untuk bug off-by-count di tcache
poisoning -- beda dari overflow/UAF biasa yang biasanya langsung crash kalau
salah. Kalau re-desain exploit heap serupa di masa depan, selalu hitung
berapa kali tcache akan di-pop dari bin yang sama, dan pastikan jumlah chunk
yang di-free CUKUP (bukan cuma "ada 1 chunk buat racun").

**Hasil test (2026-11-15, revisi v2.1 -- setelah fix pembatasan panjang opsi 5):**
- Jalan pintas v1 (opsi 5 `panjang=40` langsung timpa `otoritas` di SATU
  chunk yang direuse, tanpa fragmen ke-3/UAF-write/leak): **ditolak**
  (`"panjang invalid."`) -- dites ulang di panjang 17/32/40, semua ditolak.
- Teknik v2 (3 fragmen + UAF-write + tcache poisoning, panjang maks dipakai
  cuma 8): **tetap 5/5 berhasil** lewat network setelah fix, flag identik,
  alamat heap berbeda tiap koneksi. `solve.py` diupdate (prompt
  `"(0-40): "` -> `"(0-16): "`, logika solve tidak berubah).
- Chaff, NULL-deref, slot invalid, `ulimit -c`: dites ulang, semua masih
  seperti sebelumnya (lihat hasil test v2 di atas).
- Attachment (`dist/columbina_attachment.zip`) dibangun ulang dari binary
  v2.1 yang sudah di-strip -- byte-identik dengan `bin/columbina` v2.1.

## Attachment peserta

`dist/columbina_attachment.zip` isi 3 file (sama seperti v1, tidak berubah):
`columbina` (di-`strip --strip-all`), `libc.so.6`, `ld-linux-x86-64.so.2` --
kedua file glibc diekstrak langsung dari image Docker yang sama (dijamin
match dengan yang dipin via digest). Peserta WAJIB pakai libc yang dibagikan
ini (bukan libc sistem mereka) -- v2 makin menuntut ini karena safe-linking
behavior (termasuk apakah aktif sama sekali) bisa beda antar versi glibc.
Jalankan lokal dengan `./ld-linux-x86-64.so.2 --library-path . ./columbina`
(perlu `chmod +x` semua, exec bit tidak terbawa lewat zip Windows).
