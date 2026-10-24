# 普通宝石合成：角色事务交付

接普通CCombineGem、体力450、杂学600005或恢复已付结果前读本文。2026-10-24，本批只新增独立Module与政策，原鉴定ready的inventory.py、equipment_detail.py、currency-v1.json保持固定；共享入口、真实角色和发布由主集成负责。

## 来源与范围

先读`GEM_COMPOSITION_RESOURCE_SOURCE.md`：它纠正旧`EQUIPMENT_GEMS_SOURCE_RESEARCH.md`的602053换算错误，**实际杂学600005=0x927c5**。原体力450/630与客栈活力440/620是并列资源，不能调用role_vigor扣合成费用。杂学属于class4/zaxue，任务首技能100008所属class6/other-skills不能为此提供基线。

原请求c0424是精确8字节BE32实例key1/key2；同key需至少两颗。原普通未培养210模板、14族×1..15级，下一模板取原genegemid；15级拒绝。排除培养、天珠、剑魂和熔炼；不据名字相似或存在cgemeffect行扩权。

唯一执行政策`design/equipment-gem-composition-v1.json`采用原显示概率与费用：成功率min(100,原宝石successrate+当前杂学等级0..6对应加成)；体力5×(原料等级+6)。本地服务器采用显示值作为概率、两种结果均扣全额体力、失败扣第二原料一颗且第一保留、成功任一绑定则输出绑定，均为**designed**。原两同类同级合成/失败损一颗来自客户端和PC官方；原服RNG、哪颗损失、具体扣体力时点未证实。现金不扣。

## 启动与明确来源

1. Inventory表结构准备好后，启动迁移阶段同库调用`equipment_gem_composition.prepare(db)`及`role_stamina.prepare(db)`，保存不可变rules。前者同时安装归属本Module的原料来源失效触发器。命令热路径不建表、不加载配置、不连接、不commit、不发送。
2. 体力由新`role_stamina_profiles`唯一保存，`initialize(...,value,maximum,'explicit_known_stamina')`仅供可信完整迁移。当前值/上限0..2^24且maximum>0；每次消费version CAS。缺旧档保持未知；没有自动新角100、等级推上限、登录补满、离线或在线恢复。现有vigor不变。原恢复显示floor(max/100)+2的时间接线另批。
3. 普通宝石原额外flags尚无通用Inventory权威。`initialize_material(...,key,nonbinding_flags,'explicit_known_gem_instance')`显式持久导入当前模板/数量/绑定/quality来源。binding只取ItemState.binding，不在额外flags重复保存；0xa0原拒绝，其余尚未支持的非绑定位也拒绝。只支持quality=None。Module所属触发器在通用写入者更新数量/模板/绑定/quality或删除实例时立即删除旧来源；即使外部扣后补回原数量，来源也保持失效。纯slot移动保留来源，但旧受理仍因库存revision失效。合成只为已验证的本次剩料和产物同事务恢复来源；接通用奖励、拆分、整理的完整flags写入者仍须提供可信迁移，不能默认为flags0。
4. 调用方提供可信**同db、当前租约、只读**`study_source(db,inventory)->CompositionStudy(role_id,epoch,policy,version,level,skill_id=600005,namespace='zaxue')`。缺失/部分/错误namespace拒绝，明确未学0合法。本批测试用真实临时SQLite技能fixture，不宣称已有生产杂学ledger；禁止从任务other-skill ledger推600005。生产技能所有者需给完整来源的公开Adapter。

## 受理、执行与保存

角色所有者在当前租约事务调用`admit(db,inventory,rules,stamina_rules,server_request_id,payload,captured_draw,study_source)`。只读取并固定完整两ItemState、flags来源、库存版本、杂学policy/version/level和体力版本/余额/上限。draw是可信受理时固定的0..9999整数，成功条件draw<成功百分比×100；客户端不能提供draw或request_id。

保留同一不可变CompositionCommand供重试。实际执行调用`apply(...,command,study_source=reader,precommit=root_hook)`，fresh逐项复核原基线；原料、产物、体力、通用资产凭据、专用合成凭据及root唯一资源source更新同一事务。合成自身不另建HP/MP源，不修改装备详情或角色装备policy。

root_hook沿既有`(db,inventory,current_snapshot,*,replayed)`同步契约接当前唯一资源来源，实际生产必须接；低层Module允许None仅供独立资产消费方自行在外层同步。异步回调会明确拒绝且关闭未等待协程。调用方还负责所有者队列/期限、连接与战斗准入、取消/断线以及提交后的有界逻辑投递；raw请求无重试ID，新的相同线包是新操作，不能按payload永久去重。

只有所有领域/source及当前原生背包、装备栏、450/630绝对值编码均成功后，调用方才commit一次并投递返回messages。任何异常必须回滚整个外层事务，不能捕获错误后继续提交已扣体力/原料。产物复用现有真实grant堆叠规则；可能归并的目标非满堆也须明确已知flags0，未知目标拒绝。满背包且扣料后没有足够产出空间时整笔失败。

## 已付与完成条件

两种凭据必须同时存在且fingerprint/完整计划一致；孤立/冲突凭据拒绝，不修补、不二次扣款、不重新抽样。paid允许新当前epoch读取历史命令，跳过旧材料和技能基线，读取**当前**背包与体力；后来数量变化/技能学习/体力变化不会回放旧快照。root_hook必须走replayed=True严格当前只读分支。过期inventory对象仍拒绝。

本片完成条件：原14族/边界概率/体力/绑定与同堆规则；完整原请求与450/630 codec/赋值；同事务真实材料、体力、九处SQL故障、source更新后故障和当前编码失败回滚；失败第二颗保留规则；未知/过期来源/旧租约/满包/未知产物堆拒绝；已付在后来变化及重登后SQL authorizer禁止DML仍返回当前；鉴定三生产SHA保持。具体执行结果和固定双轴审查见本批batch/ready，不以本页自行证明通过。

未验范围：生产杂学ledger及学习、体力自动恢复/真实基线迁移、共享可信RNG受理与加密投递/正式发布/真实GUI，宝石镶嵌摘除、完整评分/属性/战斗。本片不是全量恢复完成；这些仍在持续目标内。

方法：TDD在已沿用授权的纯规则、角色调用方事务、原协议与root来源接缝逐个red→green；codebase-design把合成计划/原料元数据/幂等和体力权威集中为小Interface，现有实际资产grant与root source沿已有Seam复用；research实际纠正资源及技能键；writing-for-agents按启动→fresh→paid共置接线和拒绝/完成条件；code-review使用本项目既有非Git固定清单适配、独立Standards与Spec两轴。没有虚构Git提交或tracker。
