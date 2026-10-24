# Standards

Reviewed only the fixed foundation diff `6204e48e00f7b1b528937abe8d651da1f7b6300dff5efa9e2d36d7cc2cde761a`, relative to composition R2. This repository has no Git fixed point or tracker; the explicit manifest adaptation is used without inventing either. No Spec report was read.

## Documented standards

No actionable documented-standard violation found.

`current/AGENTS.md` requires module ownership, architecture compliance, client-first evidence and applied skills. The three production additions leave the shared entry points and seven previously frozen production files unchanged. `ARCHITECTURE.md`, “状态所有权” and “交易、奖励与跨区”, require current-role ownership and caller-transaction mutation: `equipment_gem_storage.py`’s `_owned`, `read` and `replace_state` use the fenced Inventory snapshot, compare the complete current basis, and perform source/version CAS without opening a connection, committing or sending. Startup DDL remains in explicit `prepare`.

`DESIGN_AUTHORITY.md`, “每个缺口的处理顺序”, requires distinguishing verified values from designed rules. `design/equipment-gems-v1.json` separates these; replacement, binding, ordering and activation limits are explicit. The storage docstrings and foundation handoff state the remaining paid-action, score/color, role-resource and runtime closure. This is not represented as deployed gameplay.

## Fowler baseline — judgement calls

No actionable smell found after checking all twelve: Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man and Refused Bequest. `GemState`, `SocketRequest` and `EquipmentGemBasis` bundle the independently versioned concepts. `NativeGemEquipmentDetail` overrides the documented configuration-copy/destruction Adapter while executing the original parser; this does not constitute Refused Bequest. No heuristic was promoted to a hard rule.

## Validation and limits

- `verify_snapshot.py`: PASS all 1,320 frozen dependency hashes and diff SHA.
- Independently rehashed all 10 owned additions and confirmed their absence in composition R2; all seven previous production SHA remain identical.
- Ran from fixed `current/revival`, UTF-8 bundled Python: `verify_equipment_gems.py`, `verify_equipment_gem_detail.py`, `verify_equipment_gem_storage.py`, `verify_equipment_gem_requests.py`: all PASS.
- Validation covers 210 rows, pure plans, real native detail/codecs and transaction/CAS failure rollback. It does not establish paid socket actions, root resource integration, shared admission, deployment, GUI lifecycle or commercial concurrency. No source was edited.

Count: documented hard violations 0; heuristic smells 0. Standards only.
