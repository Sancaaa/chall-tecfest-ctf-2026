# Intended Solution: The Apprentice Grimoire

**Kategori:** Reverse Engineering  
**Difficulty:** Easy  
**Flag:** `TecFest26{g0_vm_4ppr3nt1c3_gr1m01r3}`

---

## Ringkasan Konsep

Peserta diberikan sebuah binary Go (`grimoire`, ELF 64-bit Linux, tidak di-strip) yang mengimplementasikan *Virtual Machine* (VM) sederhana untuk memvalidasi input flag. Tidak ada obfuscation, anti-debugging, atau self-modifying code.

---

## Langkah Analisis

### 1. Navigasi Simbol Binary Golang

Binary Go berukuran ~2,2 MB karena menyertakan runtime Go. Karena binary tidak di-strip, peserta dapat langsung mencari fungsi user-defined pada simbol:

```bash
nm grimoire | grep ' main\.'
```

Simbol penting yang muncul:
- `main.main`
- `main.executeVM`
- `main.spellBytecode`
- `main.spellTarget`

### 2. Analisis `main.main` dan `main.executeVM`

Di Ghidra atau IDA, buka `main.main`. Terlihat program mencetak prompt `"Speak the incantation: "`, membaca satu baris dari `stdin`, lalu memanggil `main.executeVM(input)`. Jika hasilnya `true`, program mencetak `"The spell holds!"`, jika `false` mencetak `"The spell fizzles."`.

Di dalam `main.executeVM`, terlihat pengecekan panjang input (`len(input) == len(spellTarget)`) diikuti loop interpreter dengan dua state utama: Program Counter (`pc`) dan Accumulator (`acc`), serta indeks karakter (`idx`).

Karena hanya terdapat 7 opcode, compiler Go menghasilkan blok `if-else` (percabangan standar) tanpa jump table:

| Opcode | Nama | Operasi |
|--------|------|---------|
| `0x01` | `LOAD` | `acc = input[idx]`, `pc++` |
| `0x02` | `XOR` | `acc ^= bytecode[pc+1]`, `pc += 2` |
| `0x03` | `ADD_IDX` | `acc += byte(idx)`, `pc++` |
| `0x04` | `CMP` | Jika `acc != target[idx]`, langsung return `false` (fail fast); else `pc++` |
| `0x05` | `NEXT` | `idx++`; jika `idx >= len(target)` maka `pc++`, else `pc = 0` |
| `0x06` | `SUCCESS` | Return `true` |
| `0x07` | `FAIL` | Return `false` |

### 3. Ekstraksi Bytecode dan Target dari `.rodata`

Pada Go, tipe `string` direpresentasikan sebagai header 16 byte `(ptr, len)` di `.data` yang menunjuk ke byte statis di section `.rodata`.

Melalui Ghidra atau inspeksi ELF pada simbol `main.spellBytecode` dan `main.spellTarget`:
- `main.spellBytecode` (8 byte): `01 02 5a 03 04 05 06 07`
- `main.spellTarget` (36 byte): `0e 40 3b 1f 43 2e 34 6f 74 2a 47 75 11 39 45 14 7e 3b 3c 3b 7d 49 44 82 51 82 1f 58 44 88 55 89 8b 49 8b 4a`

### 4. Rekonstruksi Logika & Inversi Flag

Untuk setiap karakter `input[i]`, VM menjalankan urutan instruksi:

1. `LOAD`: `acc = input[i]`
2. `XOR 0x5a`: `acc = acc ^ 0x5a`
3. `ADD_IDX`: `acc = (acc + i) & 0xff`
4. `CMP`: pastikan `acc == target[i]`
5. `NEXT`: lanjut ke `i + 1` dan ulangi dari `pc = 0` hingga semua 36 karakter cocok, lalu eksekusi `0x06 SUCCESS`.

Karena setiap karakter diproses secara independen (1-ke-1), inversi dapat dilakukan secara analitik:

```python
flag_byte = ((target[i] - i) & 0xFF) ^ 0x5A
```

Atau secara brute-force 256 nilai byte untuk setiap posisi `i`.

---

## Menjalankan Solver Otomatis

```bash
cd solver
python3 solve.py ../dist/grimoire
```

Output yang diharapkan:

```text
[*] Binary      : .../dist/grimoire
[*] Bytecode    : 01 02 5a 03 04 05 06 07
[*] XOR key     : 0x5a
[*] Target len  : 36
[*] Target hex  : 0e403b1f432e346f742a4775113945147e3b3c3b7d49448251821f58448855898b498b4a
[+] Flag        : TecFest26{g0_vm_4ppr3nt1c3_gr1m01r3}
```

---

## Estimasi Kesulitan & Potensi Unintended Solution

- **Kesulitan:** Easy. Peserta berlatih navigasi simbol Golang di Ghidra/IDA, membaca struktur string Go di `.rodata`, memahami interpreter VM sederhana, dan menulis skrip inversi Python.
- **Unintended Solution:** Tidak ada shortcut `strings` karena byte `spellTarget` terenkripsi XOR + offset indeks dan `spellBytecode` bukan teks ASCII yang terbaca. Karena validasi bersifat per karakter secara independen dan fail-fast, peserta dapat melakukan side-channel/timing brute-force jika menstrumentasi binary, namun kompleksitasnya setara dengan analisis statis langsung.
