# 仓库银两与修理投影：交集成窗口

2026-10-23。本批仅修改NPC所属模块/验证与政策，未改game_runtime/runtime_storage/accounts/serve/gateway，未操作PID8724或现场库。主策划已确认发布快照冻结解除，但shared继续由原始窗口独占。仓库协议证据见[NPC_DEPOT_MONEY_NATIVE.md](NPC_DEPOT_MONEY_NATIVE.md)。

后续接线已完成：主集成应用了NPC_DEPOT_TYPES与repair_role_equipment；本窗口实际加密money脚本已由原{}转绿，已装备修理完整20map及重连也绿。最新动态presence、关闭撤权和移动进展见[NPC_LIFECYCLE_INTEGRATION.md](NPC_LIFECYCLE_INTEGRATION.md)。以下补丁/红例描述保留当时缺口的成因，当前完成范围按此更新与对应结果判断。

## 仓库钱的具体接线

NPC Module已提供npc_depot.MONEY_TYPES={0xc03fb,0xc03fc}及npc_gameplay.NPC_DEPOT_TYPES={原open,两种钱请求}。NPC_GAMEPLAY_TYPES包含这些请求，现有战斗/序章/loading门控因此可沿用。decode_money验证原16字节两signed64字段与正金额；depot_operation重验线包NPCkey==地图证明key，不接受客户端换一个NPC绕过仓库访问。

原始集成窗口只需把RoleOwner的NPC分支内`if kind==npc_depot.OPEN_DEPOT`（以及紧跟的8字节专属检查）替换成`if kind in npc_gameplay.NPC_DEPOT_TYPES: return await self.depot_request(cmd,kind,body)`。已有depot_request内仅open读取8字节；其它操作要求已有访问票据，重新取得地图证明并校验地址/位置版本，再调用depot_operation。钱线包的key/amount由Module验证。精确可审阅差异：[npc-depot-money-shared.patch](npc-depot-money-shared.patch)。该文件仅补丁产物，未应用到shared；基准hash记录在本聊天工具输出，若shared有新改动按当前区段手工集成。

上行证明→depot_operation→当前余额逻辑消息使用同一角色的有界I/O，连接仍独占加密投递。配置/schema只在prepare：新增npc_depot_cash_journal，记录请求指纹、NPCkey、方向、金额和双账户前后余额；公共凭据、规范钱包凭据与该审计表同一事务。新命令调用apply_currency，purpose=npc_depot_transfer；现金/库款结果域均0..signed63max，Python中先检查，失败不靠截断。转入/取出等额无费、保留绑银。重试重读双方当前余额，审计与公共凭据不一致拒绝。

本批先在currency-v1追加上述purpose及同角色规则，随后收到主策划与该编辑交错的“正在裁定”通知，未继续改共用policy；主策划再次明确“认可此追加设计，当前policy内容保留，我补统一决定”。后续共用policy由主策划合并。NPC所属设计只保留指向该规则的来源说明，未另设支付替代。

### 已验证与待验证

- verify_npc_depot_money.py通过：原高32位key和4294967303存/4294967301取；总额10000098765守恒；双余额不足/溢出、零/负/截断/错NPC/过期/冲突重试拒绝；真实SQL在公共凭据插入时abort回滚两余额/账本/审计，同键之后可成功；未知旧钱包/仓库不填0、不占请求键；换租约后现金9999999988、库款98777保持，旧Owner拒绝。
- verify_npc_depot_money_native.py通过原x86两请求codec、约束与截断；两种绝对余额codec；原handler写cash+b0或depot+b8且不覆盖另一槽，覆盖0、超过32位金额和signed63max。停止于观察者之前，未声称GUI显示。
- verify_npc_depot_money_runtime.py已在真实加密Peer→RoleOwner处得到红例：开仓后存款无返回（{}），尚缺上述共享分发。未注入替代dispatcher或临时修改shared让它假绿；接线后原样运行该脚本，默认必须全通过。
- 本批中途旧仓库/商店与新事务重跑曾被guild_training.rules的invalid_guild_training_policy拦住。组织源码收敛后，已重新从完整prepare执行verify_npc_depot_money、verify_npc_depot_runtime、verify_npc_shop_runtime和verify_npc_repair_transactions，全部通过；启动问题已解除，不沿用过期阻塞状态。
- 只读检查看到social_owner.initialize把JSON list冻结成tuple，而当时guild_training.rules将初始空集合与[]比较。准备执行最小对照时，组织源码已被其所属窗口更新；当前原JSON与正式冻结快照调用均通过且rules相同，证据[npc-startup-guild-policy-block.json](npc-startup-guild-policy-block.json)。NPC窗口未改/绕过共享启动，随后按当前源码重跑必要检查，不把早先故障当永久阻塞。
- 仅在测试脚本将客栈菜单预期从[2]更新为[2,3]；运行期本来就同时有购买与休息。组织问题收敛后已从完整prepare原样执行该持久脚本通过。

