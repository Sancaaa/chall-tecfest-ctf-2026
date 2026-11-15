# Challenge & Hosting — TecFest CyberSecurity 2026

Dokumen tunggal untuk dua hal: **(1)** cara challenge direncanakan, dibuat, dan di-QA; **(2)** cara challenge dipasang (host) ke platform CTF `WebTecFest`. Aturan lomba lengkap ada di `../Guidebook TecFest CyberSecurity.md`; dokumen ini tidak menggantikannya.

> **Sumber kebenaran status** ada di [`Challenge CTF TecFest 2026 - Chall.csv`](Challenge%20CTF%20TecFest%202026%20-%20Chall.csv). Status, flag, dan solusi sengaja tidak disalin ke sini supaya tidak basi dan tidak bocor. Dokumen ini hanya menyimpan hal yang stabil: aturan, struktur, dan prosedur.

---

## Bagian 1 — Challenge

### 1.1 Struktur 40 challenge

| Kategori (nilai di CSV) | Slot | Jumlah |
|---|---|---|
| Forensic | A–F | 6 |
| Cryptography | A–F | 6 |
| Reverse Engineering | A–F | 6 |
| Binary Exploitation | A–F | 6 |
| Web Explotation *(ejaan di CSV)* | A–F | 6 |
| Miscellaneous | A–F, plus `0`–`3` | 6 + 4 |
| **Total** | | **40** |

Slot `0`–`3` di Miscellaneous bukan challenge biasa: `0` adalah *sanity check* (100 poin, static), `1`–`3` adalah **easter egg** yang diimplementasikan di tema web (mini game mancing, ayam di scoreboard, kucing "Penguasa Challenge"), lihat bagian 2.6.

### 1.2 Tingkat kesulitan

Berlaku untuk **5 kategori** (Forensic, Cryptography, Reverse Engineering, Binary Exploitation, Web), **tidak untuk Miscellaneous**:

| Slot | Difficulty |
|---|---|
| A, B | Easy |
| C, D | Medium |
| E, F | Hard |

Ini sudah dicatat di kolom `Notes Author` CSV sebagai `Difficulty: Easy/Medium/Hard`. Misc dibebaskan karena isinya campur (OSINT, stego, puzzle, game, easter egg).

Implikasi: nilai poin sebaiknya mengikuti tingkat ini (Easy < Medium < Hard). Nilai poin per challenge **belum ditetapkan di berkas mana pun**, kecuali Misc `0` (100 poin static).

### 1.3 Pembagian author

Jumlah challenge per author menurut rekap CSV: Sanca 12, Marcell 7, Lele 6, Agus 6, Kelvin 6, Rahade 3 (total 40).

| Kategori | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| Forensic | Kelvin | Lele | Marcell | Marcell | Marcell | Marcell |
| Cryptography | Kelvin | Marcell | Kelvin | Marcell | Kelvin | Sanca |
| Reverse Engineering | Agus | Kelvin | Agus | Lele | Agus | Sanca |
| Binary Exploitation | Sanca | Sanca | Sanca | Sanca | Sanca | Sanca |
| Web | Lele | Agus | Lele | Rahade | Lele | Rahade |
| Misc | Marcell | Agus | Sanca | Kelvin | Lele | Rahade |

Misc `0`–`3`: Sanca. Sanca juga tercatat sebagai **Tester** untuk Reverse Engineering A.

Nama di CSV: `KelvinCrypto`, `MarcellForen`, `LeleWeb`, `AgusLinux`, `SancaPWN`, `RahadeMeow`.

### 1.4 Daftar challenge milik Sanca

| Kategori | Slot | Nama | Topik | Difficulty |
|---|---|---|---|---|
| Cryptography | F | Ronova | ECDSA biased nonce, Hidden Number Problem + lattice (LLL); convo AI disertakan sebagai attachment | Hard |
| Reverse Engineering | E | Naberius | Golang, custom VM + bytecode terenkripsi | Hard |
| Reverse Engineering | F | Rhinedottir | fork + ptrace, mesin rotor ala Enigma di atas 256 simbol | Hard |
| Binary Exploitation | A–F | (lihat CSV) | 6 slot, semua SancaPWN (B tidak lagi Agus) — nama/topik/difficulty final ada di CSV kolom `Nama Chall`/`Topik Chall`/`Notes Author` dan di `BINEXP_PLANNING.md`, sudah beda dari baris lama di tabel ini (mis. A bukan lagi "Nilou") | lihat CSV |
| Miscellaneous | C | Asmoday's Lost 13 Cubical Protocol | Rubik's cube / eigencube steganography | – |
| Miscellaneous | 0 | Emergency Food Check | Sanity check, 100 poin static | – |
| Miscellaneous | 1 | Misteri Kolam Keajaiban | Easter egg: mancing | – |
| Miscellaneous | 2 | Kandang Ayam Semesta | Easter egg: gacha ayam | – |
| Miscellaneous | 3 | Kucing Penguasa TecFest | Easter egg: selesaikan semua challenge | – |

