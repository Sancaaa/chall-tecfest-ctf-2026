# Naberius Chained Book of Life — Write-up & Catatan Author

Kategori: Reverse Engineering (slot E, Hard) · Author: SancaPWN
Flag: lihat `flag.txt` (di-gitignore) dan kolom `Flag` di CSV.
Attachment peserta: **hanya** `dist/naberius` (ELF x86-64, static, stripped).

> Status: draft awal. Go build dan solver sudah lolos tes end-to-end (lihat "Verifikasi").
> Belum dilakukan: QA oleh orang lain, uji paste ke model whitelist, pin digest image.

## Ringkasan

Binary Go meminta satu baris input (58 karakter). Pengecekan dilakukan oleh **stack VM kustom**
yang menjalankan bytecode terenkripsi yang di-embed lewat `go:embed`. Kesulitan datang dari
lapisan-lapisan VM, bukan dari beban membaca decompile Go (satu goroutine, tanpa garble).

Lapisan yang harus dipecahkan peserta:

| # | Lapisan | Efek |
|---|---|---|
| 1 | Dispatch `(byte ^ k) & 15` ke tabel pointer fungsi | Arti byte opcode harus dibaca dari tabel; nibble atas byte opcode adalah noise acak |
| 2 | Rolling key per instruksi | Tidak ada blob bytecode statis yang bisa langsung di-disassemble; dekode harus sinkron dengan state VM |
| 3 | Opcode `PATCH` | Instruksi "umpan" di cipher dikoreksi saat runtime; dekoder yang mengabaikan PATCH desync (sampah) tepat setelah umpan |
| 4 | Dua stage berantai (`SEAL`) | Stage 2 dienkripsi lagi dengan kunci hash dari 29 byte pertama `mem` (setelah SWP). Harus selesaikan stage 1 dulu |
| 5 | `MODE` | Ganti tabel dispatch dan kunci opcode ke tabel B; semua opcode pindah slot |
| 6 | `MIX` (akumulator) | Hasil tiap byte bergantung pada byte-byte sebelumnya (urutan eksekusi), jadi tidak bisa diselesaikan independen |
| 7 | Permutasi SWP + urutan grup diacak | Posisi karakter di flag tidak sama dengan indeks `mem`, dan urutan cek acak |

## Arsitektur VM

Instruksi tetap 4 byte: `[op, a, b, c]`. `mem` = 64 byte (salinan input), stack 8-bit, akumulator `acc` (awal `0x5A`).

| ID | Nama | Semantik |
|---|---|---|
| 0 | PUSH a | push a |
| 1 | LOAD a | push mem[a&63] |
| 2 | ADD | y=pop, x=pop, push x+y |
| 3 | SUB | y=pop, x=pop, push x−y |
| 4 | XOR | y=pop, x=pop, push x^y |
| 5 | ROL a | push rol8(pop, a&7) |
| 6 | MUL | y=pop, x=pop, push x·y (mod 256) |
| 7 | MIX a | x=pop; acc = rol8(acc^x, 1) + a; push acc |
| 8 | CHK a | x=pop; bad \|= x^a; nchk++ |
| 9 | SWP a b | tukar mem[a&63] dan mem[b&63] |
| 10 | PATCH a b c | `code[a\|b<<8] ^= c` (byte cipher) |
| 11 | SEAL a | key = hash(mem[:a]); XOR sisa cipher (setelah SEAL) dengan aliran xorshift32(key) |
| 12 | MODE | pakai tabel B dan kunci opcode B |
| 13 | HALT | berhenti |
| 14 | DROP | pop |
| 15 | NOP | – |

Handler di Go bernama netral `rite0`..`rite15` (indeks = ID di atas). Nama fungsi tetap bisa
dipulihkan dari `gopclntab` walau di-strip, jadi penamaan netral memang disengaja.

### Enkripsi bytecode

Untuk instruksi ke-`i` dengan rolling state `h` (awal `0x4E414245`):

```
ks      = drift(h, i)                      # 4 byte
plain   = cipher[4i:4i+4] ^ ks             # (lapis 2 sudah dibuka oleh SEAL untuk stage 2)
h       = stir(h, le32(plain), i)          # pakai plaintext RUNTIME (setelah patch)
handler = table[sel][(plain[0] ^ k) & 15]
```

Karena `h` memakai plaintext **setelah** patch, dekoder yang melewatkan PATCH tidak sekadar salah
membaca satu instruksi: aliran seluruhnya desync. Itu disengaja: kegagalannya kelihatan, dan
mengarahkan peserta ke handler `rite10`.

Stage 1 (dan prologue SWP) tidak bergantung pada input, jadi bisa didekode penuh tanpa tahu flag.
Stage 2 hanya terbuka bila kunci `SEAL` benar, yaitu hash dari `mem[:29]` setelah SWP.

### Struktur program

```
[ prologue: SWP... ]                          # permutasi 58 posisi
[ stage 1: 29 grup, urutan acak ]             # tabel A
SEAL 29
MODE
[ stage 2: 29 grup, urutan acak ]             # tabel B
HALT
```

