#!/usr/bin/env python3
"""Generator Naberius Chained Book of Life.

Membaca flag.txt, merakit program bytecode VM, mengenkripsinya, lalu menulis:
  src/book.bin        blob bytecode terenkripsi (di-embed ke binary Go)
  src/tables_gen.go   dua tabel dispatch (A dan B) + kunci opcode
  build/params.json   parameter yang bisa diekstrak peserta dari binary (dipakai solve.py)
  build/author.json   rahasia author (permutasi, daftar patch)
  build/disasm.txt    listing program lengkap untuk verifikasi manual

Seed tetap, jadi hasil reproducible. Ubah SEED untuk instance berbeda.
Jalankan:  python gen.py
"""

import json
import os
import random
import sys

from naberius_spec import *
import vmsim

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20261109
rng = random.Random(SEED)

N_PATCH_STAGE = 12   # jumlah instruksi "umpan" yang dikoreksi PATCH, per stage


# --------------------------------------------------------------------------- tabel dispatch
def gen_tables():
    a = list(range(16))
    rng.shuffle(a)
    while True:
        b = list(range(16))
        rng.shuffle(b)
        # tiap opcode harus pindah slot saat MODE, supaya disassembler stage 1 tidak bisa dipakai ulang
        if all(a.index(op) != b.index(op) for op in range(16)):
            break
    return a, b


TAB_A, TAB_B = gen_tables()
K_A = rng.randrange(256)
K_B = rng.randrange(256)
TABS = {"A": TAB_A, "B": TAB_B}
KEYS = {"A": K_A, "B": K_B}


# --------------------------------------------------------------------------- instruksi
class Ins:
    def __init__(self, op, a=None, b=None, c=None, tab="A"):
        self.op = op
        self.a = rng.randrange(256) if a is None else a & 0xFF
        self.b = rng.randrange(256) if b is None else b & 0xFF
        self.c = rng.randrange(256) if c is None else c & 0xFF
        self.tab = tab
        self.hi = rng.randrange(16)       # nibble atas byte opcode: noise, tidak dipakai dispatcher
        self.stored_a = None              # nilai `a` (umpan) di cipher bila instruksi ini dipatch
        self.patch_target = None          # untuk instruksi PATCH: Ins yang dikoreksi
        self.delta = 0

    def op_byte(self):
        slot = TABS[self.tab].index(self.op)
        return ((slot ^ (KEYS[self.tab] & 15)) & 15) | (self.hi << 4)

    def real(self):
        return bytes([self.op_byte(), self.a, self.b, self.c])

    def stored(self):
        a = self.a if self.stored_a is None else self.stored_a
        return bytes([self.op_byte(), a, self.b, self.c])


def junk(tab):
    r = rng.random()
    if r < 0.5:
        return [Ins(OP_PUSH, a=rng.randrange(256), tab=tab), Ins(OP_DROP, tab=tab)]
    if r < 0.8:
        return [Ins(OP_NOP, tab=tab)]
    return [Ins(OP_LOAD, a=rng.randrange(MEM_SIZE), tab=tab), Ins(OP_DROP, tab=tab)]


def make_group(j, val, acc, tab):
    """Satu byte flag: LOAD j, rantai transformasi (tepat satu MIX), CHK target."""
    kinds = [rng.choice(["xor", "add", "sub", "rol", "mul"]) for _ in range(rng.randint(3, 5))]
    kinds.insert(rng.randint(0, len(kinds)), "mix")
    out = [Ins(OP_LOAD, a=j, tab=tab)]
    v = val
    for kd in kinds:
        if kd == "xor":
            c = rng.randint(1, 255)
            atom = [Ins(OP_PUSH, a=c, tab=tab), Ins(OP_XOR, tab=tab)]
            v ^= c
        elif kd == "add":
            c = rng.randint(1, 255)
            atom = [Ins(OP_PUSH, a=c, tab=tab), Ins(OP_ADD, tab=tab)]
            v = (v + c) & 0xFF
        elif kd == "sub":
            c = rng.randint(1, 255)
            atom = [Ins(OP_PUSH, a=c, tab=tab), Ins(OP_SUB, tab=tab)]
            v = (v - c) & 0xFF
        elif kd == "rol":
            r = rng.randint(1, 7)
            atom = [Ins(OP_ROL, a=r, tab=tab)]
            v = rol8(v, r)
        elif kd == "mul":
            m = rng.randrange(3, 256, 2)           # ganjil -> bijektif mod 256
            atom = [Ins(OP_PUSH, a=m, tab=tab), Ins(OP_MUL, tab=tab)]
            v = (v * m) & 0xFF
        else:  # mix
            imm = rng.randrange(256)
            atom = [Ins(OP_MIX, a=imm, tab=tab)]
            acc = (rol8(acc ^ v, 1) + imm) & 0xFF
            v = acc
        out += atom
        if rng.random() < 0.12:
            out += junk(tab)
    out.append(Ins(OP_CHK, a=v, tab=tab))
    return out, acc


