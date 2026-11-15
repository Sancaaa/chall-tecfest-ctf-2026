# gen.sage — generator soal Ronova (ECDSA biased nonce / HNP)
# File AUTHOR. Output ke attachment/ untuk peserta, kunci.txt + _debug.json untuk author.
#
#   sage gen.sage [SEED]
#
# Kerentanan: nonce k dibuat dengan panjang bit bervariasi; sebagian kecil
# tanda tangan punya k pendek (byte atas nol). "hint" = panjang bit k
# (sinyal sampingan). Peserta harus menyaring yang pendek lalu HNP berbobot.

import json, hashlib, os, sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ---------------- parameter kesulitan (tombol) ----------------
NUM_TOTAL  = 1500          # total tanda tangan yang dibagikan
NUM_SHORT  = 80            # berapa yang nonce-nya sengaja pendek (berguna)
SHORT_BITS = [250, 251, 252]  # panjang bit k untuk yang pendek -> bocor 4..6 bit
FLAG       = b"TecFest26{ROnov4aAa4a4a4Aaa44AAA4a4A}"
# --------------------------------------------------------------

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1337
set_random_seed(seed)

# secp256k1
p  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
E  = EllipticCurve(GF(p), [0, 7])
G  = E(Gx, Gy)
Fn = Integers(n)

# private key (pastikan tidak kecil)
d = ZZ(Fn.random_element())
while d.nbits() < 250:
    d = ZZ(Fn.random_element())
Q = d * G

def h_of(i):
    msg = f"Ronova ledger entry #{i}".encode()
    return int(hashlib.sha256(msg).hexdigest(), 16) % n

# tandai indeks mana yang pendek, lalu diacak supaya urutan tak membocorkan
short_idx = set(range(NUM_SHORT))

rows = []      # (h, r, s, hint)  -> untuk peserta
debug = []     # (h, r, s, hint, k, true_bits) -> author
for i in range(NUM_TOTAL):
    h = h_of(i)
    while True:
        if i in short_idx:
            L = SHORT_BITS[randint(0, len(SHORT_BITS) - 1)]
            k = ZZ(randint(2**(L - 1), 2**L - 1))     # k < 2^L, byte atas nol
        else:
            k = ZZ(Fn.random_element())               # nonce penuh (tak berguna)
        if k % n == 0:
            continue
        R = Integer(k) * G
        r = Integer(R.xy()[0]) % n
        if r == 0:
            continue
        s = (inverse_mod(Integer(k), n) * (h + d * r)) % n
        if s == 0:
            continue
        break
    hint = Integer(k).nbits()
    rows.append((int(h), int(r), int(s), int(hint)))
    debug.append((int(h), int(r), int(s), int(hint), int(k), int(Integer(k).nbits())))

# acak urutan (bawa debug ikut agar tetap sinkron)
perm = list(range(NUM_TOTAL))
shuffle(perm)
rows  = [rows[j]  for j in perm]
debug = [debug[j] for j in perm]

# enkripsi flag: kunci = SHA256(d)
key = hashlib.sha256(int(d).to_bytes(32, "big")).digest()
iv  = os.urandom(16)
ct  = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(FLAG, 16))

os.makedirs("attachment", exist_ok=True)

capture = {
    "curve": "secp256k1",
    "p": int(p), "n": int(n), "G": [int(Gx), int(Gy)],
    "public_key": [int(Q.xy()[0]), int(Q.xy()[1])],
    "note": "hint = observed nonce size; most are useless.",
    "signatures": [{"h": h, "r": r, "s": s, "hint": hint} for (h, r, s, hint) in rows],
}
with open("attachment/capture.json", "w") as f:
    json.dump(capture, f)

with open("attachment/flag.enc", "w") as f:
    json.dump({"iv": iv.hex(), "ct": ct.hex(), "cipher": "AES-256-CBC", "kdf": "sha256(d_be32)"}, f)

# CATATAN: convo AI untuk peserta BUKAN dibuat di sini. Ia file gimmick buatan
# tangan: attachment/session-*.jsonl (sesi Claude Code palsu). gen.sage sengaja
# TIDAK menyentuhnya supaya tidak tertimpa saat regenerasi data.

# file author (JANGAN ke attachment)
with open("kunci.txt", "w") as f:
    f.write(f"seed={seed}\nd={int(d)}\nflag={FLAG.decode()}\n")
with open("_debug.json", "w") as f:
    json.dump({"d": int(d), "rows": debug}, f)

short_hints = sorted(h for (_, _, _, h) in rows)[:NUM_SHORT]
print(f"[gen] seed={seed} selesai. total={NUM_TOTAL} short={NUM_SHORT}")
print(f"[gen] d.nbits={int(d).bit_length()}  leaked bits pada subset ~ {256 - max(short_hints)}..{256 - min(short_hints)}")
print(f"[gen] attachment/: capture.json, flag.enc, chat-ai.txt ; author: kunci.txt, _debug.json")
