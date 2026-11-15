#!/usr/bin/env python3
"""
Internal Diagnostics Tool — PT. Scarameow Logistics
Dijalankan lewat: sudo /usr/bin/python3 /opt/admin-tools/simpler.py -p <host>

CATATAN BUAT PESERTA WORKSHOP:
Tool ini sengaja punya character blacklist yang TIDAK lengkap.
Cari karakter apa yang lolos filter dan bagaimana shell memperlakukan
karakter itu saat dipakai di dalam os.system().
"""

import os
import sys

# Filter karakter "berbahaya" — tapi ada yang kelewat dari daftar ini.
BLACKLIST = [';', '&', '|', '`', '>', '<', '\n']


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "-p":
        print("Usage: simpler.py -p <host>")
        print("  Simple internal ping utility for admin diagnostics.")
        sys.exit(1)

    target = " ".join(sys.argv[2:])

    for ch in BLACKLIST:
        if ch in target:
            print(f"Karakter terlarang terdeteksi: {ch!r}")
            sys.exit(1)

    cmd = f"ping -c 1 {target}"
    os.system(cmd)


if __name__ == "__main__":
    main()
