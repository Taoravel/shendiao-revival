# Spec

缺失0、额外范围0、错误实现0。

本批重读code-review，沿用codebase-design及ARCHITECTURE/DESIGN_AUTHORITY，以权威Impact→原native consumer的Seam核对固定两文件；非Git，无提交列表。candidate及release生产哈希一致，base与指定旧发布一致，8个harness哈希匹配：

- battle_protocol.py：1a472edf4f1a9db20d8c08ba05eb5516b56b723b87b2b2c80ca0c0a60c75cd22
- training_battle.py：0eff784921f509c3f173de8ebd9aeab2a539f098b9a26fed1d5e1a675e91b127

需求“第2回合有攻击动作但没有命中/伤害表现”对应research_battle_damage.py:5–9的原target result-map消费。candidate/battle_protocol.py:106–111将signed HP变化写入独立result map/key1；training_battle.py:256–260逐Impact传真实hp_change，保留每事件单次MP标量，防御无Impact则无伪目标。冻结harness/verify_battle_damage_presentation.py:37–38、44–110覆盖旧64字节HP0、人物/宠物/多目标/致死/防御/技能及太湖猫两回合的一致性要求；wild实际委托同TrainingBattle。未改公式、Owner、余额或auto-target。

仅静态审查及哈希核验，未运行代码、DB、服务、登录、GUI或真实战斗；不据此宣称真人画面已修复。
