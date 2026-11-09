# Attribution and provenance

Built on PLSI by Insilico Medicine (MIT). Not affiliated with or endorsed by Insilico Medicine or xAI.

PLSI v0.2.1, commit `17c433c4a9ecb54279ab02ba1d7d63ee8e8a2e81`, https://github.com/Insilico-org/plsi.

`hebe/plsi_kernel.py` preserves the original `PHENOAGE_WEIGHTS`, `chronological_age` and `phenoage` definitions byte-for-byte as source segments from `src/plsi/map/derive.py`. Only a provenance header and their standard-library imports surround those definitions. Source and generated-file hashes are recorded in `vendor/provenance.json`. The upstream source's own copyright wording is retained in `vendor/LICENSE`: Copyright (c) 2026 PLSI contributors.

This is selective reuse of the numerical kernel, not the complete PLSI runtime. The first prototype uses its own import, approval and storage contract. No claim is made to support PLSI plan/scoring or to fix its FHIR importer. The full upstream disclaimer is retained in `vendor/DISCLAIMER.md`. No UN life tables, LOINC datasets or methylation clocks are redistributed in this milestone.

Hebe original code: Copyright (c) 2026 BrainArts, MIT.
