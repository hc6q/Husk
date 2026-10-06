#!/usr/bin/env python3
"""Experiment: retain virtual time when a non-icount snapshot enters fixed icount.

Only for the pinned No-JIT test build. This is not applied by build_ios.sh.
Native snapshot timer state omits the timer/icount subsection. Seed the
instruction clock from its saved, paused cpu_clock_offset instead of zero.
Already-instruction-counted snapshots keep their original counters and bias.
"""
from pathlib import Path
import sys

file = Path(sys.argv[1]) / 'system/cpu-timers.c'
source = file.read_text()
marker = '/* HUSK_NOJIT_SNAPSHOT_CLOCK_EXPERIMENT */'
if marker not in source:
    anchor = 'static const VMStateDescription icount_vmstate_timers = {'
    functions = r'''/* HUSK_NOJIT_SNAPSHOT_CLOCK_EXPERIMENT */
static bool husk_loaded_icount_subsection;

static int husk_timer_pre_load(void *opaque)
{
    husk_loaded_icount_subsection = false;
    return 0;
}

static int husk_icount_post_load(void *opaque, int version_id)
{
    husk_loaded_icount_subsection = true;
    return 0;
}

static int husk_timer_post_load(void *opaque, int version_id)
{
#if defined(HUSK_NO_JIT) && defined(CONFIG_TCG_INTERPRETER)
    TimersState *s = opaque;
    if (icount_enabled() && !husk_loaded_icount_subsection) {
        if (version_id < 2 || s->cpu_clock_offset < 0 ||
            s->cpu_ticks_enabled || icount_enabled() != ICOUNT_PRECISE) {
            error_report("[NoJIT] Cannot align this snapshot instruction clock");
            return -EINVAL;
        }
        s->qemu_icount = 0;
        qatomic_set_i64(&s->qemu_icount_bias, s->cpu_clock_offset);
        fprintf(stderr, "[NoJIT] Snapshot clock aligned at %" PRId64 " ns\n",
                s->cpu_clock_offset);
    }
#endif
    return 0;
}

'''
    changes = [
        (anchor, functions + anchor),
        ('    .needed = icount_state_needed,\n',
         '    .needed = icount_state_needed,\n    .post_load = husk_icount_post_load,\n'),
        ('    .name = "timer",\n    .version_id = 2,\n    .minimum_version_id = 1,\n',
         '    .name = "timer",\n    .version_id = 2,\n    .minimum_version_id = 1,\n'
         '    .pre_load = husk_timer_pre_load,\n    .post_load = husk_timer_post_load,\n'),
    ]
    for old, new in changes:
        if source.count(old) != 1:
            raise SystemExit('Pinned QEMU timer migration shape changed')
        source = source.replace(old, new, 1)
    file.write_text(source)
# Fixed icount normally adds PMU event INST_RETIRED. The shipped snapshot
# advertises PMCEID0=0x20001, so retain that CPU capability set instead of
# weakening the CPU migration checks (0x20101 would fail their raw readback).
helper = file.parent.parent / 'target/arm/helper.c'
old = '''static bool instructions_supported(CPUARMState *env)
{
    /* Precise instruction counting */
    return icount_enabled() == ICOUNT_PRECISE;
}'''
new = '''static bool instructions_supported(CPUARMState *env)
{
#if defined(HUSK_NO_JIT) && defined(CONFIG_TCG_INTERPRETER)
    /* HUSK_NOJIT_SNAPSHOT_PMU: retain the native snapshot's PMU events. */
    return false;
#else
    /* Precise instruction counting */
    return icount_enabled() == ICOUNT_PRECISE;
#endif
}'''
source = helper.read_text()
if new not in source:
    if source.count(old) != 1:
        raise SystemExit('Pinned QEMU PMU feature shape changed')
    helper.write_text(source.replace(old, new, 1))
# A 1 ns instruction clock must not run millions of instructions before
# checking host input. Bound each scheduling budget, without advancing time
# or skipping any guest instruction; divide that budget across the vCPUs.
ops = file.parent.parent / 'accel/tcg/tcg-accel-ops-icount.c'
old = '        return icount_round(deadline);'
new = '''#if defined(HUSK_NO_JIT) && defined(CONFIG_TCG_INTERPRETER)
        /* HUSK_NOJIT_ICOUNT_SLICE: keep host I/O responsive under TCI. */
        if (icount_enabled() == ICOUNT_PRECISE) {
            return MIN(icount_round(deadline), 50000);
        }
#endif
        return icount_round(deadline);'''
source = ops.read_text()
if new not in source:
    if source.count(old) != 1:
        raise SystemExit('Pinned QEMU icount scheduling shape changed')
    ops.write_text(source.replace(old, new, 1))
print('[NoJIT] Experimental snapshot instruction-clock alignment applied')
