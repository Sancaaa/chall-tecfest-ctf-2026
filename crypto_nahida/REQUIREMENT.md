# Requirement — Nahida (Cryptography E)

> **Dokumen author. Berisi intended solution. Jangan masuk attachment, deskripsi, tema web, atau repo publik.**
> Status challenge ada di CSV (`Cryptography`, slot `E`); dokumen ini hanya spesifikasi desain dan kriteria selesai.

| Item | Nilai |
|---|---|
| Kode / nama | **Nahida** |
| Kategori / slot | Cryptography E (Hard) |
| Author | SancaPWN |
| Tipe | nc (service) + attachment (pcap + source) |
| Terinspirasi | Real World CTF "Personal Proxy" (writeup CryptoHack), disederhanakan dan diubah |
| Topik | AES-CFB dengan IV statis: kebocoran keystream, pemalsuan header ber-CRC32, rantai CFB, dan oracle AES yang dibangun dari rantai itu |

---

## 1. Tujuan desain

1. **Hard asli**, bukan Hard karena bertele-tele. Satu rantai langkah yang tiap langkahnya masuk akal, tapi gabungannya tidak ada di writeup mana pun.
2. **Tidak bisa diselesaikan AI dalam 2–3 putaran** (definisi dan cara uji di bagian 8). Peserta boleh memakai AI; soal ini harus tetap membutuhkan pemahaman peserta.
3. **Solvable tanpa scanning, fuzzing, atau brute force** terhadap server (aturan guidebook). Semua yang perlu ditemukan bisa dibaca dari source, pcap, atau balasan server.
4. **Aman di-host sebagai instance bersama**: stateless, tidak bisa dipakai menyerang host, tidak ada koneksi keluar, satu tim tidak bisa merusak soal untuk tim lain.

---

## 2. Cerita (usulan, boleh diubah)

Perusahaan fiktif memakai gateway internal untuk meneruskan lalu lintas karyawan ke layanan dalam. Panitia (peserta) menyadap pcap sesi beberapa klien. Tujuan: ambil isi rahasia di layanan `vault` tanpa mengetahui kunci gateway. Nama dan tema bebas (serasi dengan soal Sanca lain bergaya Genshin), selama deskripsi tidak membocorkan teknik.

---

## 3. Spesifikasi protokol

### 3.1 Cipher
- AES-128-**CFB128**, satu kunci acak 16 byte (bukan password; tujuannya mencegah brute force kamus).
- `IV = SHA256(key)[:16]`, **statis** untuk semua koneksi dan **dipakai untuk dua arah** (satu kunci, satu IV).
- Tanpa MAC. Hanya ada CRC32 di header (3.2).
- Notasi: `E` = AES-ECB enkripsi satu blok; `K0 = E(IV)`; blok ke-i keystream = `E(C_{i-1})`.

### 3.2 Frame header (tepat 1 blok = 16 byte, di awal stream klien)

| Offset | Ukuran | Isi |
|---|---|---|
| 0 | 1 | `ver` (= 1) |
| 1 | 1 | `cmd` (= 1, CONNECT) |
| 2 | 4 | `ip` (IPv4) |
| 6 | 2 | `port` (big endian) |
| 8 | 4 | `sid` (acak, bebas; **tidak dicek ke state mana pun**) |
| 12 | 4 | `crc32` atas byte 0–11, `zlib.crc32`, **little endian** |

Payload dimulai di blok 1 dan merupakan aliran byte tanpa struktur dari sisi gateway.

### 3.3 Tujuan virtual (diproses dalam proses Python yang sama, **tanpa socket keluar**)

