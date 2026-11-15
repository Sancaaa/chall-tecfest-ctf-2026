# Source Internal: The Apprentice Grimoire

Direktori ini berisi source code Go untuk challenge **The Apprentice Grimoire** (`grimoire`).

## Catatan Desain

- Binary dikompilasi untuk `linux/amd64` tanpa CGO dan **tanpa** strip simbol (`-s -w` tidak digunakan) agar simbol `main.main` dan `main.executeVM` tetap tersedia saat dianalisis di Ghidra atau IDA.
- Flag `-trimpath` digunakan saat build untuk menghapus path direktori lokal mesin pembuat dari metadata binary.
- `spellBytecode` dan `spellTarget` dideklarasikan sebagai string literal sehingga tersimpan statis di section `.rodata`.

## Build & Test

Jalankan unit test secara lokal:

```bash
go test -v ./...
```

Build binary peserta ke `../dist/grimoire`:

```bash
# Linux / macOS
make build

# Windows PowerShell
.\build.ps1
```
