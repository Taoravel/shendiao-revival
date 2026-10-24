# 暗雷自动普攻：真实发送链修复

2026-10-23。人类截图：太湖之滨/小花猫，自动面板29回合、普通攻击，第一回合请等待/准备中。用户要求修复；沿本窗口已有暗雷接入授权，不操作人类客户端或现场角色，不把GUI截图当服务器原始线包。

## 原证据与红反馈

research_battle_auto.py在离线原image SHA256 2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791上执行原自动发送0x1195aa0至网络单例取用前，随后原CSendAction marshal 0xe41550。角色为0000000100000000000000000101，宠物为0000000100000000000000000001，即ATTACK/target0/id0/角色或宠物/auto1。原分支将缓存目标清零（1195acf/1195bc1），非自动路径保留目标21。没有模拟这些字段存储或封送，也没有读取正在运行的客户端/凭证。

真实连续RC4/MPPC Peer→RoleOwner→WildBattle→TrainingBattle→Battle.submit回归先红：Native auto attack was ignored until timeout，last_rejection=Invalid target。旧验证只用手动目标21，无法覆盖原自动target0。现场日志另见战斗最终仍可胜利，但不能据此称自动即时受理正常。

## 修复与方法

diagnosing-bugs以原发送代码的线包构建确定性回归；优先假设为auto target0不被识别（原回归红，修后立即推进）、随后检查播放确认能否进入下回合、自动重发/宠物标记能否继续。无需临时日志或修改真人数据。codebase-design把自动线包到权威命令的转换留在已有战斗Adapter Interface，不放网络线程、地图或资产结算，不改变Battle目标安全规则。

唯一生产改动为training_battle.py：仅auto1+普通attack+target0时，从服务端当前fighters中按原位置顺序选择敌对、存活、未逃跑目标；没有目标仍交既有拒绝。非自动target0、非法flag、己方目标继续拒绝。该选择顺序为当前单怪范围的明确designed选择；自动线包语义为client_verified。没有恢复自动技能/高级AI，也没有宣称解决受击动画/飘字字段。原普通战斗与奖励数值不变。

## 当前验证

verify_wild_auto_runtime.py实际临时数据库与加密Owner路径：无宠角色4回合即时普通自动、每回合播放确认和下一回合、战斗结束与一次奖励；真实自有参战宠1回合双端原自动指令；手动空目标/非法auto flag/攻击己方均拒绝且快照不变。每轮真实下行脚本交原unmarshal解码；这不等于动画消费者或真人GUI验收。没有推进时钟或等待30秒来伪造自动成功。

发布将以实际当前不可变运行服为基准，仅覆盖这一生产文件及精确记录的研究/验证文件，保留其他窗口已发修复。固定diff、两轴报告、必要旧回归、manifest及最终发布记录另附；在实际启动核验前不称已上线。


2026-10-24独立收口：最终纯自动候选wild-auto-20261023T180606Z以原已发healing为base，training SHA80b2267e1972a325cb1e891f2c5251342bab2c067ccf6b28dc4c77ec58f480ef，仅6行，准确AUTO_ONLY.patch及Standards/Spec各0见同名review/REVIEW.md。四项固定runner验证全绿（自动人物/宠、既有wild11项、battle runtime、BattleOwner10项）。此前135625Z曾复制到同期damage的TargetResult单行却未带匹配protocol，已REJECTED，没有启动。新builder只从BASE精确派生6行，不再写共享training/protocol。交接见WILD_AUTO_READY_HANDOFF.json；统一发布伤害后若整合，必须保留该伤害行和新protocol，不拿pure-auto整文件覆盖。此时仍未称上线。


合成版wild-auto-20261023T181143Z以固定battle-damage-20261023T180731Z为base，完整保留其protocol+TargetResult，仅叠同6行自动普攻；training精确SHA7b6d81c9885517b2036419d437bddc5c9260f7e6a73c5339e1eb2949647640db（文本导出会统一换行，不能套用工作区旧hash）。两轴0项，5项固定runner/隔离输出检查绿：真实自动人物4回合/宠物、wild11、manual battle、原HP消费者8项及只读DB副本启动（108旧表行内容不变）。1431 manifest复核全匹配。此时现场仍是healing/45272，主集成正在先发布damage；没有抢listener或发跨聊天消息。


## 实际发布

2026-10-24 02:21:00北京时间，本窗口依据此前“由本窗口完成接入”及本次“继续”的直接用户授权，在统一窗口伤害版6008准确启动并完成后验核对后完成自动修复发布；不是抢先修改其发布或回退旧training。发布前再次核对当前实际命令/唯一listener以及无Established玩家连接；未启动游戏、认证真人或代玩。

当前PID12336，唯一127.0.0.1:28993，run_release.py为wild-auto-20261023T181143Z；base为battle-damage-20261023T180731Z。两生产文件的合成准确SHA：protocol1a472edf4f1a9db20d8c08ba05eb5516b56b723b87b2b2c80ca0c0a60c75cd22（与base相同），training7b6d81c9885517b2036419d437bddc5c9260f7e6a73c5339e1eb2949647640db。相对最新base的生产增量仍仅training自动6行，另两研究/测试辅助文件。1431 manifest及启动hash复核一致、gateway.pid同步12336、601与未认证心跳通过。

一致性备份为runtime/deployments/wild-auto-20261023T181143Z/accounts-at-stop.sqlite3；quick_check=ok、108张既有表的行数和内容SHA前后相同，没有任务/属性改写、删除角色或自动迁移资源。实际证据见该候选preflight.json、deployment-verification.json和evidence/latest-deployment-verification.json。

当前已发普通自动普攻受理与既有伤害结果map修复；没有把原HP消费者通过说成GUI渲染验收，自动技能/高级AI未在本批恢复。请以后取当前实际运行base而非旧6008、45272或pure-auto快照；不再改共享training/protocol中的其他范围。
