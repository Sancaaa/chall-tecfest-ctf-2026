"""Spesifikasi bersama VM "Naberius Chained Book of Life".

Dipakai gen.py (assembler + enkripsi), vmsim.py (VM referensi Python), dan solve.py.
Semua primitif di sini HARUS identik dengan implementasi Go di src/vm.go.
"""

MASK = 0xFFFFFFFF

H0 = 0x4E414245          # state awal rolling key ("NABE")
ACC0 = 0x5A              # akumulator awal untuk opcode MIX
FLAG_LEN = 58            # panjang flag (TecFest26{...})
HALF = 29                # separuh pertama (stage 1), separuh kedua (stage 2)
MEM_SIZE = 64            # memori kerja VM (salinan input)
INS_SIZE = 4             # tiap instruksi: [op, a, b, c]

# ID logis opcode. Byte opcode di bytecode BUKAN ID ini; lihat tabel dispatch.
(OP_PUSH, OP_LOAD, OP_ADD, OP_SUB, OP_XOR, OP_ROL, OP_MUL, OP_MIX,
 OP_CHK, OP_SWP, OP_PATCH, OP_SEAL, OP_MODE, OP_HALT, OP_DROP, OP_NOP) = range(16)

OP_NAMES = ["PUSH", "LOAD", "ADD", "SUB", "XOR", "ROL", "MUL", "MIX",
            "CHK", "SWP", "PATCH", "SEAL", "MODE", "HALT", "DROP", "NOP"]

GO_NAMES = [f"rite{i}" for i in range(16)]   # nama netral: pclntab Go tetap membocorkan nama fungsi


def rol8(x, r):
    r &= 7
    x &= 0xFF
    return x if r == 0 else ((x << r) | (x >> (8 - r))) & 0xFF


def ror8(x, r):
    return rol8(x, (8 - (r & 7)) & 7)


def rol32(x, r):
    return ((x << r) | (x >> (32 - r))) & MASK


def keystream(h, i):
    """4 byte keystream untuk instruksi ke-i dengan rolling state h."""
    x = (h ^ ((i * 0x9E3779B1) & MASK)) & MASK
    x ^= x >> 16
    x = (x * 0x85EBCA6B) & MASK
    x ^= x >> 13
    x = (x * 0xC2B2AE35) & MASK
    x ^= x >> 16
    return x.to_bytes(4, "little")


def hmix(h, w, i):
    """Update rolling state dengan word plaintext instruksi ke-i (little endian)."""
    h = rol32((h ^ w) & MASK, 7)
    return (h * 0x01000193 + i) & MASK


def seal_key(prefix):
    """Kunci lapis kedua dari n byte pertama memori kerja (setelah swap)."""
    key = 0x811C9DC5
    for b in prefix:
        key = ((key ^ b) * 0x01000193) & MASK
    key ^= key >> 16
    key = (key * 0x7FEB352D) & MASK
    key ^= key >> 15
    key = (key * 0x846CA68B) & MASK
    key ^= key >> 16
    return key


def stream2(key, n):
    """Aliran xorshift32 sepanjang n byte untuk lapis kedua (stage 2)."""
    s = (key | 1) & MASK
    out = bytearray()
    for _ in range(n):
        s ^= (s << 13) & MASK
        s ^= s >> 17
        s ^= (s << 5) & MASK
        out.append(s & 0xFF)
    return bytes(out)
