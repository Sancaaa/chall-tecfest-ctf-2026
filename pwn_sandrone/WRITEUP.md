# Writeup — Sandrone (Binary Exploitation C)

Teknik: shellcode injection (NX off) + **badchar-free XOR payload encoding**. Solver lengkap ada di [`solve.py`](solve.py) — bagian ini menjelaskan alur & alasan tiap langkah.

## 1. Recon

```
nc <host> 40301
debug: buf @ 0x7ffc...
payload diagnostik:
```

Program langsung leak satu alamat stack (`buf`), lalu minta input dengan prompt `payload diagnostik: `. Coba kirim teks panjang biasa → balasannya cuma prompt kedua, `kontrol overflow: `. Jadi ada **dua prompt berurutan**, bukan satu seperti kebanyakan soal overflow.

Coba kirim byte NUL (`\x00`) di tengah input pertama → bagian setelah NUL **hilang** saat program memprosesnya lebih lanjut (keliatan dari testing panjang-pendek respons). Ini sinyal: input pertama lewat fungsi yang berhenti di byte NUL — klasik ciri `strcpy`. Coba kirim input pertama yang sangat panjang (lebih dari ~128 byte) → tidak crash, program tetap lanjut ke prompt kedua — artinya overflow (kalau ada) bukan di sini, atau buffernya cukup besar.

## 2. Dua channel, dua aturan main

Dari percobaan di atas, program punya **dua channel input terpisah** di `vuln()`:

1. **"payload diagnostik"** — dibaca lewat `fgets()` lalu disalin ke buffer kerja lewat `strcpy()`. Dua karakteristik ini otomatis jadi **badchar**: `fgets` berhenti di byte `\n` (`0x0a`), `strcpy` berhenti di byte `\0` (`0x00`). Ini bukan filter yang sengaja ditambahkan (tidak ada `if (byte == ...) reject`) — ini konsekuensi alami dari cara dua fungsi C itu bekerja.
2. **"kontrol overflow"** — dibaca lewat `read()` mentah, 256 byte, ke buffer 64 byte. Overflow klasik, **tidak** ada badchar sama sekali di sini (raw read tidak peduli isi byte apa pun).

**Kenapa dipisah begini (bukan satu channel saja)?** Return address yang mau kita tulis adalah alamat stack (`buf`-related), yang hampir pasti punya byte `0x00` di 2 byte teratasnya (alamat userspace 64-bit kanonik berbentuk `0x00007fxxxxxxxxxx`). Kalau return-address overwrite ini juga harus lewat `strcpy`, byte NUL di tengah alamat itu sendiri akan memotong copy SEBELUM byte-byte sesudahnya (termasuk sisa alamat) sempat tertulis — beda dari kasus format-string (lihat `pwn_ei`) di mana urutan byte bisa diakali karena `%n` punya "direct parameter access"; di sini kita menulis byte mentah berurutan, tidak ada cara melompati posisi. Jadi overwrite return address **harus** lewat channel mentah (`read()`), sementara shellcode (yang memang harus "dibersihkan" dulu baru dieksekusi) lewat channel yang disanitasi.

## 3. Shellcode harus di-encode dulu

Shellcode standar (`shellcraft.amd64.linux.cat("flag.txt") + exit(0)` dari pwntools) hampir pasti mengandung byte `0x00` dan/atau `0x0a` di suatu tempat (immediate value, syscall number, dll). Kalau dikirim mentah lewat channel 1, `strcpy`/`fgets` motong di byte pertama yang kena — shellcode jadi tidak lengkap, exploit gagal diam-diam (mirip jebakan NUL di `pwn_ei`, tapi di sini yang kepotong adalah SHELLCODE-nya, bukan sisa format string).

**Solusi: payload obfuscation pakai XOR** (bitwise, memanfaatkan sifat involutory XOR: `A ⊕ K ⊕ K = A`) — encode shellcode dengan satu key byte `K` sedemikian hingga **tidak ada** byte hasil encode yang masuk badchar set, lalu taruh satu **decoder stub kecil** (badchar-free juga) di depannya yang men-decode shellcode itu di memory tepat sebelum dieksekusi.

### 3a. Nyari key `K` yang valid — bukan asal coba-coba

Referensi: Justin Sepvian (ITB), *"Badchar-Free XOR Payload Encoding in Binary Exploitation: A Combinatorial, GF(2), and Algorithmic Analysis"* (2026). Makalah ini memformalkan pencarian key pakai set theory + Galois Field GF(2⁸) + Principle of Inclusion-Exclusion (PIE), bukan brute force 256 key satu-satu.

Intinya: misal `S` = himpunan byte unik di shellcode, `B` = himpunan badchar (`{0x00, 0x0a}` di soal ini). Key `K` **valid** kalau `(S ⊕ K) ∩ B = ∅` — tidak ada byte di `S` yang kalau di-XOR `K` jadi anggota `B`. Tiap badchar `b` "memblokir" sejumlah key lewat `Ab = {s ⊕ b | s ∈ S}` (persis sebanyak `|S|`, karena XOR bijektif). Union dari semua `Ab` (dihitung PIE biar tidak double-count overlap) dikurangi dari 256 kandidat = jumlah key valid.

Implementasi praktisnya pakai hash set (lihat `Algorithm 1` di paper), bukan nested-loop brute force — `solve.py` mengimplementasikan ini persis:

```python
S = set(raw_shellcode)
invalid_keys = set()
for b in BADCHARS:
    for s in S:
        invalid_keys.add(s ^ b)
valid_keys = sorted((set(range(256)) - invalid_keys) - BADCHARS)
KEY = valid_keys[0]  # key terkecil, sesuai Algorithm 1 paper
```

