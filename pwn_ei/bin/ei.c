// Binary Exploitation D - Ei
// Topik: Format string exploitation. printf(user_input) tanpa specifier,
//        leak lewat %p/%x dan/atau %n-write ke variabel global pengecekan.
// Protections: NX on, canary on, PIE off ("medium standar", lihat BINEXP_PLANNING.md)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int access_granted = 0;
char flag[256];

void give_flag(void) {
    fputs(flag, stdout);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    // Baca flag SEKALI DI PALING AWAL (sebelum interaksi apa pun) -- kalau
    // filenya tidak ada, langsung ketahuan & exit di sini juga (bisa diganti),
    // bukan baru ketahuan setelah berhasil exploit. give_flag() cuma print
    // buffer ini, tidak buka file lagi -- satu-satunya tempat yang perlu
    // nge-handle "flag tidak ada" ya di sini, bukan dobel.
    FILE *f = fopen("flag.txt", "r");
    if (!f) {
        puts("Buat flag.txt di directory ini untuk debugging.");
        return 1;
    }
    fgets(flag, sizeof(flag), f);
    fclose(f);

    char input[256];

    while (1) {
        printf("> ");
        fflush(stdout);
        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\n")] = 0;
        if (strcmp(input, "exit") == 0) break;

        printf(input); // VULNERABLE: format string, input user langsung jadi format
        printf("\n");

        if (access_granted) {
            give_flag();
            break;
        }
    }
    return 0;
}
