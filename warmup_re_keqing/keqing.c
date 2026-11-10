// Reverse Engineering - Warm-up - Keqing
// Topik: basic static analysis, flag kelihatan langsung lewat `strings`.
// Sengaja TANPA proteksi/obfuscation apapun -- ini warm-up.
#include <stdio.h>
#include <string.h>

// Flag sengaja ditulis langsung sebagai string literal di source,
// jadi ikut masuk section .rodata binary hasil compile apa adanya.
const char *SECRET_SCROLL = "TecFest26{keq1n9_m41n5}";

int main(void) {
    char answer[64];

    printf("=== Yuheng Archives - Keqing's Hidden Scroll ===\n");
    printf("Keqing selalu teliti baca kontrak sampai detail terkecil.\n");
    printf("Kamu juga harus teliti baca binary ini sampai detail terkecil.\n\n");
    printf("Masukkan kata sandi gulungan rahasia: ");
    fflush(stdout);

    if (!fgets(answer, sizeof(answer), stdin)) {
        return 1;
    }
    answer[strcspn(answer, "\r\n")] = '\0';

    // Sengaja bukan cek terhadap flag -- program ini TIDAK perlu dijalankan
    // untuk dapat flag, cukup dibaca string-nya dari binary (static analysis).
    if (strcmp(answer, "elektro") == 0) {
        printf("Benar! Tapi gulungan rahasianya ada di tempat lain...\n");
    } else {
        printf("Salah. Coba baca lebih teliti.\n");
    }

    return 0;
}
