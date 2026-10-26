# Crystallographic Orthogonal Indexer

Read README.md and docs/PROJECT_STATE.json before making changes. The current
application is version 1.0. Its launcher and scientific module are at this root.

Keep every scientific convention, unit, signed normal, frame distinction,
stability guard and accepted reference documented in the project state. Do not
invent the missing experimental Top hkl or introduce a direct-[uvw] mode.

Run tests in the background with `python -B tools/run_source_validation.py
--mode all --name UNIQUE_RECEIPT_NAME`. The runner hides Tk windows and keeps
temporary files under validation/temporary/. Do not control the user's desktop.

Windows compilation, dependency/tool installation and installation QA remain
deferred until the user explicitly requests them. The build script is not a
source-test entry point. The user manages Git commits and pushes manually.

Keep archive/ byte-preserved. Historical scripts/receipts describe their original
locations and are not current entry points; archive/organization-2026-10-26/
path-map.json records relocations. Current state is docs/PROJECT_STATE.json,
decisions are docs/DECISIONS.jsonl, and current test evidence is in validation/.