Untuk status terkini lihat CSV (filter kolom `Author` = `SancaPWN`).

### 1.5 Kolom CSV dan siklus status

Kolom: `Kategori, Num, Nama Chall, Topik Chall, Author, Status, Intended Solution, Flag, Attachment, Tester, QA Status, Deployment Status, Notes Author, Notes Tester`.

Nilai yang dipakai saat ini:

- `Status` (author): `Not Started` → `In Progress` → `Review` → `Completed`
- `QA Status` (tester): `On Progress` → `Passed`
- `Deployment Status`: `Deployed`

Sebuah challenge dianggap **siap lomba** bila `Status = Completed`, `QA Status = Passed`, dan `Deployment Status = Deployed`. Pada saat dokumen ini ditulis, hanya Misc `1`–`3` yang memenuhi ketiganya. Perhatikan bahwa RE A dan Web B berstatus `Review` tetapi `QA Status` masih kosong (Web B bahkan belum punya Tester), dan kolom `Attachment` pada kedua baris itu berisi nama challenge, bukan nama berkas.

### 1.6 Checklist per challenge (definisi selesai)

Isi di CSV bila sudah ada, lalu centang:

- [ ] Nama, topik, kategori, dan difficulty sesuai slot (bagian 1.2)
- [ ] Deskripsi untuk peserta (tanpa membocorkan solusi); bila ada ilustrasi, taruh sebagai gambar
- [ ] Flag berformat `TecFest26{...}` dan tercatat di kolom `Flag`
- [ ] Intended solution tertulis di kolom `Intended Solution`
- [ ] Solver yang berjalan end-to-end (disimpan di folder author, bukan di attachment peserta)
- [ ] Attachment peserta sudah dibersihkan: tidak berisi flag, solver, path lokal, `.git`, atau metadata author
- [ ] Bila butuh service: image/server berjalan stabil, ada timeout, dan tidak bisa dipakai menyerang host
- [ ] Tester lain (bukan author) berhasil solve hanya dari attachment + deskripsi
- [ ] Solvable **tanpa scanning/fuzzing/brute force terhadap server** (dilarang di guidebook; peserta bisa didiskualifikasi). Untuk Web, semua petunjuk recon harus bisa ditemukan manual dan tidak menuntut wordlist besar. Challenge Web B ("file backup konfigurasi ter-expose") dan sejenisnya perlu dicek ulang terhadap aturan ini: sediakan petunjuk di deskripsi atau di halaman agar penemuan file tidak mengharuskan `ffuf`/`dirsearch`.
- [ ] Dipasang ke CTFd (bagian 2.3) dan dites ulang dari akun peserta di server lomba

### 1.7 Catatan desain dari guidebook

- Peserta boleh memakai AI (model whitelist: GPT-5.6 Instant, Claude Sonnet 5.5, Gemini 3.6 Flash, DeepSeek-V3.2) tetapi tanpa agent. Challenge yang terlalu mudah dikerjakan sekali tanya akan membuat skor tidak membedakan tim, jadi author sebaiknya mencoba mem-paste attachment ke model whitelist saat QA.
- Penilaian write-up menilai analisis dan kreativitas. Intended solution yang jelas membantu panitia memeriksa kesesuaian write-up.
- Panitia boleh memberi hint atau mengubah challenge lewat Open Ticket di Discord; siapkan hint bertingkat sejak awal.
- Dari 40 challenge, **5 challenge Bounty First Blood** harus ditunjuk. Belum ada catatan challenge mana yang dipilih.

---

## Bagian 2 — Hosting

### 2.1 Platform

`WebTecFest/` = **CTFd 3.8.8** (Docker) dengan tema kustom `tecart` dan dua plugin. Dokumentasi platform ada di `WebTecFest/README.md` dan `WebTecFest/PROJECT.md`; dokumen ini hanya merangkum yang relevan untuk memasang challenge.

| Komponen | Detail |
|---|---|
| Aplikasi | `ctfd/ctfd:3.8.8`, port host `8888` → container `8000` |
| Database | MariaDB 10.11 |
| Cache/event | Redis 4; `SERVER_SENT_EVENTS=true` untuk push notifikasi |
| Tema | `tecart` (retro pixel art) |
| Plugin `tecart_capture` | Tipe challenge `tecart`: submit **wajib** menyertakan link chat AI dan file solver/script (maks 64 MB); tiap submit direkam di tabel `tecart_captures` termasuk yang salah |
| Plugin `tecart_extras` | Freeze scoreboard, API easter egg, leaderboard mini game mancing |

Semua challenge yang masuk lomba harus bertipe **`tecart`**, kalau tidak, aturan submission (AI link + solver) tidak ditegakkan.

### 2.2 Menjalankan platform

Data yang ada di `WebTecFest/` saat ini hanya dummy untuk uji tampilan dan tidak didokumentasikan di sini. Platform akan di-host di infrastruktur terpisah milik Sanca. Untuk dev lokal, dari folder `WebTecFest/`:

