# solve.sage — intended solver Ronova (HNP berbobot + LLL/BKZ)
#   sage solve.sage
# Hanya memakai attachment/ (capture.json, flag.enc). Tidak melihat _debug/kunci.

import json, hashlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# -------- parameter solver (yang perlu disetel peserta) --------
M_SEL     = 70                         # berapa sig terpendek yang dipakai
BLOCKS    = [2, 10, 20, 30, 40]        # BKZ bertahap (2 = ~LLL)
# ----------------------------------------------------------------

cap = json.load(open("attachment/capture.json"))
p, n = cap["p"], cap["n"]
E = EllipticCurve(GF(p), [0, 7])
G = E(cap["G"][0], cap["G"][1])
Q = E(cap["public_key"][0], cap["public_key"][1])

sigs = cap["signatures"]
# LANGKAH 1: saring -> ambil M_SEL dengan hint (panjang nonce) terkecil
sigs = sorted(sigs, key=lambda x: x["hint"])[:M_SEL]
m = len(sigs)

# LANGKAH 2: t_i, a_i  (k_i = a_i + t_i*d mod n)
T, A, Lbits = [], [], []
for sg in sigs:
    si = inverse_mod(sg["s"], n)
    T.append((sg["r"] * si) % n)
    A.append((sg["h"] * si) % n)
    Lbits.append(sg["hint"])          # B_i = 2^hint
L = max(Lbits)
B = 2**L

# LANGKAH 3: lattice HNP BERBOBOT (bukan B seragam). Versi integer (×n).
#   bobot w_i = 2^(L - hint_i) menyamakan batas tiap kolom.
w = [2**(L - Lbits[i]) for i in range(m)]
dim = m + 2
Mx = Matrix(ZZ, dim, dim)
for i in range(m):
    Mx[i, i] = n * n * w[i]
for i in range(m):
    Mx[m,   i] = n * T[i] * w[i]
    Mx[m+1, i] = n * A[i] * w[i]
Mx[m,   m]   = B
Mx[m+1, m+1] = B * n

def recover(mat):
    for row in mat.rows():
        dcol = row[-2]
        if dcol == 0:
            continue
        for cand in (ZZ(dcol / B) % n, (n - ZZ(dcol / B)) % n):
            if cand != 0 and cand * G == Q:
                return cand
    return None

# LANGKAH 4: reduksi bertahap, cek tiap tahap
d = None
red = Mx
for bs in BLOCKS:
    red = red.BKZ(block_size=bs) if bs > 2 else red.LLL()
    d = recover(red)
    if d:
        print(f"[solve] private key ketemu di block_size={bs}")
        break

if not d:
    print("[solve] GAGAL memulihkan d")
    exit(1)

# LANGKAH 5: dekripsi flag
enc = json.load(open("attachment/flag.enc"))
key = hashlib.sha256(int(d).to_bytes(32, "big")).digest()
flag = unpad(AES.new(key, AES.MODE_CBC, bytes.fromhex(enc["iv"])).decrypt(bytes.fromhex(enc["ct"])), 16)
print(f"[solve] d = {int(d)}")
print(f"[solve] FLAG = {flag.decode()}")
