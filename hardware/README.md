# Hardware Campaign

The supplied TikuOS tree supports multiple boards. The information-utility
patch is architecture-independent at the policy layer but requires the existing
Cortex-M worker-thread backend for Stage 1.

## Campaign stages

1. Build patched firmware with `TIKU_THREADS_ENABLE=1 TIKU_UTILITY_ENABLE=1`.
2. Run a synthetic worker workload with fixed CPU budgets.
3. Record cycle counts, worker switches, deadline misses and broker updates.
4. Repeat with information-aware and legacy policies on the same firmware.
5. Measure board input current/voltage with a calibrated power monitor.
6. Run the CardioFusion-derived workload.
7. Run the APC-RLNC-derived communication workload where the board/radio
   supports it.
8. Repeat across clock frequencies and relevant sleep modes.

## Required campaign manifest

Record board, MCU, board revision, firmware commit, upstream TikuOS revision,
patch hash, compiler/toolchain version, optimization flags, clock tree,
measurement instrument, shunt, sample rate, supply voltage, workload seed,
configuration hash and raw measurement file hash.

## Toolchain

The repository cannot honestly claim a successful cross-compiled firmware image
without the corresponding vendor toolchain. CI should install the board-specific
compiler and run `make MCU=... TIKU_THREADS_ENABLE=1 TIKU_UTILITY_ENABLE=1` on
real toolchain runners.
