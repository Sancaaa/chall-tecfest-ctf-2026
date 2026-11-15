# Binary Exploitation — Rencana Konsep (A–F)

> **Update:** ke-6 binary sudah diimplementasikan, dikompilasi, dan diuji end-to-end (proses lokal + container Docker asli via koneksi network) di folder `pwn_sandrone/`, `pwn_mavuika/`, `pwn_furina/`, `pwn_ei/`, `pwn_istaroth/`, `pwn_columbina/`. Detail compiler/libc/bug yang ditemukan saat testing ada di `NOTES.md` masing-masing folder. Narasi/gimmick **belum** ditambahkan (sengaja) — baru fungsional inti sesuai topik CSV.

Dokumen rencana/konsep untuk 6 slot Binary Exploitation (lihat CSV, kategori `Binary Exploitation`). Status, flag final, dan solver tetap dicatat di CSV + folder author masing-masing (lihat `CHALLENGE_DAN_HOSTING.md` bagian 1.5–1.6).

Konvensi folder mengikuti challenge yang sudah ada (`crypto_nahida`, `re_naberius`, `misc_asmoday`): satu folder per soal, isi `Desc.txt` (deskripsi peserta), `Clue.txt` (hint bertingkat), `Dockerfile` + `docker-compose.yml`, `flag.txt`/`secrets/flag`, `solve.py`, `WRITEUP.md`. Semua 6 slot dipasang sebagai service `nc` (lihat `CHALLENGE_DAN_HOSTING.md` 2.4). 5 dari 6 slot **plus** attachment binary — peserta diberi alamat `nc host port` **dan** binary untuk reverse/hitung offset sendiri (offset return address/variabel pada soal overflow adalah properti statis stack frame, tidak masuk akal diminta "diramal" tanpa binary). Attachment = binary saja untuk A/B/C/E (Sandrone/Mavuika/Furina/Istaroth); Columbina (F) butuh binary + `libc.so.6` + `ld-linux-x86-64.so.2` yang sama persis dengan image Docker (heap exploitation sensitif ke versi glibc). **Kecuali D (Ei, format string): sengaja nc-only, tanpa attachment** — offset vararg printf dan alamat target bisa 100% ditemukan lewat probing `%N$p` di koneksi live (lihat `pwn_ei/readme`), beda dengan soal overflow yang offset-nya cuma kebaca dari disassembly binary. Attachment final ada di `dist/*_attachment.zip` tiap folder `pwn_*/` (kecuali `pwn_ei/`) dan dicatat di kolom `Attachment` CSV.

---

## A — Sandrone (Medium) — Sanca — **In Progress** (CSV)

- **Revisi tingkat kesulitan (v1):** awalnya Easy (sejajar B/Mavuika), tapi shellcode injection butuh skill ekstra di atas ret2win (nulis/generate shellcode + paham NX/stack executable), bukan cuma "cari offset & return address" — di taksonomi pwn umum ini biasanya 1 tingkat di atas ret2win murni. Dinaikkan ke Medium, slot Easy D (Ei) ditukar turun untuk gantinya (lihat alasan di bagian D).

