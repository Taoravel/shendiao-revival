# 寿命食品中毒事务接线

2026-10-23。32004岁寒三友与32009蟹黄汤包的真实品质寿命、3%中毒分支、永久基础资质变更及原生回复已实现并离线验证。全量目标仍active；共享稳定随机上下文路由、部署、提示/动画、GUI和实际战斗另验。固定32036与32007分别沿PET_LIFETIME_ITEMS_INTEGRATION、PET_QUALITY_LIFETIME_INTEGRATION。

## 来源与明确补全

原PFS完整attributes/lists及CRC审计见pet-lifetime-source-audit.json。原32004/32009均itemtype546、needLevel1、outbattleuse2；效果funtionid0，原品质ai0/bi0分别3/0和2/50。即品质100对应300/250寿命，32009已知品质0仍有50效果。原物品说明及bookanswer36017同时确认3%中毒、降低一定资质；它是食品的永久资质副作用，不据此制造战斗DOT状态。

定向原配置/帮助和端游攻略检索未给出具体下降点数、服务器舍入或完整状态顺序。当前恢复设计集中design/pet-toxic-food-v1.json：每次中毒五项当前基础资质各减1、最低0；先改当前未含血脉的基础，再投影当前血脉；保留成长原整数、等级/XP、已分配点数、血脉与真实潜能。HP/MP保留当前绝对值，仅超过新的较低上限时裁剪，死亡保持0。以上下降点数/顺序/resources与服务端品质取整均designed；不得标成原服实测或主策划已单独审定的精确公式。策略可按后续原证据替换。

抽样以可信均匀整数0..9999、draw<300中毒表达原3%；分辨率与边界是恢复设计。领域不自行抽随机数，不读取客户端draw，重试不重抽已付结果。当前基础资质是永久变化的未加血脉值，不是重写成含血脉的五项值；旧生成/成长/血脉历史receipt保留当时基础，当前通知重读当前基础，避免旧ACK恢复中毒前状态。

## 原生Owner接线

```python
inventory.receive_pet_consumable(body, epoch, request_id, now_ms, precommit, draw)
```

draw是追加在precommit之后的可位置参数，默认None，既有普通药/食物/精华调用兼容。body仍为16字节`>iiQ`：自有携带实例key、kind1、owned live pet key。Owner在可信受理命令中固定一次draw，在同一命令失败重试时沿用；当前时间按现有限时技能契约传入。可以为所有宠物kind1受理附加稳定draw，只有这两种食品消费此值，调用方无需复制模板/品质公式。原`receive(USE_ITEM,body)`和无上下文`use_pet_consumable`对这两种食品明确拒绝，主集成必须接context Adapter，不能给一个默认安全draw绕开副作用。

precommit沿INVENTORY_RESOURCE_HOOK_INTEGRATION：同db、同当前冻结assets、实际fresh False/validated paid True。根source与共享共同受理凭据由Owner在同一事务加入；True保持严格只读，不因低层已付而补造wrapper/common付款或修复后来pending来源。回复完整当前Pet与实际cash背包，提交前完成编码；有到期map必须传可信Unix毫秒。

验收条件：Owner验证场景/非战斗/交易/传送等资格，领域重新验证当前lease、owned active pet、原物品与真实quality/needLevel、明确普通基础成长/血脉/care；一次扣1、增加对应寿命、一次中毒判断及基础变化。任一资产/receipt/source/hook/native编码失败整个角色事务回滚；提交后再由连接Owner发消息。共享路由及其稳定draw/context factory当前仍由主集成接入，本窗口未改runtime_storage/game_runtime/accounts/serve/gateway。

## 可信组合事务Interface

```python
receipt = inventory.use_pet_toxic_food(
    db, key, pet_id, epoch, request_id, draw, expected_growth_version)
```

调用方拥有当前fenced事务并负责整体commit/rollback；方法不新开连接或内部commit。expected_growth_version为当前成长版本，None仅供Owner读取当前状态执行的原生Adapter。返回冻结FoodReceipt，含模板/真实quality/固定draw/poisoned、历史before/after成长和care、policy及replayed；历史after不能作为当前通知。

新inventory_pet_toxic_food_receipts按role/request_id持久化完整随机事实与结果，fingerprint包含pet/key/期望版本及food/growth/blood/care政策。历史确认允许draw=None（从已付receipt读固定结果）；若调用方另传不同draw则拒绝。旧实例耗尽删除也可读历史。只有低层receipt且无native wrapper时，Adapter仍给True并保持只读，不写补丁。旧未知基础/血脉/care均需明确可信导入，不能猜0。care子凭据以request_id哈希派生固定长度，最长160字符受理ID不会溢出子键。

成长内部damage_base_aptitudes只由同事务食品计划调用：读取并比较完整当前成长，CAS保存profile/state并增加资产版本；血脉字段不写。资质已经全0时不制造虚假成长版本变化，但有效寿命食品仍可增加寿命并保存实际中毒判断。care沿唯一账本increase_lifetime操作保存，没有第二份寿命记录。

## 实际方法与验证

tdd沿已约定Inventory caller transaction/不可变快照/native Adapter Seam：缺draw参数红→正常食用绿；中毒路径未计划红→真实基础写入/资源裁剪绿；随后逐项加入真实故障与历史重试。codebase-design把多资产食品计划与随机receipt集中在pet_lifetime_food，基础写入集中growth store、寿命集中care，Owner只提供受理上下文和来源hook。writing-for-agents按原生/组合事务/历史分支提供Interface与完成条件。

verify_pet_toxic_lifetime及pet-toxic-lifetime-verification.json已通过：32004品质100/draw9999加300；32009品质100/draw299加250且基础1130/1235/960/657/1122→1129/1234/959/656/1121，原decoder读五项与145/145HP；draw300不毒、32009品质0加50。后来伤势/忠诚损失不被已付重试覆盖，旧精华receipt不会恢复旧基础，低层和wrapper已付均在SQL禁止写入下成功；不同已捕获draw冲突拒绝。

真实growth/care/debit/care-child-receipt/food-receipt/wrapper六个保存点abort、外层失败、未知cash和晚期bag溢出均完整回滚，同失败键随后只生效一次。未知/零效果quality、缺/布尔/负/超界draw、旧血脉、signed32寿命溢出、陈旧/布尔期望版本、他人/畸形请求拒绝；最低资质0、HP0不复活、当前血脉先后顺序、保留潜能、实际opaque换租约鲜/历史请求和重开已验证。160字符受理ID真实提交/重放通过，161拒绝；限时技能宠缺时钟回滚整次中毒，补当前c0007后原UI过期空格与原expiry map保持。禁止热路径读文件。

verify_inventory_resource_hook增加真实中毒及根source同步、source CAS后人为失败全回滚、相同命令随后成功、已付True不重抽。另“低层食品已付+根source已同事务付、无wrapper”的重放在SQL禁止INSERT/UPDATE/DELETE时仍通过实际根strict True，人物70/40/resource version0保持。必要成长/血脉/养护/技能保护与到期/绑定、装备资格与六槽存储、当前只读、共同Owner命令、新资源NPC all、任务宠物经验回归通过。

未验证：共享食品稳定draw接线与发布后的原客户端交互、原中毒提示/动画、精确原服下降公式、神兽/仙兽完整资格、还童/进化/蜕变及全量剩余系统。领域验证不等于在线完整可玩验收。
