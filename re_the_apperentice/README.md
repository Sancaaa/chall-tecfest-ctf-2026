# The Apprentice Grimoire

**Kategori:** Reverse Engineering  
**Difficulty:** Easy  
**Points:** 500  
**Author:** TecFest CTF Committee

---

## Deskripsi

> Seorang penyihir magang menemukan sebuah grimoire kuno dalam bentuk binary Golang. Katanya, mantra di dalamnya dilindungi oleh sebuah mesin virtual mini yang hanya menerima satu kalimat sihir yang tepat.
>
> Jika mantranya benar, program menjawab `"The spell holds!"`. Jika salah, `"The spell fizzles."`. Bisakah kamu membaca cara kerja mesin virtual tersebut dan menemukan mantra yang benar?

---

## File

| File | Deskripsi |
|------|-----------|
| `dist/grimoire` | Binary Linux x86-64 (Golang, unstripped) yang berisi VM validator |

---

## Hints

1. Binary ini dikompilasi dari Golang tanpa di-strip. Cari fungsi utama buatan developer seperti `main.main` dan `main.executeVM` di daftar simbol.
2. Bytecode VM dan array target tidak dibangun saat runtime; keduanya tersimpan statis sebagai string literal di section `.rodata`.
3. Setiap karakter input diproses secara independen oleh VM menggunakan XOR dengan byte konstanta lalu ditambah indeks posisinya. Kamu bisa membalikkan operasinya atau melakukan brute-force per karakter.

---

## Struktur

```text
the-apprentice-grimoire/
├── challenge.yml        # Metadata challenge untuk platform
├── README.md            # Ringkasan challenge (internal panitia)
├── dist/                # Attachment peserta
│   └── grimoire
├── src/                 # Source code & build script internal
│   ├── README.md
│   ├── Makefile
│   ├── build.ps1
│   ├── go.mod
│   ├── main.go
│   └── main_test.go
└── solver/              # Write-up & solver resmi
    ├── README.md
    └── solve.py
```

---

## Flag

```text
TecFest26{g0_vm_4ppr3nt1c3_gr1m01r3}
```
