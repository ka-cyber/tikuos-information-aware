# TikuOS Source Audit

The supplied tree was inspected at source level. The relevant Stage-1 extension
points are concrete rather than inferred:

| Mechanism | Supplied implementation | Role in experiment |
|---|---|---|
| Scheduler | `kernel/scheduler/tiku_sched.c` | drains events and hands CPU to workers when idle |
| Worker model | `kernel/threads/tiku_thread.c/.h` | preemptive Cortex-M worker selection |
| CPU accounting | worker `cycles` / architecture cycle source | resource measurement/proxy |
| Cycle budgets | `tiku_thread_budget_*` | enforceable CPU quota |
| Worker introspection | `tiku_thread_get`, state/cycles/switches | experiment instrumentation |
| Timers | `kernel/timers/` | temporal scheduling substrate |
| VFS | `kernel/vfs/` | persistent/device abstraction |
| NPU | `kernel/vfs/tree/tiku_vfs_tree_npu.*` + platform drivers | future resource domain, not changed in Stage 1 |
| Link/radio | `kernel/link/` | future resource domain, not changed in Stage 1 |
| ADC/sensing | platform HAL/driver tree | future workload source |
| Power | CPU idle + power VFS/board paths | future measured energy campaign |
| Memory tiers | `kernel/memory/` | future resource domain |

The existing worker selector is in `tiku_thread_switch()`, not in the event
scheduler. The patch therefore changes the worker policy at the actual decision
point rather than adding a parallel fake scheduler.

The legacy path remains intact as fallback.
