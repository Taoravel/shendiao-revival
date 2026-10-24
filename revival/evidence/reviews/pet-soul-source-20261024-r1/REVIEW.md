## Standards

# Standards

status: completed

固定对象：`changes.diff` SHA256 `7f8793730d734a05ce0c3b32ae5327b475ff8eb5cb799ca364c200fca479148c`；1371项依赖。8个hunk均为新增，与清单scope一致。无Git/tracker，沿用获准固定清单适配，没有制造提交或issue。独立审查，未读取Spec报告。

## 发现

硬性违反：0。判断性气味：0。本轴无最高严重项。

已读取并实际采用code-review与codebase-design：

- `current/AGENTS.md`共享入口分工及`ARCHITECTURE.md`“状态所有权”“交易、奖励与跨区”：新增存档Module经公开Inventory当前租约快照验证角色/宠物，完整before与库存版本共同CAS；所有变更留在调用方事务，没有连接、提交、发送、全局锁或独立资源写入者。只新增元魂来源表，未把纯来源CAS包装成付费动作。
- `ARCHITECTURE.md`“连接、执行与背压”：DDL与配置加载明确限制为启动；规则加载生成只读映射和精确有理数。纯协议仅返回不可变逻辑字节，文档明确编码先于提交、投递归连接所有者。
- `DESIGN_AUTHORITY.md`“每个缺口的处理顺序”：原表、原码研究与服务端未实现项分开；保留累计XP、符号、比例和未知raw字段；缺档返回None，未知模板/特权拒绝，明确空档须显式提供。历史原码研究没有冒充本批服务端准入或GUI验收。
- codebase-design：来源计算、存档Adapter与协议各隐藏相应复杂度；冻结SoulBean/Profile/Basis表达领域含义，测试通过公开Interface观察行为。逐项判断Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Bequest，未见值得提出的气味。

标准来源还包括`current/GLOSSARY.md`；固定树中未发现CODING_STANDARDS.md或CONTRIBUTING.md。

## 实际验证

固定`current/revival`，指定Python与PYTHONUTF8=1，独立运行全部exit0：

- `verify_pet_souls.py`：28个XP边界、24个上限组合、3个精确ID检查、原420有理数/负比例/raw保留和未知拒绝。
- `verify_pet_soul_protocol.py`：原六字段bean及空/2槽/5槽完整map序列化、新对象解码字段，摘除意图与截断拒绝。
- `verify_pet_soul_storage.py`：显式完整档案、未知与空区别、只读导入重试、不重置、2处真实SQL故障与编码后异常全回滚、过期before/租约拒绝。

`verify_snapshot.py`在上述验证前后均通过：1371个固定依赖及diff未改变；额外核对8个新增hunk与manifest一致。

未验证：背包元魂实例来源、付费穿戴/摘除/融合、技能/完整属性与根资源来源联动、共享接线、发布、加密投递、GUI、战斗与容量。审查没有启动服务或客户端、打开真实角色库或修改固定源码。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。


## Spec

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


Standards: 0 hard / 0 judgement findings; Spec: 0 findings. No worst issue in either axis. Full restoration remains active.
