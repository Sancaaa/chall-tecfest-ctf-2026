# Source Internal

Folder ini berisi bahan pembuatan challenge **Aku Suka Kessoku Band**.

## File

- File FLAC asli Kessoku Band yang digunakan sebagai base audio.
- Script untuk menyisipkan flag ke dalam spectrogram dan metadata.

## Cara Pembuatan Challenge

### Part 1 — Spectrogram

Flag part 1 disisipkan ke dalam audio menggunakan teknik **steganografi spectrogram**.
Alat yang digunakan: [Sonic Visualiser](https://www.sonicvisualiser.org/) atau `sox` + `PIL`.

Caranya:
1. Render teks flag menjadi gambar putih di atas hitam.
2. Konversi gambar tersebut menjadi sinyal audio (tone sweep / SSTV-like).
3. Tambahkan ke bagian **akhir** track audio menggunakan `ffmpeg` atau `sox`.

### Part 2 — Metadata COMMENT

Flag part 2 di-encode dengan **Base64 sebanyak 7 kali**, lalu disisipkan ke field `COMMENT` pada metadata FLAC.

```
Original : TecFest26{1_LQv3_mU51c_4nD_BOCHI!}
Encode x1: VGVjRmVzdDI2ezFfTFF2M19tVTUxY180bkRfQk9DSEkhfQ==
Encode x2: VkdWalJtVnpkREkyZXpGZlRGRjJNMTl0VlRVeFkxODBia1JmUWs5RFNFa2hmUT09
Encode x3: VmtkV2FsSnRWbnBrUkVreVpYcEdabFJHUmpKTk1UbDBWbFJWZUZreE9EQmlhMUptVVdzNVJGTkZhMmhtVVQwOQ==
Encode x4: Vm10a1YyRnNTblJXYm5CclVrVnJlVnBZY0VkYWJGSkhVbXBLVGsxVWJEQldiRkpXWlVacmVFOUVRbWxoTVVwdFZWZHpOVkpHVGtaaE1taHRWVlF3T1E9PQ==
Encode x5: Vm0xMGExWXlSbk5UYmxKWFltNUNjbFZyVm5KbFZuQlpZMFZrWVdKR1NraFZiWEJMVkdzeFZXSkVRbGRpUmtwWFdsVmFjbVZGT1VWUmJXeG9UVlZ3ZEZaV1pIcE9Wa3BIVkd0YWFFMXRhSFJXVmxGM1QxRTlQUT09
Encode x6: Vm0weE1HRXhXWGxTYms1VVlteEtXRmx0TlVOamJGWnlWbTVLYkZadVFscFpNRlpyV1ZkS1IxTnJhRlppV0VKTVZrZHplRlpYU2tWUmJHUnBVbXR3V0Zkc1ZtRmpiVlpHVDFWV1VtSlhlRzlVVmxaM1pFWmFWMXBJY0U5V2EzQklWa2QwWVdGRk1YUmhTRkpYVm14R00xUXhSVGxRVVQwOQ==
Encode x7: Vm0wd2VFMUhSWGhYV0d4VFltczFWVmx0ZUV0WFJteDBUbFZPYW1KR1dubFdiVFZMWWtaYWRWRnNjRnBOUmxweVYxWmtTMUl4VG5KaFJscHBWMFZLVFZaclpIcGxSbHBZVTJ0V1VtSkhVbkJWYlhSM1YwWmtjMVp0Um1waVZscEhWREZXVjFWdFNsaGxSemxWVm14YU0xcEZXbUZXTVhCSlkwVTVWMkV6UWtsV2EyUXdXVmRHUmsxWVVtaFRSa3BZVm0xNFIwMHhVWGhTVkd4UlZWUXdPUT09
```

Field `COMMENT` pada FLAC diisi dengan nilai **Encode x7** di atas.

Tools: `metaflac`, `Kid3`, atau `mutagen` (Python).

```bash
metaflac --set-tag="COMMENT=Vm0wd2VFMUhSWGhYV0d4VFltczFWVmx0ZUV0WFJteDBUbFZPYW1KR1dubFdiVFZMWWtaYWRWRnNjRnBOUmxweVYxWmtTMUl4VG5KaFJscHBWMFZLVFZaclpIcGxSbHBZVTJ0V1VtSkhVbkJWYlhSM1YwWmtjMVp0Um1waVZscEhWREZXVjFWdFNsaGxSemxWVm14YU0xcEZXbUZXTVhCSlkwVTVWMkV6UWtsV2EyUXdXVmRHUmsxWVVtaFRSa3BZVm0xNFIwMHhVWGhTVkd4UlZWUXdPUT09" kessoku_band.flac
```
