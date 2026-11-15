"""Solver author Rhinedottir.

Membaca build/author.json (kabel rotor, tabel harapan, alamat call site hasil
build), mendekripsi tabel harapan berurutan, lalu opsional memverifikasi ke
binary asli:

    python3 solve.py                          # cetak flag hasil model
    python3 solve.py --bin dist/rhinedottir   # + uji terima/tolak di binary (Linux/WSL)
    python3 solve.py --negative               # tunjukkan model tanpa rip/autokey gagal
"""
import argparse
import json
import subprocess

from machine import Machine, run_dec, salt_of


def load(path="build/author.json"):
    return json.load(open(path))


def solve(a):
    return bytes(run_dec(a["params"], a["exp"], a["salts"]))


def run_bin(binpath, line, timeout=10):
    p = subprocess.run([binpath], input=line + b"\n", capture_output=True, timeout=timeout)
    return p.stdout.decode(errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="build/author.json")
    ap.add_argument("--bin")
    ap.add_argument("--negative", action="store_true")
    args = ap.parse_args()

    a = load(args.author)
    flag = solve(a)
    print("flag:", flag.decode())

    if args.negative:
        # model naif: tanpa salt rip
        naive = bytes(run_dec(a["params"], a["exp"], [0, 0, 0]))
        print("tanpa rip :", naive)
        # model naif: salt benar tapi tanpa autokey (state tidak mengikuti plaintext)
        m = Machine(a["params"])
        out = []
        for i, y in enumerate(a["exp"]):
            m._step()
            m.p[2] = (m.p[2] + a["salts"][i % 3]) & 255
            out.append(m._path(y))
        print("tanpa autokey:", bytes(out))

    if args.bin:
        ok = run_bin(args.bin, flag)
        print("flag benar   ->", "DITERIMA" if "diterima" in ok else "DITOLAK", "|", ok.strip().splitlines()[-1])
        bad = bytearray(flag)
        bad[-2] ^= 1
        r = run_bin(args.bin, bytes(bad))
        print("flag salah 1 byte ->", "DITERIMA" if "diterima" in r else "DITOLAK")
        r = run_bin(args.bin, flag[:-1])
        print("panjang salah ->", r.strip().splitlines()[-1])
        assert "diterima" in ok


if __name__ == "__main__":
    main()