```bash
docker compose up -d
```

Lalu buka `http://localhost:8888` dan `/admin`.

### 2.3 Memasang satu challenge ke CTFd

Lewat panel admin (`/admin/challenges`):

1. Buat challenge baru dengan tipe **tecart**.
2. Isi nama, kategori, deskripsi, poin. Ejaan kategori harus konsisten karena dipakai filter di halaman `/challenges`.
3. Tambah **Flag** (tipe static, case sensitive kecuali sengaja diubah) berformat `TecFest26{...}`.
4. Unggah **Files** (attachment peserta) dan/atau tulis alamat service (`nc host port` atau URL) di deskripsi.
5. Tambah **Hints** bila ada.
6. Set **Visibility**. Gunakan `hidden` untuk challenge Wave 2 sampai 14.30 WITA, lalu ubah ke `visible`.
7. Tes dari akun peserta: submit flag salah, submit flag benar dengan link AI + solver.
8. Isi `Deployment Status = Deployed` di CSV.

Catatan: guidebook menyebut **dynamic snapshot scoring**. Tipe `tecart` kini punya mode scoring **Snapshot** (default 500 → turun 50 per solve → minimum 100; poin dikunci saat submit, tidak turun lagi untuk yang sudah solve). Pilih di form **Admin → Challenges → New** (tipe wajib `tecart`) pada kolom **Scoring**: *Snapshot* (default; Initial/Decay/Minimum terisi 500/50/100) atau *Static* (isi Value). Bisa juga diubah di halaman Edit selama belum ada solve. Misc `0` (sanity check) tetap **Static** 100 poin. Mode tidak bisa diganti setelah challenge punya solve, jadi setel sebelum dibuka ke peserta. Jangan pakai Linear/Logarithmic bawaan CTFd: poin semua solver ikut turun.

### 2.4 Challenge yang butuh service (nc / web / pwn)

Platform CTFd hanya menyimpan file dan teks. **Tidak ada pengelola instance challenge** (seperti ctfd-whale atau container per tim) di repo ini.

Challenge yang hampir pasti butuh service:

- Cryptography A–F: semua pola attachment + oracle `nc` (dikonfirmasi berlaku ke 6 soal, bukan cuma punya Sanca).
- Binary Exploitation A–F (SancaPWN): service `nc` yang menjalankan binary. 5 dari 6 slot **plus** attachment binary untuk dianalisis offline (wajib untuk soal berbasis overflow — tanpa binary peserta tidak bisa reverse/hitung offset return address/variabel, itu properti statis stack frame). Attachment = binary saja untuk Sandrone/Mavuika/Furina/Istaroth; Columbina (heap UAF) butuh binary + `libc.so.6` + `ld-linux-x86-64.so.2` yang dipin sama seperti image Docker, karena exploit heap sensitif ke versi glibc.

**BASI, diganti revisi 14 Nov (lihat `pwn_ei/NOTES.md` & `pwn_ei/readme`):** paragraf ini tadinya bilang Ei dikecualikan dari attachment karena alamat `access_granted` di-leak live lewat `debug: access_granted @ %p`. Baris leak itu **sudah dihapus** dari `ei.c` — Ei **sekarang juga dapat attachment** (`dist/ei` + `dist/ei_attachment.zip`), peserta cari alamat `access_granted` sendiri lewat `nm`/`objdump`/gdb (no-PIE, statis). Binary Ei **tidak di-strip** (beda dari 5 soal lain) — itu sengaja, karena mekanisme soal memang mengharapkan peserta membaca nama simbolnya. Lihat `dist/*_attachment.zip` di masing-masing folder `pwn_*/` (termasuk `pwn_ei/` sekarang) dan kolom `Attachment` di CSV (kolom CSV untuk Ei masih kosong saat dokumen ini diperbaiki — perlu diisi).
- Forensic E: "bikinin nc, 7 pertanyaan" (MarcellForen); 1 soal forensic lain juga butuh `nc` tapi belum ditentukan slotnya di CSV (kandidat C/D/F).
- Web A–F: aplikasi web, satu container per soal, flag statis dibagi semua tim (state scoped session/cookie peserta) — kecuali Web D (lab Rahade), yang paling kompleks (lihat 2.3 untuk vuln chain-nya).
- Misc C: `server.py` (TCP, port `13337`, timeout 20 detik) di folder `[misc] asmoday`. Sudah ada `Dockerfile` dan `docker-compose.yml` (image hanya berisi `server.py`, ada batas koneksi per IP dan total); belum diuji build karena Docker belum dinyalakan saat ditulis.
- Misc E ("All-in Or Nothing", poker): web, satu container.

**Infrastruktur hosting sudah diputuskan** — 5 node (VPS-A edge/LB, VPS-B CTFd, Homelab-1 16c/16GB Proxmox untuk soal yang beri shell/RCE, Homelab-2 8GB/4core baru untuk soal tanpa shell, Raspi5 ARM untuk backup+monitor). Detail peran tiap node, pemetaan soal ke node, dan model ancaman lengkap ada di `ARSITEKTUR_INFRA_DAN_ANCAMAN.md` (dokumen sensitif, jangan dipublikasikan). Pola di bawah ini (Dockerfile/compose per soal, socat, dst.) tetap berlaku di kedua homelab.

