# Write-up: re_naberius

> **Hasil blackbox test.** Hanya binary `naberius` yang dipakai (tanpa source/author notes).
> **Flag:** `TecFest26{1_4M_7H3_sh4d3_s1NN3R_W17CH_4nd_4LCH3MY_17_s3LF}`
> **Jangan** taruh file ini di attachment/repo yang bisa dibaca peserta.

## TL;DR

Binary ini sebenarnya **bukan program pengecek flag biasa**, tapi **sebuah mesin virtual (VM) mini** yang ditulis dengan Go. Flag kamu adalah *input* untuk program bytecode di dalam VM itu. Bytecode-nya terenkripsi dan "dirantai" (tiap instruksi didekripsi pakai hasil instruksi sebelumnya). Solusi: tiru VM-nya di Python, lalu cari byte flag satu per satu dengan melihat `ASSERT` mana yang gagal.

## 1. Recon: lihat dulu apa ini

```
$ file naberius
ELF 64-bit LSB executable, x86-64, statically linked, stripped
$ ./naberius
=== Naberius, the Chained Book of Life ===
Each page is sealed by the one before it.
Speak thy name, witch: <input>
The Book remains closed.            # kalau salah
The Book of Life writes thy name. So it is.   # kalau benar
```

- `strings` penuh `runtime.`, `goroutine`, `GC` → ini **binary Go**, dan *stripped*, jadi nama fungsi `main.*` hilang.
- Dua kalimat flavor text berbunyi: *"Each page is sealed by the one before it"*. Ini petunjuk: ada **rantai** (chain), di mana bagian berikutnya baru bisa dibuka kalau bagian sebelumnya benar.
- `strace`: program hanya `write` banner, `read(0)` satu baris, `write` hasil, lalu `exit`. Tidak ada file/jaringan. Jadi seluruh logika ada di dalam binary.

## 2. Menemukan `main.main` di binary Go yang stripped

Di Go, string tidak berakhir NUL, jadi *xref* ke string "Naberius" tidak muncul di Binary Ninja. Trik yang saya pakai: **gdb + frame pointer**. Go memakai `rbp` chain, jadi:

1. `catch syscall read` dengan kondisi `$rdi == 0` (baca stdin).
2. Telusuri `[rbp+8]` berulang → daftar return address.
3. Return address terakhir sebelum `runtime.main` (`0x4353eb`) adalah **`0x492865`**, tepat di dalam fungsi `0x492680` = `main.main`.

Alur `main.main` (pseudo-C setelah dirapikan):

```c
println(banner1); println(banner2); print("Speak thy name, witch: ");
line = bufio.Reader.ReadString('\n');
line = strings.TrimRight(line, "\r\n");
if (len(line) == 0x3a && check(line))   // check = fungsi di 0x492180
    puts("The Book of Life writes thy name. So it is.");
else { puts("The Book remains closed."); os.Exit(1); }
```

Jadi flag **harus 58 karakter** (`0x3a`), lalu dicek oleh `0x492180`.

## 3. Bongkar `check`: ternyata VM

`0x492180` menyiapkan sebuah struct konteks (`ctx`) lalu memanggil `0x492960` (loop utama). Isi `ctx`:

| Offset | Arti |
|---|---|
| `+0x00/+0x08` | pointer + panjang **bytecode** (`0xb68` byte = 730 instruksi × 4 byte) |
| `+0x18` | buffer 64 byte berisi **input kita** |
| `+0x58/+0x60/+0x68` | **stack** (slice byte, maks `0x100`) |
| `+0x70` | register "MAC" (awal `0x5a`) |
| `+0x71` | byte *flag error* (OR dari semua kesalahan) |
| `+0x78` | jumlah `ASSERT` yang sudah dieksekusi |
| `+0x80` | `pc` |
| `+0x88` | state hash berantai `h` (awal `"EBAN"` = `0x4e414245`) |
| `+0x8c` | kunci opcode (awal `0x60`) |
| `+0x90` | tabel dispatch yang aktif (0 atau 1) |
| `+0x98` | flag `halted` |
| `+0xa0 / +0x120` | dua tabel 16 pointer handler (dua *permutasi* berbeda) |

**Syarat sukses** (akhir `0x492960`): `flags == 0` **dan** `jumlah ASSERT == 0x3a (58)` **dan** `halted` **dan** stack kosong. Artinya: 58 kali `ASSERT` semua harus cocok. Satu `ASSERT` per karakter flag.

### Cara 1 instruksi dijalankan

Bytecode 4 byte per instruksi, **terenkripsi per instruksi**:

```
g    = fmix32( pc*0x9e3779b1 ^ h )              # murmur3 finalizer
byte[i] = ((g >> 8*i) & 0xff) ^ kode_mentah[pc*4+i]   (i = 0..3)
h    = pc + rol32(word ^ h, 7) * 0x1000193      # h ikut "dirantai" oleh instruksi ini
```

Karena `h` bergantung pada semua instruksi sebelumnya, **tidak bisa melompat ke tengah** untuk mendekripsi: harus dari awal secara berurutan. Ini yang dimaksud "setiap halaman disegel oleh halaman sebelumnya".

Opcode = `(key ^ byte0) & 0xf`, dipetakan lewat salah satu dari dua tabel. Argumen handler adalah `byte1, byte2, byte3`.

### 16 opcode (hasil dibaca dari disassembly tiap handler)

