# Aku Suka Kessoku Band 🎸

**Kategori:** Forensic  
**Difficulty:** ⭐⭐ Easy–Medium  
**Points:** 1000  
**Author:** TODO

---

## Deskripsi

> Btw aku lagi dengerin lagu Kessoku Band nih, keren banget!  
> Tapi... ada yang aneh sama file musiknya. Kayaknya ada sesuatu yang disembunyiin di sana 👀
>
> Bisakah kamu temukan apa yang tersembunyi di dalam musik ini?
>
> **Flag terbagi menjadi 2 bagian. Gabungkan keduanya untuk mendapatkan flag lengkap!**

---

## File

| File | Deskripsi |
|------|-----------|
| `kessoku_band.flac` | File audio FLAC yang mengandung flag tersembunyi |

---

## Hints

1. 🔭 Musik itu bisa *dilihat*, bukan hanya didengar. Coba lihat bentuk gelombangnya secara visual di bagian akhir lagu.
2. 🏷️ Metadata sebuah file audio bisa menyimpan lebih dari sekadar judul dan artist. Ada apa di field `COMMENT`?
3. 🔄 Sesuatu di metadata tampak seperti teks acak... tapi mungkin bukan acak sama sekali. Coba decode berulang kali.

---

## Struktur

```text
aku-suka-kessoku-band/
├── challenge.yml        # Metadata challenge
├── dist/                # Attachment untuk peserta
│   └── kessoku_band.flac
├── src/                 # Source internal & cara pembuatan
│   └── README.md
└── solver/              # Intended solution & solver resmi
    ├── README.md
    └── solve.py
```

---

## Flag

```
TecFest26{1_LQv3_mU51c_4nD_BOCHI!}
```

> ⚠️ **JANGAN** expose file ini kepada peserta!
