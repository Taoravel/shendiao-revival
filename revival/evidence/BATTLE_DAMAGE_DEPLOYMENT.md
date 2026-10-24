# 攻击后伤害结果恢复

用户现场：太湖之滨，小花猫，第2回合，人物“醉死你的温柔[4]”古墓派2级；攻击动作播放，但未见伤害表现。此记录不从静态截图推断血条实际变化。

方法采用 diagnosing-bugs：原行动发送→实际 TrainingBattle/WildBattle 出包→原 SSendRoundScript 解码→原目标结果消费者形成确定性反馈。旧服将 HP 差值写入 DemoAttr list；原消费者在 0x11910df..0x1191821 从目标结果 map 的 key1 读取 HP 差值，因此旧包可解码但读取值为0。相同攻击实际扣16时，修正后原消费者读取-16。

最小候选：`runtime/deployments/battle-damage-20261023T180731Z`。BASE 为已验证的治疗发布 `npc-role-healing-20261023T125539Z`，共1429个冻结生产输入。仅两个生产文件变化：battle_protocol.py 添加不可变 TargetResult 并正确写结果 map；training_battle.py 从 BASE 仅替换目标结果构造一行。自动选敌、剧情、私有地图池、社交和 NPC 距离变更均未进入本候选。

候选生产 SHA256：

- battle_protocol.py：1a472edf4f1a9db20d8c08ba05eb5516b56b723b87b2b2c80ca0c0a60c75cd22
- training_battle.py：0eff784921f509c3f173de8ebd9aeab2a539f098b9a26fed1d5e1a675e91b127

精确候选五项检查全部通过：伤害原消费者8项、战斗行为8项与原协议8条、独立战斗所有者10项、真实加密临时角色流程2组、暗雷资产/断线/恢复/隔离11组。相同伤害检查对 BASE 为红；其中多目标新增接口项的 BASE AttributeError 单独说明，不把它冒充现场根因。其他6项从真实目标结果 DemoAttr 错位失败；旧包原消费者0读值也被独立确认。

验收 harness 使用冻结版本，生产模块路径逐个断言来自候选或指定 BASE，全部生产与 harness SHA 前后核验。伤害脚本仅将报告 ROOT 重定向到 harness/workspace，里面的两份生产副本只用于报告哈希，不参与模块导入。候选启动预演仅在当前库一致备份的可丢弃副本执行：108张原表所有行不变、无新增表、quick_check=ok。

在新候选发布前发现旧 PID36632 已不存在、端口无监听。先独立验证旧发布1429输入及 runner，备份当前存档并恢复同一已审 runner 为 PID45272；601未认证握手/心跳、启动模块哈希和108表所有行前后不变均已通过。没有将旧备份还原到真人库。恢复证据：reviewed-service-recovery.json。

状态：2026-10-24 02:19:44（北京时间）已发布，实际 PID6008，唯一28993监听，601未认证握手与心跳通过。全1429生产输入、实际启动模块哈希、108张旧表所有行保留与quick_check均通过；无新表、无真人角色/任务改写。停服点一致备份位于发布目录 accounts-at-stop.sqlite3。报告为 battle-damage-deployment-verification.json 与发布目录 deployment-verification.json。

固定包独立 Standards/Spec 各0项发现，规划根另有独立双轴0与原消费者红绿复核；报告位于 reviews/battle-damage-release-20261024。部署脚本在全部输入哈希、进程身份确认与元数据复制后，最后检查无连接才切换；该检查是瞬时空服守卫，不是原子停止接入协议。未将此限制冒称为任意新连接零中断保证。

本批不启动游戏客户端，不代玩真人战斗。原消费者能收到伤害已经验证；真实受击动作、飘字和画面仍需发布后真人验收，不能把离线消费者执行当作完成GUI验证。

后续实际运行版本更新：自动普攻窗口在伤害版之上发布 wild-auto-20261023T181143Z，02:21左右实际 PID12336，替代历史6008。集成方独立只读核对1431输入、runner、实际启动哈希和两处伤害修复仍在；相对伤害版仅 training_battle 自动target0段及2个研究/检查文件新增。规划根对该实际新版再次执行8项伤害原消费者检查全绿，见 wild-auto-root-release-verification-20261024.json 与 root-battle-damage-20261024/wild-auto-20261023T181143Z/verification.json。当前伤害修复有效；后续候选以这个实际新BASE为准。未为核查再次启停服务。各窗口后续改为统一交单、集中切换，避免相邻发布让历史PID误充当前状态。

并行源码保存范围：此前私有地图/剧情入场、地图池 pin、场景发送围栏等共享源码仍属后续候选，未混入本次发布。延迟投递/队列满/旧场景/传送断线 receipt 等完整故障闭环尚未在最终私有候选完成；后续从新实际运行 BASE 继续，不能仅凭工作区绿灯宣称部署。
