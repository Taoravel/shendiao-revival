# Spec

Status: completed

Independent Spec axis using the code-review and codebase-design Skills already read in full. Fixed diff `06e4e08c6dc71e0479fde3a839a6d2021b0e9bc39012f1250b97ff5d3756bdb9`, 1373 frozen dependencies; non-Git fixed-manifest adaptation with no invented commits/tracker. Only the new resource-source verification and its specification are in scope. No production changes are claimed. Standards report is not consulted.

Findings: 0.

Reviewed the two added paths against `evidence/PET_SOUL_RESOURCE_SOURCE_VERIFICATION.md`, the prior `PET_SOUL_SOURCE_FOUNDATION.md` / `ROLE_EQUIPMENT_GEMS_INTEGRATION.md` Interface conditions and the architecture's caller-owned same-role transaction requirement. No missing in-scope verification, incorrect asserted behavior or scope creep found.

The fixture creates actual temporary AccountStore/Inventory roles, pets and explicit known attribute/resource/equipment bases. It calls each real public ordinary-v2 and complete-gem source hook directly. The assertions independently require literal70HP/40MP,100/100 caps, unchanged resource numerical version and final attributes, with the committed root source revision matching the actual soul CAS inventory revision.

A real root receipt INSERT trigger fails after the soul CAS and source transition have begun; reopening via current public Interfaces verifies the complete soul, inventory and resource profile rolled back. A pending source is rejected by each paid branch; after fresh settlement, SQL write denial proves the paid path only reads the current state. The test exercises source synchronization, not a manufactured paid gameplay controller. No second resource writer, shared activation or missing-production red is claimed.

## Independent verification

Fixed working directory: `current/revival`. `PYTHONUTF8=1`; interpreter `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

- `verify_pet_soul_resource_sources.py`: exit0; both actual root hooks, root receipt rollback, resource preservation and paid SQL-readonly checks passed.
- `verify_snapshot.py`: passed before and after; all1373 dependency hashes and the fixed diff remained unchanged.

No source/fixed inputs were modified, no Standards report was read, and no service/client or real role database was opened. Unverified: soul item metadata/flags, paid equip/remove/fusion admission/materials/receipts, final pet attributes, actual shared integration, encrypted delivery, deployment, GUI, battle effects and capacity.

Spec summary: 0 findings; no worst issue within this axis.
