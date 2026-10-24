# 宠物忠诚恢复费用：准确发布闭包

2026-10-24。依据 NPC_PET_LOYALTY_V2_DECISION.md 和原客户端报价研究，当前已知普通血脉每宠按 `(45 + 2 × power个位) × 缺失忠诚` 收费；原颜色只决定忠诚上限。原20级及以下免费、现金用途、恢复类型和NPC资格不变。合法care但确实缺失blood的旧实例沿用45单价并记录来源，不生成blood0。畸形的已知数据拒绝，不回退。

历史paid先查，保留npc.1和原指纹；不会补扣新旧价格差、重放旧忠诚或覆盖当前伤势。新请求才按当前受支持的血脉和角色状态报价。

## 方法、决定与实际反馈

沿用 diagnosing-bugs：先用固定当前服BASE重现真实入口，再修改一个接线点。领域中的正确金额不足以证明按钮可用。codebase-design 将计价留在既有NPC角色事务Module，跨入口复用共享结算Interface；TDD沿既有公开plan/settle、真实Owner/Peer和持久化事务Seam验证；code-review分开规范与规格两轴。

BASE：private-story-20261023T190051Z / PID14480。

两输入候选 npc-loyalty-20261023T193535Z 的领域6组/34坏配方通过，但实际Owner原c2333请求失败。BASE runtime_storage保留kind!=1时拒绝已知人物资源的临时门控，因此费用模块尚未被调用；根也独立复现同一失败。该候选不发布，历史失败和两源Spec缺失1保留。

三输入候选 npc-loyalty-20261023T193742Z 只追加从BASE删除宠物恢复门控2行；未删除修理门控、未复制工作区其它共享变化。原sameOwner检查转绿，根独立重放也转绿。NPC已更正‘仅两输入即可完整激活’交单口径：两输入是所属领域增量，已知profile实际激活还依赖这处共享接线。

准确生产SHA：

- npc_recovery.py：e9a450596b38c8434139deb186f27f32ac1eb6cb916248a13ef79a9a43c17bab
- runtime_storage.py：7d27f9c22b9eed3aa2eb7b67e63d51b208f61025f616ea411fb555bcb5b08df1
- design/npc-pet-loyalty-v2.json：09cc5d0572dc56b439b1ab16d132b70fb4e36390ca8642db5d67821d5af7ea29

1440生产输入全部冻结，原剧情、伤害、自动普攻及库存/组织等其它BASE保持。6项准确候选检查全部通过：费用领域6组/34坏配方、实际Owner6组、旧两个训练师kind4、旅店资源12项、自然入梦流程、原伤害消费者8例。包括power0/9/1139的900/1260/1260、多宠异色、免费门槛、未知旧档、旧模块真实先付900再改变血脉后新模块只读重放、晚期SQL与原生编码分配失败回滚、同失败ID一次成功、重登旧epoch拒绝。

验证旧模块仅为显式允许的已冻结测试fixture；当前被测npc_recovery等所有生产导入均来自准确candidate/source。验证脚本只重定向报告/哈希和旧fixture路径到绑定的OUT，未替换领域、dispatcher或自有编码器。生产、harness、实际OUT静态输入及原image前后均核SHA。

启动预演读取当前存档的一致备份，在可丢弃副本中运行：110张旧表所有行不变、无新增表、quick_check=ok。未改角色档案、未迁移资源来源、未还原旧库。此批不包含NPC鉴定、忠诚之外新价格、宠物进化、组织、梦醒或碰撞新片。

状态：2026-10-24 03:45:26（北京时间）三输入已发布，实际PID48572，唯一28993监听；固定副本为npc-loyalty-20261023T193742Z。1440输入与实际启动哈希匹配，601未认证握手/心跳通过，110张旧表所有行不变，无新增表，quick_check=ok。停止点一致备份保留在发布目录accounts-at-stop.sqlite3，未还原旧库、未改真人角色/任务。

根r2独立Standards硬违规0/heuristic0，Spec缺失/额外/错误均0；聚合与结构化acceptance-root.json位于reviews/npc-loyalty-release-20261024-r2。发布守卫核结构回执的release/BASE/PID、manifest/完整3输入、验收seal及三份报告SHA，不依赖同义零项文案。发布前最后空服快照为0，全部源/runner核验后才切换；该快照不宣称原子热发布。NPC另独立准确候选领域6/34坏配方和Owner6也通过，未覆盖mainchecks。

后验报告：npc-loyalty-deployment-verification.json及发布目录deployment-verification.json。此批保持剧情入梦、伤害和自动普攻修复；当前发布冻结待根只读复核后解除。真人GUI和完整异常原存档/商业容量仍未验证。
