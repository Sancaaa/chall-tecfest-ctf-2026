# Write-up Blackbox Test — `sandrone` (TecFest 2026, TESTING_PWN)

**Target:** `nc localhost 40401`
**Binary dianalisis:** `pwn_sandrone/sandrone`
(SHA256 `3f86f768a9a17b3130e47723e68e18a984144882c451d924e205ffbf48d3c00c`,
build-id `377274f00d423f25de992bb35ee6cbc593202efe` — versi terbaru yang di-upload,
sudah konsisten dengan service live di port 40401)
**Hasil:** mendapat shell (`sandrone_pwn`) dan membaca `flag.txt`. ✅

---

## 1. `file` + checksec manual

Tidak ada `checksec` terpasang di environment ini, jadi dicek manual lewat
`readelf`/`nm`:

```
$ file sandrone
sandrone: ELF 64-bit LSB executable, x86-64, ... dynamically linked, ... not stripped
```

| Mitigasi | Status | Bukti |
|---|---|---|
| **NX (stack)** | **OFF** | `readelf -lW` → `GNU_STACK ... RWE` (stack executable!) |
| **PIE** | **OFF** | `readelf -h` → `Type: EXEC` (alamat statis, bukan `DYN`) |
| **RELRO** | **Partial** | ada segmen `GNU_RELRO`, tapi tidak ada tag `BIND_NOW` di dynamic section |
| **Stack canary** | **Tidak ada** | tidak ada simbol `__stack_chk_fail` di `nm` |
| **Stripped** | Tidak — simbol lengkap (`main`, `vuln`, dll) |

Kombinasi **No canary + Stack executable + No PIE** = sinyal kuat untuk
**ret2shellcode**: begitu return address bisa ditimpa dan alamat stack diketahui,
tinggal taruh shellcode sendiri di stack dan lompat ke sana — tidak perlu ROP
chain atau gadget rumit.

`nm` nunjukin fungsi custom cuma `main` & `vuln`, import libc: `fopen`, `fclose`,
`fflush`, `printf`, `puts`, `setvbuf`, **`fgets`**, **`strcpy`**, `read`.
Munculnya `strcpy` (tidak ada bound check) + `read` jadi sinyal ada **dua titik
baca input**, dan keduanya layak dicurigai.

## 2. Reverse `vuln()`

(Binary Ninja via `/reversing-ninja` tidak dipakai karena sesi BN yang jalan saat
itu cuma punya binary lain [`furina`, `ei`] ter-load, bukan `sandrone` — untuk
binary kecil & tidak di-strip seperti ini, `objdump` manual sudah lebih dari
cukup dan hasilnya tetap bisa dicocokkan 1:1 lewat alamat seperti kalau pakai BN.)

```asm
vuln:
  sub    rsp, 0x200                  ; frame besar: 512 byte
  lea    rax, [rbp-0xd0]             ; buf_strcpy_dst (tujuan strcpy tahap 1)
  mov    [rbp-0x8], rax              ; simpan pointer itu
  lea    rax, [rbp-0xd0]
  sub    rax, -0x80                  ; rax = (rbp-0xd0) + 0x80 = rbp-0x50
  mov    [rbp-0x10], rax             ; buf_read (buffer untuk read() tahap 2)

  mov    rsi, [rbp-0x10]             ; rsi = &buf_read (rbp-0x50)
  printf("debug: buf @ %p\n", rsi)   ; <-- BOCOR alamat buf_read!

  printf("payload diagnostik: ")
  fgets(tmp_buf[rbp-0x200], 0x12c, stdin)   ; baca baris, maks 300 byte (AMAN,
                                             ;  tmp_buf besarnya pas 512 byte)
  if (fgets gagal) goto end
  strcpy(buf_strcpy_dst, tmp_buf)    ; <-- COPY TANPA BATAS PANJANG!
                                     ;     buf_strcpy_dst cuma "berjarak" 0x80
                                     ;     byte sebelum nabrak buf_read, dan
                                     ;     0xd8 (216) byte sebelum nabrak return
                                     ;     address. fgets bisa ngasih sampai 299
                                     ;     byte -> overflow juga bisa dari sini!

  printf("kontrol overflow: ")
  read(0, buf_read, 0x100)           ; <-- baca s.d. 256 byte ke buffer 80 byte
                                     ;     (jarak buf_read ke return addr = 0x50
                                     ;      + 8 byte saved rbp = 88 byte)
  leave
  ret
```

**Jadi ada DUA overflow independen** di fungsi ini:

1. **Tahap "payload diagnostik"** (`strcpy` tanpa batas) — bisa overflow sampai
   216 byte dari awal `buf_strcpy_dst` untuk menimpa return address.