- **Revisi teknik (v2, 14 Nov):** begitu dibandingkan langsung vs Furina (sama-sama "Medium"), v1 ternyata jauh lebih mekanis — leak dikasih gratis, satu tembakan `shellcode+padding+alamat`, tanpa insight tambahan (beda dari Furina yang butuh reverse 2 menu handler + hitung index + chaining). Supaya difficulty-nya benar-benar sebanding, teknik intinya ditambah **badchar-free XOR payload encoding**, mengikuti metode kombinatorial di makalah "Badchar-Free XOR Payload Encoding in Binary Exploitation" (Justin Sepvian, ITB, 2026) — lihat `pwn_sandrone/WRITEUP.md` buat detail lengkap (set theory + GF(2^8) + PIE + decoder stub teknik JMP/CALL/POP).
- **Alasan revisi awal (v1):** supaya ada 1 soal Easy yang teknik intinya genuinely beda (shellcode injection), bukan cuma reuse kode yang sudah ada (ret2win). Ret2win dipindah ke B (sekarang Mavuika, lihat bawah).
- **Topik:** Shellcode injection — NX **off** — + badchar-free XOR payload encoding (v2).
- **Konsep (v2):** Binary C 64-bit punya **dua channel input** di fungsi vuln: (1) "payload diagnostik" lewat `fgets()+strcpy()` — badchar `0x00`/`0x0a` muncul NATURAL dari cara kerja 2 fungsi ini, bukan filter buatan; shellcode yang mau dieksekusi wajib lewat sini, jadi wajib di-XOR-encode dulu (+ decoder stub posisi-independen, badchar-free juga) supaya lolos; (2) "kontrol overflow" lewat `read()` mentah, tanpa sanitasi — dipakai buat overwrite return address asli (return address = alamat stack, hampir pasti punya byte NUL, jadi TIDAK boleh lewat channel yang disanitasi).
- **Protections:** NX **off** (ciri khas soal ini), canary off, PIE off, partial RELRO.
- **Catatan ASLR (wajib dibaca sebelum implementasi):** NX off doang tidak membuat alamat buffer predictable — stack tetap kena ASLR walau PIE off (PIE cuma soal alamat kode binary). Supaya tetap deterministik tanpa perlu disable ASLR level kernel (butuh privileged container, bentrok dengan isolasi non-root yang dipakai di soal lain), **binary sendiri yang leak alamat buffer ke peserta** (print singkat "debug: buffer di 0x...") sebelum menerima input. Ini tetap mengajarkan primitive yang sama, cuma menghindarkan brute-force address yang tidak reliable buat QA.
- **Intended solution (v2):** leak alamat `buf`, turunkan alamat `payload` (offset statis, dicek `objdump`); cari key XOR valid buat shellcode (set theory/PIE, lihat WRITEUP); rakit decoder stub (JMP/CALL/POP) + shellcode terenkode, kirim lewat channel 1; kirim padding + alamat `payload` lewat channel 2 (overwrite return address mentah).
- **Info yang dibocorkan ke deskripsi:** "64-bit, C, no PIE, **NX off**, ada 2 tahap input" — disebut eksplisit biar peserta tahu arahnya shellcode (bukan ret2win), tanpa membocorkan soal badchar/XOR-nya langsung (biar ketemu sendiri dari probing, sama seperti clue tier-1 soal lain).
- **Catatan hosting (penting):** karena ini genuine arbitrary code execution (bukan cuma reuse existing function seperti ret2win), level isolasi per koneksi disamakan dengan E/F — lihat checklist di bawah (jail per koneksi + kode yang dieksekusi dibatasi, bukan full interactive shell polos di container biasa).

## B — Mavuika (Easy) — Sanca

- **Status CSV saat ini:** `Not Started`. Slot ini sekarang milik Sanca sepenuhnya (Agus tidak lagi punya slot di kategori Binary Exploitation — lihat rekap author di CSV).
- **Topik CSV:** Ret2win klasik. Overflow return address, lompat ke `win()` yang gak pernah dipanggil normal flow.
- **Protections:** NX on (beda dari A yang NX off, supaya dua-duanya tetap kerasa beda), canary off, PIE off.
- **Intended solution:** cari offset overflow (cyclic/pattern), temukan alamat `win()` (statis karena no-PIE), payload `padding + win_addr`.
- **Info yang dibocorkan ke deskripsi:** "64-bit, C, no PIE".

## C — Furina (Medium) — Sanca — **direvisi**

- **Alasan revisi:** versi awal (ret2win + calling convention) mekanismenya nyaris identik dengan A (sama-sama "overflow → kontrol return address → lompat ke fungsi"), cuma ditambah langkah isi register. Supaya tiap soal mengajarkan primitive yang benar-benar beda, root cause-nya diganti.
- **Topik baru:** **OOB array index → arbitrary write (write-what-where) → hijack GOT/dispatch-table → tetap harus panggil `win()` dengan calling convention benar.**
- **Konsep:** binary punya array pointer fungsi (`verdicts[]` — "catatan takdir"/ledger putusan) yang dipilih lewat index dari input peserta **tanpa bounds check**. Index di luar rentang menyentuh memory lain (write-what-where ringan) yang bisa dipakai menimpa salah satu entry GOT (atau entry `verdicts[]` itu sendiri) supaya pemanggilan berikutnya lompat ke `win()`. `win(a,b,c)` tetap minta argumen spesifik di register (`rdi`/`rsi`/`rdx`) — tujuan belajar "calling convention" dari CSV tetap terpakai, cuma jalan masuknya beda total dari A.
- **Protections:** NX on, PIE **off** (supaya alamat GOT/dispatch table predictable, tetap "medium"), canary boleh on sebagai red herring (bukan bug utamanya stack overflow, jadi canary tidak langsung relevan — ini sendiri bisa jadi sinyal ke peserta bahwa bug-nya bukan stack smash biasa).
- **Intended solution:** temukan index legal-tapi-di-luar-maksud-author yang menyentuh target overwrite, hitung offset ke GOT/dispatch entry, tulis alamat `win()`, siapkan argumen sesuai ABI di request berikutnya, trigger pemanggilan ulang supaya lompat ke `win()` dengan argumen benar.
- **Info yang dibocorkan ke deskripsi:** "64-bit, C, no PIE, ada tabel verdict yang dipilih lewat nomor".
- **Catatan dari CSV:** sudah ditambahkan potongan lirik Furina (French, "Le monde n'est qu'une scène...") di kolom `Notes Author` — kemungkinan dipakai sebagai banner/hint di binary/`Clue.txt`; lihat CSV untuk teks lengkap, tidak diduplikasi di sini.

