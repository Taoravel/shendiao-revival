# 元魂穿戴与摘除：真实角色事务 Interface

2026-10-24，所属候选实现；全量恢复目标仍 active。`pet_soul_action_storage` 已组合真实 Inventory、穿戴 map、珠实例来源和独立/资产成对凭据。共享入口、真实状态许可提供者、宠物最终属性/资源与战斗、部署和 GUI 尚未验收。此前 `PET_SOUL_CONTROLLER_NEXT.md` 是实现前要求，本文件记录当前实现及仍需接入的条件。

## 调用顺序与完成条件

启动时在原 Inventory、SoulStorage、OrbStorage 之后调用 `prepare(db)`；配置启动冻结。角色所有者按 `role_id + login_epoch` 顺序执行，使用调用方已有连接与同一事务。此模块不开连接、不提交、不发送、不读热配置、不建热路径表。

1. `admit(db, inventory, rules, request_id, kind, payload, *, deadline_ms, clock_ms, authority_reader)` 从真实当前状态建立冻结的 `SoulWearCommand` / `SoulRemoveCommand`。原 CUseItem 必须精确16字节 `>iiq`、正实例/count1/正signed31宠物，摘除 c0805 必须精确8字节 `>ii`、slot1..5；c0804融合不冒充穿戴。服务器固定 request_id 与完整命令；新的相同线包是新的意图。deadline 与整数单调毫秒 clock 由可信服务器给出，受理、fresh执行、最终写入后及编码后检查。已提交命令的重试不重验历史期限。
2. `authority_reader(db, inventory, pet_id, material_keys)` 同步读取当前完整 `SoulActionAuthority`，包括真实角色/宠物/epoch、带版本许可、明确 flag22，以及实际将扣除的移魂符完整非绑定flags。缺档不推许可或0。摘除通过公开 `removal_materials` 先确定实际扣除的key，再读取权限；不是先伪造flags调用授权计划。**当前验证使用明确标出的外部所有者 fixture，真实地图/战斗/flag22/材料标志来源尚待接入。**
3. `apply(db, inventory, rules, currency_rules, command, *, resource_context, clock_ms, authority_reader, precommit)` 先校验当前唯一人物资源来源，待结算来源拒绝；fresh必须仍为同epoch、完整原 map/orb/tools/许可。`SoulResourceRules` 指明实际选中的人物装备政策；普通 v2 和完整宝石政策的 carrier 均已实际验证，不用旧普通数值投影器冒算宝石政策。
4. **先 map CAS，再公开 Inventory.apply_settlement。** map basis包含原库存版本；反序会令原basis失效。CAS后独立检查珠/材料未被额外改变。穿戴扣一颗真实实例；摘除同一 AssetChange 扣移魂符并返一颗 maxNum1 新实例。由前后实际key集合定位唯一返还结果，再公开初始化新 OrbSource；不猜key、不合并未知栈。珠四字段与精确 raw6 保留，新绑定/非绑定flags按显式设计政策，不按布尔显示逆推原raw6。
5. 同事务保存专用意图/结果凭据，与 Inventory资产凭据成对。单边/冲突拒绝。`precommit(db, inventory, snapshot, *, replayed, request_id)` 必须同步加入所选实际根 inventory-resource source hook；拒绝 awaitable。模块随后独立重读真实唯一资源来源，空回调不能通过；人物资源version、HP/MP及两上限必须保持不变，借回调治疗会拒绝并回滚。将来的宠物最终属性与唯一宠物资源结算也须在这一事务组合，当前仅返回元魂原始修正向量。
6. 模块预编码当前 Bag column1、逐颗 Orb SItemTips，再完整 SendPetSouls。调用方完成其它所需原生编码后才提交，提交后由连接所有者投递。**任何异常都必须离开事务作用域，由调用方整笔回滚；不能在事务内部吞掉异常后正常退出。** 取消未提交命令依此回滚；提交后的取消不撤销已经发生的资产。

## 历史重试与当前结果

paid 分支验证原完整命令指纹、政策、操作、结果及公开 Inventory既有凭据，不再CAS、扣物、生成返还珠或重放旧属性。当前有效 Inventory 租约仍受校验；原已付命令可来自旧epoch。读当前 map、真实当前 flag22/许可及当前人物伤后资源；当前许可关闭不会重扣或阻止确认既有支付，未知来源仍拒绝。根 hook 的 replayed 分支只读，已用SQL禁止所有DML验证。

`returned_item_key` 是该历史摘除的结果确认，可能早已再次穿戴或消耗；它不是当前资产证明。当前资产以 `snapshot`、当前Orb来源及 `messages` 为准。旧摘除重试不会复活已消耗的返还物。

## 证据、设计与验证范围

原表移魂符38045费用、XP级别/有效上限与修正向量来自客户端；first-free槽、相同模板限制、新历史raw6生成、返还绑定和无现金费等本地选择集中在 `design/pet-soul-actions-v1.json`。原料/绑定不扩展为真实未知许可。原 raw4/raw5 的显示含义新证据见 `PET_SOUL_RAW6_BINDING_RESEARCH.md`：剩余可点化次数 / 魂技等级；服务器有效范围、点化扣减和技能效果公式尚未证明。raw6/+5d业务仍unknown；有名字的“已绑定”/锁图标分别读基础flags bit0/0x20。保留旧序列字段名和精确值，不把负数保真fixture当合法业务等级。

`verify_pet_soul_action_storage.py` 使用真实临时AccountStore/Inventory/根唯一资源：穿戴→摘除→再穿戴，实际原费用4符且绑定先扣，新key返还保真，14个真实SQL故障、两处原生编解码后异常、包满/腾位、无效/治疗/异步finalizer、旧epoch/孤立凭据/过期待结算与current只读重试。超时发生在真实source写后也整笔回滚，paid不调用历史clock。`verify_pet_soul_action_gem_resources.py` 用真实绿色宝石腰带，人物上限203、HP70/MP40及属性和资源version在元魂结算中不变；这不认证宝石付费镶嵌本身。

方法：TDD在已授权真实角色事务/公开Inventory/source/原生消息Seam逐片红→绿；codebase-design将稳定受理、权限重读、组合结算隐藏在一个调用方事务 Interface，依赖从外部注入；writing-for-agents将事务退出条件和历史ack的陷阱与调用步骤并列；code-review按固定清单分别作Standards/Spec独立审查，结果另存该批manifest。尚未验证真实权限提供者、完整宠物属性/HPMP/技能公式、融合/点化、战斗接线、共享加密投递、运行服部署、GUI和容量。
