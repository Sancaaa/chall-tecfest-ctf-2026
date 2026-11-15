"""Generator tabel Rhinedottir.

Pass 1 (tanpa --sites): tabel harapan diisi placeholder bukan-nol; dipakai untuk kompilasi awal agar
alamat call site diketahui. Pass 2 (--sites hasil `nm`): hitung salt dari alamat,
enkripsi flag, tulis tabel harapan sungguhan. Tata letak kode tidak berubah karena
tabel harapan berada di .data dengan ukuran tetap (diverifikasi di Dockerfile).
"""
import argparse
import json
import re

from machine import gen_params, run_enc, salt_of

SEED = "rhinedottir-enigma-maCChine-2026"


def arr(name, vals, per=16, typ="unsigned char", const=True):
    rows = []
    for i in range(0, len(vals), per):
        rows.append("  " + ", ".join("0x%02x" % v for v in vals[i:i + per]))
    c = "const " if const else ""
    return "static %s%s %s[%d] = {\n%s\n};\n" % (c, typ, name, len(vals), ",\n".join(rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tables", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--flag", required=True)
    ap.add_argument("--sites")
    a = ap.parse_args()

    flag = open(a.flag, "rb").read().strip()
    P = gen_params(SEED)
    n = len(flag)

    sites = None
    salts = None
    exp = [0xA5] * n   # bukan nol: tabel nol masuk .bss dan menggeser tata letak
    if a.sites:
        sites = {}
        for line in open(a.sites):
            m = re.match(r"([0-9a-f]+)\s+\w\s+k_([abc])_ret", line.strip())
            if m:
                sites[m.group(2)] = int(m.group(1), 16)
        assert sorted(sites) == ["a", "b", "c"], "call site tidak lengkap: %r" % sites
        salts = [salt_of(sites[k]) for k in "abc"]
        assert len(set(salts)) == 3 and 0 not in salts, "salt harus berbeda dan tidak nol: %r" % salts
        exp = run_enc(P, list(flag), salts)

    h = ["/* Digenerate oleh gen.py. Jangan diedit manual. */",
         "#define LEN %d" % n,
         "#define N0 %d" % P["n0"],
         "#define N1 %d" % P["n1"],
         "#define INIT0 %d" % P["init"][0],
         "#define INIT1 %d" % P["init"][1],
         "#define INIT2 %d" % P["init"][2],
         ""]
    rot_rows = []
    for r in P["rot"]:
        rot_rows.append("  {" + ", ".join("0x%02x" % v for v in r) + "}")
    h.append("static const unsigned char ROT[3][256] = {\n" + ",\n".join(rot_rows) + "\n};\n")
    h.append(arr("REFL", P["refl"]))
    h.append(arr("EXP", exp, const=False))
    open(a.tables, "w").write("\n".join(h))

    json.dump({"seed": SEED, "params": P, "sites": sites, "salts": salts,
               "exp": exp, "len": n}, open(a.author, "w"))
    print("tables ->", a.tables, "| len", n, "| salts", salts)


if __name__ == "__main__":
    main()