def make_swaps(perm, tab):
    """Swap sehingga mem_post[j] = flag[perm[j]] (selection sort)."""
    cur = list(range(len(perm)))
    out = []
    for j in range(len(perm)):
        p = cur.index(perm[j])
        if p != j:
            out.append(Ins(OP_SWP, a=j, b=p, tab=tab))
            cur[j], cur[p] = cur[p], cur[j]
        if rng.random() < 0.10:
            out += junk(tab)
    return out


def plan_patches(lst, n):
    """Pilih n instruksi (PUSH/ROL/MIX) sebagai umpan, sisipkan PATCH di depannya."""
    cands = [k for k, ins in enumerate(lst)
             if ins.op in (OP_PUSH, OP_ROL, OP_MIX) and k >= 8]
    targets = [lst[k] for k in rng.sample(cands, n)]
    patches = []
    for t in targets:
        d = rng.randint(1, 255)
        if t.op == OP_ROL:
            d = (d & ~7) | rng.randint(1, 7)       # pastikan umpan ROL memang beda
        t.stored_a = t.a ^ d
        t.delta = d
        patches.append(Ins(OP_PATCH, tab=t.tab))
        patches[-1].patch_target = t
        patches[-1].c = d
    for pins in patches:
        t = pins.patch_target
        idx = next(k for k, x in enumerate(lst) if x is t)
        pos = rng.randint(max(0, idx - 60), idx - 3)
        lst.insert(pos, pins)
    return patches


# --------------------------------------------------------------------------- perakitan
def build(flag):
    assert len(flag) == FLAG_LEN, f"flag harus {FLAG_LEN} byte, dapat {len(flag)}"
    perm = list(range(FLAG_LEN))
    rng.shuffle(perm)
    mem_post = bytes(flag[perm[j]] for j in range(FLAG_LEN))   # isi mem setelah swap

    order1 = list(range(0, HALF)); rng.shuffle(order1)
    order2 = list(range(HALF, FLAG_LEN)); rng.shuffle(order2)

    acc = ACC0
    stage1 = make_swaps(perm, "A")
    for j in order1:
        grp, acc = make_group(j, mem_post[j], acc, "A")
        stage1 += grp
    stage2 = []
    for j in order2:
        grp, acc = make_group(j, mem_post[j], acc, "B")
        stage2 += grp

    patches = plan_patches(stage1, N_PATCH_STAGE) + plan_patches(stage2, N_PATCH_STAGE)

    seal = Ins(OP_SEAL, a=HALF, tab="A")
    mode = Ins(OP_MODE, tab="A")
    halt = Ins(OP_HALT, tab="B")
    full = stage1 + [seal, mode] + stage2 + [halt]

    index = {id(x): k for k, x in enumerate(full)}
    for p in patches:
        off = INS_SIZE * index[id(p.patch_target)] + 1       # byte operand `a` target
        p.a, p.b = off & 0xFF, off >> 8

    # enkripsi: lapis 1 (rolling per instruksi), lapis 2 (stage 2 pakai kunci dari separuh flag)
    h = H0
    cipher = bytearray(INS_SIZE * len(full))
    for i, ins in enumerate(full):
        st = ins.stored()
        ksb = keystream(h, i)
        cipher[4 * i:4 * i + 4] = bytes(st[j] ^ ksb[j] for j in range(4))
        h = hmix(h, int.from_bytes(ins.real(), "little"), i)
    seal_idx = index[id(seal)]
    key = seal_key(mem_post[:HALF])
    start = INS_SIZE * (seal_idx + 1)
    ks2 = stream2(key, len(cipher) - start)
    for j in range(len(ks2)):
        cipher[start + j] ^= ks2[j]

    return bytes(cipher), full, patches, perm, mem_post, seal_idx, key


