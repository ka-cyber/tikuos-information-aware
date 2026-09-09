# Limitations and Failure Modes

- The host experiment is not an MCU energy measurement.
- The Stage-1 patch changes worker selection only; it is not yet a radio/NPU/
  sensing resource broker.
- The supplied CardioFusion and APC-RLNC code is used through adapters, not
  linked into the TikuOS kernel.
- Synthetic physiological traces are workload generators, not clinical
  validation.
- The expected-utility contract is only as good as the application's estimate.
  Adversarial and miscalibrated regimes are explicit failure tests.
- A positive simulator result does not establish superiority on hardware.
- The offline oracle is exact only for the documented quantized host model.
- The artifact does not claim PIR's current mathematical formulation is
  scientifically established.
