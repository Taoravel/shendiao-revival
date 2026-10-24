## Standards

# Standards

status: completed

硬性违反：0。判断性气味：0。本轴无最高严重项。

独立采用 code-review 与 codebase-design，完整内容仍在本审查上下文中沿用；没有读取 Spec 报告或当前工作区另行开发的Action。仅审固定manifest的4个新增路径，非Git/tracker固定清单适配。diff SHA256 `43f8f3ea5c4c647e8f1f58c3a283d1cb211e5582a58960613a33490c2e36e519`；4路径在前批清单均缺席，全部1382个既有输入hash继承。

按冻结AGENTS、GLOSSARY、ARCHITECTURE及DESIGN_AUTHORITY核对：

- `pet_soul_bag.current_messages` 通过公开Inventory当前事务快照、钱包和orb来源Interface检查同一活动角色租约。快照版本/物品逐项一致，未知orb整体拒绝；只读，不修复来源、不配置/DDL/连接/提交/投递，符合连接所有者在提交后发送的约束。
- 它复用公开48字节item_record，其余类型保持原编码；仅按已知nonbinding_flags与实际binding合并，使用uint32保留全部bit pattern。先Bag建立当前key，再逐珠独立tips，不向scalar Item插Octets，不解释NPC/其他列。
- codebase-design的小Interface集中来源组合与顺序，没有新增状态写入者、资源副本或重复权限策略。逐项评估全部12项气味基线，无值得报告的判断性气味。
- 两份新文档将TradeItem/Item的原参数归类纠正、宿主Adapter及原消费者执行范围与服务器权限/GUI分开；明确全消费者切换与paid资产事务前置。旧封签源报告保留历史但更正指针清楚，未据源码可用声称shared或容量验收。

## 独立验证

固定 `current/revival`、`PYTHONUTF8=1`、指定Python，均exit0：

- `verify_pet_soul_bag.py`：实际钱包/库存/两orb，原Item flags161/0x80000000、原非空Bag解码、独立tips、普通物品字节保持、SQL禁止写入下重复读取、未知orb拒绝。
- `verify_pet_soul_item_data.py`：原四字段/full SItemTips、16个原parser/converter组合与raw6保留。
- 补证报告的两个Python代码块独立提取执行：原两层map查找与parser命中消费16字节，错容器/key不更新；原TradeItem35/GivenItem2i32与Item48的RTTI及非空编解码区别，全部PASS。
- `verify_snapshot.py` 前后通过1386依赖和diff；另核对前批清单的4路径缺席与1382个继承输入hash。

只写本报告，未修改固定输入、服务/客户端或真实角色数据库。未验完整历史Item scalar、paid穿戴/摘除/融合、全部shared消费者、加密投递/GUI/战斗/容量。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。


## Spec

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


Standards: 0 hard / 0 judgement findings; Spec: 0 findings. No worst issue in either axis. Full restoration remains active.