| Tujuan | Perilaku |
|---|---|
| `10.0.0.5:9000` **vault** | Protokol baris, bagian 3.4 |
| `10.0.0.99:1` **dbg** | "Mode debug": membaca sisa stream klien (didekripsi), lalu mengirim balik **plaintext mentah, tidak dienkripsi**. Batas masukan 1024 byte, batas waktu 3 detik, lalu tutup |
| `10.0.0.7:25` mail, `10.0.0.8:631` print | **Decoy** dengan balasan terenkripsi tetap (untuk sesi umpan di pcap) |
| Lainnya, CRC salah, `ver`/`cmd` salah | Balasan **seragam**: 16 byte `0x00` yang dienkripsi dengan rantai balasan (= `K0` persis) lalu tutup. Tidak dibedakan |

Kebocoran `K0` lewat balasan error ini disengaja (padanan kebocoran null byte di soal asli). Batas jawab dan ukuran: lihat bagian 6.

### 3.4 Protokol vault (setelah header)

Stream klien setelah didekripsi (contoh tata letak, offset dihitung dari awal stream termasuk header):

| Offset | Isi |
|---|---|
| 16–31 | `HELLO vault/1.0\n` (tepat 16 byte) |
| 32–69 | `AUTH <32 hex>\n` (token statis per deployment) |
| 70–78 | `CMD stat\n` |
| 79–82 | `END\n` (**wajib** langsung setelah `CMD`) |
| 83 dst | diabaikan |

Perintah yang dikenal: `stat` dan `flag` (sama-sama 4 huruf, supaya bisa ditambal dengan XOR). `AUTH` token wajib valid untuk keduanya. Baris `END` wajib agar permintaan dianggap lengkap.

Balasan vault: **blok 0 balasan = status 16 byte**, lalu body.

| Kondisi | Status (16 byte) |
|---|---|
| Sukses | `200 OK vault/1.0` |
| Token salah / tidak ada | `401 DENIED vault` |
| Format salah (HELLO/CMD/END tidak valid) | `400 BAD REQUEST ` |

Body `stat` = beberapa baris umpan (uptime, dst). Body `flag` = flag + `\n`. **Flag minimal 36 karakter** supaya body menjangkau ≥ 3 blok balasan.

Status vault sengaja **berbeda-beda** (tidak seragam) supaya peserta mendapat umpan balik di tahap akhir; hanya lapisan gateway yang seragam.

### 3.5 Isi pcap (`capture.pcap`)

- Minimal 5 sesi TCP lengkap (handshake, data dua arah, FIN) dari beberapa IP klien, dengan stempel waktu masuk akal.
- 1 sesi **target**: klien → vault, `HELLO` + `AUTH <token>` + `CMD stat` + `END`, balasan `200 OK` + body `stat`. **Flag tidak ada** di pcap.
- 1 sesi vault lain dengan `401`/`400` (umpan).
- 2–3 sesi ke `mail`/`print` (umpan).
- Semua dienkripsi dengan kunci yang sama dengan server (pcap dibuat oleh `gen_capture.py` dari kunci deployment).
- Header diekspos hanya lewat `K0`; peserta harus mendekripsi blok 0 tiap sesi untuk tahu mana yang ke vault.

---

## 4. Intended solution (jalur utama)

