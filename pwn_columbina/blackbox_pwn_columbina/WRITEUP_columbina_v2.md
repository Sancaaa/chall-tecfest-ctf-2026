# Write-up: `pwn_columbina` — setelah binary dipatch (v2)

**Target:** `nc localhost 40601`
**BuildID lama:** `03cffab8735b14d4edd19c0484a8d838ee1e30b1`
**BuildID baru:** `e1f34a3156b17be84dc45a03a2b7cf8a2ad605c1` (ukuran file sama, `14624` byte)
**Flag:** `TecFest26{body_soul_authority_columbina_returns}` (sama dengan sebelumnya — flag tidak berubah, cuma jalur exploit-nya yang ditutup sebagian)

---

## 1. Apa yang berubah

Binary baru di-diff byte-per-byte via `objdump -d -M intel` terhadap binary lama. Hasilnya: **cuma satu perubahan logika**, di opsi 5 ("Luonnotar"):

```diff
- cmp rax, 0x28      ; (unsigned) size <= 40 diizinkan
- jbe  <lanjut>
+ cmp QWORD PTR [rbp-0x38], 0x10   ; (signed) size <= 16 diizinkan
+ jle  <lanjut>
```

Semua diff lain di luar ini cuma pergeseran alamat jump target (karena instruksi barunya 3 byte lebih pendek), **bukan** perubahan logika. Artinya: batas panjang baca raw di opsi 5 diperketat dari **≤40 byte jadi ≤16 byte**. Checksec (Partial RELRO/Canary/NX/No-PIE/SHSTK+IBT) dan semua bug lain (lihat write-up v1) **tidak berubah**:

- Opsi 2 (Free) masih **tidak** men-NULL-kan slot sesudah `free()` → UAF tetap ada.
- Opsi 1 (Add) & opsi 5 (Luonnotar) masih selalu `malloc(0x28)` → size-class tcache tetap sama.
- Opsi 1 masih bocorin alamat heap tiap alokasi (`"fragmen baru bersemayam di %p"`).

Dampaknya: exploit v1 (raw-write 40 byte sekali jalan langsung nimpa `print_fn` di offset `0x20`) **tidak jalan lagi** — 16 byte cuma nyampe offset `0x0F`, masih di dalam field `name`, nggak nyampe `print_fn`.

## 2. Primitive baru: Safe-Linking Tcache Poisoning

`libc.so.6` yang disertakan adalah **glibc 2.35** (Ubuntu 22.04):

```
GNU C Library (Ubuntu GLIBC 2.35-0ubuntu3.18) stable release version 2.35.
```

glibc ≥2.32 pakai **safe-linking**: pointer "next" di linked-list tcache nggak disimpan mentah, tapi di-XOR:

```
stored_next = (alamat_chunk_itu_sendiri >> 12) XOR next_chunk_asli
```

(simetris, dekode pakai formula yang sama). Ini biasanya menyulitkan tcache-poisoning klasik karena penyerang perlu tahu alamat chunk-nya sendiri untuk menghitung mask yang benar. **Tapi di sini kita punya dua keuntungan sekaligus:**

1. **No PIE** → semua alamat fungsi di binary statis (`0x401347` tetap).
2. **Heap-leak gratis** dari opsi 1 (`"fragmen baru bersemayam di %p"`) → kita tahu persis alamat tiap chunk yang kita alokasikan, jadi mask `(alamat >> 12)` bisa dihitung langsung, safe-linking-nya nggak jadi penghalang sama sekali.

### Kenapa butuh 2 chunk yang di-free (bukan 1)

Tcache punya counter `counts[idx]` per size-class, independen dari isi linked-list. Counter ini yang dicek SEBELUM glibc mau "pop" dari tcache (kalau count==0, tcache dianggap kosong meski secara pointer list-nya masih ada sisa). Supaya bisa melakukan **2 kali pop** (pop pertama ambil chunk asli buat majuin head, pop kedua baru ambil alamat palsu kita), kita butuh **2 kali free** dulu (count jadi 2).

### Alur konkret

