/*
 * Rhinedottir enigma maCChine - Reverse Engineering E (Hard)
 *
 * Satu binary, dua proses. Child menjalankan program peserta; parent adalah
 * "kernel"-nya: mencegat syscall bernomor palsu (0x401/0x402) lewat ptrace dan
 * menjalankan mesin rotor di sisinya. Hanya author yang boleh membaca file ini.
 *
 * Build: lihat Dockerfile (jangan compile manual di host; alamat call site
 * ikut menentukan tabel harapan).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <string.h>
#include <sys/ptrace.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>

#include "tables.h"

#define OP_ENC 0x401
#define OP_RST 0x402

static void out(const char *s) { (void)!write(1, s, strlen(s)); }
static void err(const char *s) { (void)!write(2, s, strlen(s)); }

/* ---------------------------------------------------------------- child --- */

/* Tiga call site syscall yang berbeda. Label *_ret berada tepat setelah
 * instruksi syscall (alamat itulah yang dilihat parent sebagai rip). */
#define SITE(nm)                                                              \
    static __attribute__((noinline, noclone, noipa)) long nm(long op, long a) \
    {                                                                         \
        long r;                                                               \
        __asm__ volatile("syscall\n\t.globl " #nm "_ret\n\t" #nm "_ret:"      \
                         : "=a"(r)                                            \
                         : "0"(op), "D"(a)                                    \
                         : "rcx", "r11", "memory");                           \
        return r;                                                             \
    }
SITE(k_a)
SITE(k_b)
SITE(k_c)

static int read_line(char *buf, int max)
{
    int n = 0;
    char c;
    for (;;) {
        long r = read(0, &c, 1);
        if (r <= 0)
            return n > 0 ? n : -1;
        if (c == '\n')
            break;
        if (n < max)
            buf[n++] = c;
    }
    if (n > 0 && buf[n - 1] == '\r')
        n--;
    return n;
}

static int child_main(void)
{
    unsigned char resp[LEN];
    char buf[512];

    out("== Rhinedottir enigma maCChine ==\n");
    out("Roda-roda berputar, menunggu kata sandimu.\n");
    for (;;) {
        out("sandi> ");
        int n = read_line(buf, (int)sizeof buf);
        if (n < 0)
            return 0;
        if (n != LEN) {
            out("Panjang kata sandi tidak sesuai.\n");
            continue;
        }
        k_a(OP_RST, 0);
        for (int i = 0; i < LEN; i++) {
            long x = (unsigned char)buf[i], r;
            switch (i % 3) {
            case 0: r = k_a(OP_ENC, x); break;
            case 1: r = k_b(OP_ENC, x); break;
            default: r = k_c(OP_ENC, x); break;
            }
            resp[i] = (unsigned char)r;
        }
        /* bandingkan semuanya di akhir, tanpa keluar lebih awal */
        const unsigned char *e = EXP;
        __asm__ volatile("" : "+r"(e)); /* cegah kompiler melipat EXP jadi konstanta */
        unsigned char d = 0;
        for (int i = 0; i < LEN; i++)
            d |= resp[i] ^ e[i];
        out(d == 0 ? "Mesin berdengung pelan. Kata sandi diterima.\n"
                   : "Roda-roda berputar, tetapi tidak ada yang terbuka.\n");
    }
}

/* --------------------------------------------------------------- parent --- */

static unsigned char INV[3][256];
static unsigned pos[3];

static void kreset(void)
{
    pos[0] = INIT0;
    pos[1] = INIT1;
    pos[2] = INIT2;
}

static void kstep(void)
{
    if (pos[1] == N1) {              /* double-step */
        pos[1] = (pos[1] + 1) & 255;
        pos[2] = (pos[2] + 1) & 255;
    } else if (pos[0] == N0) {       /* carry */
        pos[1] = (pos[1] + 1) & 255;
    }
    pos[0] = (pos[0] + 1) & 255;
}

