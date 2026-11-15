#!/usr/bin/env python3
from Crypto.Cipher import AES
from flag import flag
import secrets, hmac, sys
from modulus import new_modulus  # server-side GHASH modulus (not provided)


def gmul(a, b):
    r, cur = 0, a
    for i in range(128):
        if (b >> i) & 1:
            r ^= cur
        carry = cur >> 127
        cur = (cur << 1) & ((1 << 128) - 1)
        if carry:
            cur ^= RMASK
    return r


def ghash(h, aad, ct):
    def pad(d):
        return d + b"\x00" * (-len(d) % 16)
    lens = int(len(aad) * 8).to_bytes(8, "big") + int(len(ct) * 8).to_bytes(8, "big")
    data = pad(aad) + pad(ct) + lens
    y = 0
    for i in range(0, len(data), 16):
        y = gmul(y ^ int.from_bytes(data[i:i + 16], "big"), h)
    return y


def aes_ecb(key, block):
    return AES.new(key, AES.MODE_ECB).encrypt(block)


def ctr_crypt(key, ctr, data):
    out = bytearray()
    for i in range(0, len(data), 16):
        ks = aes_ecb(key, ctr)
        out += bytes(a ^ b for a, b in zip(data[i:i + 16], ks))
        v = int(int.from_bytes(ctr, "big") + 1) % (1 << 128)
        ctr = int(v).to_bytes(16, "big")
    return bytes(out)


def make_j0(nonce):
    return nonce + b"\x00\x00\x00\x01"


def encrypt(key, nonce, pt):
    j0 = make_j0(nonce)
    h = int.from_bytes(aes_ecb(key, b"\x00" * 16), "big")
    tm = int.from_bytes(aes_ecb(key, j0), "big")
    ct = ctr_crypt(key, int(int.from_bytes(j0, "big") + 1).to_bytes(16, "big"), pt)
    return ct, int(tm ^ ghash(h, AAD, ct)).to_bytes(16, "big")


def decrypt(key, nonce, ct, tag):
    j0 = make_j0(nonce)
    h = int.from_bytes(aes_ecb(key, b"\x00" * 16), "big")
    tm = int.from_bytes(aes_ecb(key, j0), "big")
    expected = int(tm ^ ghash(h, AAD, ct)).to_bytes(16, "big")
    if not hmac.compare_digest(tag, expected):
        raise ValueError("bad tag")
    return ctr_crypt(key, int(int.from_bytes(j0, "big") + 1).to_bytes(16, "big"), ct)


def build_token(username, is_admin, command):
    return username.encode().ljust(16, b"\x00") + bytes([is_admin]) + command.encode().ljust(63, b"\x00")


def parse_token(data):
    return {"username": data[:16].rstrip(b"\x00").decode(),
            "admin": data[16] == 1,
            "command": data[17:].rstrip(b"\x00").decode()}


p_int = new_modulus()
RMASK = p_int ^ (1 << 128)

AAD = b"tecfest-ghash-token-v2"

KEY = secrets.token_bytes(16)
NONCE = secrets.token_bytes(12)

known = [
    build_token("alice", 0, "show_profile --verbose --section=billing --since=2026-01-01"),
    build_token("bob", 0, "list_messages --folder=archive --limit=250 --order=descending"),
    build_token("charlie", 0, "download_report --quarter=3 --format=csv --compress=gzip-9"),
    build_token("guest", 0, "check_status --component=relay --retries=5 --timeout=30000"),
]

logs = [{"ct": ct, "tag": tag} for pt in known for ct, tag in [encrypt(KEY, NONCE, pt)]]

print(f"P = {hex(p_int)}")
for i, s in enumerate(logs):
    print(f"CT-{i}  : {s['ct'].hex() + s['tag'].hex()}")
sys.stdout.flush()

inp = input("Input: ").strip()

assert len(inp) == 192

ct_hex, tag_hex = inp[:160], inp[160:]

try:
    pt = decrypt(KEY, NONCE, bytes.fromhex(ct_hex), bytes.fromhex(tag_hex))
    token = parse_token(pt)
    if token["admin"] and token["command"] == "gibe_flag":
        print(f"Here's your flag min!: {flag}")
    else:
        print("Who r u again?")
except Exception:
    print("Invalid Input.")
