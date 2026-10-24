# 五种年糕：实际服用与共享入口验收

年糕与灵石交叉前读[PET_STONES_INTEGRATION](PET_STONES_INTEGRATION.md)：预测现传独立石头五维，BASE写入/历史保持，实际最终资质先血脉后石头。

2026-10-24。31268–31272已恢复原预测、确认请求、所属事务、实际共享分流与加密Owner链路；未发布到运行服，未做原客户端GUI。全量目标保持active。较早PET_CAKE_SOURCE_RESEARCH的未知项以本批已验证范围更新，原调查保留为历史证据。

## 当前接线

1. 启动Inventory.prepare冻结EffectRules，并创建年糕审计表及(role,pet,item)索引。旧四字段审计表只从完整历史receipt补索引，不依据当前/已删物品猜身份。未知旧宠物count/history仍要求明确导入；本次迁移不初始化宠物资产。verify_pet_cake_consumables已用真实已付记录和耗尽实例验证启动升级、历史正文不变及paid可用。
2. 原CUseItem布局为BE32实例key、BE32目标种类1、BE64宠物key。客户端10a6330本地预测/145134确认，10892f0确认后才发请求，没有另造服务器预览。实际runtime_storage.receive_inventory沿用原受理ID/共同凭据及source precommit，所属Inventory.receive在现有事务内分流已知五种年糕；共享文件未改。
3. 内部cake-current:pet:成长写前version:item只标识一次资产事实；外层稳定受理ID继续承担请求去重。新受理的相同线包使用当前新version，已付受理直接走共同当前回复。不得把二者合并、按线包内容去重或从客户端取随机数。
4. 调用方已有事务时使用inv.use_pet_cake(db,item_key,pet_id,epoch,request_id,expected_version=None)；独立可信Adapter为receive_pet_consumable(body,epoch,request_id,...,precommit=...)。CakeReceipt为历史确认；paid不写回历史before/after。成长BASE、年糕count/history、扣一件、版本、领域凭据、共同凭据及root source在同一事务成功或回滚，提交前完成回复编码。
5. 新/paid回复携带仍有效时限技能时，年糕路径提供服务器Unix毫秒。共同入口传入的monotonic计时不能作为原SGametime。已耗尽物品通过审计索引识别年糕历史，仍回当前时钟/宠物/背包；不重复发送成功提示，也不重建物品。当前普通/超级/显式消耗的已放生paid移除消息统一为原column1+pet双BE32。

## 来源与实现选择

`client_verified`：完整原1137870包含真实宠物列表查找、原CPetAttr、112c090/11297d0普通血脉以及浮点取整，37,920例与纯预测一致（158模板×16血脉×min/mid/max×5道具）。原PFS四表重读/CRC/解码/全行比对和地址记录见pet-cake-effect-native.json。1930是灵石次数，1540才是年糕次数；1940–1980是五项灵石额外资质。此批原生预测的完整矩阵使用灵石附加0、1760/进化高级修正0。

原公式：去灵石额外资质，反推血脉前资质→按原min/max算百分比区间→cpetcake[区间+1].percentage/10000乘资质跨度并截断，得到BASE增加量→再投影血脉。ratio是资质区间，不是次数；percentage不是成功概率。预测函数未发现随机抽样。总count20先拒绝145133，kind2拒绝145139，已有上限145137；原有效增长≤0对应145136。原helper未复制超级的野生禁令。

`designed`：服务器确定性应用原预测BASE增量一次；既有pet-blood-v1的有理数投影继续作唯一有效资质权威，保持绝对HP/MP、死亡、XP/加点/技能/traits/care/flags和血脉。count与BASE增量审计各记一次，currentProfile已含年糕，不再二次加审计数值。选中参战flag不等于正在战斗；实际战斗Owner准入仍须集成方保证。

原浮点预测与现有有理血脉在本次矩阵有30处相差1；不是宣称所有可能输入只有30处。明确算例500004、血脉2、速度基础1192/有效1197：原预计+8且BASE步长8，新BASE1200；现有权威有效1206，实际+9。receipt同时记预计8/实际9，145135告知实际9；不悄悄改旧血脉policy或另存第二套有效资质。

原SSendMsgNotify 0xc1775为两个BE32(messageID,原构造额外0)+UTF16 Octets向量。成功145135参数为原属性名、实际增加、剩余20-count；145136参数为原年糕名，其他三拒绝消息无参数。research_pet_cake_protocol执行3组原确认构造/codec及6组原通知decode→实际非空向量remarshal。extra0只记录原构造值，不推业务语义。

所有业务无效均不扣件、不增次数、不写成功凭据。超级旧候选的BASE/cake来源被年糕改变，保存拒绝过期候选；重新生成并保存会真正替换旧BASE/清年糕，释放20次容量。普通还童的清除和保留沿用其单独政策。

## 验证与边界

- verify_pet_cake_consumables：五种、总20、无效/上限/kind2、仙兽/野生、BASE与血脉、死亡与binding保留、超级候选失效/保存清除；五个真实写入点、调用方/原生编码失败全回滚；SQL只读paid、未知旧状态/跨角色/过期版本/旧租约拒绝、重开及旧审计schema升级。
- verify_pet_cake_shared_gate：实际共享dispatcher、共同受理去重与时限技能新/paid服务器时钟；没有shim。
- verify_pet_cake_runtime：真实RC4/MPPC输入→RoleOwner→共享事务→原生通知；同内容新受理继续消费、旧ID只读当前；实际共同receipt故障及晚期时钟编码失败全回滚且同失败ID可重试；最后一件删除、时限技能paid、后来死亡、重登、旧Owner拒绝、后来pending source不修复。人物HP10/MP20/version0始终不变。
- verify_inventory_resource_hook：实际root source同步与CAS后故障、fresh/paid只读契约，并保留其他原消费者回归。其余回归及文件哈希在pet-cake-consumables-batch.json登记。

方法：TDD沿既有Inventory事务/原生消息/实际共享受理Seam逐条从红到绿；codebase-design把预测、BASE计划和审计隐藏于EffectRules/use，既有Owner/事务维持单一权威；research用完整原消费者和PFS数据作独立预期；writing-for-agents将当前接线与完成条件集中在本文，历史索引只给指针。

未验范围：运行服发布、原GUI实际确认/提示/数量与重登；实际战斗期间准入；非零灵石、进化/1760高级资质与完整评分；普通/超级、技能和中毒食品所需稳定draw共享接线；商业数据库/容量。下批推进进化、灵石及宠装和其余装备道具；本批通过不等于全量完成。
