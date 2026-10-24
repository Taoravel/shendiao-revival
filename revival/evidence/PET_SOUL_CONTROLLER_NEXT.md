# 元魂真实资产控制器的下一实现片

工作状态：已完成orb实例来源、Bag→逐珠tips和纯wear/remove计划，分别查对应batch；本文件是继续实现的定位记录，不是完成凭据。纯计划实际数据库受理/扣物/返还/回执尚不存在，不把当前绿灯当可玩。全量目标active。

下一步直接实现 `pet_soul_actions` 的调用方事务控制器。TDD沿已授权当前角色事务、原CUseItem/c0805及真实Inventory/Source/唯一资源hook Seam，先写“实际穿戴单扣珠、元魂map正确、当前消息、同ID重试只读”的纵片，再补38045摘除保真返回与组合故障，不能停在另一层纯计划。

## 输入与真实权限

- CUseItem精确16字节 `>iiq`，正itemkey/count1/正petkey<=signed31；c0805精确8字节 `>ii`，正petkey/slot1..5。原wire没有幂等ID，角色所有者在受理时固定服务器request_id并保留整个冻结命令；新的相同线包不能自动视为旧支付重试。
- 使用当前 `SoulBasis`、wear的 `OrbBasis` 或remove当前38045堆；先取得同事务实际快照。必须有可信current-authority reader，按role/pet/当前epoch返回明确版本/许可/flag22及实际扣除tool key的完整非绑定flags。缺失/未知不默认许可或0；读源写进命令，fresh执行再读并精确比较。不是接收原client的许可对象，也不能拿class6技能缺档0代替任何杂学/特权来源。
- Pure plans已决定lowest-free、精确模板重复、只wear当前fighting pet；保留全部XP和原signedraw6，明确无历史时按政策binding生成新raw6；返还新binding1/flags0和原四项+精确raw6。所有本地选择已标design；真实宠物最终属性/HPMP与battle尚需闭合。

## 写入顺序与原子性

1. 在任何写之前，验证当前租约/完整来源/权限和稳定意图，查专用receipt与实际Inventory receipt的成对存在；单边或冲突拒绝。
2. **先执行SoulStorage完整map CAS，再Inventory资产结算。** SoulBasis含库存版本，若先扣物/扣符会令旧basis失效。wear要在map CAS后确认orb物理/来源仍相同（除本次合法推进的库存版本），再调用公开Inventory.apply_settlement单扣；orb删除触发metadata清理。不能绕过私有Inventory writer。
3. remove的公开AssetChange同时先扣38045再grant一颗新珠；原maxNum1确保非堆叠。用before/after实际新item key集合定位唯一结果，不猜key或合并未知栈；保存OrbSource(version0,new stable source_ref,原四项,明确新flags0,精确selected raw6)，使用公开来源writer。原retained_raw6不由显示标志还原。
4. 同事务写专用意图/结果receipt，与公开Inventory receipt成对。重复只调用公开writer的既有receipt校验分支，禁止把缺receipt当fresh补付；不复制Inventory私有fingerprint公式。
5. 强制同步precommit/finalization Seam，使用真实普通v2或完整gem root inventory-source hook；按当前来源和flag22投影当前宠物数据，并预编码orb bag/tips、完整SendPetSouls及必要当前绝对属性。awaitable回调拒绝并由外层回滚。角色数值/元魂/材料/source/receipts/编码任一失败整笔回滚，提交后才由连接所有者投递。
6. paid在当前有效登录里严格只读当前，不调用CAS、收费或重放历史效果；原已付命令可含旧epoch但当前读取仍fence新epoch。当前flag22等属性来源应重读用于当前显示，不用旧许可决定历史支付能否读取，也不拿旧值覆盖当前。真实reader缺失时拒绝，不补值。

## 验证最低集合

真实临时角色/宠物/钱包和原Inventory；明确已知人类唯一资源基线及真实root hook；外部角色状态/许可Seam的测试输入必须标明显式fixture，不能当真实battle/privilege入口已接。wear保留raw6=-2、正确4→6顺序和单扣；remove实际38045原级费用/绑定优先、新key4字段/精确raw6返还，再wear保真；同IDpaid在SQL禁止DML下重放且当前改变不被旧值覆盖。测试完整source/invrev、权限版本、old epoch、异角色、包满/不足符/未知flags/未知metadata、孤立或冲突receipts；故障覆盖map、asset debit/grant、metadata、inventory/source/根资源、专用receipt和原编码后异常。所有数量/钱包/HPMP/原始字段须用公开当前Interface断言。

独立列迁移当前RED见 `EQUIPMENT_NATIVE_COLUMNS_PLAN.md`；NPC/root已提供27原native组合新证据，本窗口临时public Inventory已复现wire3报未恢复而内部4有物品，owned Bag/tips/endurance也出4。该片只读/方案/RED已落盘；内部数据不迁、NPC货架4不全局alias。shared由main单写，元魂column1路径可以继续实现，不能把这项当停止所属控制器工作的阻塞。
