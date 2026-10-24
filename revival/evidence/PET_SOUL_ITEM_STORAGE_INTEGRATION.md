# 背包元魂珠实例来源存档

本批是可选完整实例来源与当前详情候选，未开放穿戴/摘除/融合请求。原生四字段证据沿用 `PET_SOUL_ITEM_SOURCE_RESEARCH.md`；数值和来源约束单一登记在 `design/pet-soul-items-v1.json`，验证与审查见 `pet-soul-item-storage-batch.json`。全量目标仍为 active；上一目标回合有实际代码、原码和事务证据，为 progress。

## Interface 与来源

启动时加载 `OrbRules.load()`，在 Inventory 之后统一 `prepare(db)`。它验证原28珠的type145、maxNum1、needLevel1、level0、outbattleuse2，复用已冻结元魂规则。角色路径不读取配置或建表，不连接、提交、发送，也不增加生命/真气存档。

`OrbSource` 必须完整提供角色、实例key、原模板、版本、政策、稳定来源标识、四字段 `OrbTips`、完整uint32非绑定旗标及 `retained_raw6`。基础绑定位仍来自实际 ItemState.binding，nonbinding_flags 的bit0必须为0，不由显示标志补全其他位。flags160也能作为已知受限来源保存，但**保存不是操作授权**；后续控制器必须按独立准入策略处理限制，不能因为有记录就放行。

`retained_raw6` 是已知穿戴历史中的精确signed32原值，包含负数，独立于四字段和基础绑定位。显式 None 表示可信调用方明确提供的“没有该穿戴历史”，不是未知历史的默认值，也不是原raw6=0。此批不提供四→六逆工厂；缺少旧资料仍不导入，不能从客户端请求、raw6非零显示或bagbit0猜值。未知新实例如何构造穿戴第六项，留给独立、标明设计来源的动作策略。

每份记录归有效 role_id+login_epoch 的角色所有者。同调用方事务里 `initialize(...,'explicit_known_orb_instance')` 仅收版本0的完整可信来源，原实际物品必须是当前自有、背包中的单个原元魂珠，quality/condition/detail均为None，不能迁就历史未知品质或堆叠。缺记录 `read` 返回None，`tip_message`拒绝，不静默建零字段。重复同一明确导入严格只读返回当前版本，不能重置或重建原初字段。

## 变更与失败

`read` 返回包含当前完整ItemState、库存版本、原始来源和基线字节的冻结 `OrbBasis`。`replace_source` 只作可信所属领域的新鲜完整来源CAS：当前basis逐项相等、源版本+1、同角色/key/template/policy/source_ref，原flags及retained_raw6保持精确不变。更新来源和真实库存版本同事务；它不扣物、返还、收费或写paid凭据。

任何其他 Inventory 写者更新template/role/quantity/binding/quality或删除物品，触发来源失效；即使绑定0→1→0也不会重新变成已知来源。槽移动不删来源，但新库存版本/完整ItemState令旧basis失效。未来资产交换控制器须验证材料与原来源，并为自己的已知结果在同事务确立新的完整来源，不把普通奖励或未知物品合并当作历史证明。

`tip_message` 从同事务当前已知实例重读四字段，产生原column1 SItemTips。调用方必须先把此元魂资产变化、独立幂等凭据及当前人物唯一资源来源hook合并，再在提交前完成原生编码；异常回滚整笔事务。paid命令由所属领域验证历史凭据后跳过CAS，只读当前。连接所有者在提交成功后投递冻结逻辑消息；共享启动/路由和所有物品消费者切换前，不能自动采用本政策。

## 实际方法与验证

TDD 沿已授权公开调用方角色事务和原生详情Seam进行，实际缺少存档Module红灯后实现。临时真实AccountStore/Inventory验证：原四字段与独立flags160、历史raw6=-2重开保真；未知None不补零；明确无历史None与整数0区分；当前tips正确；重复初始化在SQL禁止写入下通过；源和库存版本两处SQL故障及完成编码后的调用方异常全回滚；旧before/旧租约拒绝；原值不可被0/1显示结果覆盖；绑定ABA明确原始故障模型使旧来源永久失效。布尔伪造basis/物品字段拒绝。

codebase-design 把当前来源、单实例资格、JSON来源CAS与原生详情组合藏在一个Interface里，复用原ItemState与OrbTips，不扩充共享Inventory。writing-for-agents 将明确导入、新鲜CAS、paid和编码失败条件同接口并置。code-review 对固定文件清单按Standards/Spec独立复核；本工作区无Git/tracker，沿用既有固定字节证明，不制造提交或issue。

未验证：真实角色迁移、元魂资产往返和新穿戴raw6策略、材料/旗标/品质完整生成渠道、战斗锁/技能权限/空槽选择、穿戴/38045摘除/融合费用/幂等控制器、元魂与宠物最终属性/成长/还童/释放联动、全部共享消费者和原生bagflags切换、加密投递/发布/GUI/容量。原鉴定3与合成4封签文件及此前23生产文件保持不变，没有操作真实库或当前服务。