Pola hosting yang disarankan, digabung dari diskusi sebelumnya dan riset praktik komunitas CTF:

- Satu VM/VPS terpisah dari host CTFd, supaya eksploitasi challenge tidak menyentuh database lomba.
- Satu folder per challenge dengan `Dockerfile` + `docker-compose.yml` sendiri — **wajib ada setup lokal** supaya solver dan QA bisa direproduksi di environment yang identik dengan server — port unik per challenge, `restart: unless-stopped`, batas CPU/memori/proses, user non-root.
- Deploy ke node pakai **2 repo GitHub privat** (punya pribadi Sanca sebagai problem-setter): `Sancaaa/web-tecfest-ctf-2026` buat `WebTecFest/`, dan `Sancaaa/chall-tecfest-ctf-2026` buat **semua** folder soal (satu folder per soal di dalam repo yang sama, bukan repo terpisah per soal) + deploy key read-only per node — bukan `scp` manual. Karena repo privat ini murni dokumentasi/deploy pribadi, tidak perlu exclude flag/solusi — upload apa adanya. Node yang cuma butuh sebagian folder (terutama VM Proxmox yang sengaja dikasih lubang shell/RCE) pakai sparse-checkout supaya flag soal lain tidak ikut ter-clone ke VM itu. Pattern lengkap ada di `WebTecFest/deploy/warmup-setup/README.md` bagian 0b.
- **Pin base image Docker lewat digest** (bukan tag `latest`/versi pendek), supaya rebuild mendekati hari lomba tidak diam-diam mengubah environment (glibc, dsb).
- Pwn: bungkus binary dengan `socat TCP-LISTEN:PORT,fork,reuseaddr` (atau xinetd) agar tiap koneksi dapat proses sendiri. **Mount flag read-only** di level Docker (`:ro`), bukan cuma andalkan permission file — root di dalam container bisa override permission, tapi tidak bisa override mount read-only. Untuk soal yang berujung shell (Istaroth/E), pertimbangkan ganti `/bin/sh` dengan program terbatas (`catflag`) yang hanya bisa baca flag lalu keluar, bukan shell interaktif penuh.
- **Container saja bukan boundary yang cukup** untuk soal RCE/shell kalau container punya privilege ekstra — tambahkan isolasi per koneksi (rootfs read-only, tanpa akses network keluar, capability di-drop, limit CPU/memory/time), gaya `nsjail` atau `pwn.red/jail`.
- Kalau exploit Pwn "macet" lewat nc padahal lancar di lokal, cek apakah binary memanggil `setvbuf(stdout, NULL, _IONBF, 0)` di awal `main()` — tanpa itu, output bisa tertahan sampai koneksi ditutup.
- **Jangan pakai opsi `pty` di `EXEC:` socat** (`pty,stderr,setsid,sigint,sane,echo=0` ala template `bof.zip`) untuk soal yang payload-nya biner mentah (shellcode, alamat raw, dsb). Ditemukan saat implementasi 6 soal Binary Exploitation (`pwn_*`, lihat `BINEXP_PLANNING.md`): exploit yang 100% jalan lewat proses lokal langsung gagal total (EOF/connection drop) lewat koneksi network kalau socat pakai `pty` — line-discipline terminal PTY memfilter/mengubah byte tertentu dari payload. Fix: `EXEC:/usr/bin/timeout ... /path/binary` polos tanpa `pty`. Kalau butuh shell interaktif yang nyaman (misal lewat `catflag` pengganti), tetap aman tanpa `pty` karena koneksi `nc` sudah cukup untuk shell sederhana.
- Ret2win/ret2function **langsung tanpa gadget tambahan** bisa SIGSEGV di glibc modern (`movaps` di `_int_malloc` butuh stack 16-byte aligned, sedangkan `ret` langsung — beda dari `call` biasa — bikin RSP misaligned 8 byte). Fix standar: sisipkan 1 gadget `ret` polos sebelum alamat target (`exe.search(asm("ret"), executable=True)` di pwntools). Flaky antar versi glibc kalau tidak di-fix — **wajib test lawan container asli** (bukan cuma proses lokal di mesin dev) karena bug ini baru kelihatan lawan Ubuntu 22.04/glibc 2.35, tidak kelihatan di sebagian environment dev lain.
- Partial return-address overwrite (teknik umum buat "leak PIE base tanpa leak apapun duluan") **rapuh kalau pakai lebih dari 1 byte**: overwrite 1 byte deterministik (tergantung apakah 2 alamat berbagi 256-byte bucket hasil link — bisa dicek `objdump`, tidak tergantung ASLR), tapi overwrite 2 byte **flaky tergantung ASLR** (base PIE cuma page-aligned, bit 12-15 random, dan modulus 65536 tidak habis membagi 4096 beda dengan modulus 256). Kalau 1 byte tidak cukup (dua fungsi beda bucket), lebih aman pakai teknik data-only (overwrite variabel lokal biasa, bukan return address) buat tahap leak-nya — lihat desain final Istaroth di `pwn_istaroth/NOTES.md`.
- **Matikan core dump di level container** — soal pwn itu sifatnya "exploit atau crash", dan SIGSEGV dari percobaan yang salah itu normal/diharapkan (bukan cuma dari peserta jahat, tapi juga percobaan sah yang salah offset). Satu koneksi crash **tidak** merusak koneksi lain (socat `fork` isolasi per-koneksi, sudah dites), tapi kalau core dump tidak dimatikan, tiap crash bisa nulis file core ke disk container — selama 9 jam lomba dengan banyak tim (+ AI yang nyoba banyak kali), ini bisa numpuk dan habisin disk. Fix: `CMD` dibungkus shell supaya bisa jalanin `ulimit -c 0` sebelum exec ke `socat` (builtin shell, tidak bisa dipanggil langsung di exec-form `CMD [...]` tanpa shell):
  ```
  CMD ["sh", "-c", "ulimit -c 0; exec socat TCP-LISTEN:PORT,reuseaddr,fork 'EXEC:/usr/bin/timeout -k 5 N /path/binary'"]
  ```
  **Wajib pakai `exec`** sebelum `socat` — tanpa itu, `sh` tetap jadi proses PID 1 yang membungkus `socat`, dan sinyal dari Docker (`docker stop` = SIGTERM) bisa tidak diteruskan dengan benar ke `socat`/child-nya (bisa bikin container lama mati, nunggu sampai grace period abis baru SIGKILL). Dengan `exec`, `socat` langsung "menggantikan" proses shell itu (tetap PID 1, cuma image proses-nya yang berubah), jadi sinyal diterima langsung. `ulimit -c` turun ke semua proses anak (fork dari socat, exec ke binary target) secara otomatis — cukup di-set sekali di awal. **EXEC: argumen-nya wajib dikutip single-quote** di dalam string shell (`'EXEC:...'`) supaya shell tidak ikut memecah spasi di dalamnya jadi argumen socat yang salah (exec-form `CMD [...]` tanpa shell tidak kena masalah ini karena tidak ada parsing shell sama sekali, tapi begitu pindah ke shell-form demi `ulimit`, parsing spasi oleh shell jadi relevan). Sudah diterapkan ke ke-6 Dockerfile `pwn_*/` dan diverifikasi: `ulimit -c` di dalam container terbaca `0`, crash paksa (SIGSEGV) tidak menghasilkan file `core*` di manapun, dan container utama tetap `Up` normal setelah crash salah satu koneksi.
