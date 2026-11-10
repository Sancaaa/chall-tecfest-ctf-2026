"""
Jean's Favor - Warm-up Cryptography

Ini script yang dipakai Jean buat ngenkripsi flag-nya.
Baca pelan-pelan tiap bagiannya, terus pikirin: gimana cara BALIKIN prosesnya?

Flag format: TecFest26{...}
"""

# Key buat enkripsi -- sengaja ditulis gamblang di sini, gak disembunyiin
# sama sekali. Ini warm-up, jadi kamu gak perlu nyari-nyari key-nya di
# tempat lain, cukup baca file ini sampai habis.
KEY = b"MONDSTADT"


def xor_byte(data_byte, key_byte):
    """
    Operasi XOR ("exclusive or") antara 1 byte data dan 1 byte key.

    Sifat paling penting dari XOR: kalau kamu XOR dua kali pakai key
    yang SAMA, kamu balik lagi ke nilai aslinya.

        data_byte ^ key_byte ^ key_byte == data_byte

    Artinya: fungsi yang PERSIS SAMA ini bisa dipakai buat ENKRIPSI
    maupun DEKRIPSI, selama key yang dipakai sama persis.
    """
    return data_byte ^ key_byte


def xor_encrypt(data: bytes, key: bytes) -> bytes:
    """
    XOR tiap byte di 'data' dengan 1 byte dari 'key', satu-satu berurutan.

    Karena key ('MONDSTADT', panjangnya 9 byte) biasanya lebih pendek dari
    data yang mau dienkripsi, key-nya diulang terus dari awal lagi:
    key[0], key[1], ..., key[8], lalu balik lagi ke key[0], key[1], ...
    sampai semua byte di 'data' kebagian pasangan key-nya.
    """
    hasil = bytearray()  # tempat nampung hasil, byte demi byte

    for index in range(len(data)):
        data_byte = data[index]

        # index % len(key) adalah cara muter balik ke awal key begitu
        # index-nya sudah lebih panjang dari key. Contoh key panjang 9:
        #   index 0  -> key_index 0 -> key[0]
        #   index 8  -> key_index 8 -> key[8]  (byte terakhir di key)
        #   index 9  -> key_index 0 -> key[0]  (muter balik ke awal lagi)
        #   index 10 -> key_index 1 -> key[1]
        key_index = index % len(key)
        key_byte = key[key_index]

        hasil.append(xor_byte(data_byte, key_byte))

    return bytes(hasil)


if __name__ == "__main__":
    # --- Bagian ini yang dijalankan Jean buat BIKIN output.enc ---
    # (ikut dibagikan ke peserta apa adanya, biar prosesnya kebaca jelas,
    # bukan cuma hasil akhirnya doang)

    with open("flag.txt", "rb") as f:
        flag = f.read().strip()

    encrypted = xor_encrypt(flag, KEY)

    with open("dist/output.enc", "wb") as f:
        f.write(encrypted)

    print("Flag asli      :", flag)
    print("Hasil enkripsi :", encrypted.hex())
    print()
    print("Coba pikirin: kalau xor_encrypt() ini dipanggil ULANG terhadap")
    print("HASIL enkripsinya (pakai KEY yang sama persis), bakal ngasih apa?")
