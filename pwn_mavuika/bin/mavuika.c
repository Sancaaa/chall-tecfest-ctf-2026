// Binary Exploitation B - Mavuika
// Topik: Ret2win klasik
// Protections: NX on, canary off, PIE off
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

char flag[256];

void win(void) {
    fputs(flag, stdout);
    fflush(stdout);
    exit(0);
}

void vuln(void) {
    char buf[64];

    // win() ada di code segment, no PIE -> alamatnya statis dan sudah bisa dibaca
    // langsung dari attachment binary (objdump/nm/pwntools ELF.symbols), TIDAK
    // di-leak lewat program -- peserta memang harus analisis binary untuk ini.
    printf("masukkan input: ");
    fflush(stdout);
    read(0, buf, 256); // overflow return address
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    // Baca flag SEKALI DI PALING AWAL (sebelum interaksi apa pun) -- kalau
    // filenya tidak ada, langsung ketahuan & exit di sini juga (bisa diganti),
    // bukan baru ketahuan setelah berhasil exploit. win() cuma print buffer
    // ini, tidak buka file lagi -- satu-satunya tempat yang perlu nge-handle
    // "flag tidak ada" ya di sini, bukan dobel.
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        puts("Buat flag.txt di directory ini untuk debugging.");
        return 1;
    }
    fgets(flag, sizeof(flag), f);
    fclose(f);
    
    vuln();
    puts("selesai, tidak ada yang spesial.");
    return 0;
}
