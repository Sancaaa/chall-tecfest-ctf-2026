# Writeup Blackbox — `pwn_istaroth`

Target: `nc localhost 40501` | File: `istaroth`, `libc.so.6`, `ld-linux-x86-64.so.2`

## 1. Recon

```
$ file istaroth
istaroth: ELF 64-bit LSB pie executable, x86-64, dynamically linked, stripped

$ checksec --file=istaroth
RELRO:      Full RELRO
Stack:      No canary found
NX:         NX enabled
PIE:        PIE enabled
SHSTK:      Enabled   (CET shadow stack - di bytes biner)
IBT:        Enabled   (CET indirect branch tracking - di bytes biner)
```

Poin penting: **no canary** + **PIE** + **Full RELRO** + libc 2.35 disertakan. Stripped, jadi fungsi di-identifikasi manual lewat `objdump -d -M intel` (cuma ~250 baris, kecil — gampang dibaca manual tanpa perlu Binary Ninja).

## 2. Reversing manual (via objdump, karena Binary Ninja MCP server lagi down saat pertama analisis)

> **Update — sinkron dengan Binary Ninja (`/reversing-ninja`):** setelah server MCP `binary-ninja` nyala, seluruh temuan di bawah **dikonfirmasi 100%** lewat `bn_function_decompile` + `bn_function_disassembly` + `bn_function_xrefs_to`. Satu koreksi kecil: format string leak sebenarnya `"ramalan: %p %p\n"` (ada `\n` yang kelewat di ekstraksi `strings` manual — tidak mengubah exploit). `bn_function_xrefs_to(0x401219)` mengembalikan **0 caller**, mengkonfirmasi fungsi decoy itu memang yatim/tidak pernah dipanggil di jalur eksekusi normal.
>
> Pseudo-C hasil BN (lebih ringkas dari rekonstruksi manual, substansi sama):
> ```c
> // sub_401249 (read_input) — offset 0x40 = var_18 = return value yg dicek main()
> uint64_t sub_401249() {
>     int32_t var_18 = 0;
>     void buf;              // 0x50 byte
>     read(0, &buf, 0x100);  // overflow 0x100 vs 0x50
>     return var_18;
> }
> // main()
> if (sub_401249()) {
>     printf("ramalan: %p %p\n", puts, "./catflag");  // leak
>     fflush(stdout);
>     sub_401249();          // overflow ke-2 -> ROP
> }
> puts("ritual selesai tanpa insiden.");
> ```

Biner ini cuma punya 1 blok `.text` tanpa simbol, tapi gampang dipecah jadi beberapa "fungsi" dari pola `push rbp; mov rbp,rsp`:

- **`0x1219`** — fungsi yang **tidak pernah dipanggil di manapun** (no caller dalam disassembly). Isinya: `puts("TecFest26{close_but_wrong_check_your_chain}")` lalu `exit(0)`. Ini jelas **decoy / fungsi "win" palsu** yang hanya reachable kalau return address langsung ditimpa ke sini (ret2win naif) — nama stringnya sendiri ngasih tau: *"close but wrong, check your chain"*. **Jangan submit string ini sebagai flag.**

- **`0x1249`** — fungsi `read_input()`:
  ```c
  int read_input(void) {
      char buf[0x50];      // 80 byte di stack (rbp-0x50)
      int flag = 0;        // rbp-0x10, offset 0x40 dari buf[0]
      read(0, buf, 0x100); // baca MAX 256 byte ke buffer 80 byte -> STACK OVERFLOW
      return flag;         // nilai ini dikontrol penyerang (ada di dalam buf!)
  }
  ```
  Overflow 256 vs 80 byte: attacker bisa nulis lewat `buf` → saved-rbp (8 byte) → **return address fungsi ini sendiri** (8 byte) → masih sisa ruang buat ROP chain (total sisa setelah buf+rbp = 256-88 = 168 byte / 21 qword).

- **`main()` (`0x1277`)** — alur:
  1. `fopen("flag.txt","rb")` lalu langsung `fclose()` — cuma ngecek file ada, isinya **tidak pernah dibaca langsung** oleh program ini.
  2. Print banner `"Istaroth: ritual dimulai."`
  3. Panggil `read_input()` pertama kali. Kalau return value (`flag`) **!= 0**:
     ```c
     printf("ramalan: %p %p", GOT_puts_value, &"./catflag_string");
     ```
     → **info leak**: alamat runtime `puts()` di libc **dan** alamat runtime string `"./catflag"` di binary (dua-duanya absolute address, PIE-safe — kita gak perlu leak base PIE binary sendiri karena pointer string-nya sudah dikasih langsung).
  4. Panggil `read_input()` **kedua kali** (abaikan return value-nya) — ini kesempatan kedua buat nulis ROP chain.
  5. Print `"ritual selesai tanpa insiden."`, `return 0`.