## D — Ei (Easy) — Sanca

- **Revisi tingkat kesulitan:** awalnya Medium, ditukar ke Easy (gantinya A/Sandrone naik ke Medium — lihat alasan di bagian A). Exploit-nya sebanding kompleksitasnya dengan ret2win: leak + satu `%n`-write ke satu variabel global, dan `fmtstr_payload()` (pwntools) merangkum konstruksi payload jadi hampir satu baris, sama ergonomisnya dengan `shellcraft` di soal lain. Cari offset-nya juga lebih aman buat pemula — probing `%p` tidak bisa crash service, beda dari cari offset overflow yang salah dikit bisa segfault.

- **Topik CSV:** Format string exploitation.
- **Konsep:** `printf(user_input)` langsung tanpa format specifier. Dua opsi tujuan (pilih satu saat implementasi): (1) leak nilai stack (canary/alamat) lewat `%p`/`%x` berantai; (2) `%n`-style write untuk overwrite variabel global yang dicek sebelum cetak flag.
- **Protections:** NX on, canary on (supaya leak format string berguna), PIE opsional (on = medium-plus, off = medium standar).
- **Intended solution:** identifikasi offset argumen vuln `printf` (coba `%1$p`, `%2$p`, …), susun payload leak dan/atau write (pwntools `fmtstr_payload`).
- **Info yang dibocorkan ke deskripsi:** "64-bit, C, ada fitur yang mencetak ulang input kamu" — cukup memberi sinyal tanpa menyebut "format string" langsung.

## E — Istaroth (Hard) — Sanca

- **Topik CSV:** Multi-stage ROP & shell.
- **Konsep:** tidak ada `win()` siap pakai; peserta bangun ROP chain dari gadget yang ada untuk `execve("/bin/sh", …)`/ret2libc. 2 tahap di koneksi `nc` yang sama: tahap 1 leak (bocorkan alamat libc/internal lewat `puts`/`write`), tahap 2 overflow penuh pakai info tahap 1.
- **Protections:** full modern (NX on, canary on, PIE on, partial/full RELRO) — PIE on berarti wajib leak dulu.
- **Shell terbatas:** begitu shell didapat, ganti `/bin/sh` dengan `catflag` (program kecil, cuma baca+print `flag.txt` lalu exit) — dikombinasikan isolasi per koneksi (nsjail/pwn.red jail) karena kategori ini paling berisiko kalau container escape.
- **Intended solution:** leak libc di tahap 1, hitung base, susun ROP chain tahap 2, dapat shell (dibatasi `catflag` di server lomba).
- **Info yang dibocorkan ke deskripsi:** minimal — "64-bit, C, full protections, versi libc server (angka)".

- **Chaff flag (dummy flag anti-tebakan/anti-AI-asal-pattern-match):** taruh 1 fungsi decoy (nama teknis netral dulu, misal `decoy_win()` — nama final menyusul) **tepat bersebelahan secara source** dengan `win()`/jalur execve asli, supaya otomatis ikut shift bersama base saat ASLR/PIE aktif (tidak perlu alamat fixed, jadi tidak bentrok dengan PIE on). Solver yang skip tahap leak (asal lompat ke alamat tebakan) atau yang leak-nya benar tapi **salah hitung offset** (kesalahan paling umum di ROP) nyasar ke fungsi decoy ini → print flag format valid (`TecFest26{...}`) tapi **salah**. Flag asli hanya keluar lewat `catflag` yang baca file saat runtime (flag asli **tidak** pernah di-hardcode di binary; flag palsu aman di-hardcode karena sengaja salah). Jangan masukkan flag palsu ke CTFd sebagai alternate-correct; catat di `Notes Author` CSV + `WRITEUP.md` biar tester tidak bingung.

## F — Columbina (Hard) — Sanca

