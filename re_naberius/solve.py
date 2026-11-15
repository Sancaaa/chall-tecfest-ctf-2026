#!/usr/bin/env python3
"""Solver Naberius Chained Book of Life (sisi author).

Meniru jalur solve peserta:
  1. ekstrak blob dari binary (di sini dicari lewat prefix src/book.bin; peserta lewat xref go:embed)
  2. emulasi VM tanpa data: dekode instruksi + terapkan PATCH + ganti tabel saat MODE
     (stage 1 tidak bergantung input, jadi bisa didekode penuh)
  3. invert tiap grup (LOAD..CHK) secara berurutan, lacak akumulator MIX
  4. hitung kunci SEAL dari separuh flag yang sudah ketemu -> buka stage 2 -> ulangi
  5. batalkan permutasi SWP

Pemakaian: python solve.py [dist/naberius]
"""

import json
import os
import sys

from naberius_spec import *

HERE = os.path.dirname(os.path.abspath(__file__))


class Decoder:
    """Dekoder streaming yang sinkron dengan VM: rolling key, PATCH, SEAL, MODE."""

    def __init__(self, cipher, params):
        self.code = bytearray(cipher)
        self.tabs = [params["tab_a"], params["tab_b"]]
        self.ks = [params["k_a"], params["k_b"]]
        self.h, self.pc, self.sel = params["h0"], 0, 0

    def done(self):
        return self.pc * INS_SIZE >= len(self.code)

    def step(self):
        i = self.pc
        p = i * INS_SIZE
        ksb = keystream(self.h, i)
        w = bytes(self.code[p + j] ^ ksb[j] for j in range(4))
        self.h = hmix(self.h, int.from_bytes(w, "little"), i)
        self.pc += 1
        op = self.tabs[self.sel][(w[0] ^ self.ks[self.sel]) & 15]
        a, b, c = w[1], w[2], w[3]
        if op == OP_PATCH:                      # umpan pada cipher dikoreksi saat runtime
            off = a | (b << 8)
            if off < len(self.code):
                self.code[off] ^= c
        elif op == OP_MODE:
            self.sel = 1
        return op, a, b, c

    def seal(self, key):
        start = self.pc * INS_SIZE
        ks2 = stream2(key, len(self.code) - start)
        for j in range(len(ks2)):
            self.code[start + j] ^= ks2[j]


def read_until(dec, stop_ops):
    out = []
    while not dec.done():
        ins = dec.step()
        out.append(ins)
        if ins[0] in stop_ops:
            break
    return out


def solve_groups(ops, acc, mem):
    """Parse grup LOAD ... CHK dan invert. mem[j] diisi nilai byte hasil invert."""
    ops = [o for o in ops if o[0] != OP_PATCH]   # PATCH sudah diterapkan Decoder; bisa nyempil di tengah pasangan
    k = 0
    while k < len(ops):
        op, a, _, _ = ops[k]
        if op != OP_LOAD or (k + 1 < len(ops) and ops[k + 1][0] == OP_DROP):
            k += 1                              # bukan awal grup (SWP/junk/PATCH/dll.)
            continue
        j = a & 63
        k += 1
        steps = []                              # transformasi berurutan
        while ops[k][0] != OP_CHK:
            op, a, _, _ = ops[k]
            if op == OP_PUSH and ops[k + 1][0] in (OP_XOR, OP_ADD, OP_SUB, OP_MUL):
                steps.append((ops[k + 1][0], a))
                k += 2
            elif op == OP_PUSH and ops[k + 1][0] == OP_DROP:
                k += 2                          # junk
            elif op == OP_LOAD and ops[k + 1][0] == OP_DROP:
                k += 2                          # junk
            elif op in (OP_ROL, OP_MIX):
                steps.append((op, a))
                k += 1
            elif op == OP_NOP:
                k += 1
            else:
                raise ValueError(f"pola tak dikenal di ops[{k}]: {ops[k]}")
        v = ops[k][1]                           # target CHK
        k += 1
        acc_in = acc
        for op, a in reversed(steps):
            if op == OP_XOR:
                v ^= a
            elif op == OP_ADD:
                v = (v - a) & 0xFF
            elif op == OP_SUB:
                v = (v + a) & 0xFF
            elif op == OP_ROL:
                v = ror8(v, a)
            elif op == OP_MUL:
                v = (v * pow(a, -1, 256)) & 0xFF
            elif op == OP_MIX:
                acc = v                          # nilai setelah MIX = akumulator baru
                v = ror8((v - a) & 0xFF, 1) ^ acc_in
        mem[j] = v
    return acc


def apply_swaps(ops, n=MEM_SIZE):
    """perm[j] = indeks flag asli yang berada di mem[j] setelah semua SWP."""
    perm = list(range(n))
    for op, a, b, _ in ops:
        if op == OP_SWP:
            a, b = a & 63, b & 63
            perm[a], perm[b] = perm[b], perm[a]
    return perm


def main():
    params = json.load(open(os.path.join(HERE, "build", "params.json")))
    book = open(os.path.join(HERE, "src", "book.bin"), "rb").read()
    binpath = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "dist", "naberius")
    if os.path.exists(binpath):                  # ambil blob langsung dari binary
        data = open(binpath, "rb").read()
        off = data.find(book[:32])
        assert off >= 0, "blob tidak ditemukan di binary"
        cipher = data[off:off + params["blob_len"]]
        assert cipher == book, "blob di binary berbeda dari src/book.bin"
        print(f"[+] blob {len(cipher)} byte ditemukan di {binpath} @ 0x{off:x}")
    else:
        cipher = book
        print("[!] binary tidak ada, memakai src/book.bin")

    dec = Decoder(cipher, params)
    mem = [0] * MEM_SIZE

    ops1 = read_until(dec, {OP_SEAL})
    seal_op = ops1[-1]
    assert seal_op[0] == OP_SEAL
    print(f"[+] stage 1: {len(ops1)} instruksi, SEAL n={seal_op[1]}")
    perm = apply_swaps(ops1)
    acc = solve_groups(ops1[:-1], params["acc0"], mem)

    key = seal_key(bytes(mem[:seal_op[1]]))
    print(f"[+] kunci SEAL = 0x{key:08X}  (separuh pertama: {bytes(mem[:HALF])!r})")
    dec.seal(key)

    ops2 = read_until(dec, {OP_HALT})
    assert ops2[0][0] == OP_MODE and ops2[-1][0] == OP_HALT, "stage 2 tidak terbuka"
    print(f"[+] stage 2: {len(ops2)} instruksi")
    solve_groups(ops2, acc, mem)

    flag = bytearray(FLAG_LEN)
    for j in range(FLAG_LEN):
        flag[perm[j]] = mem[j]
    print("[+] flag:", flag.decode())


if __name__ == "__main__":
    main()
