// catflag - pengganti /bin/sh untuk win() Istaroth.
// Tujuan: begitu exploit berhasil dapat eksekusi kode, peserta cuma dapat
// program kecil yang membaca & mencetak flag lalu keluar -- BUKAN shell
// interaktif penuh (lihat CHALLENGE_DAN_HOSTING.md 2.4 dan CSV Notes Author E).
#include <stdio.h>

int main(void) {
    char buf[256];
    FILE *f = fopen("flag.txt", "r"); // relatif terhadap cwd proses (sama dgn istaroth)
    if (!f) {
        puts("Buat flag.txt di directory ini untuk debugging.");
        return 1;
    }
    if (fgets(buf, sizeof(buf), f)) fputs(buf, stdout);
    fclose(f);
    fflush(stdout);
    return 0;
}
