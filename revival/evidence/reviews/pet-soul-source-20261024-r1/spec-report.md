# Spec

Status: completed

Independent Spec review of fixed diff `7f8793730d734a05ce0c3b32ae5327b475ff8eb5cb799ca364c200fca479148c` and 1371 frozen dependencies. Non-Git fixed-manifest adaptation; no commits or issue tracker invented. Applying code-review and codebase-design to explicit source, pure calculation, caller-transaction CAS and original native codec Interfaces. Standards report is not consulted.

Findings: 0.

Reviewed all eight added paths against `design/pet-souls-source-v1.json`, `evidence/PET_SOUL_SOURCE_FOUNDATION.md` and `evidence/PET_EQUIPMENT_SOURCE_RESEARCH.md`, with `ARCHITECTURE.md` and `DESIGN_AUTHORITY.md` as constraints. No missing in-scope requirement, incorrect behavior or scope creep found.

The pure Module loads all 28 original soul identities and 420 exact signed scalar/ratio values; grade comparison starts at row2 without consuming cumulative XP. Effective caps use known template kind/uselevel, explicit privilege22 and boolean presence of the two original soul skills. Actual and effective grades remain separate. Exact-item duplicate lookup does not impose unproven ordinary/advanced family exclusivity. Removal38045 remains a quote, not an asset action.

The complete six-field bean and sorted full-map profile require explicit data and preserve trailing signed raw fields. Storage reads distinguish unknown from explicitly empty. Initialization repeats read current state rather than resetting later slots; fresh CAS checks the complete current pet/source and inventory version under the current role lease, and the caller retains transaction ownership. Real SQL fault and post-encoding exception checks independently confirmed rollback. Original codec tests independently confirmed empty, two-slot and five-slot map bytes and fresh decoded contents, plus the c0805 layout.

Asset exchange, flags/admission, paid equip/remove/fusion receipts, battle formulas, final pet attribute/resource integration, shared routing, deployment and GUI are explicitly outside this source-foundation scope. They remain unfinished full-restoration work; this review does not certify them.

## Independent verification

Working directory: fixed `current/revival`. Interpreter: `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`; `PYTHONUTF8=1`.

All three independently executed commands returned exit0:

- `verify_pet_souls.py` — 28 XP boundary checks, 24 template/skill/privilege cases, exact-ID checks, rational/negative scalars, raw fields and unknown-source refusals passed.
- `verify_pet_soul_protocol.py` — original bean and empty/two/five-slot map marshal/fresh-decoder contents, c0805 and truncation checks passed.
- `verify_pet_soul_storage.py` — complete current persistence/CAS, missing versus empty, SQL-readonly initialization retry, two SQL faults and encoded caller rollback, stale before/lease checks passed.

`verify_snapshot.py` passed before and after verification: all1371 dependency hashes and fixed diff unchanged. No Standards report was read, no source/fixed input was changed, and no service/client or real role database was opened.

Spec summary: 0 findings; no worst issue within this axis.
