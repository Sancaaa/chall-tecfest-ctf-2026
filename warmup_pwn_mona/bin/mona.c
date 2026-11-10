// Binary Exploitation - Warm-up - Mona
// Topik: buffer overflow paling dasar. Spam input sampai overflow -> crash
// (SIGSEGV) -> win() terpanggil sebagai signal handler dan langsung kasih flag.
// Pola mengikuti format-string-0.c: flag dibaca SEKALI ke buffer global di awal
// main() (sebelum apapun lain dijalankan), signal handler cuma print buffer itu
// (bukan buka file lagi di dalam handler).
//
// Protections: canary OFF (sengaja, lihat vuln()) -- NX/PIE tidak relevan,
// challenge ini tidak perlu redirect eksekusi ke shellcode/gadget, cukup
// crash lewat return address yang rusak.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

#define FLAGSIZE 128

char flag[FLAGSIZE];

// win() dipanggil langsung oleh kernel sebagai signal handler SAAT SIGSEGV
// tercapai (bukan dipanggil manual dari vuln()) -- itulah "win condition"
// warm-up ini: cukup bikin program crash, kamu menang.
void win(int sig) {
    (void)sig;
    printf("%s", flag);
    fflush(stdout);
    _exit(0);
}

void vuln(void) {
    char buf[64];

    printf("Mona sedang meramal nasib bintangmu...\n");
    printf("Tulis pertanyaanmu untuk Astrolabe: ");
    fflush(stdout);

    read(0, buf, 1024); // classic stack buffer overflow, tanpa bound check

    printf("Ramalan Mona: semoga harimu menyenangkan~\n");
}

int main(void) {
    // Cek & baca flag.txt di awal BANGET, sebelum hal lain -- kalau filenya
    // gak ada, langsung ketauan dari sekarang (bukan nanti pas udah crash).
    FILE *f = fopen("flag.txt", "r");
    if (f == NULL) {
        printf("flag.txt tidak ditemukan di direktori ini, lapor panitia.\n");
        exit(0);
    }
    fgets(flag, FLAGSIZE, f);
    fclose(f);

    setvbuf(stdout, NULL, _IONBF, 0);
    signal(SIGSEGV, win);

    puts("=== Mona's Astrology Commission (Warm-up) ===");
    vuln();

    return 0;
}
