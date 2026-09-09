/*
 * TikuOS information-utility contract.
 *
 * Stage-1 abstraction: application work supplies a bounded expected
 * marginal utility for a scheduling opportunity. The kernel uses that
 * contract only to order CPU workers; it does not interpret application
 * semantics (PIR, ECG, PPG, RLNC, etc.).
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#ifndef TIKU_UTILITY_H_
#define TIKU_UTILITY_H_

#include <stdint.h>

struct tiku_thread;

/*
 * Q0.16 utility.  0 means no expected decision-relevant benefit; 65535 is
 * the maximum representable utility for the caller's normalized objective.
 */
#define TIKU_UTILITY_Q16_MAX ((uint16_t)65535u)

#define TIKU_UTILITY_FLAG_DEADLINE ((uint8_t)0x01u)

typedef struct tiku_utility_hint {
    uint16_t utility_q16;
    uint32_t deadline_tick;
    uint32_t cost_cycles;
    uint8_t flags;
    uint8_t valid;
} tiku_utility_hint_t;

/*
 * Set/replace a dynamic scheduling hint.  This function is deliberately
 * O(TIKU_THREADS_MAX), bounded by the static worker capacity.
 */
int tiku_utility_hint_set(struct tiku_thread *thread,
                          uint16_t utility_q16,
                          uint32_t deadline_tick,
                          uint32_t cost_cycles,
                          uint8_t flags);

/* Remove the hint; the scheduler falls back to its legacy policy. */
void tiku_utility_hint_clear(struct tiku_thread *thread);

/* Read the currently registered hint, if any. */
int tiku_utility_hint_get(const struct tiku_thread *thread,
                          tiku_utility_hint_t *out);

/*
 * Returns a monotone integer score for comparing runnable work.  The score
 * is utility / estimated CPU cycles, represented without floating point.
 * Deadline eligibility is handled separately by tiku_utility_eligible().
 */
uint32_t tiku_utility_score(const tiku_utility_hint_t *hint);

/*
 * Wrap-safe deadline predicate.  Valid only for deadlines within 2^31 ticks
 * of now, matching the conventional unsigned modular-time assumption.
 */
int tiku_utility_deadline_eligible(const tiku_utility_hint_t *hint,
                                   uint32_t now);

/*
 * Choose among candidate workers.  Returns -1 when no utility-eligible
 * candidate exists.  Ties are resolved by round-robin order starting at
 * cursor.  Workers without a valid hint are ignored by this optional policy;
 * callers should fall back to the legacy scheduler when it returns -1.
 */
int tiku_utility_select(struct tiku_thread *const *threads,
                        uint8_t count,
                        uint8_t cursor,
                        uint32_t now);

#endif /* TIKU_UTILITY_H_ */
