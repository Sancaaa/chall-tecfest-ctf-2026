# Notes — pwn_istaroth (Binary Exploitation E)

Status: **v2 (ret2libc), fungsional & teruji** (local process via ld-linux+libc
yang dipin, DAN 5x koneksi network berturut-turut ke container Docker asli,
semua balas flag yang sama; payload salah sengaja dikirim juga -- crash bersih,
tidak ada core dump, container tetap `Up`).

## Kenapa direvisi dari v1

v1 (ret2win) kelihatan "Hard" di cerita (PIE on, "multi-stage ROP & shell" di
CSV) tapi secara teknis lemah: leak tahap 1 langsung ngasih alamat `win()`
yang SUDAH SIAP PAKAI (cuma `execve("./catflag", ...)`), jadi tahap 2 cuma
"ret ke satu alamat fungsi yang disediakan" -- tidak ada ROP chain beneran.
Hasil blackbox test independen (`TESTING_PWN/pwn_istaroth/WRITEUP.md`) dan
review solver menyimpulkan ini **Easy-Medium**, bukan Hard -- malah lebih
enteng dari Ei (yang butuh probing live) karena leak-nya "gratis" dan stabil
antar koneksi.

**v2** menghapus `win()`/`decoy_win()` sepenuhnya. Tidak ada fungsi siap pakai
di binary ini lagi -- peserta harus bangun **ROP chain ret2libc beneran**:
leak alamat `puts()` (libc asli, bukan PLT stub) + leak alamat string
`"./catflag"` (PIE, binary sendiri) di tahap 1, lalu cari gadget `pop rdi; ret`
di `libc.so.6` yang dibagikan, hitung alamat `system()` dari base libc hasil
leak, dan rangkai `system("./catflag")` di tahap 2. Ini genuinely menuntut
skill ret2libc (leak ganda, baca symbol table libc eksternal, pahami kenapa
`&puts` di kode C PIE/PIC itu alamat ASLI libc -- bukan alamat trampolin PLT
di binary sendiri -- lewat relokasi `GLOB_DAT`, beda dari `call puts@plt`
yang lewat `R_X86_64_JUMP_SLOT`/PLT lazy binding).

## Environment build

- Base image: `ubuntu:22.04`, dipin via digest
  `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11`
- gcc: `11.4.0`, glibc: `2.35`. Binary **dan** `catflag` dikompilasi di dalam
  Dockerfile. `catflag` masih dipakai sama seperti v1 -- `system("./catflag")`
  akan fork+exec `/bin/sh -c "./catflag"` relatif ke `cwd` proses
  (`/home/istaroth_pwn`), efeknya identik dengan `execve("./catflag",...)`
  v1 (shell tetap dibatasi ke `catflag`, TIDAK pernah dapat `/bin/sh` bebas --
  argumen `system()` yang kita kontrol adalah string `"./catflag"`, bukan
  `"/bin/sh"`).

## Struktur folder

Sama seperti v1 (`bin/` source+test lokal, `flag.txt`/scaffolding di dir
utama, `dist/` attachment peserta) -- **TAPI sekarang `dist/` juga berisi
`libc.so.6` + `ld-linux-x86-64.so.2`** (baru di v2, lihat bagian Attachment).

## Compile command

```
gcc -O0 -m64 -fno-stack-protector -pie -fPIE -o bin/istaroth bin/istaroth.c
gcc -O0 -m64 -fno-stack-protector -no-pie -o bin/catflag bin/catflag.c
```

`checksec` (istaroth): Partial RELRO, **No canary** (disengaja -- lihat
"Kenapa canary tetap off" di bawah), NX enabled, **PIE enabled**.

## Teknik (desain v2)

- **Tahap 1 — data-only unlock, dibungkus struct (bukan local var lepas):**
  `vuln()` punya `struct frame { char buf[64]; int unlocked; } f;`. Karena
  `unlocked` adalah FIELD struct (bukan local var terpisah), posisi
  relatifnya ke `buf` DIJAMIN oleh tata letak struct C (offset 64 persis,
  `offsetof(struct frame, unlocked) == 64`, dicek via objdump -- `64` sudah
  kelipatan 4 jadi tidak ada padding sebelum `int`). Ini LEBIH ROBUST dari
  v1 (yang pakai 2 local var lepas, offset-nya 76 byte, dan desain itu
  CUMA jalan karena canary OFF -- GCC `-fstack-protector` bisa menata ulang
  local var lepas, tapi TIDAK BISA menata ulang field dalam satu struct).
  Overflow `f.buf` 64+4=68 byte cukup buat menimpa `f.unlocked` jadi nonzero,
  **tanpa** menyentuh saved-RBP/return-address.