- **Topik CSV:** Heap exploitation.
- **Konsep:** menu-based heap chall, primitive **Use-After-Free (UAF) + function pointer overwrite** (direkomendasikan dibanding House of Force/Orange yang sangat version-sensitive — UAF+func ptr paling deterministik buat solver yang direproduksi ulang saat QA).
- **Protections:** full modern + **glibc di-pin via digest** (sesuai `CHALLENGE_DAN_HOSTING.md` 2.4) supaya heap layout tidak berubah diam-diam saat rebuild mendekati hari-H.
- **Intended solution:** alokasi beberapa chunk, free salah satu (dangling pointer tersisa karena bug author), alokasi ulang ukuran sama supaya `malloc` kembalikan chunk sama, tulis function pointer baru lewat menu "edit", trigger "view" yang memanggil function pointer → lompat ke target hijack.
- **Info yang dibocorkan ke deskripsi:** versi glibc server + "64-bit, C, menu-based heap chall".
- **Chaff flag:** taruh 1 slot function-pointer decoy (nama teknis netral, misal `decoy_ptr` — nama final menyusul) **tepat bersebelahan** dengan slot function pointer asli di struct/vtable-nya. Kesalahan index off-by-one (sangat umum di heap/array chall) akan memanggil slot decoy ini → print flag format valid tapi salah. Index yang tepat → hijack pointer asli → `catflag` → flag asli dari file. Sama seperti E: flag asli tidak pernah di-hardcode; flag palsu tidak didaftarkan ke CTFd.

---

## Checklist implementasi per soal (ringkas dari `CHALLENGE_DAN_HOSTING.md` 1.6 + 2.4)

- [ ] `setvbuf(stdout, NULL, _IONBF, 0)` di awal `main()` — wajib di semua 6 soal supaya tidak macet lewat `nc`/`socat`.
- [ ] Bungkus binary dengan `socat TCP-LISTEN:PORT,fork,reuseaddr` (atau xinetd/jail template dari referensi di 2.4), satu port unik per soal.
- [ ] Flag **asli** di-mount read-only (`:ro`) di level Docker dan dibaca dari file saat runtime — **tidak pernah** di-hardcode di binary (berlaku untuk semua soal, krusial untuk E dan F yang punya chaff flag).
- [ ] Flag **palsu** (E, F) aman di-hardcode di source karena sengaja salah; dicatat jelas di `Notes Author` CSV + `WRITEUP.md`, **tidak** didaftarkan sebagai flag valid di CTFd.
- [ ] E dan F (yang bisa dapat shell/call arbitrary) pakai `catflag` pengganti `/bin/sh` + isolasi tambahan per koneksi (nsjail/pwn.red jail), bukan cuma container polos.
- [ ] **A (Sandrone)** sekarang genuine shellcode injection (arbitrary code execution, bukan cuma reuse existing function) — treat sama seperti E/F: isolasi per koneksi (nsjail/pwn.red jail), dan kalau shellcode mengarah ke shell, pertimbangkan tetap batasi lewat mekanisme serupa `catflag` supaya tidak ada interactive shell penuh yang nganggur selama 9 jam lomba di instance bersama.
- [ ] Base image di-pin via digest, terutama untuk F (heap, sensitif ke versi glibc).
- [x] Rename fungsi/variabel/teks yang terlihat peserta sebelum build (penamaan final/custom menyusul) — jangan sampai nama asli (`win`, `vuln`, dst.) kebocor di symbol/banner. **Sudah ada fix sementara:** binary di `dist/*_attachment.zip` sudah di-`strip` (symbol table dibuang total) sebelum dizip, khususnya krusial untuk Istaroth yang tadinya punya symbol literal `decoy_win` (langsung membocorkan chaff ke siapapun yang `nm`/`objdump` binary-nya). Source asli (`pwn_*/`) tetap pakai nama `win`/`vuln`/`decoy_win` untuk kemudahan maintenance author — hanya **attachment hasil strip** yang didistribusikan. Kalau mau rename manual lebih jauh (nama fungsi/string banner bertema), source masih bisa diedit lalu di-rebuild+strip ulang.
- [x] Solver `solve.py` per soal jalan end-to-end melawan instance Docker lokal, termasuk memverifikasi solver **tidak** kena chaff flag (untuk E, F), disimpan di folder author.
- [ ] Deskripsi tiap soal ditulis sebelum protections "dibuka" ke peserta — cross-check info yang dibocorkan tidak melebihi yang direncanakan di atas.
- [x] Tester (bukan author) solve dari deskripsi + koneksi `nc` + attachment binary (`dist/*_attachment.zip`, binary saja untuk A/B/C/E, binary+libc+ld untuk F) — **bukan** dari source `.c` (source tidak didistribusikan). D (Ei) dites solve hanya dari deskripsi + `nc`, tanpa attachment (lihat alasan di atas).
- [ ] Kalau nanti source di-rebuild ulang (misal setelah rename manual), **wajib** regenerasi `dist/*_attachment.zip` dari binary yang sudah di-strip lagi — jangan copy binary mentah dari build baru begitu saja.