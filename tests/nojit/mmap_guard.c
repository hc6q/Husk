/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Linux host validation: abort on dynamic executable mappings. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/mman.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
static void check(int prot, int anonymous) {
    if (((prot & (PROT_WRITE | PROT_EXEC)) == (PROT_WRITE | PROT_EXEC)) || (anonymous && (prot & PROT_EXEC))) {
        const char text[] = "[NoJIT] ERROR: executable dynamic mapping requested\n";
        write(2, text, sizeof(text)-1); _exit(90);
    }
}
void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t offset) {
    static void *(*real)(void *,size_t,int,int,int,off_t);
    if (!real) real=dlsym(RTLD_NEXT,"mmap");
    check(prot, fd < 0 || (flags & MAP_ANONYMOUS)); return real(addr,len,prot,flags,fd,offset);
}
void *mmap64(void *addr, size_t len, int prot, int flags, int fd, off64_t offset) {
    static void *(*real)(void *,size_t,int,int,int,off64_t);
    if (!real) real=dlsym(RTLD_NEXT,"mmap64");
    check(prot, fd < 0 || (flags & MAP_ANONYMOUS)); return real(addr,len,prot,flags,fd,offset);
}
int mprotect(void *addr,size_t len,int prot) {
    static int (*real)(void *,size_t,int);
    if (!real) real=dlsym(RTLD_NEXT,"mprotect");
    check(prot, 1); return real(addr,len,prot);
}
