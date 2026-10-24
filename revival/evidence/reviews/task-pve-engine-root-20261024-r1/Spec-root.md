# Spec 独立静态审查

Missing/partial：0；Extra：0；Wrong：0。结论仅覆盖纯 engine/factory slice。

- SPEC:3 要求“不实例化 Training/Wild 或改其结果标签”。candidate/battle_owner.py:108–115 将默认 Training 与 supplied factory 分支互斥；task_pve.py:107–125 自建纯 Battle，:175–180 从本场实际状态产生正式结果。导入共享 BattleFinished 数据类型不等于运行训练引擎。默认分支保持原参数/调用，未扩大默认玩法。
- accepted policy:16、24–27 要求精确十任务、真实版本化人物及实际存活 OwnedPet。task_pve.py:49–65 固定已审政策字节；:88–123 核对启用任务/AI/NPC/map、明确HP/MP/属性/版本、宠物所属/选择/原catalog资格，拒绝训练宠物和缺省stats。来源真实性仍是调用方 Interface 前提，不把内部DTO当客户端授权。
- policy:48–57 的30秒/200回合、攻击/防御/逃跑由 :124–126、182–253 和固定reference/battle.py:150–211落实。:197–200 将真实 impacts 写入原HP消费map；:228–238 先解析并确认 playback 再产生胜/负/平/逃终态。:162–180保留raw人物/宠物资源及来源版本；:258–271真实关闭后仅产draw，不能制造胜利或治疗。:105–107、148–160 不发送技能表，未清已学账本。

方法：沿用 code-review需求追踪、codebase-design所有权/Interface副作用检查、tdd公开BattleOwner及原生独立期望审阅。读取根方九组结果，未自行执行。无Git，以冻结字节/SHA固定范围；未读Standards。

18登记输入及SPEC/diff审前后全匹配。scope SHA256=e96bf79cc5e4538ae209c28d7199c0df40c7a25465b5c1e766abfa135383725e；SPEC=27c5e63a829988f668cefd1fb45b70b594cf03f2e8902137e75c3bb17367b96a；diff=a8b0c740dc7c154ea5a7cafd9a12a3d39d49fbf94d4c4d60dfd21e0e0ed32ade。

未验：Task准入、持久资源/revive/outbox、任务奖励/10019、shared、发布及GUI均按SPEC:2留待后续；未运行测试、DB、socket、服务或真实战斗，未宣称完整成长可玩。
