# Rhinedottir enigma maCChine — Brief (Reverse Engineering, Hard)

> **Status:** desain final (B-1), sudah diimplementasikan dan lolos uji author. Detail hasil build dan uji ada di `NOTES.md`; yang belum: tester independen dan uji AI.
> **Author:** SancaPWN · **Peran:** soal resmi RE F (Hard). Slot E dipakai Naberius; soal Agus yang sebelumnya di slot E digantikan.
> **Flag:** tersimpan di `flag.txt` (di-gitignore, tidak masuk attachment). Hanya hasil enkripsinya yang ada di binary.

---

## 1. Posisi di lomba

| Item | Isi |
|---|---|
| Kategori / slot | Reverse Engineering F (Hard) |
| Hosting | Statis, hanya attachment. Tanpa `nc`/service |
| Peserta menerima | 1 binary ELF x86-64 (static, stripped, tanpa simbol) + deskripsi |
| Target solve | Tim kuat 2–3 jam dengan bantuan AI tanpa agent. Perkiraan 0–3 tim yang solve |
| Platform peserta | **Linux asli atau WSL2.** Butuh `ptrace`. Tidak untuk WSL1 dan container dengan seccomp yang memblokir ptrace |

## 2. Pembeda dari soal lain

- **Naberius (RE E):** Go, VM kustom, bytecode terenkripsi. Rhinedottir bukan VM dan bukan Go.
- **RE C (Agus):** anti-debug WinAntiDbg. Rhinedottir tidak memeriksa debugger; kegagalan `strace -f` adalah sifat bawaan `ptrace` (satu tracer per proses).
- **Satu mekanisme inti, tanpa tahap-tahap bungkus.**

## 3. Konsep: parent adalah kernel milik child

Binary melakukan `fork`. Child menjalankan program peserta, parent menjadi tracer (`ptrace`) yang mencegat syscall child. Child memanggil **syscall bernomor palsu** (`0x401`, `0x402`); parent mencegatnya, menjalankan operasinya sendiri, lalu mengisi hasil ke `rax` child. Syscall asli (`read`, `write`) dibiarkan lewat.

| | Child | Parent |
|---|---|---|
| Memegang | Input, tabel byte harapan (ciphertext), 3 call site syscall | Kabel rotor, posisi awal, aturan stepping, state rahasia |
| Dibaca sendirian | Syscall bernomor aneh yang tidak masuk akal | Handler tanpa tahu apa inputnya |

### Perangkat parent: mesin rotor ala Enigma di atas 256 simbol

- 3 rotor (permutasi 256 byte), 1 reflector (involusi tanpa titik tetap), stepping ala Enigma dengan **double-step**.
- Tiap byte input dikirim lewat `0x401`; parent mengembalikan byte terenkripsi dan memajukan rotor.
- Child baru membandingkan semua respons dengan tabel harapan di akhir (tanpa keluar lebih awal), jadi **tidak ada umpan balik per byte**.
- `0x402` mereset state; dipanggil tiap prompt baru supaya percobaan ulang konsisten.
- Input salah tidak menghentikan program; child mengulang prompt.

### Dua hal yang membuatnya Hard

1. **Input tersembunyi (`rip` pemanggil).** Parent membaca register child (`PTRACE_GETREGS`) dan menambahkan hash kecil dari `rip` (alamat setelah `syscall`) ke posisi rotor ke-3. Child punya 3 call site berbeda (dipilih dari `indeks % 3`). Model rotor yang tampak benar tetapi mengabaikan pemanggil akan menghasilkan keluaran salah.
2. **Autokey.** Byte plaintext ikut ditambahkan ke posisi rotor ke-3 setelah dienkripsi. State bergantung pada seluruh prefix, jadi tidak bisa dibalik per posisi secara independen, dan solver harus mendekripsi berurutan.

Kabel rotor tidak tersimpan dalam bentuk invers; parent menghitung inversnya saat start. Dispatcher jalur rotor di parent ditulis sebagai state machine (flattening ringan) dengan satu opaque predicate, sebagai penghubung ke topik CSV (control-flow obfuscation).