1. **Baca source.** Temukan: IV statis dari kunci, mode CFB128, rumus header + CRC, tujuan `vault` dan `dbg` (dbg membalas plaintext), balasan error seragam.
2. **Bocorkan `K0`.** Kirim byte acak ≥ 16 byte ke gateway → balasan 16 byte = `K0` (karena plaintext-nya nol). `K0` berlaku untuk blok 0 semua stream, dua arah.
3. **Dekripsi blok 0 semua sesi pcap** dengan `K0` (`ver cmd ip port sid crc`). Tentukan sesi target (ke `10.0.0.5:9000`).
4. **Palsukan header dbg.** Susun `P0'` (`dst=10.0.0.99:1`, `sid` baru, `crc32` benar) dan kirim `C0' = P0' ^ K0`. Header valid → gateway masuk mode dbg.
5. **Bangun oracle `E(x)`.** Pahami rantai CFB: setelah blok 0 diganti, blok 1 hasil dekripsinya acak, tapi tiap blok berikutnya tetap `P_{j+1} = C_{j+1} ^ E(C_j)`. Kirim `C0' || x || 0^16`; echo dbg memberi `E(x)` pada 16 byte terakhir. Banyak query bisa digabung dalam satu koneksi dengan pola `[x1][0][x2][0]...`.
6. **Dekripsi payload sesi target** (diperlukan untuk mengetahui offset `stat` dan `END`): `P_i = C_i ^ E(C_{i-1})` dengan `C_{i-1}` dari pcap, via oracle (atau lewat replay langsung ke dbg dengan header dipalsukan). Hasil: tata letak permintaan, posisi `stat`, token.
7. **Tambal perintah.** `C4' = C4 ^ (stat ^ flag)` pada offset yang tepat di ciphertext asli (header asli tidak disentuh, `sid` asli tetap). Efek sampingnya: blok 5 hasil dekripsi menjadi acak (rantai CFB), dan di situ ada `END\n`.
8. **Perbaiki blok yang rusak.** Karena `END` wajib, hitung `E(C4')` lewat oracle, lalu pilih `C5' = P5_diinginkan ^ E(C4')`. Ini membuat `END\n` valid lagi. (Bagian ini mengubah soal dari "bit-flip biasa" menjadi "membangun enkripsi CFB sendiri lewat oracle".)
9. **Kirim stream ke vault** (header asli, `C1..C3` asli, `C4'`, `C5'`). Vault membalas `200 OK` + body flag.
10. **Dekripsi balasan.** Blok 0 balasan terbaca langsung dengan `K0`. Blok 1 dst: `P_i = R_i ^ E(R_{i-1})`. Semua `R_{i-1}` diketahui, jadi satu koneksi oracle batch cukup.

Jalur alternatif yang dibolehkan (jangan ditutup): memakai token yang didapat dari langkah 6 untuk membuat permintaan baru ke vault dengan oracle-enkripsi bertahap; menurunkan `K0` dari tebakan plaintext header balasan vault di pcap alih-alih dari error.

### Solver (disimpan di folder author, bukan attachment)
`solve.py` harus berjalan end-to-end terhadap server lokal dan terhadap deployment, mencetak flag, selesai < 60 detik.

---

## 5. Hal yang sengaja dibuat sulit (dan alasannya)

| Elemen | Efek |
|---|---|
| CFB128, bukan CTR | Hanya blok 0 yang statis; bit-flip merusak blok berikutnya. Tidak bisa dikerjakan dengan resep "keystream reuse" |
| CRC32 di header | Flip bit mentah gagal; harus tahu cakupan, urutan byte, dan endian dari source |
| Balasan gateway seragam | Peserta tidak bisa membedakan CRC salah dan tujuan salah; harus teliti dari source |
| `dbg` mengembalikan plaintext | Satu-satunya jalan keluar plaintext. Harus disadari bahwa ini oracle AES, bukan sekadar "tempat melihat payload" |
| Flag hanya di respons live | Mendekripsi pcap saja tidak cukup; harus berbicara ke vault |
| `END` wajib setelah `CMD` | Tambalan saja membuat blok berikutnya rusak; harus membangun enkripsi CFB sendiri |
| Balasan vault juga rantai CFB | Mendekripsi flag butuh oracle lagi, tidak cukup `K0` |
| Banyak sesi umpan di pcap | Harus dipilah dengan `K0` terlebih dulu |

Semua kunci tetap hanya bergantung pada hal yang bisa dibaca atau dikirim secara sah; tidak ada tebakan yang butuh brute force.

---

## 6. Hosting dan keamanan

