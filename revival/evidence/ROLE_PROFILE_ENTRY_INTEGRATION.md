# 显式人物profile的入场与普通成长初始化（未部署）

2026-10-23。沿用codebase-design：在runtime_storage持久化Seam读取一致、冻结RoleLoadProfile，在world_snapshot小Interface注入可选属性快照，普通map编码复用主策划role_attribute_protocol。原生字段及19项map验证归ROLE_GROWTH_UI_RESEARCH和role-growth-protocol报告；本批不再重复推断或运行原生探针。

## 源码接线

- runtime_storage.role_load_profile在当前角色租约事务中读取等级、经验、已有成长与属性/伤势快照。没有属性基线/快照时返回明确compat路径，不建基线或推算历史潜能。
- 基线与当前快照必须成对存在；残缺记录、旧成长/属性版本、规则缺失或策略版本不匹配明确失败，不静默回到100HP兼容值。
- 事务内复用role_detail_vitals、growth_refresh校验并预编码已知普通map，冻结数据返回角色所有者；不让领域/存储工作者访问连接或加密器。
- RoleOwner.load采用同一快照的等级和经验，并调用world_snapshot(role, attribute_snapshot)恢复RoleDetail前五槽：当前HP、伤势上限、maxHP、当前MP、maxMP。其他未知槽保留原默认。只有无profile路径仍用先前实验100值；这不是新增持久化基线。
- profile伤势上限640=maxHP沿主策划明示designed无伤势模型，不宣称还原原版伤势系统；保留当前缺血缺蓝及死亡，不强制回满。
- 首次世界ACK再读取当时最新profile，避免用登录早期或历史奖励回执覆盖其后资源/成长；已有profile返回预编码0xc32c8等级490、潜能500、五维/已核验派生、当前及最大资源等。逻辑消息由目标ConnectionOwner持续FIFO编码。
- 无profile不发这份完整成长map，不套角色训练/宠物/战斗初始化消息。普通跨图仍用scene.1设计发送屏障，不误用首次ACK。

## 范围与状态

仅核对当前公开函数、字段顺序、事务/租约与调用路径，未运行额外脚本/战斗/GUI或重启部署，未访问手动现场数据库。原helper独立codec/属性验证不等于本次入口已实跑；后续由主策划独立验收或用户允许部署时核验。

此修改只闭合已明确profile的初始化，不解决无profile旧角色的基线迁移、完整装备/技能/经脉合成，也不表示当前黑屏/不能移动已修复。任务完成后的成长刷新预编码由任务窗口维护TaskWorkflow；角色/在线/社交缓存一致性上一批已通过，未为本修改重复跑全回归。

后续状态：主策划已扩充verify_growth_runtime并独立通过伤势入场、首次19项ACK、原NPC任务后的成长/伤势刷新及重连，见growth-runtime-verification.json；前述“未运行”是原交接时点。新创建记录首登基线见CREATION_PROFILE_RUNTIME_INTEGRATION.md，旧无profile角色仍不自动迁移。均非GUI/部署验收。
