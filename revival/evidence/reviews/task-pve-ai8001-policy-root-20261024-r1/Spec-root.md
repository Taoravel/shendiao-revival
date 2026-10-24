# Spec 独立静态审查

Missing/partial：0；Extra：0；Wrong：0。仅评价两份新增政策，不代表正式 engine、共享接线或成长全链已实现。

- 来源/范围：DESIGN_AUTHORITY:9–14 要求客户端→攻略→明确设计。policy:7–16、28–54 与 decision:9–13 区分原十条任务/AI/奖励/后继和设计敌阵、公式；冻结原表十行均为120XP、SMoney400、动画10019，分别接首技能十节点，未误开放101003。政策 :4、65 和 decision:29 保留完整成长目标及发布门槛。
- 准入/结果：TASK_BATTLE_INTEGRATION:24–40 要求真实快照、持久 admission、正式 producer、失败不奖及 receipt-only 恢复。policy:20–27、57、61–64 对应当前完整私有地址/NPC/租约/来源、真实回合终态、单次任务奖励和10019连续性；不把训练/暗雷结果改标签。只读实际 BASE023920/task_battle.py:227–229 确认原准入 HP>0，未把存量死亡角色当梦境复活资格。
- 资源：role-resources-v1:16、20、23 禁既有原因复活及重放治疗。policy:58–64、decision:19–21 另行明示专用 task_dream_revive，需已准入可信 raw HP0 终态、专用 planner/storage 校验与唯一凭据；同事务 CAS/扣损/宠物/outbox/任务奖励，宠物0保持0，重复不再治疗；不隐式迁移或放宽 medicine/growth。

方法：重读 code-review/codebase-design/tdd，按需求逐条追踪；检查所有权、事务 Interface、可判定失败前提和公开自然入口验收要求。无 Git，采用冻结字节/SHA；未读 Standards 报告。

9项登记输入及diff审前后匹配。scope SHA256：466c3f2a9b015f8988078845e8899fe299c0779321b0eca72be2238e725a9621；diff：d82aaaa93f6de712df85c4b780e25d96038860c5709e3f66e889bdea60da80d1。政策/决定 SHA256 分别为2cbbe2cafe3151e49f21a4ec35dab0dd9d4aa9dca82b4b28016dfcb3c13a3c56、8f4179b7a3abff5ac47bbcc1c0d6b2da51e323f6a67ff039bc64ed7b9f04e73c。

未验：未运行测试、DB、socket、服务、GUI或实际战斗；原包CRC为读取冻结研究记录，非本轴重新提取。未批准runtime/deploy，未恢复暂停的Battle goal。