- **Leak tahap 1 (BARU, inti revisi):** begitu `unlocked`, `main()` nge-print
  `printf("ramalan: %p %p\n", (void*)puts, (void*)CATFLAG_PATH)`:
  - `%p` pertama = `(void*)puts` -- alamat INI DIRESOLVE lewat GOT
    (`R_X86_64_GLOB_DAT`, diisi eager oleh dynamic linker sebelum `main()`
    jalan, KARENA mengambil alamat fungsi eksternal sebagai *data pointer*,
    bukan men-*call* dia) -- jadi nilainya ALAMAT ASLI `puts()` di
    `libc.so.6` yang jalan, BUKAN alamat trampolin `puts@plt` di binary ini.
    Dikonfirmasi via `objdump`: instruksinya `mov rax,[rip+...] # <puts@GLIBC_2.2.5>`
    (load dari GOT), bukan `call puts@plt`.
  - `%p` kedua = `(void*)CATFLAG_PATH` -- alamat string `"./catflag"` di
    `.rodata` BINARY INI (PIE, base sudah ikut lewat alamat ini) -- dipakai
    LANGSUNG sebagai argumen tahap 2, tidak perlu hitung base PIE terpisah
    (satu-satunya kebutuhan PIE-defeat di soal ini cuma buat string argumen,
    bukan buat gadget -- gadget semua diambil dari `libc.so.6`).
- **Tahap 2 — ROP chain ret2libc beneran:** offset ke return address = 88
  byte (`sub rsp,0x50` = 80 byte frame + 8 byte saved RBP, dicek objdump,
  SAMA dengan v1 walau struct-nya beda cara deklarasi -- compiler tetap
  alokasi 0x50 byte). Payload:
  ```
  'B'*88 + p64(ret_gadget) + p64(pop_rdi_ret) + p64(catflag_str_addr) + p64(system_addr)
  ```
  `ret_gadget` = 1 gadget `ret` polos dari `libc.so.6` (fix alignment movaps
  -- pola SAMA seperti Mavuika/Istaroth-v1, lihat `CHALLENGE_DAN_HOSTING.md`
  2.4). `pop_rdi_ret` = gadget `pop rdi; ret` dari `libc.so.6` (byte `5f c3`,
  dicari lewat `libc.search(asm("pop rdi; ret"))`). `system_addr` =
  `libc.symbols["system"]` + base libc hasil hitung dari leak `puts()`.
- **Kenapa TETAP `system("./catflag")`, bukan `system("/bin/sh")`:** string
  argumen yang kita kontrol berasal dari `.rodata` BINARY INI (`"./catflag"`),
  bukan string `"/bin/sh"` yang ada di `libc.so.6` sendiri (teknik ret2libc
  klasik lain yang TIDAK dipakai di sini, sengaja). Ini menjaga requirement
  CSV Notes Author ("shell dibatasi catflag") tetap terpenuhi TANPA perlu
  infra tambahan (ganti `/bin/sh` di container, dsb.) -- exploit secara
  struktural tidak pernah punya jalan untuk memanggil `system("/bin/sh")`
  kecuali peserta sengaja mengganti argumen string (yang berarti mereka
  harus leak/temukan string `/bin/sh` sendiri dari `libc.so.6` -- masih
  technically possible tapi di luar jalur yang "dikasih" soal).

## Kenapa canary TETAP off (dipertimbangkan ulang saat revisi, tetap OFF)

