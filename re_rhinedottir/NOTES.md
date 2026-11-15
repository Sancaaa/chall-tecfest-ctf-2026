# Notes — re_rhinedottir (Reverse Engineering F)

Status: **fungsional, teruji** (Kali WSL2 dan container Docker via seccomp default). Belum ada tester independen dan belum diuji ke model AI whitelist.

## Environment build

- Base image: `ubuntu:22.04`, dipin via digest `sha256:076e7bf82319619f28dd0aa9c02ab34b055ad37100395b4f49a2ffba04fb5e11` (sama dengan `pwn_*`).
- gcc `11.4.0-1ubuntu1~22.04.3`, glibc 2.35 (static).
- Flags: `-O2 -static -no-pie -fcf-protection=none -fno-ipa-icf -fno-asynchronous-unwind-tables -fno-ident -Wl,--build-id=none`, lalu `strip --strip-all`.
- Hasil: `dist/rhinedottir`, 827.872 byte, SHA-256 `dddaa3eb05966e2652383ad8a2badc843bf884ddcdd09406f8b80028e8989d60`.
- **Build reproducible:** dua kali build (`--no-cache`) menghasilkan hash identik.

## Cara build ulang

```
docker build --target out    --output type=local,dest=dist  .
docker build --target author --output type=local,dest=build .
```

`build/` berisi `author.json` (kabel rotor, tabel harapan, salt, alamat call site), `sites.txt`, dan `rhinedottir.unstripped`. `solve.py` membaca `build/author.json`. Aturan sama seperti soal lain: **jangan compile manual di host**.

## Dua pass build (penting)

Salt bergantung pada alamat `syscall` di child, tetapi tabel harapan bergantung pada salt. Karena itu Dockerfile:

1. Pass 1: tabel harapan placeholder `0xA5` (bukan nol), compile, baca alamat label `k_a_ret`/`k_b_ret`/`k_c_ret` dengan `nm`.
2. Pass 2: hitung salt dari alamat, enkripsi flag, isi tabel, compile ulang.
3. Verifikasi: alamat call site sama dan `.text` identik antara pass 1 dan pass 2 (`cmp`). Build gagal kalau tidak.

Bug yang ditemukan saat build:
- Tabel harapan berisi nol masuk `.bss` dan menggeser tata letak (`.text` berbeda). Fix: placeholder bukan-nol.
- Kompiler melipat tabel harapan non-const yang tidak pernah ditulis menjadi konstanta di kode. Fix: pointer tabel disembunyikan dengan `asm volatile("" : "+r"(e))`.

## Hasil uji

| Uji | Hasil |
|---|---|
| `solve.py --bin dist/rhinedottir --negative` (WSL2) | Flag benar DITERIMA, 1 byte salah DITOLAK, panjang salah ditolak |
| Model tanpa `rip` / tanpa autokey | Keduanya menghasilkan sampah (twist terbukti perlu) |
| `strings -a` pada binary | Tidak ada `TecFest`, `Sh0W`, `7RU7h`; hanya pesan prompt |
| Docker (`ubuntu:22.04`, seccomp default) | Flag diterima, `ptrace` tidak diblokir |
| `strace -f ./rhinedottir` | Child mencetak "saksi ketiga" lalu keluar; parent diam (tidak ada pesan menyesatkan) |
| `gdb` default (follow child) | Child gagal `PTRACE_TRACEME`, pesan "saksi ketiga" |
| `gdb` + `set follow-fork-mode parent` | Catchpoint `ptrace` kena di parent; jalur dinamis sah |
| Input EOF | Keluar normal (exit 0) |
| Input salah berulang | Prompt diulang, tidak crash |

## Yang belum

- Tester independen (bukan author) dan uji AI whitelist (paste dekompilasi child dan parent).
- WSL1 / lingkungan tanpa `ptrace` tidak diuji; deskripsi sudah memberi syarat Linux atau WSL2. Pesan error disediakan bila `ptrace` ditolak.
- Baris CSV sudah ada di slot RE F (Naberius pindah ke RE E).
- Nama dan narasi tidak dibuat; deskripsi memakai nama apa adanya.

## Catatan desain

- Tidak ada pengecekan debugger. Kegagalan `strace -f` murni karena satu proses hanya bisa dilacak satu tracer.
- Tidak ada umpan balik per byte: child membandingkan semua respons di akhir.
- Dispatcher jalur rotor di parent berupa state machine dengan satu opaque predicate (flattening ringan).
