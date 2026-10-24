# Spec

Status: completed

Findings: 0.

Independent code-review Spec axis, applying codebase-design to the public current-message Interface. Reviewed only the four frozen scope paths against `PET_SOUL_BAG_INTEGRATION.md` and the direct `PET_SOUL_BAG_TIPS_SOURCE_RESEARCH.md` supplement. Non-Git fixed-manifest adaptation; no commits or tracker invented. Diff SHA256: `43f8f3ea5c4c647e8f1f58c3a283d1cb211e5582a58960613a33490c2e36e519`.

The producer satisfies the declared same-role/current-lease/read-only contract: it reads current Inventory, explicit cash and every carried original orb source in the caller transaction, refuses unknown or mismatched sources, emits the unchanged48-byte scalar Item layout, and addresses separate16-byte SItemTips after the Bag. Known orb nonbinding flags are combined with actual binding and packed as uint32, preserving161 and the high bit. Other item records use the existing public encoder unchanged. No source initialization, repair, commit or send is introduced.

The source correction is reflected accurately:107fe20 consumes TradeItem rather than ordinary Item; four-field orb data belongs in SItemTips, not at ordinary Item+0x10. The original Bag decoder, copy/location fragment, complete two-level lookup and parser reproduction supports exact container/key addressing and verifies that wrong container/key does not create or overwrite an orb object. The code does not certify unknown Item scalars as historical zeros or infer asset permissions from flags.

No missing requirement, incorrect in-scope behavior or scope creep found. Current-source setup, prior asset/root-source settlement, precommit encoding and connection-owned ordered delivery remain caller Interface conditions. Paid actions, full historical Item scalar provenance, all-consumer switching, NPC/other columns, shared activation, encrypted delivery, deployment, GUI, pet battle formulas and capacity remain explicitly unverified.

## Independent verification

Working directory: fixed `current/revival`; interpreter: `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`, `PYTHONUTF8=1`.

All independently returned exit0:

- `verify_pet_soul_bag.py` — original48-byte flags161/high-bit, nonempty Bag decode, separate current tips, unchanged generic record, SQL-readonly repeat, unknown orb refusal.
- `verify_pet_soul_item_data.py` — original inner/full parent codecs and16 parser/converter fixtures.
- Both Python blocks extracted from the source supplement — exact/wrong-container/wrong-key lookup and parser results; Item48 with nonzero unnamed scalar fixtures; TradeItem35/GivenItem RTTI and nonempty codec distinction.

`verify_snapshot.py` passed before and after: all1386 fixed dependency hashes and diff unchanged. No Standards report was read. Only this report was written; fixed input/production, real databases, servers and clients were untouched.

Spec summary: 0 findings; no worst issue within this axis. Full restoration remains incomplete.
