#!/usr/bin/env python3
"""Hasilkan berkas rahasia untuk challenge Nahida (Cryptography E).

Menulis ke SECRET_DIR (default: ./secrets): key (hex), token (hex), flag.
Dijalankan author sekali saat setup; berkas ini TIDAK ikut image/attachment.
Nilai bisa dipaksa lewat env NAHIDA_KEY / NAHIDA_TOKEN / NAHIDA_FLAG.
"""
import os
import secrets

SECRET_DIR = os.environ.get(
    "SECRET_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets")
)

DEFAULT_FLAG = "TecFest26{cfb_st4t1c_1v_plus_crc_c0llaps3s_the_wh0le_chain}"


def main():
    os.makedirs(SECRET_DIR, exist_ok=True)
    key = os.environ.get("NAHIDA_KEY") or secrets.token_hex(16)        # AES-128
    token = os.environ.get("NAHIDA_TOKEN") or secrets.token_hex(16)    # 32 hex char
    flag = os.environ.get("NAHIDA_FLAG") or DEFAULT_FLAG
    assert len(flag) >= 36, "flag minimal 36 karakter (body >= 3 blok)"
    for name, val in (("key", key), ("token", token), ("flag", flag)):
        path = os.path.join(SECRET_DIR, name)
        with open(path, "w", newline="") as f:
            f.write(val)
        print(f"tulis {path} ({len(val)} char)")


if __name__ == "__main__":
    main()
