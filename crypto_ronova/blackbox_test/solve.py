import json, sys, hashlib
from flint import fmpz_mat
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

D = sys.argv[1]
cap = json.load(open(D + '/capture.json'))
n = cap['n']; p = cap['p']; G = tuple(cap['G']); Q = tuple(cap['public_key'])
S = cap['signatures']
maxhint = int(sys.argv[2]) if len(sys.argv) > 2 else 252
maxm = int(sys.argv[3]) if len(sys.argv) > 3 else 120

# --- EC helper untuk verifikasi kandidat d ---
def add(P1, P2):
    if P1 is None: return P2
    if P2 is None: return P1
    x1, y1 = P1; x2, y2 = P2
    if x1 == x2 and (y1 + y2) % p == 0: return None
    if P1 == P2: l = 3 * x1 * x1 * pow(2 * y1, -1, p) % p
    else: l = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (l * l - x1 - x2) % p
    return (x3, (l * (x1 - x3) - y1) % p)
def mul(k, P):
    R = None
    while k:
        if k & 1: R = add(R, P)
        P = add(P, P); k >>= 1
    return R

sel = sorted([x for x in S if x['hint'] <= maxhint], key=lambda x: x['hint'])[:maxm]
m = len(sel)
print('sigs dipakai:', m, 'bocor total bit:', sum(256 - x['hint'] for x in sel))

# k_i = t_i*d + a_i (mod n), 0 <= k_i < 2^hint_i
T = []; A = []; B = []
for x in sel:
    si = pow(x['s'], -1, n)
    T.append(x['r'] * si % n); A.append(x['h'] * si % n); B.append(1 << x['hint'])
# skala tiap kolom: c_i = 2^256 / B_i  -> semua koordinat target ~ 2^255
c = [(1 << 256) // b for b in B]
W = 1 << 255
dim = m + 2
M = [[0] * dim for _ in range(dim)]
for i in range(m):
    M[i][i] = n * c[i]
    M[m][i] = T[i] * c[i]
    M[m + 1][i] = (A[i] - B[i] // 2) * c[i]
M[m][m] = 1          # koordinat d
M[m + 1][m + 1] = W  # Kannan embedding
L = fmpz_mat(M).lll()
print('LLL selesai')

def try_d(d):
    d %= n
    if d and mul(d, G) == Q: return d
    return None

found = None
for r in range(L.nrows()):
    row = [int(L[r, j]) for j in range(dim)]
    if abs(row[m + 1]) != W: continue
    sg = 1 if row[m + 1] == W else -1
    for cand in (sg * row[m], -sg * row[m]):
        if try_d(cand): found = cand % n
    if found: break
# cadangan: turunkan d dari koordinat k_i juga
if not found:
    for r in range(L.nrows()):
        row = [int(L[r, j]) for j in range(dim)]
        if abs(row[m + 1]) != W: continue
        sg = 1 if row[m + 1] == W else -1
        for i in range(m):
            for sgn in (1, -1):
                k = (sgn * sg * row[i] // c[i]) + B[i] // 2
                for kk in (k - 1, k, k + 1):
                    d = (sel[i]['s'] * kk - sel[i]['h']) * pow(sel[i]['r'], -1, n) % n
                    if try_d(d): found = d; break
                if found: break
            if found: break
        if found: break

if not found:
    print('GAGAL'); sys.exit(1)
print('d =', found)
enc = json.load(open(D + '/flag.enc'))
key = hashlib.sha256(found.to_bytes(32, 'big')).digest()
pt = AES.new(key, AES.MODE_CBC, bytes.fromhex(enc['iv'])).decrypt(bytes.fromhex(enc['ct']))
print(pt)
try: print('FLAG:', unpad(pt, 16).decode())
except Exception as e: print('unpad err', e)
