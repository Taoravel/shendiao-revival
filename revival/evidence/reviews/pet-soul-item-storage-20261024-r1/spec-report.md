# Spec

Status: completed

Findings: 0.

Independent Spec review using code-review and codebase-design. Reviewed only the four added scope paths against `design/pet-soul-items-v1.json` and `evidence/PET_SOUL_ITEM_STORAGE_INTEGRATION.md`, with the original item-data research as source evidence and the project architecture/design constraints. Non-Git fixed-manifest adaptation; no commits or tracker invented. The fixed diff SHA256 is `dfc4f1b66713c13ddc98030655b9186740cf6f0c5bcf9c6c44d0f6453dcf09b6`.

The implementation meets the declared metadata-only scope: explicit four-field orb data, even uint32 nonbinding flags, independently retained signed raw6, and explicitly supplied None for absent worn history. Missing rows remain unknown and cannot produce tips. Current real Inventory/lease validation restricts sources to owned carried single original orbs with the stated known primitive fields. Initialization retries read current state without reset. Fresh changes require complete current basis equality, stable identity/provenance/flags/raw6, next source version, and the same caller transaction for metadata plus inventory revision. Generic physical mutations invalidate source records, including binding ABA.

The public Interfaces and actual temporary-database checks support the specified current tips, strict read-only initialization retry, two SQL failure rollbacks, post-encoding caller rollback, stale before/lease rejection and signed history preservation. The related native data driver independently verifies the original four-field/full SItemTips codecs and original parser/converter branches. No missing requirement, incorrect in-scope behavior or scope creep found.

Trusted import provenance and caller rollback/source synchronization remain explicit Interface conditions. This result does not certify equip/remove/fusion authorization, new raw6 construction, fees/materials/receipts, real metadata migration, final pet attributes, root resource hooks, shared activation, deployment, encrypted delivery, GUI or capacity.

## Independent verification

Working directory: the fixed `current/revival` directory. Interpreter: `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`, with `PYTHONUTF8=1`.

Both commands independently returned exit 0:

- `verify_pet_soul_item_storage.py` — real source CAS/tips, exact flags/negative history, no-reset SQL-readonly retry, two SQL faults, encoded caller rollback, binding ABA and stale lease.
- `verify_pet_soul_item_data.py` — original16-byte/full SItemTips codecs,16 original parser/converter fixtures and raw6 preservation.

`verify_snapshot.py` passed before and after execution: all1382 fixed dependency hashes and the diff unchanged. No Standards report was read; no fixed input, production file, real database, server or client was modified or opened.

Spec summary: 0 findings; no worst issue within this axis. Full restoration remains incomplete.
