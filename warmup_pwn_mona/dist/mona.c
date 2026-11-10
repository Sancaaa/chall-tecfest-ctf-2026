#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>

#define FLAGSIZE 128

char flag[FLAGSIZE];

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

    read(0, buf, 1024);

    printf("Ramalan Mona: semoga harimu menyenangkan~\n");
}

int main(void) {
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