Untuk shellcode di soal ini (51 byte, 32 byte unik) vs `B={0x00,0x0a}`: **196 dari 256 key valid**, dipakai yang terkecil (`0x03`).

### 3b. Decoder stub — percobaan pertama gagal, ini pelajarannya

Decoder stub perlu tahu di mana posisi shellcode yang di-encode (supaya bisa di-decode in-place), **tanpa** menaruh alamat mentah (karena alamat mentah = badchar lagi, masalah yang sama persis berulang satu level lebih dalam). Perlu teknik **posisi-independen**.

**Percobaan pertama (gagal):** pakai `lea rsi, [rip+label]` (RIP-relative addressing) buat ngambil alamat shellcode relatif terhadap posisi stub sendiri. Begitu di-assemble dan dicek byte-nya:

```
lea rsi,[rip+0x12]  ->  48 8d 35 12 00 00 00
                              ^^ ^^ ^^ zero-padding -- BADCHAR
```

x86-64 selalu encode `lea reg,[rip+disp32]` dengan field displacement **4 byte**, dan untuk offset kecil (stub cuma puluhan byte), 3 byte teratas dari 4-byte itu otomatis `0x00`. Instruksi decoder-nya SENDIRI jadi kena badchar — gagal sebelum sempat decode apa-apa.

**Fix: teknik `JMP/CALL/POP`** (klasik, dari Erickson — *Hacking: The Art of Exploitation*, yang juga jadi salah satu rujukan paper di atas):

```asm
.intel_syntax noprefix
start:
    jmp short call_shellcode
decoder:
    pop rsi          ; rsi = return-address yang di-push instruksi call di bawah
    mov rdi, rsi      ; simpan titik awal, dipakai buat jump balik setelah decode
    mov cl, LEN
    mov dl, KEY
decode_loop:
    xor byte ptr [rsi], dl
    inc rsi
    dec cl
    jnz decode_loop
    jmp rdi
call_shellcode:
    call decoder
```

Kuncinya di `call decoder`: instruksi ini MUNDUR ke label `decoder` yang definisinya di ATAS posisi `call` itu sendiri — jadi `rel32`-nya **negatif** (two's complement). Byte tertinggi dari angka negatif kecil itu `0xFF`, bukan `0x00`. `call` otomatis push alamat instruksi SESUDAH dirinya (yaitu `call_shellcode` + 5 byte = persis awal shellcode terenkode yang ditaruh tepat setelah stub ini) ke stack, lalu lompat ke `decoder`. `pop rsi` mengambil alamat itu — dapat alamat shellcode terenkode **tanpa pernah menulis satu alamat mentah pun** di instruksi manapun.

Hasil: stub 26 byte, nol badchar (diverifikasi otomatis di `solve.py` lewat `assert`).

## 4. Rakit payload lengkap

```
channel1 = decoder_stub (26 byte) + shellcode_encoded (51 byte)   -> total 77 byte, 0 badchar
channel2 = b"A" * 88 + p64(payload_addr)                           -> overwrite return address
```

`payload_addr` dihitung dari leak: `buf` dan `payload` ada di SATU array (`frame[192]`) yang dibagi manual via pointer (lihat `bin/sandrone.c` dan `NOTES.md`) — `payload = buf - 0x80` (properti statis layout stack, dicek lewat `objdump`, bukan ditebak). Offset 88 byte ke return address juga dari `objdump` (`buf` di `rbp-0x50`, jarak ke saved RBP = `0x50`, + 8 byte saved RBP itu sendiri).

## 5. Kirim & dapat flag

```bash
python3 solve.py REMOTE=1 HOST=<host> PORT=40301
```

Alurnya: kirim `channel1` ke prompt "payload diagnostik" (tersimpan di buffer `payload`, utuh karena sudah badchar-free) → kirim `channel2` ke prompt "kontrol overflow" (overwrite return address mentah, tidak kena filter apa pun) → `vuln()` return ke `payload_addr` → decoder stub jalan, decode shellcode di tempat, lompat eksekusi → shellcode `cat flag.txt; exit(0)` → flag ke stdout.

Diverifikasi 5x run berturut-turut lawan container live (alamat ASLR beda tiap koneksi) — 100% dapat flag, juga lolos sebagai proses lokal non-Docker.

## 6. Kenapa ini bikin difficulty-nya naik dibanding versi lama

Versi lama sandrone: leak dikasih, offset dicek sekali lewat `objdump`, lalu satu tembakan `shellcode_mentah + padding + alamat` — nyaris semekanis ret2win begitu leak di tangan. Versi ini menambah **dua lapis insight asli**: (1) sadar ada dua channel dengan aturan beda dan alasan kenapa overwrite return address tidak boleh ikut lewat channel yang disanitasi, dan (2) encoding shellcode (termasuk decoder stub-nya sendiri) supaya lolos badchar — bukan sekadar "tulis shellcode, kirim". Ini yang dimaksud supaya level kesulitannya sebanding dengan Furina (OOB write-what-where + chaining 2 request), bukan sekadar label "Medium" yang sama tapi beda jauh secara efektif.

## Referensi

- Sepvian, J. (2026). *Badchar-Free XOR Payload Encoding in Binary Exploitation: A Combinatorial, GF(2), and Algorithmic Analysis.* Institut Teknologi Bandung.
- Erickson, J. (2008). *Hacking: The Art of Exploitation*, 2nd ed. No Starch Press. (Teknik JMP/CALL/POP untuk shellcode posisi-independen.)
