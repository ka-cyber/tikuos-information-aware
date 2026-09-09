/*
 * TikuOS information-utility contract implementation.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include "tiku_utility.h"
#include "../threads/tiku_thread.h"
#include <hal/tiku_cpu.h>

#ifndef TIKU_UTILITY_MAX_THREADS
#define TIKU_UTILITY_MAX_THREADS TIKU_THREADS_MAX
#endif

#if TIKU_UTILITY_MAX_THREADS != TIKU_THREADS_MAX
#error "TIKU_UTILITY_MAX_THREADS must match TIKU_THREADS_MAX"
#endif

static tiku_utility_hint_t s_hints[TIKU_UTILITY_MAX_THREADS];
static struct tiku_thread *s_owner[TIKU_UTILITY_MAX_THREADS];

static int find_slot(const struct tiku_thread *thread)
{
    uint8_t i;
    if (thread == (const struct tiku_thread *)0) return -1;
    for (i = 0; i < TIKU_UTILITY_MAX_THREADS; ++i) {
        if (s_owner[i] == thread) return (int)i;
    }
    return -1;
}

static int alloc_slot(struct tiku_thread *thread)
{
    int free_slot = -1;
    uint8_t i;
    if (thread == (struct tiku_thread *)0) return -1;
    for (i = 0; i < TIKU_UTILITY_MAX_THREADS; ++i) {
        if (s_owner[i] == thread) return (int)i;
        if (free_slot < 0 && s_owner[i] == (struct tiku_thread *)0)
            free_slot = (int)i;
    }
    if (free_slot >= 0) s_owner[free_slot] = thread;
    return free_slot;
}

int tiku_utility_hint_set(struct tiku_thread *thread,
                          uint16_t utility_q16,
                          uint32_t deadline_tick,
                          uint32_t cost_cycles,
                          uint8_t flags)
{
    int slot;
    if (thread == (struct tiku_thread *)0 || cost_cycles == 0u)
        return -1;
    tiku_atomic_enter();
    slot = alloc_slot(thread);
    if (slot < 0) {
        tiku_atomic_exit();
        return -1;
    }
    s_hints[slot].utility_q16 = utility_q16;
    s_hints[slot].deadline_tick = deadline_tick;
    s_hints[slot].cost_cycles = cost_cycles;
    s_hints[slot].flags = flags;
    s_hints[slot].valid = 1u;
    tiku_atomic_exit();
    return 0;
}

void tiku_utility_hint_clear(struct tiku_thread *thread)
{
    int slot;
    tiku_atomic_enter();
    slot = find_slot(thread);
    if (slot >= 0) {
        s_hints[slot].valid = 0u;
        s_owner[slot] = (struct tiku_thread *)0;
    }
    tiku_atomic_exit();
}

int tiku_utility_hint_get(const struct tiku_thread *thread,
                          tiku_utility_hint_t *out)
{
    int slot;
    if (out == (tiku_utility_hint_t *)0) return -1;
    tiku_atomic_enter();
    slot = find_slot(thread);
    if (slot < 0 || !s_hints[slot].valid) {
        tiku_atomic_exit();
        return -1;
    }
    *out = s_hints[slot];
    tiku_atomic_exit();
    return 0;
}

uint32_t tiku_utility_score(const tiku_utility_hint_t *hint)
{
    uint64_t numerator;
    if (hint == (const tiku_utility_hint_t *)0 ||
        !hint->valid || hint->cost_cycles == 0u)
        return 0u;

    /*
     * Preserve ordering exactly without floating point:
     * floor(utility_q16 * 2^16 / cost_cycles).
     * Saturation is not needed for a uint32 result because utility<=65535.
     */
    numerator = ((uint64_t)hint->utility_q16 << 16);
    numerator /= (uint64_t)hint->cost_cycles;
    return (numerator > 0xffffffffULL) ? 0xffffffffu : (uint32_t)numerator;
}

int tiku_utility_deadline_eligible(const tiku_utility_hint_t *hint,
                                   uint32_t now)
{
    uint32_t delta;
    if (hint == (const tiku_utility_hint_t *)0 || !hint->valid)
        return 0;
    if ((hint->flags & TIKU_UTILITY_FLAG_DEADLINE) == 0u)
        return 1;
    delta = hint->deadline_tick - now;
    return ((int32_t)delta >= 0);
}

int tiku_utility_select(struct tiku_thread *const *threads,
                        uint8_t count,
                        uint8_t cursor,
                        uint32_t now)
{
    uint8_t offset;
    int best = -1;
    uint32_t best_score = 0u;

    if (threads == (struct tiku_thread *const *)0 || count == 0u)
        return -1;

    for (offset = 0; offset < count; ++offset) {
        uint8_t idx = (uint8_t)((cursor + offset) % count);
        tiku_utility_hint_t hint;
        uint32_t score;

        if (threads[idx] == (struct tiku_thread *)0) continue;
        if (tiku_utility_hint_get(threads[idx], &hint) != 0) continue;
        if (!tiku_utility_deadline_eligible(&hint, now)) continue;
        score = tiku_utility_score(&hint);
        if (best < 0 || score > best_score) {
            best = (int)idx;
            best_score = score;
        }
    }
    return best;
}
