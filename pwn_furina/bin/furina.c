// Binary Exploitation C - Furina
// Topik: OOB array index -> arbitrary write (write-what-where) -> hijack dispatch-table
//        -> tetap harus panggil win() dengan calling convention (argumen register) benar.
// Protections: NX on, PIE off, canary on (red herring - bug utamanya bukan stack overflow)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdint.h>

#define N_VERDICTS 4
#define NOTE_LEN   32

// court.case_notes dan court.verdicts SENGAJA ditaruh bersebelahan dalam satu struct:
// index yang tidak dicek di case_notes bisa menulis keluar batas array itu dan
// menimpa isi court.verdicts (dispatch table berisi function pointer).
struct {
    char case_notes[N_VERDICTS][NOTE_LEN];
    void (*verdicts[N_VERDICTS])(long, long, long);
} court;

void verdict_placeholder(long a, long b, long c) {
    (void)a; (void)b; (void)c;
    printf("Putusan belum ditetapkan untuk index ini.\n");
}

char flag[256];

void win(long defendant_id, long verdict_code, long judge_signature) {
    if (defendant_id == 0x1337 && verdict_code == 0xC0DE && judge_signature == 0xF00DBEEF) {
        fputs(flag, stdout);
        fflush(stdout);
    } else {
        printf("Argumen putusan salah, sidang ditunda.\n");
    }
}

static long read_long(const char *prompt) {
    char line[64];
    printf("%s", prompt);
    fflush(stdout);
    if (!fgets(line, sizeof(line), stdin)) exit(0);
    return strtol(line, NULL, 0);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    for (int i = 0; i < N_VERDICTS; i++) court.verdicts[i] = verdict_placeholder;

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

    // win() ada di code segment, no PIE -> alamatnya statis, dibaca dari attachment
    // binary (objdump/nm/pwntools ELF.symbols), TIDAK di-leak lewat program.
    puts("=== Oratrice Mecanique D'Analyse Cardinale ===");
    while (1) {
        printf("\n1. Catat catatan kasus (index, panjang, isi)\n"
                 "2. Jatuhkan putusan (index, a, b, c)\n"
                 "3. Keluar\n> ");
        fflush(stdout);
        long choice = read_long("");

        if (choice == 1) {
            long idx = read_long("index: ");
            long len = read_long("panjang: ");
            if (len < 0 || len > 4096) {
                printf("panjang tidak valid.\n");
                continue;
            }
            printf("isi: ");
            fflush(stdout);
            // BUG: idx TIDAK dicek terhadap N_VERDICTS -> bisa menulis keluar batas
            // array case_notes dan menimpa court.verdicts (write-what-where).
            read(0, (char *)court.case_notes + idx * NOTE_LEN, len);
        } else if (choice == 2) {
            long idx = read_long("index: ");
            if (idx < 0 || idx >= N_VERDICTS) {
                printf("index putusan di luar batas.\n");
                continue;
            }
            long a = read_long("a: ");
            long b = read_long("b: ");
            long c = read_long("c: ");
            court.verdicts[idx](a, b, c);
        } else {
            break;
        }
    }
    return 0;
}