2. **Tahap "kontrol overflow"** (`read` mentah 0x100 byte ke buffer 80 byte) —
   bisa overflow di byte ke-89 (offset ke return address = **88 byte**).

Exploit ini pakai **jalur ke-2** karena paling langsung: alamat yang dibocorkan
`printf("%p")` persis alamat buffer yang dipakai `read()` ini, jadi tidak perlu
hitung offset leak-ke-target.

> 📝 **Catatan tambahan buat Sanca:** tahap 1 (`strcpy`) juga vulnerable secara
> independen dari tahap 2 — kalau challenge-nya dimaksudkan cuma punya satu bug
> "resmi" di tahap `read()`, baris `strcpy(buf_strcpy_dst, tmp_buf)` tanpa cek
> panjang itu kemungkinan bug tidak sengaja (bisa dipakai buat overflow juga,
> bahkan sebelum sampai ke prompt "kontrol overflow"). Worth dicek ulang kalau
> mau jalur solve-nya cuma satu yang "intended".

## 3. Validasi offset lewat blackbox probing (tahap `read`)

Supaya tidak cuma mengandalkan pembacaan statis, offset exploit tetap divalidasi
langsung ke service: kirim `'A' * n` ke prompt `"kontrol overflow: "` untuk
berbagai `n`, lihat prosesnya selesai normal (`"selesai.\n"`) atau crash
(koneksi putus).

| total byte dikirim | hasil |
|---|---|
| 80 – 88 | selesai normal |
| 89+ | **crash** (koneksi putus) |

→ **offset ke return address = 88 byte**, pas sesuai hitungan dari disassembly
(`0x50` jarak buffer ke saved rbp + `8` byte saved rbp = `0x58` = 88).

## 4. Exploit: ret2shellcode

Karena:
- alamat `buf_read` **dibocorkan tiap konek** (ASLR stack jadi tidak masalah),
- stack **executable** (NX off),
- offset ke return address **88 byte** (cukup luas buat shellcode kecil ~48 byte),

payload-nya:

```
payload = shellcode_execve("/bin/sh")   # ditaruh di awal buf_read
         + padding 'A' sampai 88 byte
         + p64(leaked_buf_addr)         # timpa return address -> lompat balik ke buf_read
```

Begitu `vuln()` `ret`, RIP lompat ke alamat `buf_read` itu sendiri dan
menjalankan shellcode kita → shell `/bin/sh` → `cat flag.txt`.

## 5. Hasil

```
$ id
uid=1500(sandrone_pwn) gid=1500(sandrone_pwn) groups=1500(sandrone_pwn)
$ pwd
/home/sandrone_pwn
$ cat flag.txt
TecFest26{c0_Lum_B1_nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA}
```

**Flag:** `TecFest26{c0_Lum_B1_nAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA}`

(Formatnya kelihatan seperti flag dummy/placeholder buat testing infra — wajar
untuk folder `TESTING_PWN`.)

Sudah dites ulang & konsisten dapat flag yang sama lewat `solve_sandrone.py`
(pwntools) dan `oneliner_sandrone.sh` (socket murni, tanpa pwntools).

---

## Ringkasan intuitif (alur mikir buat yang baru belajar pwn)

1. **`file` + checksec**: non-stripped, no canary, no PIE, **stack executable**.
   Kombinasi ini auto-triggers insting "coba ret2shellcode", bukan ROP/ret2libc.
2. **`nm`/`objdump`**: cuma ada `main` & `vuln`, import ada `fgets` + `strcpy`
   (tanpa bound check) dan `read` — dua kandidat titik overflow sekaligus.
3. **Baca alur `vuln()`**: `printf("%p", &buf_read)` sebelum `read()` yang
   overflow — ini **selalu** berarti "exploit author sengaja kasih leak alamat
   stack", sinyal paling jelas buat ret2shellcode/ret2stack tanpa perlu
   bruteforce ASLR.
4. **Validasi offset overflow langsung ke service** (kirim payload panjang
   bertahap sampai ketemu titik crash) — jangan cuma percaya hasil hitung
   manual dari disassembly tanpa dicocokkan ke behavior asli.
5. Susun payload: `shellcode + padding + alamat_bocor`, kirim, `cat flag.txt`.

---

## Isi folder

- `WRITEUP_sandrone.md` — dokumen ini.
- `solve_sandrone.py` — exploit pakai pwntools (lengkap, ada komentar, `io.interactive()` di akhir).
- `oneliner_sandrone.sh` — versi satu baris `python3 -c "..."`, murni `socket`
  Python (tanpa pwntools), karena untuk challenge ini **tidak bisa** pola
  statis `payload | nc host port` — alamat leak-nya beda setiap koneksi, jadi
  perlu baca respons dulu sebelum kirim payload (butuh socket dua arah, bukan
  pipe satu arah ke `nc`).
