# 普通NPC绑银购买接线

接mode1或修改普通商店费用/绑定/重放时读本文及主策划[NPC_SHOP_BOUND_PAYMENT_DECISION.md](NPC_SHOP_BOUND_PAYMENT_DECISION.md)。配方唯一来源design/npc-shop-payments-v1.json；原按钮及20项原指令依据见NPC_SHOP_MODES_NATIVE_RESEARCH。来源、当前工作区、固定发布与GUI分别验收。

## 当前实现位置

本功能首次由唯一集成窗口部署到固定发布npc-bound-shop-20261023T115742Z/PID39796，现由治疗发布npc-role-healing-20261023T125539Z/PID36632继承。首次发布中的npc_gameplay.py SHA256为e5d70e181a18dd13ff29ed0c9302bb65f980e8b498160c5eb8a444a15d344bfa；该值指首次固定发布，治疗增量另审另验。当前监听以runtime/deployment.json为准。

真实Peer先复现mode1未受理红例，再使用原GameRuntime/RoleOwner/ConnectionOwner与连续RC4/原MPPC验证实现；未替换dispatcher。正式源码两新脚本及旧现金回归全部通过。NPC窗口另独立比较44084 BASE与固定候选，恰四个输入改变且无删除，详见npc-bound-shop-candidate-audit.json。集成方完成一致性备份、停止44084和启动39796；NPC与root独立复核1427个启动输入哈希、601 Challenge/合法心跳、quick_check及107张既有表逐行不变，证据npc-bound-shop-deployment-verification.json和npc-bound-shop-root-verification.json。后续源码改动不会进入此固定进程。

## 行为与兼容

npc_shop_payments启动加载冻结两个ShopPayment。mode0仍cash/npc_shop/binding0；mode1只bound_silver/npc_shop_bound/binding1。Purchase新增默认mode0；decode_purchase保留原三值返回Interface，plan读取原第四字段并加入冻结意图，无需改共享取NPCkey方式。原service2许可、货架与正价检查继续生效，没有新NPC绑定或零价兜底。

NPC外层租约事务仍同时执行钱包、Inventory真实实例工厂、领域与通用凭据、原资源source同步和最终回包编码。bound物品仅按Inventory既有元数据合并，不进入非绑定堆叠。回包读取当前背包和当前绑银绝对余额，现金随原背包读当前值；没有混付、自动换币或旧钱包隐式初始化。

mode0保留原五元组fingerprint的序列化字节，政策总版本不变。mode1额外纳入mode/currency/binding/payment policy，跨mode或payment policy冲突拒绝。可信同受理键重试一次，新收到的相同线包有新受理身份；晚期失败不消耗该键。

## 验证与后续

verify_npc_bound_shop_runtime的隔离候选结果：两份原32000共300绑银、现金1000保留，绑定/非绑定分别堆叠；受理重试、跨mode冲突、当前250而非历史400余额回包、相同新线包各次购买、绑银不足不改扣cash、特殊mode拒绝、重连与未知旧钱包拒绝通过。

verify_npc_bound_shop_sources：真实source CAS与原生projection后注入晚错，钱包/物品/source和四类凭据整体回滚，同失败键再成功；HP70/MP40/version0保留。真实满包及已满绑定堆叠触发支付后的Inventory失败，全部回滚。另直接执行已部署npc-20261023T102110Z的旧purchase，在同库产生真实mode0已付凭据，再由候选重放无变化；改变payment policy只使mode1旧凭据冲突，mode0继续兼容。未以手算同一哈希冒充历史兼容。

旧verify_npc_shop_runtime通过，明确不支持的模式用2作对照，仍验证现金费用、重试、满包回滚和重连。两轴审查固定快照在reviews/npc-bound-shop-20261023；最终Standards硬违规0/判断问题0，Spec缺失0/额外范围0/错误实现0；两轴独立复跑冻结候选验证及字节哈希一致。root另独立复跑两新脚本全绿，证据evidence/root-bound-shop。

方法：tdd先真实wire红例再实现一个购买纵切；codebase-design把付款规则启动冻结、保留既有共享Interface与单事务；code-review独立Standards/Spec；writing-for-agents将当前状态和历史证据分开。历史mode0兼容脚本从ROOT/revival定位原固定发布，硬验其ea920…SHA256，适应新固定runner的OUT/source；不在验证时动态造旧receipt算法。发布由唯一集成方执行，NPC窗口独立验收，未操作真人角色。全NPC目标继续；零价货架、特殊商店/货币、治疗/特殊修理、完整动态触发及GUI仍单列未完成。
