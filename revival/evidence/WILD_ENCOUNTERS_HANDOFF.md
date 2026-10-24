# 普通怪物、暗雷及奖励接线交付

当前奖励默认已升级v2，接入前先读[WILD_REWARDS_V2.md](WILD_REWARDS_V2.md)：新增宠物资源与经验、三类独立掉落、现金和当前宠物刷新；下文v1数值及“宠物经验pending”属于历史批次，不作为v2接线规则。共享入口仍未接入本模块。

2026-10-23。本批完成独立领域实现和离线验证；运行服接线、部署、客户端实测仍待共享入口集成。接入暗雷移动、战斗开启或野怪奖励时阅读本文。按根AGENTS，共享入口由原始复原聊天统一编辑，本窗口未修改serve.py、gateway.py、accounts.py、game_runtime.py及runtime_storage.py。

## 来源与设计决定

`recover_wild_encounters.py`重新读取原config.pfs，经PFS长度/CRC、BXML解码与现有目录语义比对，忽略格式化XML产生的空白差异。核对地图304行、怪物5635行、宠物158行、背景41行及人物经验/物品原表；摘要见wild-encounters-source-audit.json。

`catalogs/wild-encounters.json`覆盖46张可用非安全地图、107条普通怪物分布，优先使用怪物title=`地图名:普通`，缺失时联查宠物desciption场景链接与唯一可捕获练功区同名同模型模板。模板、名称、模型、图鉴/标题分布、场景最低等级及battleground字段为client_verified；将展示分布作为整图暗雷池、等权抽样和最低等级作为敌等级均为designed。83条图鉴联查缺项保留审计，不把无唯一对应的宠物塞进怪物池；专用普通模板不依赖图鉴匹配。

