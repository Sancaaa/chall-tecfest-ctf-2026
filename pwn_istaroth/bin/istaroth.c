// Binary Exploitation E - Istaroth (v2 -- ret2libc, ROP chain asli)
// Topik: Multi-stage ROP & shell.
//   Tahap 1: overflow data-only menimpa int `unlocked` yang ditaruh sebagai
//     FIELD STRUCT (bukan local var lepas) bersama buf -> posisi relatifnya
//     dijamin stabil oleh tata letak struct C, tidak bisa ditata ulang
//     compiler/stack-protector (aman dipakai lagi kalau canary dinyalakan
//     ulang suatu saat). Overflow ini TIDAK menyentuh saved-RBP/return-address.
//     Begitu unlocked != 0, program bocorkan DUA alamat runtime sekaligus:
//       (1) alamat resolved (void*)puts -- fungsi pointer ke simbol libc
//           eksternal di binary PIE/PIC selalu di-resolve ke alamat ASLI di
//           shared object asalnya (lewat relokasi GLOB_DAT, beda dari
//           `call puts@plt` yang lewat trampoline PLT) -- jadi nilai ini
//           sudah alamat puts() yang BENERAN di libc.so.6, bisa dipakai
//           langsung hitung base libc pakai libc.so.6 yang dibagikan di
//           attachment.
//       (2) alamat string "./catflag" di .rodata BINARY INI SENDIRI -- sudah
//           termasuk PIE base, dipakai LANGSUNG sebagai argumen tahap 2,
//           TIDAK perlu hitung PIE base binary secara terpisah.
//   Tahap 2: overflow penuh ke return address. TIDAK ADA win()/execve siap
//     pakai di binary ini -- peserta BANGUN SENDIRI ROP chain: cari gadget
//     "pop rdi; ret" di libc.so.6 yang dibagikan, pakai alamat string tahap 1
//     sebagai argumen, pakai alamat system() (dihitung dari base libc tahap 1)
//     sebagai target akhir -> system("./catflag"). Ini ret2libc beneran,
//     bukan sekadar ret ke satu alamat fungsi yang sudah disediakan di binary.
// Protections: NX on, canary OFF (disengaja -- lihat Dockerfile/NOTES.md:
//   canary+ret2libc butuh leak byte canary juga lewat side-channel yang
//   menumpuk skill lain di luar fokus soal ini; fokus "Hard" di sini adalah
//   PIE-defeat dua-leak + bangun ROP chain ret2libc beneran), PIE on,
//   Partial RELRO.
// Chaff: decoy_notice() di bawah TIDAK PERNAH reachable dari jalur manapun --
//   murni jebakan "strings"/grep buat yang nggak baca alur program dan asal
//   nebak flag dari string literal yang kelihatan di binary.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHAFF_FLAG "TecFest26{close_but_wrong_check_your_chain}"

// String argumen untuk system() di tahap 2 -- alamatnya ikut di-leak di tahap
// 1 (sudah termasuk PIE base, dipakai langsung tanpa hitung ulang).
static const char CATFLAG_PATH[] = "./catflag";

void decoy_notice(void) {
    puts(CHAFF_FLAG);
    fflush(stdout);
    exit(0);
}

struct frame {
    char buf[64];
    int unlocked; // field struct -> posisi RELATIF ke buf dijamin stabil oleh
                  // tata letak struct C (lihat komentar di atas file).
};

int vuln(void) {
    struct frame f;
    f.unlocked = 0;
    read(0, f.buf, 256); // baca s.d. 256 byte ke buffer 64 byte -> OVERFLOW
    return f.unlocked;
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stdin, NULL, _IONBF, 0);

    // Cek file flag DI PALING AWAL (sebelum interaksi apa pun) -- biar kalau
    // dites dari attachment/dist tanpa flag yang benar, langsung ketahuan.
    FILE *flag_check = fopen("flag.txt", "r");
    if (!flag_check) {
        puts("Buat flag.txt di directory ini untuk debugging.");
        return 1;
    }
    fclose(flag_check);

    puts("Istaroth: ritual dimulai.");
    if (vuln()) { // tahap 1
        printf("ramalan: %p %p\n", (void *)puts, (void *)CATFLAG_PATH);
        fflush(stdout);
        vuln(); // tahap 2
    }
    puts("ritual selesai tanpa insiden.");
    return 0;
}
