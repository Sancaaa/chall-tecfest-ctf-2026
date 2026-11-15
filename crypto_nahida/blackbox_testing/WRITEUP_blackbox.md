# Nahida — Cryptography (Hard) — Write-up Blackbox

**Target:** `nc localhost 13338`
**Attachment:** `server.py`, `capture.pcap`
**Flag:** `TecFest26{7er1_tEr1_D415h0R1!_m45u_M45u_k4W4IIiIiIIii_nOOo!}`

> Catatan: write-up ini hanya untuk review internal (author/problem setter).
> Jangan disalin ke deskripsi/attachment publik — ini berisi langkah solve
> dan nilai antara (keystream, token) yang membocorkan intended solution.

## 1. Baca source dulu

Dari `server.py`, gateway "TecTunnel" ini membungkus setiap koneksi dalam
satu frame: **16 byte header** (`ver,cmd,ip,port,sid,crc32`) lalu **payload**,
semuanya dienkripsi **AES‑CFB‑128**. Yang langsung mencurigakan:

```python
IV = hashlib.sha256(KEY).digest()[:BLOCK]   # IV sesi diturunkan dari kunci

def _dec(): return AES.new(KEY, AES.MODE_CFB, iv=IV, segment_size=128)
def _enc(): return AES.new(KEY, AES.MODE_CFB, iv=IV, segment_size=128)
```

**IV statis, diturunkan dari KEY yang juga statis** — dan dipakai ulang di
*setiap* koneksi baru, untuk arah dekripsi (request masuk) maupun enkripsi
(reply keluar). Ini pelanggaran dasar penggunaan CFB/stream cipher: IV wajib
unik per pesan. Begitu IV&key dipakai ulang, keystream block pertama
`E(IV)` menjadi **sama persis** di semua koneksi dan semua arah — itu celah
utamanya.

Bug pendukung lain di handler:

```python
if len(buf) < BLOCK:
    self._reply(b"\x00" * BLOCK, True)   # (1) oracle keystream0 gratis
    return
...
if dst == DBG:
    return payload[:1024], False          # (2) echo TANPA re-enkripsi
```

(1) Kalau kita kirim <16 byte lalu diamkan koneksi, server membalas
`AES_CFB_encrypt(0x00*16)` yaitu **`E(IV)` murni** — keystream block pertama,
gratis, tanpa butuh apa‑apa.

(2) Rute `DBG` (diagnostik loopback) membalas payload **hasil dekripsi**
dalam bentuk **plaintext mentah** (`enc=False`). Ini adalah **decryption
oracle**: body yang kita kirim sebagai "ciphertext" apapun, akan dibongkar
lalu dikembalikan apa adanya.

## 2. Mengubah oracle (2) jadi "AES single-block encrypt oracle"

CFB-128 decrypt: `P_i = C_i XOR E(C_{i-1})`, dengan `C_{-1} = IV`.

Karena kita bebas mengisi *byte apa saja* sebagai "ciphertext" yang kita
kirim (server tidak peduli apakah itu betulan hasil enkripsi), kita bisa
susun pesan 3-block ke rute DBG:

```
block0 = header_DBG  (dibuat valid pakai keystream0 = E(IV) yang sudah bocor)
block1 = X            (nilai apapun yang ingin kita "enkripsi")
block2 = 0x00 * 16
```

Server mendekripsi:
- `P0` = header DBG valid → rute = DBG, **enc=False** (reply tidak dienkripsi ulang)
- `P1` = `X XOR E(block0)` → sampah, tidak dipakai
- `P2` = `0 XOR E(X)` = **`E(X)`** ← inilah yang kita mau!

Karena rute DBG membalas **semua** payload mentah (bukan cuma block pertama),
`P2` ikut dikirim balik dalam bentuk plaintext. Hasilnya: kita punya oracle
`E(X)` untuk **X sembarang** yang kita pilih — setara "known-key oracle"
tanpa pernah tahu AES key aslinya.

