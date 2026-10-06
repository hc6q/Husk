/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "qemu/osdep.h"
#include "husk-ios-jit.h"

#if !defined(HUSK_NO_JIT) || !defined(CONFIG_TCG_INTERPRETER)
#error "Husk No-JIT requires the QEMU TCI backend"
#endif

#ifdef __APPLE__
#include <TargetConditionals.h>
#if TARGET_OS_IPHONE
#include <os/proc.h>
#include <mach/mach.h>
#endif
#endif

/* Query the linked QEMU, not an app preference or a build log. */
HUSK_EXPORT bool husk_tci_enabled(void) { return true; }

/* Audit current mappings, including dependencies loaded after app startup. */
HUSK_EXPORT bool husk_nojit_memory_is_safe(void)
{
#if defined(__APPLE__) && TARGET_OS_IPHONE
    vm_address_t address = 0;
    while (true) {
        vm_size_t size = 0;
        natural_t depth = 0;
        vm_region_submap_info_data_64_t info;
        mach_msg_type_number_t count = VM_REGION_SUBMAP_INFO_COUNT_64;
        kern_return_t result;
        do {
            count = VM_REGION_SUBMAP_INFO_COUNT_64;
            result = vm_region_recurse_64(mach_task_self(), &address, &size,
                                         &depth, (vm_region_recurse_info_t)&info,
                                         &count);
            if (result == KERN_INVALID_ADDRESS) {
                return true;
            }
            if (result != KERN_SUCCESS) {
                return false;
            }
            if (info.is_submap) {
                depth++;
            }
        } while (info.is_submap);
        if ((info.protection & (VM_PROT_WRITE | VM_PROT_EXECUTE))
            == (VM_PROT_WRITE | VM_PROT_EXECUTE)) {
            fprintf(stderr, "[NoJIT] ERROR: W+X mapping at %p\n",
                    (void *)(uintptr_t)address);
            return false;
        }
        if (size == 0 || address + size < address) {
            return false;
        }
        address += size;
    }
#else
    return true;
#endif
}

/* Retain the ABI, but never probe, allocate or detach a debugger. */
void husk_ios_jit_install_trap_handler(void) {}
bool husk_ios_jit_prewarm(size_t bytes) { (void)bytes; return false; }
bool husk_ios_jit_is_available(void) { return false; }
bool husk_ios_jit_mapjit_works(void) { return false; }
void husk_ios_jit_detach(void) {}
HuskDualMapping husk_ios_jit_allocate(size_t bytes)
{
    (void)bytes;
    return (HuskDualMapping){0};
}
void husk_ios_jit_release(HuskDualMapping *m) { memset(m, 0, sizeof(*m)); }

size_t husk_ios_available_memory(void)
{
#if defined(__APPLE__) && TARGET_OS_IPHONE
    return os_proc_available_memory();
#else
    return 0;
#endif
}

void husk_ios_jit_log_footprint(const char *tag)
{
#if defined(__APPLE__) && TARGET_OS_IPHONE
    task_vm_info_data_t info;
    mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &count)
        == KERN_SUCCESS) {
        fprintf(stderr, "[NoJIT] footprint[%s]=%llu available=%zu\n",
                tag ? tag : "", (unsigned long long)info.phys_footprint,
                husk_ios_available_memory());
    }
#else
    (void)tag;
#endif
}