[2012端游官方战斗规则](https://sdxl.wanmei.com/info/qita/fight/20120729/133541.shtml)支持野外行走自动切入战斗、战斗获取经验、30秒指令窗口与200回合上限，属于guide_supported，未证明与1.6.1完全相同。[历史宠物分布](https://sdxl.wanmei.com/info/newplayer/10to19/20120626/131961.shtml)与客户端存在差异：历史太湖有小偷、客户端小偷图鉴仅雷峰塔1/2层；本版优先客户端。[2022化境更新](https://sdxl.wanmei.com/news/gamebroad/20220525/237864.shtml)说明练功区有角色经验、宠物经验和金钱，但版本不同，不能推导当前奖励公式。检索未找到可信的1.6.1原服普通怪经验公式、基础金钱、药品掉率；采用独立设计配置继续恢复。

遇怪唯一设计来源`design/wild-encounters-v1.json`：普通已受理CHECK/STOP跨格位移累积，64逻辑像素尝试一次、20%概率，每报告最多一次，出生/换图5秒保护，结束10秒冷却。按端点欧氏距离向下取整且每报告上限64，非真实路径长度或速度反作弊。monster.dat区域语义未证明，未用于运行判定。v1仅单人单怪；捕获、稀有怪、队伍和特殊移动待补。

奖励唯一设计来源`design/wild-rewards-v1.json`：胜利人物经验=max(1,floor(场景最低等级原nextexp/100))，绑定银=场景等级×2；单次互斥掉落白芍33001一棵10%、杜仲33013一棵10%、无掉落80%，掉落绑定1。人物高于场景等级10级以上不领奖；胜负资格以入场快照固定。物品身份/原nextexp为client_verified，全部比例、金额、绑定和资格为designed。暂不实现倍数时间、装备掉落和死亡惩罚。宠物经验字段保持pending；不能宣称普通野怪全奖励已完成。

## 集成顺序及完成条件

1. **启动配置**：在监听前完成`load_wild_rules()`、`load_wild_reward_rules()`与`prepare_wild_reward_storage(db)`，复用现有钱包、成长、库存迁移。判定路径只接冻结配置；已有钱包/成长不隐式初始化。完成条件：网络热路径没有配置读盘或DDL。
2. **角色遇怪门控**：在角色有界邮箱中为当前租约创建`WildEncounters(Location, rules, now_ms, rng)`。地图所有者先受理移动，随后将旧Location和原MoveResult交给`accepted_move(previous,result,now_ms,eligible)`。eligible来自角色所有者，只有存活、单人、普通移动、非战斗/换图/剧情等模式可为真。地图变更后先结束旧门控，再以新激活位置创建新门控；旧租约实例丢弃。完成条件：ROLE_MOVE意图、静止、拒绝移动、重复版本、传送offer不掷遇怪，冷却期间更新仍消费位置版本。
3. **受理战斗**：收到EncounterTicket后先在角色所有者冻结全部玩法变更，固定真实版本化属性/参战宠快照，创建`WildBattle(Participant,ticket,training_rules,clock)`并放入独立battle_id有界邮箱。复用已有战斗调度的输入身份/世代、重试、超时与播放确认保护；WildBattle是命令引擎Adapter，不自带调度器。以`register_wild_reward`加入角色租约事务并提交入场计划，再显式`accepted(ticket,battle.id)`和发送opening。完成条件：每票仅一个已受理战斗，入场前已持久化固定奖励和掉落roll；事务失败关闭未展示的战斗。
4. **跨所有者失败**：只有明确战斗拒绝才调用`rejected(ticket,now_ms)`；超时保留pending并查询真实受理状态。已受理battle不能取消为未受理。断线/进程恢复需要持久化战斗身份及终局outbox，当前模块没有实现这一运行时恢复器。完成条件：迟到回调不能释放新票或向新连接发旧开场。
5. **终局及奖励**：角色所有者校验battle_id、租约、属性版本并接收可信`WildBattle.finished()`，通过有界持久化资源在一个活动角色事务调用`settle_wild_reward`，同事务完成资源/死亡/宠物处理及终局outbox确认。返回不是commit成功；任一异常整事务回滚。结算函数不自建连接、不提交、不发包。完成条件：成功后奖励、资源及确认一起落盘；未落盘终局可重试，不能先释放战斗又丢弃失败奖励。
6. **终局后的刷新**：提交成功后重读当前经验、成长/属性、钱包、背包并通过已有原生编码器刷新，角色缓存使用当前绝对值。历史回执只确认曾发金额，不作当前余额。最后用可信战斗终局调用`finished(ticket,battle_id,now_ms)`启动冷却。逃跑/失败/平局零奖励；close/播放超时只产生中止，不能伪造victory。完成条件：刷新经目标连接所有者有序发送，背包满时掉落不重抽，重登不重发。

WildBattle复用现有TrainingBattle动作/播放实现，但替换敌人属性、原始名称/模板/模型、场景战斗背景和终局scope；普通战斗音乐1为designed。适配器保留现有训练数字技能策略，不能据此称门派战斗全恢复；不允许缺失真实人物属性时套训练默认值。宠物奖励与真实战后资源的事务接线仍待战斗/宠物/角色共同集成。finished中旧currency_reward/item_rewards保持引擎默认零，普通野怪奖励以本批持久化plan/receipt为准，避免两条路径重复发奖。

## 本批方法、产物和验收

- codebase-design：将遇怪概率/位移/冷却/预留生命周期集中在角色拥有的小Interface；地图只提供已受理位置，战斗只运行属性快照，奖励加入角色事务，无全服锁/队列、网络或数据库对象跨所有者共享。
- writing-for-agents：本交接按启动→移动→受理→失败→终局→刷新编排，每步给可判定完成条件，数值仅引用唯一配置，来源与上线状态分别记录。
- 产物：recover_wild_encounters.py、wild_encounters.py、wild_battle.py、wild_rewards.py，两份design配置、一份分布目录及两份验证程序/报告。
- verify_wild_encounters.py：13项通过，包括真实MapOwner受理CHECK→遇怪、冷却/重复/租约/传送/胜负，以及107条实际WildBattle开场逐条执行原客户端解码器，核对模型、模板ID、等级、血量与地图背景。
- verify_wild_rewards.py：8组真实临时SQLite/Inventory/钱包/经验检查通过，覆盖一次发奖、异终局冲突、外层资源失败整事务回滚、背包满回滚后固定掉落重试、逃跑/失败/平局、越级抑制、未登记/训练/异入场拒绝、旧租约拒绝。没有修改在线角色。
- 回归verify_battle.py：8项通过，8种原生协议解码通过；verify_world_monsters.py：5635模板中5632可编码，3个原模型缺失保持原报告。
- 未验证：共享运行入口与终局outbox/重登恢复、战后资源原子落盘、宠物经验、全原服数值、GUI实机暗雷切场/表现、商业并发容量。当前运行服没有加载本批模块。