```
Target: A (dialokasikan, TIDAK pernah di-free — ini objek yang print_fn-nya mau dibajak)
FAKE  = A + 0x20   (persis posisi field print_fn milik A)

1. Add(0) -> leak A         (A tidak di-free, datanya tetap hidup)
2. Add(1) -> leak B         (chunk korban #1, sekadar filler)
3. Add(2) -> leak D         (chunk korban #2, "next"-nya mau dikorup)
4. Free(1)                  tcache head=B,  count=1
5. Free(2)                  tcache head=D,  count=2, D->next decode ke B
6. Edit(2) raw 8 byte:
     crafted = (D >> 12) ^ FAKE
   -> timpa 8 byte pertama D (field "next" tcache-nya) dengan crafted,
      supaya nanti waktu D di-pop, head SELANJUTNYA bukan B lagi,
      tapi "terdekode" jadi FAKE.
7. Add(3) -> pop ke-1: malloc(0x28) balikin D (legit). Majuin head -> FAKE.
8. Luonnotar(idx bebas, size=8, data=p64(0x401347)) -> pop ke-2:
      malloc(0x28) balikin FAKE (=A+0x20)!
      read() PERSIS 8 byte ditulis di situ = alamat WIN_FUNC.
      Karena FAKE == A+0x20, 8 byte ini LANGSUNG nimpa print_fn milik A.
9. Uji otoritas fragmen(0) -> entry=A, print_fn=*(A+0x20)=0x401347
   -> call 0x401347(A) -> WIN_FUNC cetak flag.
```

Semua write di atas sengaja **persis N byte** (short-read/short-send, tanpa newline nyasar) supaya tidak nyenggol byte lain di luar target, khususnya header malloc chunk tetangga — jadi nggak perlu korupsi heap metadata sama sekali. Fungsi tujuan (`0x401347`) tetap fungsi "menang" yang sama dari binary lama (puts banner + fputs isi `flag.txt`), karena memang fungsi ini tidak terhapus/berubah di binary baru.

## 3. Script solve v2

Lihat `solve_columbina_v2.py`. Dites berkali-kali, konsisten dapat flag yang sama:

```bash
python solve_columbina_v2.py HOST=127.0.0.1 PORT=40601
```

```
[*] A (target chunk) = 0x25c87480
[*] B (sacrifice #1) = 0x25c874b0
[*] D (sacrifice #2) = 0x25c874e0
[*] FAKE target (A+0x20, print_fn-nya A) = 0x25c874a0
[+] FLAG: TecFest26{body_soul_authority_columbina_returns}
```

> Catatan koneksi: saat testing, `pwntools remote('localhost', PORT)` kadang nyangkut karena nyoba IPv6 (`::1`) duluan sebelum fallback ke IPv4 — service-nya kelihatannya cuma benar-benar sehat lewat IPv4. Script ini connect pakai `fam="ipv4"` / host `127.0.0.1` langsung biar stabil. Kalau kamu run manual dan ketemu hang serupa, coba paksa IPv4 juga.

## 4. Soal one-liner

**Untuk v2, one-liner blind (satu kali kirim semua byte tanpa baca balasan) TIDAK memungkinkan.** Bedanya sama v1: dulu alamat tujuan (`0x401347`) statis dan bisa ditulis langsung tanpa perlu tahu apa-apa dari server. Sekarang kita **wajib baca alamat heap (`A` dan `D`) yang dibocorkan server secara live**, lalu hitung `crafted = (D>>12) ^ (A+0x20)` sebelum bisa kirim langkah berikutnya — nilai ini beda setiap koneksi (heap ASLR), jadi nggak bisa di-hardcode di satu payload statis. Exploit ini butuh interaksi dua arah (baca leak → hitung → kirim), minimal lewat script seperti `solve_columbina_v2.py`.

## 5. Catatan ke problem setter

- Patch opsi 5 berhasil menutup jalur exploit yang PALING simpel (raw-write 40 byte sekali jalan), bagus.
- Tapi root cause sebenarnya (opsi 2 "Free" tidak men-NULL-kan slot → UAF) **masih utuh**, dan dikombinasikan dengan leak alamat heap gratis dari opsi 1, itu sudah cukup buat tcache safe-linking poisoning penuh — jadi soal ini **masih solvable**, cuma butuh langkah lebih banyak (dan nggak bisa lagi dapet lewat one-liner blind).
- Kalau intent-nya memang mau soal ini selesai cuma lewat jalur "Luonnotar" tanpa UAF tcache-poisoning, perbaikan yang lebih menutup total: (a) `free()` di opsi 2 harus `array[idx] = NULL` sesudahnya, dan/atau (b) hilangkan print `"%p"` dari opsi 1 supaya nggak ada heap-leak gratis (tanpa leak itu, safe-linking di glibc 2.35 akan jauh lebih sulit dilawan karena kita nggak tahu alamat absolut chunk manapun).
