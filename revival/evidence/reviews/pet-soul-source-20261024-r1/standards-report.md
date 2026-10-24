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
