#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "kernel/threads/tiku_thread.h"
#include "kernel/utility/tiku_utility.h"
extern uint32_t *tiku_thread_switch(uint32_t *old_sp);

static uint32_t cycles;
void tiku_atomic_enter(void) {}
void tiku_atomic_exit(void) {}
void tiku_thread_arch_boot(void) {}
void tiku_thread_arch_pend(void) {}
uint32_t tiku_thread_arch_cycles(void) { return cycles += 100u; }
uint32_t *tiku_thread_arch_frame_init(uint32_t *top, void (*entry)(void *),
                                       void *arg, void (*exit_fn)(void))
{ (void)entry; (void)arg; (void)exit_fn; return top - 8; }

static void worker(void *arg) { (void)arg; }

int main(void)
{
    TIKU_THREAD(a, 512);
    TIKU_THREAD(b, 512);
    TIKU_THREAD(c, 512);

    assert(tiku_thread_start(&a, worker, 0) == 0);
    assert(tiku_thread_start(&b, worker, 0) == 0);
    assert(tiku_thread_start(&c, worker, 0) == 0);

    assert(tiku_utility_hint_set(&a, 100, 0, 100, 0) == 0);
    assert(tiku_utility_hint_set(&b, 5000, 0, 1000, 0) == 0); /* density wins */
    assert(tiku_utility_hint_set(&c, 90, 0, 100, 0) == 0);

    /* Force the kernel to yield to workers. */
    tiku_thread_kernel_block();
    (void)tiku_thread_switch((uint32_t *)0);

    assert(tiku_thread_state(&b) == TIKU_THREAD_RUNNING);
    assert(tiku_thread_state(&a) == TIKU_THREAD_READY);
    assert(tiku_thread_state(&c) == TIKU_THREAD_READY);

    /* Non-runnable highest-value worker must be filtered before ranking. */
    a.state = TIKU_THREAD_DONE;
    (void)tiku_thread_switch((uint32_t *)0);
    assert(tiku_thread_state(&b) == TIKU_THREAD_RUNNING ||
           tiku_thread_state(&c) == TIKU_THREAD_RUNNING);

    /* Restart must clear the old hint before the new workload is admitted. */
    a.state = TIKU_THREAD_DONE;
    assert(tiku_thread_start(&a, worker, 0) == 0);
    tiku_utility_hint_t fresh;
    assert(tiku_utility_hint_get(&a, &fresh) != 0);

    /* Dynamic contract: update a's hint; next switch must change winner. */
    assert(tiku_utility_hint_set(&a, 65535, 0, 10, 0) == 0);
    (void)tiku_thread_switch((uint32_t *)0);
    assert(tiku_thread_state(&a) == TIKU_THREAD_RUNNING);

    puts("TikuOS patched scheduler host execution: PASS");
    return 0;
}