# --------------------------------------------------------------------------- output
def write_go_tables(path):
    def block(name, tab):
        lines = [f"func {name}() [16]handler {{", "\treturn [16]handler{"]
        for slot, op in enumerate(tab):
            lines.append(f"\t\t(*vm).{GO_NAMES[op]}, // slot {slot:2d}")
        lines += ["\t}", "}", ""]
        return "\n".join(lines)

    src = ("// Dihasilkan oleh gen.py. Jangan diedit manual.\n"
           "package main\n\n"
           f"const (\n\tkA byte = 0x{K_A:02X}\n\tkB byte = 0x{K_B:02X}\n)\n\n"
           + block("tableA", TAB_A) + block("tableB", TAB_B))
    with open(path, "w", newline="\n") as f:
        f.write(src)


def write_disasm(path, full, patches, seal_idx):
    patched = {id(p.patch_target): p for p in patches}
    with open(path, "w", newline="\n") as f:
        f.write("# idx  tab  op      a  b  c   catatan\n")
        for i, ins in enumerate(full):
            note = ""
            if id(ins) in patched:
                note = f"UMPAN di cipher a=0x{ins.stored_a:02X} (dipatch -> 0x{ins.a:02X})"
            if ins.op == OP_PATCH:
                t = ins.patch_target
                note = f"-> byte {INS_SIZE * full.index(t) + 1} (ins #{full.index(t)}) ^= 0x{ins.c:02X}"
            if i == seal_idx:
                note = "SEAL: stage 2 terenkripsi lagi dengan kunci dari mem[:29]"
            f.write(f"{i:4d}  {ins.tab}    {OP_NAMES[ins.op]:<6} "
                    f"{ins.a:02X} {ins.b:02X} {ins.c:02X}   {note}\n")


def selftest(cipher, flag):
    vm = vmsim.VM(cipher, TAB_A, TAB_B, K_A, K_B)
    assert vm.run(flag), "flag benar harus lolos"
    for i in range(len(flag)):                       # tiap byte harus ikut menentukan hasil
        bad = bytearray(flag)
        bad[i] ^= 1 << rng.randrange(8)
        assert not vm.run(bytes(bad)), f"mutasi byte {i} masih lolos"
    for _ in range(50):
        junk_in = bytes(rng.randrange(32, 127) for _ in range(FLAG_LEN))
        assert not vm.run(junk_in)
    print("selftest OK: flag benar lolos, 58 mutasi + 50 acak ditolak")


def main():
    flag_path = os.path.join(HERE, "flag.txt")
    flag = open(flag_path, "rb").read().strip()
    cipher, full, patches, perm, mem_post, seal_idx, key = build(flag)

    os.makedirs(os.path.join(HERE, "src"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    with open(os.path.join(HERE, "src", "book.bin"), "wb") as f:
        f.write(cipher)
    write_go_tables(os.path.join(HERE, "src", "tables_gen.go"))
    write_disasm(os.path.join(HERE, "build", "disasm.txt"), full, patches, seal_idx)

    with open(os.path.join(HERE, "build", "params.json"), "w") as f:
        json.dump({"tab_a": TAB_A, "tab_b": TAB_B, "k_a": K_A, "k_b": K_B,
                   "h0": H0, "acc0": ACC0, "blob_len": len(cipher)}, f, indent=1)
    with open(os.path.join(HERE, "build", "author.json"), "w") as f:
        json.dump({"seed": SEED, "perm": perm, "seal_index": seal_idx,
                   "seal_key": f"0x{key:08X}", "n_instr": len(full),
                   "n_patch": len(patches)}, f, indent=1)

    selftest(cipher, flag)
    print(f"instruksi: {len(full)}  blob: {len(cipher)} byte  patch: {len(patches)}  seed: {SEED}")
    print("ditulis: src/book.bin src/tables_gen.go build/params.json build/author.json build/disasm.txt")


if __name__ == "__main__":
    sys.exit(main())