主集成已应用分发，NPC窗口原样运行实际wire脚本通过，证据npc-depot-money-runtime.json。此前“Shared depot-money route not integrated: {}”保留在baseline文件，现已转绿。主策划另用verify_npc_depot_money_guards核对真实票据过期、移动撤销、新线包各转一次与同内部ID去重的区别、错NPC/畸形请求无余额及账本变化。待现场GUI；当前运行8724是否加载后续功能按发布摘要核对，工作区源码不会热进入该不可变发布。

## 修理与磨损的最终属性Interface

`npc_repairs.repair(accounts, inventory, intent, precommit=None, *, draw_source=secrets.randbelow)`新增可选第四位置参数，方便既有RoleOwner.io(fn,*args)调用。precommit Interface为`(db, inventory, current_inventory_snapshot) -> tuple[(type:int, body:bytes), ...]`。trusted函数由集成层提供，不能来自客户端。

调用顺序：同租约事务→验证期限与钱包→公共凭据/抽样/修理扣款及条件→当前耐久/当前现金预编码→重新取immutable_snapshot_transaction(db)→precommit→提交。重试也重取当前快照并执行投影，跳过随机和扣款。precommit用root的current_equipment_projection(db,account,role,epoch,snapshot,rules)和read_growth、growth_refresh产生最终原生消息；返回tuple，任一投影或编码错误回滚条件、费用及所有凭据。只投递逻辑消息，不能在hook提交、另开连接、提前发布RoleOwner状态或操作Session。无hook的旧调用保持旧返回形状，不能据此声称普通修理最终属性已接完。

磨损已有`Inventory.wear_equipment(db,key,settlement_id,expected_version,amount)`调用方事务Interface，随后在同db取immutable_snapshot_transaction并做同一最终投影/预编码再commit；磨损重复凭据不代表当前完整装备快照。需由当前角色租约调用方围栏，不从战斗Module直接写库。

verify_npc_repair_projection.py已通过真实资产路径：绑定49009实际equip后磨损到0；修理precommit看到同事务最终45/35/19、HP70/MP40；先编码后受控拒绝使扣款/条件/全部凭据回滚；相同受理命令随后成功，已提交重试不重抽且重投当前状态。另用明确高基线16777209及武器+8得到16777217，真实growth_refresh因原float32不精确而拒绝，整个修理回滚。此脚本只准备NPC/背包/人物属性真实依赖，不包括组织/完整shared启动，范围明确记录。

主集成已把可信projector传入实际NPC修理路由。NPC窗口verify_npc_equipped_repair_runtime实际装备/原repair/重连通过完整20项map45/35/19、HP70/MP40和现金960；主策划独立repair hook覆盖晚期失败与真实float拒绝。本窗口未擅自写shared。其它装备/成长刷新仍由集成统一保证同一最终投影，完整伤势/高级装备和实际GUI另验。

## 方法与状态

codebase-design用于把存取款及事务凭据放在NPC Module，把角色最终属性规则留在root Module，通过调用方事务Seam组合；tdd从不支持存取款和缺少precommit参数的真实红例逐条实现，并以原x86和既有root属性数值作独立oracle。writing-for-agents把shared唯一编辑者、具体一处差异、旧/当前验证范围及完成条件写在本页。未验证现场GUI、商业数据库/容量、异常关服恢复和完整NPC全部服务。