Dengan `keystream0 = E(IV)` + oracle `E(X)` ini, kita bisa:
- **Mendekripsi** ciphertext apapun block‑demi‑block (asal tahu ciphertext block sebelumnya).
- **Mengenkripsi** plaintext apapun yang kita susun sendiri (bikin header valid milik kita, lalu rantai CFB-nya kita generate sendiri block demi block lewat oracle).

## 3. Memakai `capture.pcap`: menyadap token yang valid

`capture.pcap` berisi 5 koneksi TCP ke gateway. Dua di antaranya
(`192.168.1.50:40001` dan `192.168.1.54:40005`) mendapat reply **49 byte**
— identik dengan panjang reply sukses `"200 OK vault/1.0\nuptime 41d\n..."`.
Tiga lainnya mendapat reply 32 byte = `"401 DENIED vault\nnot authorized\n"`
(percobaan token salah / traffic decoy).

Jadi salah satu sesi yang **sukses** (`192.168.1.50:40001`) pasti memakai
**token yang benar**. Karena IV/key gateway statis di semua koneksi — bukan
hanya saat live, tapi juga saat capture diambil — keystream block‑0 yang
sudah kita bocorkan dari service live (`E(IV)`) **berlaku juga** untuk
men-dekripsi header request yang disadap itu. Lanjutannya didekripsi
block‑demi‑block lewat oracle `E(X)` di atas, pakai ciphertext block
sebelumnya (dari pcap) sebagai `X`.

Hasil dekripsi payload request tersebut:

```
HELLO vault/1.0
AUTH 570cc28128201ee0083038963488c5ab
#########
CMD stat
######
END
############
```

(`#` adalah padding baris yang diabaikan parser `vault_handle` — tidak
mengganggu.) **Token asli vault berhasil didapat**: `570cc28128201ee0083038963488c5ab`.

## 4. Replay dengan command `flag`

Dengan token asli di tangan, kita susun request baru ke `VAULT`
(`10.0.0.5:9000`) secara live:

```
HELLO vault/1.0
AUTH 570cc28128201ee0083038963488c5ab
CMD flag
END
```

Header (block0) kita enkripsi sendiri pakai `keystream0`. Setiap block
payload berikutnya dienkripsi berurutan: minta `E(C_{i-1})` ke oracle DBG,
lalu XOR dengan plaintext block‑i — persis cara CFB asli bekerja, hanya
saja kita yang mengisi keystream‑nya lewat oracle, bukan AES key.

Kirim ke `nc localhost 13338`, terima balasan terenkripsi, dekripsi dengan
teknik yang sama (`keystream0` untuk block pertama reply, lalu oracle untuk
block selanjutnya):

```
200 OK vault/1.0
TecFest26{7er1_tEr1_D415h0R1!_m45u_M45u_k4W4IIiIiIIii_nOOo!}
```

## 5. Ringkasan alur solve

1. Baca `server.py` → sadari IV statis diturunkan dari KEY dan dipakai ulang
   di semua koneksi/arah (bug kriptografi inti).
2. Kirim <16 byte ke service live → bocorkan `keystream0 = E(IV)` gratis.
3. Manfaatkan rute `DBG` (`enc=False`, echo mentah) sebagai **oracle enkripsi
   AES satu-block sembarang** `E(X)`.
4. Pakai `keystream0` + oracle untuk **mendekripsi** request sukses di
   `capture.pcap` → dapat **token vault** yang valid.
5. Pakai `keystream0` + oracle lagi untuk **mengenkripsi** request
   `CMD flag` baru dengan token itu, kirim ke service live, dekripsi
   balasannya → **flag**.

Intinya: reuse IV/key pada stream cipher mode + adanya satu rute yang
membalas plaintext tanpa re-enkripsi = kombinasi yang membuat seluruh
skema bisa dibongkar tanpa pernah menyentuh AES key-nya sama sekali.
