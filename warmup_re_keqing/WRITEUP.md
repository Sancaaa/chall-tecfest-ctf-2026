# Warm-up Reverse Engineering — Keqing

**Author:** SancaPWN
**Difficulty:** Warm-up (sangat mudah)

## Konsep

Binary C biasa, tanpa proteksi/obfuscation/packing apapun. Flag ditulis langsung
sebagai string literal di source (`SECRET_SCROLL`), sehingga ikut masuk ke section
`.rodata` apa adanya. Logic program (cek password "elektro") adalah red herring —
tidak perlu dijalankan sama sekali.

## Compile

Dikompilasi di WSL (Kali, gcc 15.2.0) supaya ELF Linux x86-64, bukan PE Windows:

```
gcc -m64 -no-pie -fno-stack-protector -o keqing keqing.c
```

## Intended Solution

1. Extract `keqing_attachment.zip`, `chmod +x keqing`.
2. `strings keqing | grep TecFest` (atau buka di Ghidra/IDA, lihat tab Strings).
3. Flag langsung terbaca plaintext.

## Flag

`TecFest26{keq1n9_m41n5}`

## File author

- `keqing.c` — source
- `keqing` — binary hasil compile (ELF, author only, jangan dibagikan nama file aslinya ke repo publik tanpa cek ulang)
- `dist/keqing_attachment.zip` — attachment peserta (binary saja)
- `flag.txt` — flag asli (jangan di-upload)
