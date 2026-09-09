# Cross-Repository Intersection Map

| Concept | TikuOS | PIR | CardioFusion | APC-RLNC | Measurement |
|---|---|---|---|---|---|
| Expected information utility | worker selection contract **[NEW]** | PIV/utility hypothesis | SQI + event evidence | decoding/delivery evidence | delivered utility per total resource |
| Uncertainty | not kernel-visible | state uncertainty | SQI / modality degradation | erasure/channel uncertainty | hint error / calibration |
| Urgency | hard deadline contract | urgency state | event probability | delivery deadline | deadline success |
| Resource cost | worker cycles/budget **[EXPLICIT]** | resource constraints | inference/sensing cost | coding/transmission cost | cycles; future joules |
| Dynamic state | mutable hint **[NEW]** | state-space/controller | time-varying signal quality | time-varying wireless state | seeded trace |
| Communication reliability | link layer exists **[EXPLICIT]** | reliability objective | workload output | RLNC/PDR/decode **[EXPLICIT]** | delivered information |

The important boundary is that PIR supplies an application-level estimate;
TikuOS supplies a generic resource-control mechanism. CardioFusion and APC-RLNC
instantiate the workload without becoming kernel dependencies.
