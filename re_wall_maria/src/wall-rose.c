#include <stdio.h>
#include <string.h>

#define KEY 0x2A
#define FAIL do{ puts("Tch. Kamu bukan Levi."); return 1; }while(0)

int main(void){
    char pw[64], code[64];
    printf("== Wall Rose ==\nPassword: ");
    if(scanf("%63s",pw)!=1) return 1;
    if(strcmp(pw,"shinzou_wo_sasageyo")!=0) FAIL;
    puts("Gerbang Rose terbuka.");
    printf("Secret code: ");
    if(scanf("%63s",code)!=1) return 1;
    if(strlen(code)!=7) FAIL;
    if(((code[0]^KEY)&0xFF)!=0x7e) FAIL;
    if(((code[1]^KEY)&0xFF)!=0x1e) FAIL;
    if(((code[2]^KEY)&0xFF)!=0x5e) FAIL;
    if(((code[3]^KEY)&0xFF)!=0x1e) FAIL;
    if(((code[4]^KEY)&0xFF)!=0x41) FAIL;
    if(((code[5]^KEY)&0xFF)!=0x1e) FAIL;
    if(((code[6]^KEY)&0xFF)!=0x4f) FAIL;
    putchar(0x7e^KEY);
    putchar(0x4f^KEY);
    putchar(0x49^KEY);
    putchar(0x6c^KEY);
    putchar(0x4f^KEY);
    putchar(0x59^KEY);
    putchar(0x5e^KEY);
    putchar(0x18^KEY);
    putchar(0x1c^KEY);
    putchar(0x51^KEY);
    putchar(0x53^KEY);
    putchar(0x19^KEY);
    putchar(0x4d^KEY);
    putchar(0x1e^KEY);
    putchar(0x1e^KEY);
    putchar(0x58^KEY);
    putchar(0x19^KEY);
    putchar(0x75^KEY);
    putchar(0x5e^KEY);
    putchar(0x1e^KEY);
    putchar(0x5e^KEY);
    putchar(0x1e^KEY);
    putchar(0x41^KEY);
    putchar(0x1e^KEY);
    putchar(0x19^KEY);
    putchar(0x75^KEY);
    putchar(0x59^KEY);
    putchar(0x5e^KEY);
    putchar(0x1e^KEY);
    putchar(0x5e^KEY);
    putchar(0x1b^KEY);
    putchar(0x49^KEY);
    putchar(0x57^KEY);
    putchar(10);
    return 0;
}