- Konfirmasi via `readelf -r`: alamat GOT yang dibaca di langkah 3 (`0x3fe0`) memang slot `puts@GLIBC_2.2.5` — jadi leak itu betulan alamat `puts()` di libc.
- String `"./catflag"` (di `.rodata`, offset `0x2008`) adalah argumen yang sengaja "dikasih gratis" lewat leak — kemungkinan besar skrip/binary bantu yang nge-`cat` `flag.txt` dengan privilege yang sesuai.

## 3. Kenapa bukan ret2win biasa?

PLT program **tidak** meng-import `system()`/`execve()` — cuma `puts, printf, read, fopen, fclose, fflush, setvbuf, exit`. Jadi:
- Gak bisa langsung `ret` ke `system@plt` (gak ada).
- Fungsi "win" di `0x1219` cuma print flag palsu, bukan solusi.
- Satu-satunya cara ngambil flag asli: **bikin ROP chain pakai libc** (leak dulu → hitung base libc → panggil `system("./catflag")` manual lewat gadget). Ini juga yang dimaksud di flag decoy: *"check your chain"*.

## 4. Exploit plan

1. **Trigger leak**: kirim ≥65 byte apa aja (misal `b"A"*65`) ke `read_input()` pertama → byte ke-65 (`'A'=0x41`) jatuh di offset `0x40` → `flag != 0` → masuk cabang leak.
2. **Parse leak**: ambil 2 alamat hex dari output `"ramalan: 0x... 0x..."` → `puts_leak`, `catflag_ptr`.
3. **Hitung libc base**: `libc_base = puts_leak - offset(puts, libc.so.6 lokal)` (libc 2.35 Ubuntu, disediakan di folder yang sama).
4. **Susun ROP chain** untuk overflow kedua, dieksekusi lewat `leave;ret` milik `read_input()` sendiri (bukan `main()`, jadi gak perlu overflow dua layer):
   ```
   [80 byte padding][8 byte junk rbp][pop rdi;ret][&"./catflag"][ret (alignment)][&system]
   ```
   → `system("./catflag")` jalan, mengeluarkan isi `flag.txt` lewat helper tadi.

## 5. Hasil

```
$ python3 solve.py
...
[+] libc_base=0x764fee6c1000 system=0x764fee711d00
TecFest26{s33dS_0F_S70r13S_8R0u9h7_8y_7H3_W1Nd_aND_cUl71va73d_8Y_71m3}
```

**Flag: `TecFest26{s33dS_0F_S70r13S_8R0u9h7_8y_7H3_W1Nd_aND_cUl71va73d_8Y_71m3}`**

Script lengkap: [`solve.py`](./solve.py) di folder ini.

## 6. Soal "oneliner" `python3 -c "..." | nc ...`

**Tidak memungkinkan untuk chall ini**, dan ini bagian dari desain soalnya:

- Pola `python3 -c "payload" | nc host port` cuma cocok buat exploit *single-shot* yang gak butuh baca balasan server (misal overwrite return address statis/known offset).
- Istaroth butuh **dua round-trip** yang saling tergantung: input #1 → baca leak alamat libc dari respons server → *hitung* alamat `system()`/gadget **berdasarkan leak itu** → baru kirim input #2 (ROP chain). `nc` dengan stdin dari pipe gak bisa baca-balik-dan-hitung-dinamis seperti ini.
- Ini juga poin cerdas dari soal: trik "decoy flag di `0x1219`" khusus menjebak solver yang coba ret2win statis/oneliner naif tanpa leak — mereka akan dapat flag palsu, bukan asli.

Yang paling dekat dengan "oneliner" adalah menjalankan seluruh exploit (leak + hitung + ROP) dalam **satu baris `python3 -c`** yang connect sendiri ke socket (gak lewat pipe `nc`), karena logikanya memang harus reaktif. Kalau tetap mau coba pendekatan ret2win statis cuma buat lihat perilaku decoy-nya (BUKAN buat ambil flag asli), oneliner berikut valid buat itu saja (asumsi offset return address `read_input()` = 88 byte dari awal buffer, PIE base biner tidak diketahui jadi target `0x1219` perlu ditambah base — **tidak akan berhasil tanpa leak base biner**, jadi ini cuma demonstrasi konsep, bukan solve):

```bash
python3 -c "import sys; sys.stdout.buffer.write(b'A'*88 + b'\x19\x12\x00\x00\x00\x00\x00\x00')" | nc localhost 40501
```

(Catatan: payload di atas pakai offset *statis* untuk base `0x1219` — karena PIE, ini cuma jalan kalau base biner kebetulan `0x0000` yang gak realistis. Makanya exploit asli tetap harus lewat `solve.py` yang reaktif.)