- Instance **bersama** untuk semua tim (bukan per tim) dengan reset otomatis, kecuali challenge yang menyimpan state (Web multi-step) yang perlu dites apakah aman dipakai bersamaan.
- Alamat service ditulis di deskripsi challenge dan diuji dari jaringan luar, bukan hanya `localhost`. Kalau alamat/port predictable, deploy instance sesaat sebelum wave dibuka, bukan jauh-jauh hari.
- Monitoring uptime (bukan anti-cheat): `WebTecFest/deploy/uptime-watch` — satu container cek semua port publik soal tiap beberapa puluh detik, alert ke Discord privat panitia kalau down/pulih. Lihat `WebTecFest/docs/Monitoring_Documentation.md`.

#### Referensi template dan tutorial hosting Pwn

- [Hosting pwn challenges: a simple tutorial](https://152334h.github.io/blog/hosting-pwn-challenges) — titik awal paling ramah pemula, termasuk cara mengunci shell supaya peserta tidak bisa merusak/menimpa flag di tengah lomba.
- [rCTF — deployment.md](https://rctf.osec.io/meta/running-a-successful-ctf/deployment.md) dan [rCTF — common-mistakes/challenges.md](https://rctf.osec.io/meta/common-mistakes/challenges.md) — praktik isolasi per koneksi, pinning image, dan kesalahan umum deployment pwn/RCE.
- [Eadom/ctf_xinetd](https://github.com/Eadom/ctf_xinetd) dan [sec-db/ctf_xinetd](https://github.com/sec-db/ctf_xinetd) — template xinetd klasik: satu binary per container, tinggal edit `ctf.xinetd`.
- [giantbranch/pwn_deploy_chroot](https://github.com/giantbranch/pwn_deploy_chroot) — satu container untuk banyak binary lewat `chroot`, generate flag & port per soal otomatis, ada opsi `catflag` pengganti `/bin/sh`.
- [redpwn/rDeploy](https://github.com/redpwn/rDeploy) — baca `docker-compose.yml` per soal, auto-generate config xinetd dari field `binary:`, template deskripsi sudah menyertakan baris `nc host port`.
- [FHICTF — Making pwn challenges](https://vdev-eo0.pages.dev/making_pwn_challs) — contoh Dockerfile dengan entrypoint `socat`, plus catatan buffering stdout di atas.

#### Saran untuk Web dengan file upload (Web A)

Terlepas dari strategi flag (statis atau per tim), soal upload punya risiko tersendiri: kalau satu tim berhasil upload webshell dan nama filenya bisa ditebak atau foldernya bisa dilist, tim lain bisa langsung pakai webshell itu tanpa menemukan bypass upload sendiri. Itu bukan soal flag sharing, tapi state yang ditinggalkan satu tim dan "dipinjam" tim lain. Mitigasinya murah dan tidak butuh identitas tim:

- Nama file hasil upload **di-randomize di server** (bukan dipakai dari nama asli yang dikirim peserta).
- **Disable directory listing** di folder upload.
- Folder upload **dibersihkan berkala** (cron tiap beberapa puluh menit) supaya webshell/file lama tidak menumpuk sepanjang 9 jam lomba.

### 2.5 Waktu, wave, dan notifikasi

Jadwal dari guidebook (WITA, minggu ke-2 November 2026): Wave 1 pukul 10.00, Wave 2 pukul 14.30, freeze 18.00, selesai 19.00.

- Konfigurasi di `/admin/config` → **CTF Time**: Start, End, dan **Freeze Time**.
- Freeze juga dapat dipasang dari terminal; perintah tersedia di `WebTecFest/README.md` bagian "Pengujian Pembekuan Papan Skor". Spanduk freeze muncul otomatis di semua halaman.
- Pengumuman ke peserta: `/admin/notifications` (tipe toast atau alert, dengan opsi suara) atau `POST /api/v1/notifications` dengan access token admin.
- Pembagian challenge ke Wave 1 vs Wave 2 **belum tercatat**; tentukan lalu atur lewat Visibility.

### 2.6 Easter egg (Misc 1–3)

Dibangun di tema/plugin, bukan challenge CTFd biasa, jadi **tidak ikut** langkah 2.3:

| Slot | Mekanisme | Lokasi |
|---|---|---|
| Misc 1 | Mini game mancing di beranda; flag didapat setelah mendapat chest | `fishing-game.js`, API `/api/v1/fishing/*` |
| Misc 2 | Ayam melayang di `/scoreboard`; klik membuka peti | `easter-rooster.js` |
| Misc 3 | Setelah semua challenge `x/x SOLVED`, kucing/peti terbuka; klaim server-side maks 2x per akun/tim (1x per wave), disimpan di `tecart_easter_claims` | `easter-penguasa.js`, `POST /api/v1/tecart/easter/penguasa` |

Perhatian:

- Flag Misc 3 di CSV ditulis `Tecfest26{...}` (huruf kecil `f`), sedangkan format resmi `TecFest26{...}`. Putuskan mana yang benar dan samakan di CSV dan sistem.
- Logika Misc 3 bergantung pada jumlah challenge yang terlihat saat itu. Uji ulang setelah daftar challenge asli terpasang, termasuk skenario Wave 2.

### 2.6a Challenge Warm-up (6 soal, terpisah dari 40 soal lomba)

Warm-up berlangsung minggu ke-1 November 2026, poin **tidak masuk nilai utama**
(lihat guidebook). Satu soal easy per kategori (Forensic, Cryptography, Reverse
Engineering, Binary Exploitation, Web), ditambah Miscellaneous yang **memakai ulang**
`misc_emergency_food/` (sanity check kompetisi utama) — bukan soal baru, by design.

Tercatat di CSV dengan `Kategori` berawalan `Warm Up - ...` (grup terpisah dari rekap
40 soal utama, lihat baris setelah Miscellaneous Num 3). Semua author `SancaPWN`.

| Kategori | Nama | Folder | Butuh service? |
|---|---|---|---|
| Forensic | Qiqi's Secret Recipe | `warmup_foren_qiqi/` | Tidak (attachment statis) |
| Cryptography | Jean's Favor | `warmup_crypto_jean/` | Tidak (attachment statis) |
| Reverse Engineering | Keqing's Hidden Scroll | `warmup_re_keqing/` | Tidak (attachment statis) |
| Binary Exploitation | Mona's Astrology Commission | `warmup_pwn_mona/` | Ya, nc port `40111` (host-side, skema 5 digit) |
| Web Explotation | Dawn Winery | `warmup_web_diluc/` | Ya, web static (nginx) port `50111` (host-side, skema 5 digit) |
| Miscellaneous | Emergency Food Check | `misc_emergency_food/` | Tidak (dipakai ulang) |

Catatan desain:

- Semua sengaja dibuat *trivial* (tujuannya pemanasan pakai platform, bukan skill
  check) — tidak ada proteksi/obfuscation di Forensic/Crypto/RE, dan Pwn-nya cukup
  "spam A sampai SIGSEGV" tanpa perlu hitung offset/alamat (canary off, signal
  handler `SIGSEGV` di server yang langsung kirim flag saat crash — lihat
  `warmup_pwn_mona/NOTES.md`).
- **Sudah diuji lewat Docker container via network** (`docker compose up -d --build`
  + koneksi TCP/HTTP terpisah ke `127.0.0.1`, bukan cuma proses lokal): `warmup_pwn_mona`
  5x koneksi nc berturut-turut semua balas flag, `ulimit -c`=0 terkonfirmasi, tidak ada
  file `core*` menumpuk; `warmup_web_diluc` 3 file ke-serve `200 OK` lewat curl, file
  read-only di dalam container. Detail di masing-masing `NOTES.md`/`WRITEUP.md`.
- Ditemukan saat testing: `warmup_web_diluc` awalnya crash loop karena `cap_drop: ALL`
  mencegah entrypoint `nginx:alpine` resmi `chown` cache dir miliknya sendiri saat
  startup — fix-nya tambah `cap_add: [CHOWN, SETUID, SETGID]` (sudah diterapkan di
  `docker-compose.yml`-nya). Kalau ada chall Web lain yang pakai image official serupa
  (butuh drop privilege root->non-root saat start) dan pakai pola `cap_drop: ALL`
  yang sama, cek dulu apakah kena masalah serupa.
- `warmup_web_diluc/Dockerfile` masih pakai tag `nginx:1.27-alpine`, belum di-pin
  via digest — pin dulu sebelum deploy (lihat komentar di Dockerfile-nya).
- Port host-side di `docker-compose.yml` sudah diupdate ke skema 5 digit final
  (`40111` Mona, `50111` Diluc — kategori+slot+digit-4=1/warm-up, lihat
  `ARSITEKTUR_INFRA_DAN_ANCAMAN.md` bagian 3a). Port internal container (`10110`,
  `80`) tidak ikut berubah, tetap hardcode di Dockerfile masing-masing. Catatan
  lama: port dev awal (`10110`/`8090`, sebelum skema 5 digit final dipakai) masih
  muncul di beberapa log/test-hasil historis (`NOTES.md`/`WRITEUP.md`) — itu akurat
  untuk waktu ditulis, bukan port yang dipakai sekarang.

### 2.7 Checklist sebelum warm-up dan lomba

Warm-up berlangsung minggu ke-1 November 2026 dengan website yang sama dengan lomba.

- [ ] Pasang 6 challenge warm-up (2.6a) bertipe `tecart`, set Visibility sebelum minggu ke-1 November
- [ ] Pasang 40 challenge asli bertipe `tecart` di instance lomba
- [ ] Gunakan akun admin dan kredensial database baru di infra lomba
- [ ] Batasi anggota tim maksimal 3 sesuai guidebook
- [ ] Set CTF Start/End/Freeze sesuai jadwal; tes freeze dan unfreeze
- [ ] Selaraskan mode scoring dengan guidebook (dynamic snapshot) dan nilai poin per difficulty
- [ ] Tentukan Wave 1/Wave 2 dan 5 challenge Bounty First Blood
- [ ] Siapkan konfigurasi produksi (reverse proxy/HTTPS) dan host service challenge (2.4)
- [ ] Kredensial peserta dikirim H-2 ke email ketua tim (guidebook); siapkan data tim
- [ ] Setup channel Discord Open Ticket
- [ ] Jalankan `python tools/run_all_tests.py --tier all --url <url>` dari `WebTecFest/`
- [ ] Backup database dan folder upload CTFd sebelum lomba dan setelah freeze
- [ ] Rencana darurat: siapa yang bisa restart container, dan cara umumkan lewat notifikasi
- [ ] Isi `targets.json` di `WebTecFest/deploy/uptime-watch` dengan alamat publik semua server soal, dan jalankan sebelum lomba dimulai

### 2.8 Setelah lomba

- Akses website tetap hidup hingga 19.00 WITA hari berikutnya agar peserta bisa mengumpulkan write-up.
- Plugin `tecart_capture` merekam link AI, file solver, dan setiap percobaan submit untuk pemeriksaan kecurangan; submission juga bisa dilihat di panel admin `/admin/submissions`.
- Pengumuman pemenang 30 November 2026.

### 2.9 Checklist praktis: bikin 1 challenge baru dari nol

Urutan kerja dari ide sampai live, menggabungkan pola yang sudah dipakai di
`pwn_mavuika`/`crypto_nahida`/`misc_asmoday` dkk — pakai folder itu sebagai
contoh/template, bukan nulis dari kosong.

1. **Pilih kategori + slot (A–F)** — cek CSV dulu (`Challenge CTF TecFest 2026 -
   Chall.csv`) biar nggak bentrok nama/slot yang sudah dipakai author lain.
2. **Bikin folder** `<kategori>_<namachall>/` (pola nama existing, huruf kecil +
   underscore: `pwn_mavuika`, `crypto_nahida`, `misc_asmoday`). Isi minimal:
   - `Dockerfile` + `docker-compose.yml` — wajib ada setup lokal (lihat 2.4).
   - `Desc.txt` — draft deskripsi yang nanti di-paste ke CTFd (termasuk baris
     `nc <host> <port>` atau `http://<host>:<port>` — isi port asli, bukan
     placeholder, biar gampang langsung copas pas upload).
   - `solve.py` — intended solution, sekaligus solver otomatis buat QA.
   - `NOTES.md` — catatan desain, hasil test, TODO sebelum deploy.
   - `flag.txt` (mount `:ro`, **jangan** di-bake ke image) dan/atau
     `dist/<nama>_attachment.zip` kalau ada attachment peserta.
3. **Hardening wajib** di `docker-compose.yml` (pola yang sudah ada di semua
   folder soal): `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`,
   `pids_limit`, `mem_limit`, `cpus`, user non-root di image, flag/file sensitif
   di-mount `:ro`. Pwn tambahan: `ulimit -c 0` + `exec` di `CMD` (lihat
   `warmup_pwn_mona/Dockerfile` buat contoh lengkap + alasannya).
4. **Tentukan port 5 digit** (`K CC W I`, lihat `ARSITEKTUR_INFRA_DAN_ANCAMAN.md`
   bagian 3a): `K`=kategori (1 Crypto, 2 Forensic, 3 RE, 4 Pwn, 5 Web, 6 Misc),
   `CC`=slot A–F (01–06), `W`=`0` (soal resmi, bukan warm-up), `I`=`1` (instance
   default). Set ini di `docker-compose.yml` sisi host (`ports: "<IP>:<port>:<port-internal>"`)
   — port internal container **tidak perlu** ikut skema, bebas sesuai kode/Dockerfile.
5. **Test lokal**: `docker compose up -d --build`, jalankan `solve.py` lokal
   pastikan dapat flag; test juga beberapa koneksi paralel kalau soal `nc` (lihat
   `warmup_pwn_mona/NOTES.md` buat pola test yang sudah dipakai: cek `ulimit -c`,
   cek container tetap `Up` setelah crash berulang).
6. **Commit + push** folder ini ke repo privat `chall-tecfest-ctf-2026` — flag
   dan `solve.py` boleh ikut (kebijakan Sanca, lihat
   `WebTecFest/deploy/warmup-setup/README.md` bagian 0b), tapi tetap **jangan**
   pernah masuk ke attachment peserta atau deskripsi CTFd.
7. **Deploy ke node yang benar** (lihat `ARSITEKTUR_INFRA_DAN_ANCAMAN.md` bagian
   3 buat pemetaan lengkap): soal tanpa shell → Homelab 8GB; soal yang memberi
   shell/RCE → Proxmox 16GB (VM sesuai kategori, lihat
   `WebTecFest/deploy/competition-setup/README.md` bagian 2). Di node tujuan:
   `git pull` (atau `git sparse-checkout add <folder>` kalau belum ada), lalu
   `docker compose up -d --build`.
8. **Tambah route di VPS 2GB**: satu blok `stream{}` (nc) atau `http{}` (web) di
   `nginx.conf` buat port baru, `nginx -t && systemctl reload nginx`.
9. **Tambah entry** ke `targets.json` di `WebTecFest/deploy/uptime-watch` biar
   soal baru ikut terpantau.
10. **Upload ke CTFd** (Admin Panel → `/admin/challenges`, lihat 2.3): tipe
    **tecart**, kategori sesuai, deskripsi dari `Desc.txt` (pastikan host:port
    di dalamnya sudah final, bukan draft), flag statis, **attachment yang sudah
    dibersihkan** dari flag/solver/path lokal/`.git`/metadata author (beda dari
    `dist/` di repo — itu boleh ada solve.py, yang di-upload ke CTFd tidak
    boleh), hints kalau ada, Visibility sesuai Wave 1/2.
11. **Update CSV** — isi semua 14 kolom yang relevan (`Status`, `Flag`,
    `Attachment`, `Deployment Status`, dst), encoding UTF-8 + CRLF + tanpa
    newline akhir tetap terjaga, jangan sentuh kolom/baris lain (lihat `CLAUDE.md`
    root repo poin 2).
12. **QA**: minta Tester coba dari jaringan luar (bukan `localhost`/IP Tailscale
    sendiri) lewat `chall.tecfest.site:<port>` beneran, submit flag salah dan
    benar, catat hasil di kolom `Tester`/`QA Status`/`Notes Tester`.

---

## Pertanyaan Terbuka

1. ~~Hosting service challenge: pakai VPS terpisah seperti usulan 2.4, atau ada infrastruktur lain dari TecArt?~~ **Sudah diputuskan** — 5 node (lihat `ARSITEKTUR_INFRA_DAN_ANCAMAN.md`).
2. Nilai poin per difficulty dan mode scoring final.
3. Challenge mana yang Wave 1 dan Wave 2, dan mana 5 challenge Bounty.
4. Penulisan flag easter egg Misc 3 (`Tecfest26` vs `TecFest26`).
5. Apakah `Guidebook ... .md` atau `.docx` yang final (versi `.md` lebih baru)?