/* Jalur sinyal rotor -> reflector -> rotor balik, ditulis sebagai state machine. */
static unsigned kpath(unsigned a)
{
    unsigned st = 0x1a7, i = 0;
    for (;;) {
        switch (st) {
        case 0x1a7:
            i = 0;
            st = 0x2c3;
            break;
        case 0x2c3:
            a = (ROT[i][(a + pos[i]) & 255] - pos[i]) & 255;
            i++;
            st = (i < 3) ? 0x2c3 : 0x4e9;
            if ((pos[i & 1] * (pos[i & 1] + 1)) & 1) /* opaque: selalu genap */
                st = 0x7f2;
            break;
        case 0x7f2:
            a ^= 0x5a;
            st = 0x4e9;
            break;
        case 0x4e9:
            a = REFL[a];
            i = 2;
            st = 0x31b;
            break;
        case 0x31b:
            a = (INV[i][(a + pos[i]) & 255] - pos[i]) & 255;
            if (i) {
                i--;
                st = 0x31b;
            } else {
                st = 0x6d0;
            }
            break;
        case 0x6d0:
            return a;
        default:
            return 0;
        }
    }
}

static unsigned kenc(unsigned x, unsigned long rip)
{
    unsigned salt = (unsigned)(((rip >> 4) ^ (rip >> 12)) & 0xff);
    unsigned y;
    kstep();
    pos[2] = (pos[2] + salt) & 255;
    y = kpath(x);
    pos[2] = (pos[2] + x) & 255;
    return y;
}

static int kernel(pid_t pid)
{
    int st, insys = 0, have = 0, sig = 0;
    long pending = 0;
    struct user_regs_struct rg;

    if (waitpid(pid, &st, 0) < 0)
        return 1;
    if (WIFEXITED(st))          /* child sudah keluar sebelum sempat dilacak */
        return WEXITSTATUS(st);
    if (ptrace(PTRACE_SETOPTIONS, pid, 0, PTRACE_O_TRACESYSGOOD | PTRACE_O_EXITKILL) < 0) {
        err("Mesin tidak bisa dijalankan di lingkungan ini (ptrace ditolak).\n");
        kill(pid, SIGKILL);
        return 1;
    }
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 256; j++)
            INV[i][ROT[i][j]] = (unsigned char)j;
    kreset();

    for (;;) {
        if (ptrace(PTRACE_SYSCALL, pid, 0, sig) < 0)
            break;
        sig = 0;
        if (waitpid(pid, &st, 0) < 0)
            break;
        if (WIFEXITED(st))
            return WEXITSTATUS(st);
        if (WIFSIGNALED(st))
            return 128 + WTERMSIG(st);
        if (!WIFSTOPPED(st))
            continue;
        int s = WSTOPSIG(st);
        if (s == (SIGTRAP | 0x80)) {
            insys = !insys;
            if (ptrace(PTRACE_GETREGS, pid, 0, &rg) < 0)
                continue;
            if (insys) {
                have = 0;
                if (rg.orig_rax == OP_ENC) {
                    pending = (long)kenc((unsigned)(rg.rdi & 255), rg.rip);
                    have = 1;
                } else if (rg.orig_rax == OP_RST) {
                    kreset();
                    pending = 0;
                    have = 1;
                }
                if (have) {
                    rg.orig_rax = (unsigned long long)-1;
                    ptrace(PTRACE_SETREGS, pid, 0, &rg);
                }
            } else if (have) {
                rg.rax = (unsigned long long)pending;
                ptrace(PTRACE_SETREGS, pid, 0, &rg);
                have = 0;
            }
        } else {
            sig = (s == SIGSTOP || s == SIGTRAP) ? 0 : s;
        }
    }
    return 1;
}

int main(void)
{
    pid_t pid = fork();
    if (pid < 0)
        return 1;
    if (pid == 0) {
        if (ptrace(PTRACE_TRACEME, 0, 0, 0) < 0) {
            out("Ada saksi ketiga di ruangan ini. Mesin menolak bekerja.\n");
            _exit(1);
        }
        raise(SIGSTOP);
        _exit(child_main());
    }
    return kernel(pid);
}
