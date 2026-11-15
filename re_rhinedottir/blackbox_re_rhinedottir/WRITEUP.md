# Write-up `re_rhinedottir` (Reverse Engineering)

> **SPOILER, hanya untuk panitia/author.** Jangan taruh di folder attachment, repo publik, atau CTFd.

**Flag:** `TecFest26{Sh0W_ME_7He_7RU7h_4nd_7he_Me4N1N9_0f_7H1S_W0RLd}`

Solver: [solve.py](solve.py) (43 baris, `python solve.py rhinedottir`).
Metode: blackbox. Yang dipakai hanya binary `rhinedottir`, Binary Ninja (static), dan satu kali run untuk melihat perilaku.

---

## 1. Triage

```
rhinedottir: ELF 64-bit LSB executable, x86-64, statically linked, stripped
```

Dijalankan tanpa input:

```
== Rhinedottir enigma maCChine ==
Roda-roda berputar, menunggu kata sandimu.
sandi> Panjang kata sandi tidak sesuai.
```

Tiga petunjuk dari sini:

- Judulnya **"enigma maCChine"**, dengan **CC** yang sengaja dibesarkan. Ini mengarah ke mesin Enigma dan ke *syscall*/*ptrace*.
- Programnya mengulang prompt `sandi>` tanpa henti. Itu *password checker*, dan outputnya hanya diterima atau ditolak.
- Panjang password harus tepat 58 (0x3a). Cek panjang ada di fungsi child `0x401b60`, dengan toleransi `\r`.

Strings lain cuma pesan: `Ada saksi ketiga di ruangan ini...` (anti-debug), `ptrace ditolak`, dan pesan diterima/ditolak. Tidak ada flag di strings.

## 2. Static: dua proses yang saling bicara

`_start` meneruskan `0x401560` sebagai `main`. Fungsi itu melakukan `fork()`, lalu:

| Proses | Isi |
|---|---|
| **Child** | `PTRACE_TRACEME`, `raise(SIGSTOP)`, lalu masuk `sub_401b60` (baca password, cek) |
| **Parent (tracer)** | Loop `PTRACE_SYSCALL`, mencegat syscall milik child |

Kalau `PTRACE_TRACEME` gagal (sudah ada debugger), child mencetak "Ada saksi ketiga..." dan keluar. Jadi **gdb/strace tidak bisa langsung dipasang di child**. Anti-debug ini sekaligus alasan kenapa analisis statis lebih efisien di sini.

### Child (`0x401b60`): hanya kurir

Setelah membaca 58 karakter, child:

1. Memanggil `syscall(0x402)` sekali, untuk **reset** mesin.
2. Untuk tiap karakter `i`, memanggil **`syscall(0x401, ch)`**. Hasilnya (1 byte) disimpan ke buffer.
   Syscall `0x401` bukan syscall Linux asli. Syscall dipanggil lewat **tiga wrapper berbeda** (`0x401b10`, `0x401b20`, `0x401b30`), dipilih dari `i % 3`.
3. Membandingkan buffer dengan 58 byte konstan di `0x4c7100`. Kalau semua sama: *"Kata sandi diterima"*.

Jadi enkripsinya tidak ada di child. Child hanya menyodorkan karakter dan menerima hasilnya.

### Parent (tracer): mesin Enigma yang sebenarnya

Di setiap syscall-entry dengan `orig_rax == 0x401`, tracer:

- membaca karakter dari `rdi`,
- menghitung hasilnya sendiri,
- mengubah `orig_rax` jadi `-1` supaya kernel tidak menjalankan syscall,
- menulis hasilnya ke `rax` saat syscall-exit.

Komponen mesin dari data di binary:

| Data | Alamat | Isi |
|---|---|---|
| Reflektor | `0x499180` | 256 byte |
| Rotor 0/1/2 | `0x499280` + `256*k` | 3 tabel permutasi 256 byte |
| Rotor kebalikan | dibuat saat runtime | `INV[k][ROT[k][j]] = j` |
| Posisi awal | `0xe`, `7`, `0xb5` | `p0`, `p1`, `p2` |

Alur satu huruf (persis Enigma, tapi alfabetnya 256 byte):

```
x -> rotor0 -> rotor1 -> rotor2 -> reflektor -> rotor2^-1 -> rotor1^-1 -> rotor0^-1 -> out
     (tiap rotor k: out = ROT[k][(x + p[k]) & 255] - p[k])
```

Dua perilaku berikut tidak ada di Enigma asli:

- **`p0` dan `p1` berputar seperti odometer.** `p0` naik 1 tiap huruf. Saat `p0 == 0x2a`, `p1` ikut naik. Jalur `p1 == 7` meloncat dulu ke `p1 = 8` dan menambah `p2` 1 (jalur ini melewati cek `0x2a`).
- **`p2` bukan odometer biasa.** Nilainya `(rip>>4 ^ rip>>12) + p2`, lalu setelah dipakai ditambah **karakter plaintext**:
  - `rip` adalah alamat instruksi setelah `syscall` di wrapper. Itu kenapa ada **tiga wrapper**: tiap `i % 3` memberi hash berbeda (`0x401b18`, `0x401b28`, `0x401b38`).
  - Penambahan plaintext membuat ini mode **autokey**. State berikutnya bergantung pada huruf sebelumnya.

Ada juga *state machine* kecil dengan angka aneh (`0x1a7`, `0x2c3`, `0x4e9`, `0x7f2`, `0x6d0`, `0x31b`) di decompile. Ini hanya obfuscation (CFF kecil), ditambah *opaque predicate* `((x+1)*x) & 1`, yang **selalu 0** karena `x*(x+1)` selalu genap. Setelah dibersihkan, urutannya tetap sederhana: rotor 0, 1, 2, reflektor, rotor 2, 1, 0.

## 3. Kenapa gampang di-solve (inti ide)

Karena state hanya bergantung pada **plaintext yang sudah dipilih**, bukan pada hal rahasia lain:

> Untuk huruf ke-`i`, coba semua 256 kemungkinan, ambil yang outputnya sama dengan `TARGET[i]`, lalu update state dan lanjut. Tidak perlu brute force 58 huruf sekaligus.

Satu langkah adalah komposisi permutasi byte: ketiga rotor bijektif, dan reflektor adalah involusi tanpa fixed point (sudah saya cek, persis sifat reflektor Enigma). Jadi **tiap posisi punya tepat 1 kandidat**. Saya cek juga: dari 0..255, tiap posisi hanya memberi 1 jawaban, sehingga flag unik dan tidak perlu backtracking.

## 4. Solver

Intinya:

```python
state, flag = [0x0E, 0x07, 0xB5], ""
for i, want in enumerate(TARGET):
    for c in range(256):
        b, nxt = step(state, c, RIPS[i % 3])   # tiru syscall 0x401
        if b == want:
            flag += chr(c); state = nxt; break
```

`step()` adalah salinan langsung dari parent (rotor, reflektor, inverse, update `p0/p1/p2`).
Tabel dibaca langsung dari file binary (offset file `0x99180`, `0x99280`, `0xc6100`), jadi solver tidak perlu hardcode data besar.

```
$ python solve.py rhinedottir
TecFest26{Sh0W_ME_7He_7RU7h_4nd_7he_Me4N1N9_0f_7H1S_W0RLd}
```

## 5. Verifikasi

Dijalankan ke binary asli (salinan di WSL):

```
sandi> TecFest26{Sh0W_ME_7He_7RU7h_4nd_7he_Me4N1N9_0f_7H1S_W0RLd}
Mesin berdengung pelan. Kata sandi diterima.
sandi> TecFest26{...W0RLe}                      (1 karakter diubah)
Roda-roda berputar, tetapi tidak ada yang terbuka.
```

## 6. Catatan untuk problem setter

- **Dynamic analysis:** saya hanya menjalankan binary untuk melihat perilaku. Saya **tidak** memasang debugger/tracer di dalam prosesnya, karena `PTRACE_TRACEME` di child menolak saksi kedua. Semua logika mesin dibaca dari static dan divalidasi dari hasil solver ke binary asli. Karena binary static, `LD_PRELOAD` tidak bisa dipakai untuk bypass. Peserta yang ingin debug dinamis harus patch panggilan `ptrace` (atau memakai debugger yang bisa meng-attach ke parent), atau cukup membaca tracer seperti di sini.
- **Jalur solve yang mungkin dipakai peserta (belum saya uji, ini perkiraan):** (a) port tracer ke script seperti ini, jalur yang saya pakai; (b) menulis tracer sendiri yang mengirim kandidat karakter ke child lalu membaca hasilnya. Karena state bergantung pada plaintext, peserta tetap harus memecahkan huruf demi huruf.
- **Tingkat kesulitan:** menurut saya menengah. Ide "dua proses, syscall palsu" cukup mudah ketemu dari `ptrace`, tapi menemukan bahwa `rip` wrapper ikut jadi state dan `p2` autokey adalah bagian yang paling mudah terlewat. Tanpa keduanya, solver peserta akan salah dari karakter ke-2.
- **Pengingat (AI rule peserta):** pola ini sangat mudah di-port oleh AI dari decompile. Pertimbangkan apakah level ini sesuai kategori dan poinnya.
