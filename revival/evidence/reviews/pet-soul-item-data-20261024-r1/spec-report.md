# Spec

Status: completed

Independent Spec review using code-review and codebase-design already read in full. Fixed diff `ed037e464dc63db197b44fc8721ab26edf509d8187f0ba22a6c6964dd6cd1c3b`,1378 dependencies; five additions, no existing production changes, non-Git fixed-manifest adaptation without invented commits/tracker. Reviewed only manifest scope against `PET_SOUL_ITEM_DATA_INTEGRATION.md`, completed primary `PET_SOUL_ITEM_SOURCE_RESEARCH.md` and the architecture/design constraints. No Standards report consulted.

Findings: 0. No missing in-scope requirement, incorrect behavior or scope creep found.

The specified “仅16字节…累计经验、魂技ID、穿戴bean的raw5、穿戴bean的raw4” is implemented as four explicit integer fields with exact-length decoding and preserved signed trailing values. The distinct four-field Module avoids conflating carried item tips with six-field worn PetSoul data. The required “raw6!=0…显示标志” projection preserves the immutable original bean, exposes no inverse factory, and remains separate from the bag's unsigned flags bit0. None of these display values is treated as asset authority.

The “原column1的0xc03fe SItemTips” wrapper uses exactly column/key plus the sixteen-byte inner Octets; no template/raw6 or ordinary-equipment detail is inserted. Ownership, current container/source, transaction and delivery remain explicit caller requirements.

The native fixture driver compares original four-field codec and complete parent bytes, executes sixteen parser/converter cases including negative raw values, checks field placement and natural returns, and rejects six-field misuse, wrong lengths, boolean primitives, illegal keys and original-decoder truncation. Its fixed grade2 and31277/type2 host adapters are disclosed and do not certify XP calculation, complete item factory, gameplay admission or GUI.

## Independent verification

Fixed working directory: `current/revival`; `PYTHONUTF8=1`; interpreter `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

- `verify_pet_soul_item_data.py`: exit0; original16-byte/full SItemTips, sixteen original parser/converter fixtures, signed fields/cross-order mapping, marker distinction and invalid/truncated refusal passed.
- `verify_snapshot.py`: passed before and after; all1378 frozen dependency hashes and diff unchanged.

No source/fixed input changed; no service/client or real role database opened. Unverified: item persistence/full flags provenance, lossless historical asset round trip, equip/remove/fusion permissions/materials/receipts, final pet battle effects, shared routing, encrypted delivery, deployment, GUI and capacity.

Spec summary: 0 findings; no worst issue within this axis.