| Opcode | Fungsi |
|---|---|
| `PUSH x` | push konstanta |
| `LOAD x` | push `input[x & 63]` |
| `ADD / SUB / MUL / XOR` | pop 2, operasi, push (mod 256) |
| `ROL x` | pop, rotate-left 8-bit sebanyak `x`, push |
| `MAC x` | `mac = rol8(mac ^ pop, 1) + x`, push `mac` (**state berantai antar cek**) |
| `ASSERT x` | `pop == x`? kalau tidak, flag error; `count++` |
| `SWAP i j` | tukar `input[i]` dan `input[j]` (mengacak urutan flag) |
| `PATCH lo hi v` | `kode_mentah[lo + hi*256] ^= v` (mengubah bytecode ke depan) |
| `KDF n` | hash `n` byte input pertama → seed xorshift32 → **XOR seluruh sisa bytecode** |
| `SWITCH` | pindah ke tabel opcode ke-2 dan ganti `key = 0x5e` |
| `POP`, `NOP`, `HALT` | buang elemen, tidak ada, berhenti |

Dua tabel dispatch itu hanyalah dua urutan berbeda dari 16 handler yang sama. `SWITCH` memicu ganti tabel di tengah program, jadi **byte opcode yang sama berarti hal lain sebelum dan sesudahnya**. Ini anti static-decompile yang sederhana tapi efektif.

## 4. Apa yang dilakukan bytecode-nya

Hasil dekripsi (dari emulator) terlihat teratur:

1. **~60 instruksi pertama**: rangkaian `SWAP` dengan indeks naik berurutan → mengacak (permutasi) 58 byte input. Diselingi `NOP/POP/PUSH+POP` sebagai sampah, dan beberapa `PATCH` untuk mengubah instruksi di depan.
2. **Blok cek**, diulang 58×:
   ```
   LOAD  idx        ; ambil 1 byte (sudah terpermutasi)
   PUSH/MUL/ADD/SUB/ROL/MAC ...   ; olah dengan konstanta + state MAC
   ASSERT nilai     ; harus sama
   ```
3. Di tengah ada `KDF 29`, yang mem-XOR sisa bytecode dengan keystream dari hash **29 byte input pertama (terpermutasi)**. Kalau 29 byte itu salah, sisa bytecode jadi sampah dan VM berhenti lebih awal (`HALT` di `pc=398`, baru 31 ASSERT dari 58).

Inilah makna "chain": byte flag yang benar *membuka* bagian bytecode berikutnya.

## 5. Strategi solve

Karena setiap blok cek hanya memuat **1 byte input yang baru** (kadang 2) ditambah state yang sudah diketahui dari cek sebelumnya, kita bisa menebak **byte demi byte**:

1. Jalankan emulator dengan tebakan saat ini (prefix `TecFest26{` dan penutup `}` sudah diketahui).
2. Cari `ASSERT` pertama yang gagal. Lihat `LOAD` mana (posisi asli, sudah dilacak lewat `SWAP`) yang belum diketahui.
3. Brute-force 95 karakter printable untuk byte itu (95² bila ada 2 byte), ambil yang membuat `ASSERT` tsb lulus.
4. Ulangi. Jika ada beberapa kandidat, jalankan DFS (cabang yang salah akan gagal di `ASSERT` berikutnya).

Contoh percabangan: untuk `ASSERT #4`, pasangan `N0` dan `N1` sama-sama lulus, tapi `N0` gagal di `ASSERT #28`. Jadi yang benar `N1` (dari `s1NN3R`).

Karena `KDF` bergantung pada prefix input, urutan ini otomatis konsisten: setelah semua `ASSERT` sebelum `KDF` lulus, 29 byte prefix sudah benar, sisa bytecode otomatis terdekripsi benar.

## 6. Script solver

Lihat [`solve.py`](solve.py): 80 baris, satu file, hanya library standar. Menjalankannya (±15 detik):

```bash
python solve.py ../re_naberius/naberius
```

Keluaran:

```
TecFest26{1_4M_7H3_sh4d3_s1NN3R_W17CH_4nd_4LCH3MY_17_s3LF}
```

Konfirmasi ke binary asli:

```
$ echo 'TecFest26{1_4M_7H3_sh4d3_s1NN3R_W17CH_4nd_4LCH3MY_17_s3LF}' | ./naberius
The Book of Life writes thy name. So it is.
```

Satu-satunya "magic number" di solver yang diambil dari binary: offset bytecode `0x152b80`, panjang `0xb68`, dua tabel opcode, dan konstanta hash. Semuanya terbaca dari static analysis.

## 7. Catatan untuk problem setter (hasil blackbox)

- **Jalur solve realistis untuk peserta:** (a) kenali Go + VM, (b) rekonstruksi handler, (c) tiru VM. Alternatif: **DBI/gdb** pada `check` (`0x492960`) dengan breakpoint di dispatcher untuk dump instruksi terdekripsi, tapi karena `KDF` bergantung pada input, dump hanya valid kalau prefix benar, jadi tetap butuh pendekatan byte-demi-byte.
- **Tidak ada kebutuhan brute-force ke instance** (tidak ada service sama sekali), sesuai aturan guidebook.
- **Kesulitan nyata:** binary Go stripped (tidak ada nama `main.*`, string tanpa xref) dan decompiler Binary Ninja salah membaca beberapa hal. Contoh: shift 32-bit di Go di-*lower* jadi `shr` + `sbb`/`and` (mask), yang oleh pseudo-C terbaca seperti `(x - x)` sehingga terlihat "selalu 0" dan membuat dekripsi instruksi tampak tidak berpengaruh. Ini jebakan alami yang bagus (jangan dipercaya mentah-mentah, cek disassembly).
- Level: menengah-sulit untuk peserta Tecart. Tidak ada anti-debug, jadi gdb jalan normal.
- Saran kecil bila ingin lebih mudah: hapus `strip` (nama `main.*` ikut muncul); bila ingin lebih sulit: buat jumlah byte di tiap `ASSERT` lebih dari 2.