Satu grup (satu byte `mem[j]`): `LOAD j`, 4–6 transformasi (XOR/ADD/SUB/ROL/MUL dengan konstanta,
tepat satu `MIX`), lalu `CHK target`. Junk (`PUSH;DROP`, `LOAD;DROP`, `NOP`) disisipkan acak.
`PATCH` juga bisa nyempil di tengah pasangan `PUSH;op`.

Sukses jika `bad == 0`, `nchk == 58`, `HALT` tercapai, dan stack kosong.

## Jalur solve (intended)

1. Binary Go di-strip tetapi `gopclntab` utuh. Pulihkan nama fungsi (GoReSym atau skrip Ghidra Go),
   temukan `main.main` → `verify` → `newVM` → `run`, dan variabel `book` (`go:embed`, ±2,9 KB).
2. Baca `run`: loop fetch–decode–dispatch. Temukan dua hal: rolling key (`drift`/`stir`) dan
   dispatch `table[(op ^ k) & 15]`. Ambil dua tabel (`tableA`, `tableB`) dan `kA`, `kB`.
3. Tulis dekoder. Handler `rite10` (PATCH) harus diterapkan, atau aliran desync.
4. Dekode stage 1 lengkap: SWP (prologue), lalu grup LOAD..CHK. Parse tiap grup dan invert
   transformasinya dari `CHK target` ke belakang. `MIX` dibalik dengan
   `x = ror8(acc_new − a, 1) ^ acc_old`, jadi grup harus diproses sesuai urutan eksekusi.
5. Setelah 29 byte `mem[:29]` ketemu, hitung kunci `SEAL` (`binding`) dan buka stage 2.
   `MODE` mengganti ke tabel B / `kB`; dekoder yang memakai tabel A akan gagal.
6. Invert stage 2 dengan cara yang sama (akumulator berlanjut dari stage 1).
7. Batalkan permutasi SWP (`flag[perm[j]] = mem[j]`). Hasilnya flag. Bisa diverifikasi dengan
   menjalankan binary.

`solve.py` melakukan alur itu. Pakai: `python solve.py dist/naberius`.

## Verifikasi (sudah dijalankan)

- `python gen.py` → selftest: flag benar lolos, 58 mutasi satu byte dan 50 input acak ditolak
  (simulator referensi `vmsim.py`).
- `python solve.py dist/naberius` → mengekstrak blob dari binary dan mencetak flag yang benar.
- Binary Go (Docker `golang:1.23-bookworm`, dijalankan di container Alpine): dari 63 kasus
  (flag benar, 58 mutasi satu byte, input kosong/pendek/terlalu panjang) hanya flag benar yang lolos.
- Binary tidak mengandung string `TecFest26` (flag tidak ada di data; yang ada hanya cipher).

## Build ulang

```bash
python gen.py                                           # tulis src/book.bin + src/tables_gen.go + build/*
docker build --target out --output type=local,dest=dist .
python solve.py dist/naberius                            # harus mencetak flag
```

Seed tetap (`SEED` di `gen.py`) sehingga bytecode reproducible. Ganti `SEED` bila ingin tabel,
permutasi, dan konstanta yang berbeda. Setelah ganti flag/seed, **jalankan ulang ketiga langkah di atas**
dan salin ulang `dist/naberius` ke CTFd.

## Checklist verifikasi manual (belum)

- [ ] Pin base image Docker via digest (`golang:1.23-bookworm@sha256:...`) di `Dockerfile`
- [ ] Tester lain (bukan author) solve hanya dari `dist/naberius` + `Desc.txt`
- [ ] Uji paste decompile ke model whitelist (GPT-5.6 Instant, Claude Sonnet 5.5, Gemini 3.6 Flash,
      DeepSeek-V3.2). Perkiraan solve dengan AI: ±1,5–2,5 jam. Kalau ada model yang selesai
      dalam < 45 menit, tambah kesulitan (lihat "Knob kesulitan")
- [ ] Jalankan binary di mesin yang bukan environment build (glibc tidak relevan: static)
- [ ] Pastikan `dist/` yang dilampirkan hanya berisi `naberius` (tanpa `build/`, `src/`, `gen.py`)
- [ ] Isi CSV: Nama, Topik, Intended Solution, Flag, Attachment = `naberius`

## Knob kesulitan

Lebih mudah:
- Kurangi `N_PATCH_STAGE` di `gen.py` (default 12 per stage).
- Hapus rolling key (ubah `drift` jadi konstanta) → tidak perlu emulasi sinkron.
- Jadikan nama handler deskriptif (`GO_NAMES`).

Lebih sulit:
- Buat satu opcode lagi yang hasilnya bergantung pada byte flag sebelumnya (selain `MIX`).
- Patch lintas stage (PATCH di stage 1 mengubah byte stage 2), membuat dekode stage 2 dari
  cipher mentah salah secara senyap.
- Sembunyikan tabel (hitung slot dengan permutasi turunan seed, bukan array literal).

## Hint bertingkat

Lihat `Clue.txt`.
