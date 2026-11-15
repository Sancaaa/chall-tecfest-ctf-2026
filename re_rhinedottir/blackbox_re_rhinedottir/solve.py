#!/usr/bin/env python3
# Solver re_rhinedottir. Pakai: python solve.py rhinedottir
import sys

d = open(sys.argv[1] if len(sys.argv) > 1 else "rhinedottir", "rb").read()

REFL   = d[0x99180:0x99180 + 256]                        # reflektor
ROT    = [d[0x99280 + 256 * i:0x99280 + 256 * (i + 1)] for i in range(3)]  # 3 rotor
TARGET = d[0xc6100:0xc6100 + 58]                         # ciphertext yang dibandingkan
RIPS   = [0x401b18, 0x401b28, 0x401b38]                  # alamat setelah `syscall` di 3 wrapper
INV    = [{v: j for j, v in enumerate(r)} for r in ROT]  # rotor kebalikan


def step(p, ch, rip):
    """Tiru satu syscall 0x401 milik tracer. Return (byte keluar, state baru)."""
    p0, p1, p2 = p
    h = (rip >> 4) ^ (rip >> 12)
    if p1 == 7:
        p1, e = 8, (p2 + 1) & 255
    else:
        e = p2
        if p0 == 0x2A:
            p1 = (p1 + 1) & 255
    pp = [(p0 + 1) & 255, p1, (h + e) & 255]
    b = ch
    for k in range(3):                                   # rotor 0 -> 1 -> 2
        b = (ROT[k][(b + pp[k]) & 255] - pp[k]) & 255
    b = REFL[b]                                          # pantul
    for k in (2, 1, 0):                                  # rotor 2 -> 1 -> 0 (inverse)
        b = (INV[k][(pp[k] + b) & 255] - pp[k]) & 255
    pp[2] = (ch + pp[2]) & 255                           # autokey: plaintext ikut memutar rotor 2
    return b, pp


state, flag = [0x0E, 0x07, 0xB5], ""
for i, want in enumerate(TARGET):
    for c in range(256):                                 # state hanya bergantung plaintext -> tebak per huruf
        b, nxt = step(state, c, RIPS[i % 3])
        if b == want:
            flag += chr(c)
            state = nxt
            break
print(flag)