## 4. Alur penyelesaian yang dimaksud (jangan disalin ke deskripsi peserta)

1. Jalankan binary: hanya ada prompt dan vonis di akhir.
2. `strace -f` menolak (child sudah dilacak parent). Pesan di child memberi tahu ada "saksi ketiga".
3. Dekompilasi child: banyak `syscall` bernomor aneh dengan 3 fungsi pembungkus.
4. Parent: loop tracer, handler `0x401`/`0x402`, mesin rotor.
5. Model peserta tidak cocok dengan hasil asli, lalu ditemukan campuran `rip` dan autokey.
6. Ekstrak kabel rotor dan tabel harapan, hitung salt dari 3 alamat call site, dekripsi berurutan (mesin bersifat reciprocal untuk satu state).

Jalur dinamis yang sah: gdb di parent (nested trace diizinkan), `catch syscall`, atau patch `PTRACE_TRACEME` supaya `strace` bisa dipakai.

## 5. Berkas di folder ini

| Berkas | Fungsi |
|---|---|
| `src/rhinedottir.c` | Sumber C (child + parent) |
| `src/tables.h` | Digenerate oleh `gen.py` (kabel rotor, tabel harapan) |
| `machine.py` | Model referensi mesin (dipakai generator dan solver) |
| `gen.py` | Generator tabel; dua kali jalan karena alamat call site baru diketahui setelah kompilasi |
| `Dockerfile` | Build di container (base Ubuntu 22.04 dipin digest) |
| `solve.py` | Solver author |
| `flag.txt` | Flag (di-gitignore) |
| `Desc.txt`, `Clue.txt` | Deskripsi dan hint bertingkat |
| `dist/rhinedottir` | Attachment peserta (hasil `docker build --output`) |
| `build/` | `author.json`, hasil build author (tidak dibagikan) |
| `NOTES.md`, `WRITEUP.md` | Catatan desain/uji dan penyelesaian |

Aturan dari soal lain berlaku: binary diambil dari container, tidak di-compile manual di host (alamat call site ikut menentukan hasil).

## 6. Rencana QA

- Solver author end-to-end di Docker, plus uji bahwa binary menerima flag dan menolak variasinya.
- Tunjukkan bahwa model tanpa `rip`/autokey gagal.
- `strings`/`grep` pada binary final: tidak boleh ada flag atau potongannya.
- Uji di Ubuntu (container), Kali WSL2, dan Docker dengan seccomp default.
- Tester independen (bukan author) solve dari binary + deskripsi.
- Uji AI: paste dekompilasi child saja, lalu parent saja, ke model whitelist. Lolos bila tidak ada yang menghasilkan flag tanpa bimbingan manusia.

## 7. Hint bertingkat (Open Ticket)

1. "Siapa yang sebenarnya menjawab syscall aneh itu?"
2. "Ada dua proses dalam satu berkas."
3. "Mesin itu mengenali dari mana kamu memanggilnya."

## 8. Risiko

| Risiko | Mitigasi |
|---|---|
| ptrace diblokir di lingkungan peserta | Cantumkan syarat Linux/WSL2 di deskripsi; child dan parent mencetak pesan jelas bila ptrace gagal |
| Terlalu sulit | Longgarkan dengan hint 3, atau turunkan salt `rip` jadi lebih tampak |
| Terlalu mudah (oracle gdb) | Autokey membuat oracle per byte harus berurutan |
| Kompiler menggabungkan atau memindah call site | `-fno-ipa-icf`, `noipa`, dan build memverifikasi alamat sama di dua pass |
| Flag bocor | Hanya ciphertext di binary; cek `strings` sebelum rilis |

## 9. Keputusan yang sudah diambil

- Hanya ELF.
- Tidak tumpang tindih dengan anti-debug RE C Agus.
- Twist `rip` tersembunyi dipakai.
- Tidak ada narasi/lore; nama dipakai apa adanya.
