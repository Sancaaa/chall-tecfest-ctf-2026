#!/usr/bin/env python3
"""Solver re_naberius: emulasi VM kecil di dalam binary, lalu cari input byte-per-byte.

Pakai:  python solve.py [path/ke/naberius]
"""
import sys, struct, itertools

M = 0xFFFFFFFF
LEN = 58                                   # panjang flag (dicek binary: 0x3a)
elf = open(sys.argv[1] if len(sys.argv) > 1 else "naberius", "rb").read()
CODE = elf[0x152b80:0x152b80 + 0xb68]      # bytecode terenkripsi (slice global di .noptrdata)

# nibble -> opcode. Tabel ke-2 aktif setelah opcode SWITCH.
T = [["HALT","SWITCH","ASSERT","LOAD","KDF","SUB","POP","PATCH","NOP","MUL","ADD","SWAP","XOR","MAC","PUSH","ROL"],
     ["ASSERT","PUSH","SWAP","MAC","NOP","LOAD","SUB","MUL","SWITCH","POP","XOR","PATCH","ROL","ADD","HALT","KDF"]]

rol32 = lambda x, n: ((x << n) | (x >> (32 - n))) & M
rol8  = lambda x, n: ((x << (n & 7)) | (x >> (8 - (n & 7)))) & 0xFF

def fmix(g):                               # murmur3 finalizer
    g ^= g >> 16; g = g * 0x85ebca6b & M
    g ^= g >> 13; g = g * 0xc2b2ae35 & M
    return g ^ (g >> 16)

def run(flag, stop=None):
    buf, idx = bytearray(flag.ljust(64, b"\0")), list(range(64))   # idx = posisi asli tiap byte
    code, h, key, sel, mac = bytearray(CODE), 0x4e414245, 0x60, 0, 0x5a
    st, loads, res, pc = [], [], [], 0
    while pc < len(code) // 4:
        g = fmix((pc * 0x9e3779b1 & M) ^ h)
        b = [(g >> (8 * i) & 0xFF) ^ code[pc * 4 + i] for i in range(4)]   # dekripsi 1 instruksi
        h = (pc + rol32(struct.unpack("<I", bytes(b))[0] ^ h, 7) * 0x1000193) & M
        pc += 1
        op, x, y, z = T[sel][(key ^ b[0]) & 0xF], b[1], b[2], b[3]
        pop = lambda: st.pop() if st else 0
        if   op == "HALT": break
        elif op == "PUSH": st.append(x)
        elif op == "LOAD": st.append(buf[x & 63]); loads.append(idx[x & 63])
        elif op == "POP":  pop()
        elif op == "ADD":  a, c = pop(), pop(); st.append((c + a) & 255)
        elif op == "SUB":  a, c = pop(), pop(); st.append((c - a) & 255)
        elif op == "MUL":  a, c = pop(), pop(); st.append(c * a & 255)
        elif op == "XOR":  a, c = pop(), pop(); st.append(c ^ a)
        elif op == "ROL":  st.append(rol8(pop(), x))
        elif op == "MAC":  mac = (rol8(mac ^ pop(), 1) + x) & 255; st.append(mac)
        elif op == "SWAP": i, j = x & 63, y & 63; buf[i], buf[j] = buf[j], buf[i]; idx[i], idx[j] = idx[j], idx[i]
        elif op == "PATCH":
            if (x | y << 8) < len(code): code[x | y << 8] ^= z
        elif op == "SWITCH": sel, key = 1, 0x5e
        elif op == "KDF":                  # xorshift32 stream, seed = hash n byte input pertama
            s = 0x811c9dc5
            for c in buf[:min(x, 64)]: s = (s ^ c) * 0x1000193 & M
            s ^= s >> 16; s = s * 0x7feb352d & M; s ^= s >> 15; s = s * 0x846ca68b & M; s ^= s >> 16
            s |= 1
            for i in range(pc * 4, len(code)):
                s ^= s << 13 & M; s ^= s >> 17; s ^= s << 5 & M; code[i] ^= s & 255
        elif op == "ASSERT":
            res.append((pop() == x, loads)); loads = []
            if stop is not None and len(res) > stop: break
    return res

def solve(known):
    flag = bytearray(LEN)
    for i, c in known.items(): flag[i] = c
    res = run(bytes(flag))
    bad = next((k for k, (ok, _) in enumerate(res) if not ok), None)
    if bad is None: return known if len(res) == LEN else None
    unk = [i for i in dict.fromkeys(res[bad][1]) if i not in known]     # byte yang baru dimuat di cek ini
    if not unk or len(unk) > 2: return None
    for guess in itertools.product(range(32, 127), repeat=len(unk)):
        k2 = {**known, **dict(zip(unk, guess))}
        f = bytearray(LEN)
        for i, c in k2.items(): f[i] = c
        r = run(bytes(f), stop=bad)
        if len(r) > bad and r[bad][0] and (out := solve(k2)): return out
    return None

known = {i: c for i, c in enumerate(b"TecFest26{")}; known[LEN - 1] = ord("}")
ans = solve(known)
print(bytes(ans[i] for i in range(LEN)).decode())
