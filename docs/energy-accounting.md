# Energy Accounting Protocol

## What is and is not measured

The host experiment reports CPU-cycle accounting. It must not be described as
measured energy or energy efficiency.

For hardware validation record separately:

1. CPU active cycles and wall time
2. CPU current/voltage and integrated joules
3. sleep current/voltage and sleep duration
4. sensing/ADC current and active duration
5. NPU/accelerator current and active duration
6. radio TX/RX current and active duration
7. memory/storage activity if externally measurable
8. scheduler/controller cycles and joules
9. total board input energy

## Calibration experiment

For each target board, sweep CPU frequency and workload classes, then regress
cycle count against directly measured CPU energy. Repeat for memory-heavy,
accelerator-heavy, sensing-heavy and radio-heavy workloads. Do not use one
cycle-to-joule coefficient across all operating modes unless residual error is
shown to be acceptable.

The hardware result must report measurement instrument, shunt value, sampling
rate, voltage rail, firmware commit, compiler, clock configuration and board
revision.