Sempat dipertimbangkan nyalain ulang canary (biar cocok definisi "full
modern" di `BINEXP_PLANNING.md`), TAPI diputuskan tetap OFF karena:

1. **Trik struct (lihat di atas)** sudah menghilangkan alasan TEKNIS lama
   kenapa canary mengganggu desain v1 (reorder local var) -- jadi canary ON
   secara TEKNIS sekarang mungkin dicoba lagi kalau mau.
2. **TAPI** canary ON butuh leak nilai canary juga supaya solver bisa taruh
   byte yang benar di offset yang benar sebelum saved-RBP -- dan TIDAK ADA
   cara leak canary dalam desain ini tanpa primitive baca-memori tambahan
   (byte-brute-force antar-koneksi TIDAK applicable di sini karena setiap
   koneksi socat men-`EXEC:` proses BARU [bukan in-process `fork()`], jadi
   canary beda tiap koneksi -- lihat diskusi di `CHALLENGE_DAN_HOSTING.md`).
   Cara satu-satunya adalah nambah leak ketiga (print nilai canary juga),
   yang berarti menumpuk SATU skill lagi (canary bypass) di atas 2 skill yang
   sudah ada (PIE-defeat ganda + ROP chain ret2libc) -- ini PERSIS alasan
   yang sudah ditulis di `Dockerfile` SEBELUM revisi ini ("fokus Hard di
   soal ini adalah PIE-defeat + ROP chain, bukan brute-force canary").
   Diputuskan dipertahankan: 2 skill (PIE-defeat ganda + ret2libc) sudah
   cukup untuk level Hard dibanding Furina/Sandrone (Medium, 0 leak), dan
   menambah canary-bypass berisiko soal jadi terlalu berat/frustrasi untuk
   CTF internal klub (bukan CTF nasional).

## Chaff flag (desain v2 -- BERUBAH dari v1)

v1: `decoy_win()` ditaruh BERSEBELAHAN dengan `win()` di source, supaya
alamatnya ikut shift bareng base PIE -- solver yang salah hitung OFFSET
tahap 2 nyasar ke sini dan dapat flag salah secara ALAMI (reachable via
jalur exploit yang mirip tapi offset keliru).

v2 TIDAK punya mekanisme "reachable via kesalahan serupa" itu lagi, karena
jenis "kesalahan alami" di ret2libc beda karakternya: kalau peserta salah
hitung base libc / gadget / argumen, hasilnya hampir selalu SIGSEGV
(connection drop), BUKAN "ketemu alamat lain yang juga valid dan reachable".
Tidak ada cara murah untuk membuat decoy yang reachable secara alami di
sini tanpa menambah mekanisme buatan yang terasa dipaksakan.

`decoy_notice()` dipertahankan sebagai fungsi, TAPI sekarang MURNI
string-trap (`strings`/`grep` doang, TIDAK reachable dari exploit manapun) --
sama dengan pola yang sudah dipakai Ei/Furina (yang juga tidak punya decoy
reachable, hanya Istaroth v1 & Columbina yang punya versi "adjacency").
Trade-off ini diterima karena fokus Hard sudah dipenuhi lewat teknik
eksploitasi itu sendiri (ROP chain ret2libc), bukan lewat jebakan flag.

## Hosting

- Port: `40601`. Flag dari file `flag` (bind mount `:ro`). Socat tanpa `pty`.
- `catflag` ikut di-copy & dikompilasi di image yang sama, permission `550`.
- CMD dibungkus `sh -c "ulimit -c 0; exec socat ..."` (sama seperti v1).
- **BARU:** `libc.so.6` + `ld-linux-x86-64.so.2` sekarang ikut di-extract dari
  container (lihat `deploy_pwn.sh`, `NEEDS_LIBC` diubah dari `0` jadi `1`
  khusus untuk soal ini) -- dibutuhkan untuk solve.py (hitung offset
  puts/system/gadget) DAN wajib ikut `dist/istaroth_attachment.zip` (lihat
  bagian Attachment) karena exploit sekarang bergantung ke versi glibc exact.

## Cara test ulang

```
bash deploy_pwn.sh istaroth   # dari WSL -- rebuild, extract bin+libc+ld baru, strip, zip ulang
python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40601
python3 solve.py   # test lokal non-Docker, pakai bin/istaroth + bin/libc.so.6 + bin/ld-linux-x86-64.so.2
```

**Hasil test (2026-11-14, revisi v2):**
- Lokal (via `ld-linux-x86-64.so.2 --library-path . ./istaroth`): berhasil,
  flag `TecFest26{s33dS_0F_S70r13S_8R0u9h7_8y_7H3_W1Nd_aND_cUl71va73d_8Y_71m3}`.
- Remote (5x koneksi berturut-turut ke container Docker asli port 40601,
  masing-masing proses/ASLR baru): **5/5 berhasil**, flag identik, alamat
  leak berbeda tiap koneksi (dikonfirmasi ASLR genuinely aktif & genuinely
  dikalahkan tiap kali, bukan hardcoded).
- Payload tahap 2 yang SENGAJA salah (alamat sampah `0xdeadbeefdeadbeef`):
  koneksi putus bersih (SIGSEGV internal container), **container tetap
  `Up`**, `ulimit -c` terkonfirmasi `0` di dalam container, TIDAK ada file
  `core*` yang numpuk setelah crash paksa.

## Attachment peserta (PENTING, berubah dari v1)

`dist/istaroth_attachment.zip` sekarang isi **3 file** (dulu cuma 1):
`istaroth` (di-`strip --strip-all`), `libc.so.6`, `ld-linux-x86-64.so.2` --
kedua file glibc diekstrak langsung dari image Docker yang sama (dijamin
match dengan yang dipin via digest, sama persis pola yang sudah dipakai
Columbina). Peserta WAJIB pakai libc yang dibagikan ini (bukan libc sistem
mereka) karena exploit bergantung ke offset `puts`/`system`/gadget yang
spesifik ke versi 2.35-0ubuntu3.18 ini. Jalankan lokal dengan
`./ld-linux-x86-64.so.2 --library-path . ./istaroth` (perlu `chmod +x`
semua, exec bit tidak terbawa lewat zip Windows). `catflag` TETAP TIDAK
disertakan (helper server-side saja, sama seperti v1).

String `CHAFF_FLAG` (`TecFest26{close_but_wrong_check_your_chain}`) tetap
ada secara literal di binary (walau sudah di-strip -- strip cuma hapus
symbol table, bukan string literal), by design (strings-trap, lihat bagian
Chaff di atas). Rebuild ulang? Jalankan `bash deploy_pwn.sh istaroth` dari
WSL -- otomatis extract bin+libc+ld baru, strip in-place, dan re-zip
`dist/istaroth_attachment.zip` dari file yang sama.
