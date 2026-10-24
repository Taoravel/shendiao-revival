# 原其他技能完整快照：可复用离线decoder与consumer

2026-10-24。按research Skill后台委派，重新读取research、codebase-design、ARCHITECTURE及DESIGN_AUTHORITY，复用既有PROLOGUE_FIRST_SKILL_RESEARCH定位。本批只新增独立研究脚本与本文；不改角色技能、任务、训练codec或正式技能公式，不操作GUI、网络、在线DB或战斗。

## 可直接复用的Interface

`revival/research_other_skill_snapshot.py`：

```python
native_other_skills(payload: bytes, existing: Mapping[int, int] | None = None) -> dict[int, int]
```

传入SSendOtherSkills的**body**，不是外层网络frame；existing是合成初始map，函数按值复制，不修改调用方mapping。返回原客户端技能manager执行后的完整map，来自实际native树节点，并经原值查询交叉核对；没有用Python计算覆盖/删除结果。

- flag1：本批支持新项、更新、完整保留及缺项删除；必须传完整当前快照。
- flag0：只覆盖已有key更新/删除。若payload含初始map没有的新key，明确抛NotImplementedError；该路径可能调快捷栏/呈现函数，本批不伪装其已验证。
- 研究预算为最多512项、body长度2..8192。初始key/value为signed i32。不是网络不可信包模糊测试器；畸形body可能由原decoder或harness拒绝。
- 返回值仅是隔离native状态，不是技能授予授权。flag的完整业务语义、原server快照范围仍按前报告保留未知。

调用方可把自己的完整角色账本编码结果直接交给此函数，与期望map比较；研究脚本不导入或调用待恢复的role_skills/task_first_skill实现。main只打印六例JSON，无自动写证据/数据库副作用。离线调用时以项目Python加`-B`避免生成pycache。

## 原始来源、地址与实际执行链

原映像`revival/evidence/native-image.bin`，50675712字节，BASE0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。公开函数每次核此SHA；不接受另一个构建冒充该证据。

| 原路径 | VA / 作用 |
|---|---|
| SSendOtherSkills ctor | f30da0；type0xc36c3、vtable22852e8，构造map哨兵 |
| 原decoder | f30e50；map helper77b200，尾byte写packet+14（f30ecf）；实际运行且断言消费完整body |
| 原Process | 12d6810；读取global29448a4，12d681c把flag是否等于1投影为bool，5f3eb0复制map，12d683c调用真实consumer |
| 原consumer | 12d60f0；manager+40保存other-map；12d61d9..12d6218删除传入集合中不存在的旧key；12d6285..12d6355插入/写入新值 |
| 原值查询 | 12d1d50；原map查找及value读取，缺项返回0；与实际树读值交叉核验 |

**最终脚本执行了decoder→Process→consumer整段，而不只是沿前批直接调用consumer。** 每例先通过原decoder/Process/consumer注入合成existing，再通过相同原链处理调用方payload；hook计数每例三入口各2次，未替换其分支。Process内部原map复制与消费者中的树查找、删除、插入、值写入均保留原指令。

复用`research_battle.NativeBattleDecoder`的映像映射、分配器/CRT/STL字符串等已有系统Adapter；没有调用其main。manager+40的初始空哨兵来自原ctor，packet随后重新构造，避免与manager共用正在处理的map。UI singleton2945610和scene2944564设空；flag1原分支跳过新增项快捷栏处理。没有hook技能decoder/Process/consumer或以Python授予/删除技能。flag0仅选择无需新项呈现的例子，不执行完整GUI。

## 最终脚本实际运行结果

下表旧key均为人工fixture，不宣称其人物合法技能基线。**2147483647只用于证明i32 value没有被截成byte或固定1，不是批准的技能等级。**

| 原始existing | 输入快照 / flag | 实际native结果 |
|---|---|---|
| {100001:2,100002:9} | {100001:2,100002:9,100008:2147483647} / 1 | 三项全保留，新增100008高值正确 |
| 上述两旧项+100008:7 | 完整三项，高值 / 1 | 两旧值不变，100008更新至2147483647 |
| 两旧项+100008:7 | 故意漏100002，保留100001与高值100008 / 1 | 100002确实删除，其他值正确 |
| 两旧项+100008:7 | 空map / 1 | 真正清空，map大小0 |
| 完整三项高值 | 原样完整map / 1 | 完全不变 |
| 两旧项+100008:7 | {100001:3,100008:11} / 0 | 更新两个已有项且删除100002 |

完整三项flag1原body：`03000186a100000002000186a200000009000186a87fffffff01`；漏项敏感性body：`02000186a100000002000186a87fffffff01`；空body：`0001`。每例返回值均与脚本独立期望断言一致。最终六例均已实际运行通过，另在落脚本前做过最短四次顺序反馈；没有扩大GUI/网络或战斗验证。

## 方法、决定与未验证范围

research将结论直接落到原映像入口与实际反馈，codebase-design将复用点收为一个小Interface，隐藏Unicorn、map哨兵及Process参数细节；现有harness作为系统Adapter复用，未另建测试框架。敏感性选择“漏一个旧key”，验证的是完整替换与不丢旧值，而非镜像生产编码器的自证。

本次不证明原100179必须授何技能、授几级、何时授、是否收费，也不恢复任何正式伤害/耗蓝公式。前批100008身份、SSendOtherSkills替换语义与未知grant规则保持。没有验证快捷栏图标、提示/气泡、flag0新项、恶意畸形全集、真实角色基线、真实客户端技能可用性、持久化账本、事务/重连/并发、实际发送或部署。角色账本包需由调用方另作核验，不能将这里的合成map称真实人物技能已落盘。

唯一新增产物：`revival/research_other_skill_snapshot.py`与本文；未编辑任何生产Module、共享入口、政策或训练codec。

脚本SHA256：`6687f49953f34f387fafdc26d4965aec8aa6511bd0f25b92c279d7dae1a3ff49`；复用harness SHA256：`4aa276ece9ea4a9f13d9c4f9a0de2900f97cf77ff3783aeecc92e7d5f3a47b45`。

### 调用方提供的两条实际候选body：追加最小反馈

脚本完成后，调用方提供现有battle_protocol.other_skills的两条body；本研究未修改或导入其编码器，直接把字节交给公开native_other_skills。实际原链均通过：

- `02000186a700000003000186a80000000101`，合成existing={100007:3}，原输出={100007:3,100008:1}；旧100007未丢失。
- `02000186a800000007000186a90000000401`，合成existing={100008:1,100009:4}，原输出={100008:7,100009:4}；高于1的value保留，同包另一项不变。

以上两例实际执行原decoder/Process/consumer，不证明候选任务事务、主线程SQL authorizer或真实技能授予已通过本研究验收；那些由调用方自己的验证报告举证。至此收敛，不扩大研究。
