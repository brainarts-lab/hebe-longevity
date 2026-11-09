# Attribution and provenance

Built on PLSI by Insilico Medicine (MIT). Not affiliated with or endorsed by Insilico Medicine or xAI.

PLSI v0.2.1, commit `17c433c4a9ecb54279ab02ba1d7d63ee8e8a2e81`, https://github.com/Insilico-org/plsi.

`hebe/plsi_kernel.py` preserves the original `PHENOAGE_WEIGHTS`, `chronological_age` and `phenoage` definitions byte-for-byte as source segments from `src/plsi/map/derive.py`. Only a provenance header and their standard-library imports surround those definitions. Source and generated-file hashes are recorded in `vendor/provenance.json`. The upstream source's own copyright wording is retained in `vendor/LICENSE`: Copyright (c) 2026 PLSI contributors.

`hebe/plsi_units.py` is PLSI's `src/plsi/map/units.py` unchanged except for removing one import used only in type annotations. The two sourced unit conversions are copied from `maps/blood_phenoage.yaml`. Hashes are in `vendor/provenance.json`.

`vendor/plsi` bundles a byte-identical subset of PLSI at the same commit (toolbelt source, maps, contracts, references, the Nostradamus and Challenger skills, persona, license and disclaimer). `vendor/plsi.manifest.json` lists every file with its hash and the one file left out (`src/plsi/mh_caution.py`, imported by no PLSI module). Hebe runs this toolbelt for state, calculators, evidence, screening and plan gates; it adds its own import, approval and storage contract in front. No claim is made to fix PLSI's FHIR importer. The full upstream disclaimer is retained in `vendor/DISCLAIMER.md`. No UN life tables, LOINC datasets or methylation clocks are redistributed in this milestone.

Hebe original code: Copyright (c) 2026 BrainArts, MIT.
