# 首次学技后的梦境战斗：下一配方候选

2026-10-24，主策划基于用户授权“客户端优先、端游攻略其次、仍未知自行补全”制定。仅为下一独立设计候选，当前优先完成AI8001真实胜利、耐久存档与首次教学；不把新增政策文件当作现役支持。

唯一执行参数来源：[task-pve-ai8027-v1.json](D:/神雕侠侣/revival/design/task-pve-ai8027-v1.json)。原始来源：[NEXT_DREAM_BATTLE_SOURCE_ROOT.md](D:/神雕侠侣/revival/evidence/NEXT_DREAM_BATTLE_SOURCE_ROOT.md)，固定SHA `70d345271193234a1f47e4e50e96402804bc4556bf0682deb64d8c510dcf6668`。该研究实际核十三PFS成员长度/CRC/BXML，二十任务完整字段/边、NPC/monster/技能，并重新打开同端游官方页、有界定向查找；没有恢复AI8027敌阵或100008公式。严禁以场景三个DisplayNPC推三只敌人、以MonsterNum0推零敌自动赢、以同AI打开101004。

本候选精确采用十条首次教学的原唯一后继，保留原AI8027、说书人10908/私有模板1501、255经验/SMoney600与原对白和下一CG节点。怪物29105的梦魇邪兽/6070与不可捕捉为client_verified；选择两只、站位21/22、3级各HP60/MP0/攻10防4速8及背景音乐均为designed。场景实体仍归MapOwner，战斗配方不伪造NPC交互资格。

100008原描述明确两目标及耗蓝随人物等级增加，但paramA/B/C/D0不证明免费，其他同名500001/500067不是玩家100008。官方[2013万兽山庄攻略](https://sdxl.wanmei.com/news/gamenews/20130814/148481.shtml)仅支持“早期太祖长拳可用于固定伤害”的定性线索，没有本版定量公式。因而本配方明确designed：每次耗蓝2+人物等级，基础伤害20+5×人物等级，不减物防；防御仍向下减半至少1；每个实际目标伤害裁剪到当前HP。3级例为一次5MP、对每个未防御目标35伤害，两个60HP敌人一般需要两次技能，实际速度/HP/MP及宠物会改变过程。不是原服公式，也不推广到野外、门派技能或后期副本。

只有完整已知技能账本内真正已学100008/value>=1才授权本场使用，保留完整map和高值；已授予不等于每战重授。行动包原来只有一个主目标，第二目标由本设计在实际行动时选择最低站位的另一活敌，去重最多2；主目标/角色已先死亡则取消且不耗蓝。MP只扣一次；不足时拒绝且保留本轮另选普通攻击/防御/逃跑的机会。原operation_id保持100008，effect10011只作客户端资源引用；需验证一次原执行中两个独立HP结果和一次MP变化，不能回到旧DemoAttr假伤害表现。

本次是TaskPve新配方，不借Training/Wild实例结算改标签。raw资源先保存、梦境死亡专用恢复和Task奖励/后继/consumer/outbox同事务，持久producer保留原事件；AI8001-only permit不能变更task/hash来冒充AI8027授权。新配方需独立可信permit绑定，并让原8001旧配方仍能解析其pending恢复。现TaskBattle每registry一个engine_revision，直接覆盖唯一current registry会阻断旧pending，这是实际Interface条件；按服务器精确task选新准入、按admission原recipe选恢复，禁止删校验或重写epoch/revision解决。已settled纯current查询与pending兑现权限不同。

本战原Animation0，后继100161等另有Animation10001/NPC10084，不因赢战直接完成后继、发假SStartCG或CEnd。第一场10019是另一原字段/电影，原生研究未闭合其自动启动桥，同样不得借本政策补造。下一CG/AI8002继续按角色成长单独恢复。

方法：research已按primary来源闭合已知与未知；codebase-design把配方、真实已学状态、单场战斗、角色存档与连接发送保留在各自权威Interface，旧版本恢复是明确变化的Seam；code-review对本候选独立Standards/Spec双轴检查。验收须覆盖精确十任务/反例101004，真实已学与不足MP，2/1/0活目标、原native HP/MP消费、200回合/邮箱限额、真胜/败/逃/断线、晚失败回滚、新租约旧8001与新8027 pending恢复、付后当前读取以及另一角色/地图/战斗独立推进。当前只有设计与来源检查，没有本场实现、GUI、真人资料或发布验证。