- **Satu port nc** `10501` (skema K CC W I, lihat `WebTecFest/deploy/competition-setup/README.md`; `13337` dipakai Asmoday). Satu proses Python `socketserver` threaded.
- **Stateless dan tanpa state global lintas-tim.** Dilarang: cache anti-replay `sid`, penghitung global, antrean. Alasan: satu tim bisa mengunci soal untuk semua tim. Rate-limit hanya per IP.
- Batas: 5 koneksi bersamaan per IP, 60 koneksi/menit per IP (oracle batch memakai sedikit koneksi, jangan terlalu ketat), 4 KiB input per koneksi, timeout 5 detik per koneksi.
- **Tanpa socket keluar.** Semua "host" adalah dict di proses. Container tanpa network keluar, user non-root, rootfs read-only, `cap_drop: ALL`, batas CPU/memori/proses.
- Kunci, token, dan flag dibaca dari berkas rahasia yang di-mount `:ro`; tidak ada di image maupun attachment.
- Base image dipin dengan digest (aturan hosting di `CHALLENGE_DAN_HOSTING.md`, 2.4).
- Folder `crypto_nahida/` berisi `Dockerfile`, `docker-compose.yml`, `server.py`, `gen_capture.py`, `solve.py`, `WRITEUP.md`, `Clue.txt`, mengikuti pola `misc_asmoday`.
- Daftarkan alamat di `targets.json` uptime-watch sebelum lomba.

---

## 7. Attachment peserta

| Berkas | Isi |
|---|---|
| `capture.pcap` | Bagian 3.5 |
| `server.py` | Versi bersih: tanpa kunci, token, flag; membaca dari berkas rahasia. Semua logika cipher/CRC/tujuan **utuh dan terbaca** |
| (deskripsi) | `nc <host> 10501`, cerita, tanpa petunjuk teknik |

Dilarang ada di attachment: flag, `solve.py`, path lokal, `.git`, metadata author, komentar yang membocorkan teknik (mis. kata "oracle", "CFB chaining").

Draf deskripsi (silakan ubah):
> Gateway internal PT Nahida meneruskan lalu lintas karyawan ke layanan dalam. Kami berhasil menyadap sebagian lalu lintasnya. Layanan `vault` menyimpan rahasia yang kami butuhkan. `nc <host> 10501`

---

## 8. Kriteria selesai dan ketahanan terhadap AI

### 8.1 Definisi
"Putaran" = satu balasan model + penguji menjalankan skrip hasilnya lalu menempel keluaran ke chat. Tanpa agent dan tanpa tool otomatis, seperti yang berlaku bagi peserta.

### 8.2 Gerbang AI (wajib lolos sebelum `QA Status = Passed`)
- Uji dengan **keempat model whitelist** (GPT-5.6 Instant, Claude Sonnet 5.5, Gemini 3.6 Flash, DeepSeek-V3.2).
- Tiga gaya prompt: (a) tempel `server.py` + hex pcap + deskripsi, minta flag; (b) sama, tambah "pahami mode CFB dan kebocoran keystream"; (c) minta rencana lalu skrip, relay hasil.
- **Lulus** bila tidak ada model yang menghasilkan flag dalam ≤ 3 putaran, dan ≥ 3 dari 4 model belum selesai dalam 6 putaran. Simpan log hasil di folder author.
- Prediksi: model akan menemukan IV statis dan CRC dengan cepat, lalu gagal di langkah 5 (oracle), 8 (perbaikan blok), atau 10 (dekripsi balasan).

### 8.3 Gerbang manusia
- Tester (bukan author) dengan bantuan AI harus bisa menyelesaikannya dalam ≤ 4 jam; bila tidak ada tester yang berhasil dalam 4 jam, gunakan tuas relaksasi (8.5).

### 8.4 Tuas bila AI terlalu mudah
- Ubah cakupan atau urutan CRC dan gunakan varian lain (CRC-32C).
- Buat `END` dan `CMD` melintasi batas blok sehingga tambalan merusak bagian yang bermakna.
- Pecah flag ke dua perintah (`flag 0`, `flag 1`).
- Tambah tahap yang butuh dua oracle bertingkat (mis. token vault diturunkan dari hasil `E(.)` tertentu).

### 8.5 Tuas relaksasi bila terlalu sulit untuk manusia
- Hapus kewajiban `END` (vault mengabaikan sisa, jalur tambalan sederhana).
- Beri petunjuk hint 1–2 gratis di deskripsi.
- Letakkan flag langsung di body `stat`.

