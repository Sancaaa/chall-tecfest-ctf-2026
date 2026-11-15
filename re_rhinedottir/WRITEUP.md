# Writeup — Rhinedottir enigma maCChine (RE Hard)

> Dokumen author. Jangan dibagikan ke peserta.

## Ringkasan

Satu ELF static stripped yang `fork`: child menjalankan prompt, parent adalah tracer (`ptrace`) yang menjadi "kernel" child. Child memanggil syscall bernomor palsu `0x401` (enkripsi satu byte) dan `0x402` (reset), parent menjawabnya dengan mesin rotor Enigma-like di atas 256 simbol. Flag adalah input yang tiap byte-nya, setelah melewati mesin, sama dengan tabel harapan di child.

## Langkah

1. **Observasi.** Program hanya menampilkan prompt dan vonis. `strace -f` gagal dengan pesan "saksi ketiga" karena child sudah dilacak parent (satu tracer per proses). Di gdb: `set follow-fork-mode parent`.
2. **Child.** Dekompilasi `main`/fungsi child: input dibaca dengan `read`, panjang harus 58, tiap byte dikirim lewat salah satu dari tiga fungsi pembungkus `syscall` (dipilih `indeks % 3`) dengan nomor `0x401`; respons dikumpulkan lalu dibandingkan dengan tabel 58 byte di `.data` tanpa keluar lebih awal. `0x402` dipanggil sekali per percobaan.
3. **Parent.** Loop `PTRACE_SYSCALL`; pada syscall-entry dengan `orig_rax == 0x401/0x402`, parent menjalankan operasi sendiri, mengubah `orig_rax` menjadi `-1` agar kernel melewatkannya, dan mengisi `rax` pada syscall-exit.
4. **Mesin.** Tiga rotor 256 simbol (`ROT`), satu reflector tanpa titik tetap (`REFL`), invers dihitung saat start. Stepping ala Enigma: jika `pos[1] == N1` → double-step (`pos[1]++`, `pos[2]++`); jika `pos[0] == N0` → carry ke `pos[1]`; lalu `pos[0]++`. Jalur sinyal ditulis sebagai state machine dengan satu opaque predicate yang tidak pernah aktif.
5. **Jebakan.** Model yang hanya meniru rotor menghasilkan sampah, karena:
   - parent memakai `rip` pemanggil (`GETREGS`): `salt = ((rip >> 4) ^ (rip >> 12)) & 0xff` ditambahkan ke `pos[2]` setelah `kstep()`; alamat setelah `syscall` pada tiga call site berbeda;
   - parent menambahkan **plaintext** ke `pos[2]` setelah enkripsi (autokey), sehingga dekripsi harus berurutan.
6. **Solusi.** Ambil `ROT`, `REFL`, `N0`, `N1`, posisi awal dari parent; tabel `EXP` dari child; tiga alamat call site dari fungsi pembungkus (alamat instruksi setelah `syscall`). Lalu dekripsi berurutan: per byte, `step` → `pos[2] += salt` → `x = path(y)` → `pos[2] += x`. `solve.py` melakukan persis ini dari `build/author.json`.

## Jalur dinamis (alternatif sah)

Break di handler parent (gdb, `follow-fork-mode parent`) untuk melihat keluaran per byte untuk input yang dipilih sendiri. Autokey membuat oracle ini harus dijalankan berurutan per posisi, tetapi tetap bisa diotomasi.

## Verifikasi

`python3 solve.py --bin dist/rhinedottir --negative` (di Linux/WSL): flag benar diterima, satu byte salah ditolak, model tanpa `rip` dan model tanpa autokey menghasilkan sampah.
