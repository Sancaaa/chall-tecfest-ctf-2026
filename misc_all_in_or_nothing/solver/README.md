# Writeup & Solver — All-in Or Nothing

## Dua Jalur Penyelesaian

### Jalur 1: Cara Orang Gila (10x Menang Poker Berturut-turut)
Permainan menggunakan Simplified Heads-Up Texas Hold'em yang diacak di server (`secrets.SystemRandom`). Setiap kemenangan beruntun menambah `win_streak`. Kekalahan atau *Fold* mengembalikan streak ke `0`. Jika `win_streak == 10`, dealer menyerah dan memberikan flag.

### Jalur 2 (Intended): Blackmail & Perang Psikologis
1. **Clue 1 (`/robots.txt` -> `/staff/shift-receipt`)**: Menemukan bukti penggelapan dana **Panti Harapan** untuk membayar pinjol (`PANTI-9042`).
2. **Clue 2 (`GET /api/table/state` -> `audit_memo_b64`)**: Decode Base64 memo internal berisi kecurangan *cold-deck* terhadap sahabatnya **Bima** & gadai Rolex (`BIMA-404`).
3. **Clue 3 (`/static/assets/dealer_badge.svg` `<metadata>`)**: Decode ROT13 untuk mengungkap penipuan asuransi kesehatan ibunya demi top-up situs slot `KING_MAXWIN88` serta lokasi endpoint `/logs/vault-audit`.
4. **Clue 4 (`/logs/vault-audit`)**: Decode Hex log audit Sindikat pukul 03:17 WIB untuk mendapatkan kode penggelapan kas brankas (`SYNDICATE-777`).
5. **Konfrontasi (`HOLD UP!`)**:
   - Babak 1: Taktik `[B]` + `PANTI-9042`
   - Babak 2: Taktik `[B]` + `BIMA-404`
   - Babak 3: Taktik `[A]` + `KING_MAXWIN88`
   - Babak 4: Taktik `[C]` + `SYNDICATE-777`

## Menjalankan Solver

```bash
python solve.py http://127.0.0.1:13500
```