### 8.6 Checklist umum (mengacu 1.6 di `CHALLENGE_DAN_HOSTING.md`)
- [ ] Nama, topik, kategori, difficulty sesuai slot (Cryptography E, Hard)
- [ ] Flag `TecFest26{...}` ≥ 36 karakter, dicatat di CSV
- [ ] Intended solution tercatat di CSV (ringkas, merujuk dokumen ini)
- [ ] `solve.py` end-to-end terhadap lokal dan deployment
- [ ] Attachment bersih (bagian 7)
- [ ] Docker diuji dari jaringan luar; limit dan timeout bekerja; flag `:ro`
- [ ] Gerbang AI (8.2) lulus, log tersimpan
- [ ] Gerbang manusia (8.3) lulus
- [ ] Solvable tanpa brute force (guidebook)
- [ ] Dipasang ke CTFd bertipe `tecart`, dites dari akun peserta

---

## 9. Hint bertingkat (via Open Ticket)

1. "Bandingkan bagaimana IV dibuat dan apa yang terjadi pada balasan saat tujuan salah."
2. "Dalam CFB, hanya blok pertama yang sama di setiap koneksi. Blok berikutnya bergantung pada ciphertext sebelumnya."
3. "Salah satu layanan di gateway tidak mengenkripsi balasannya. Apa yang bisa dilakukan dengan itu?"
4. "Jika kamu punya cara mendapatkan `E(x)` untuk x pilihanmu, kamu bisa mengenkripsi dan mendekripsi apa pun dalam rantai CFB."

---

## 10. Estimasi pekerjaan

| Tugas | Perkiraan |
|---|---|
| `server.py` + Docker | 3–4 jam |
| `gen_capture.py` (scapy) | 2–3 jam |
| `solve.py` + `WRITEUP.md` | 3–4 jam |
| QA (tester + gerbang AI) | 4–6 jam |
| Deploy + uji dari luar | 1–2 jam |

Total sekitar 2–3 hari kerja satu orang. Jadwal lomba minggu ke-2 November, jadi jika waktunya tidak cukup, gunakan tuas relaksasi 8.5 sebelum membuang desain.

---

## 11. Keputusan yang masih terbuka

1. Flag final diset di `secrets/flag`. **CSV masih memuat flag berbeda/terpotong — selaraskan** (lihat §12).
2. Nama tokoh/narasi (Nahida hanya kode di CSV).
3. Apakah soal ini jadi Bounty First Blood (§12: bukan anchor anti-AI).
4. Port final: **`10501`** (skema competition-setup). Alamat server menyusul saat deploy.
5. ~~Tuas 8.4/8.5~~ — diputuskan **diterima as-is** (§12).

---

## 12. Catatan hasil (diterima as-is, 15 Nov 2026)

- Soal **tersolve penuh** secara blackbox (`blackbox_testing/WRITEUP_blackbox.md`): rantai `keystream0 = E(IV)` → oracle `E(X)` via DBG → token dari pcap → `CMD flag` → dekripsi balasan; flag didapat.
- **Temuan desain:** jalur **craft-fresh** (susun request baru lewat oracle) melewati jalur patch, karena `vault_handle` tidak mengikat `sid`/anti-replay. Akibatnya klaim §4/§5 "`END` wajib memaksa rekonstruksi blok" **tidak memaksa** apa pun, dan tuas §8.4 soal `END`/`CMD` lintas-blok **tidak efektif** kecuali craft-fresh diblokir lebih dulu.
- **Keputusan:** diterima sebagai **Hard yang fair dan solvable**, **bukan** soal anti-AI. Tidak mengejar lolos gerbang §8.2; pembeda disandarkan pada nilai write-up + kecepatan. Tuas 8.4/8.5 tidak dipakai.
- Hygiene: `blackbox_testing/` memuat flag + token cleartext → author-only, jangan pernah ikut ke `dist/`.
