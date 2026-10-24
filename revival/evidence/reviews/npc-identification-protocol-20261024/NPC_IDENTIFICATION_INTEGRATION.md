# NPC装备鉴定：模型与接线边界

2026-10-24。恢复495状态查询及后续实际鉴定前读取本文和NPC_IDENTIFICATION_NATIVE_RESEARCH.md。原协议/界面证据不等于NPC关联、付费配方或鉴定结果已恢复；生产registry和共享入口本批未开放495。

## 当前装备模型能证明什么

当前equipment_detail.py的EquipmentDetail仅表示identified(0/1)、prefix_quality、score和唯一ID的base_properties tuple；条件/颜色在独立EquipmentCondition，绑定/数量/所在栏在ItemState。None仍是未知详情，不能用0冒充已知未鉴定。完整高级容器在当前干净编码器中明确为空；未知旧宝石、强化、附加效果不能被这份模型可靠揭示或自动置零。

实际DetailRules.load的1038模板工厂全部初始identified1、prefix1、score0，并保存原模板base_properties；这证明新工厂不会自己产生未鉴定装备，不能推定已有角色未鉴定存量为零。可信initialize_equipment_detail允许初始化明确已知干净实例，禁止覆盖已有详情；构造器允许identified0，因此显式迁移可能保存已知未鉴定实例。NPC窗口没有读取真实玩家库存，当前存量需资产Owner另按权威库存核实。

可交root裁定的最小可靠范围是：已经持久保存且明确来源为干净模型的实例，其已知品质/评分/原属性/条件均保持，只展示当前已知identified状态。是否允许将0变1、收费及原结果配方需正式政策；本批不以显示flag推导原服随机属性，也不重铸任何字段。现role_equipment明确拒identified!=1及与允许模板不符的属性；放开鉴定不能绕过该限制。

Inventory.immutable_snapshot_transaction(db)在同一当前租约事务返回冻结InventorySnapshot及inventory_revision，包含当前自有ItemState/detail/condition。后续495只读查询应由RoleOwner先重证当前NPC，再在该事务验证角色/租约、目标实例真实在column1（现背包对应equipment_slot is None）、期望inventory_revision及已知详情；未知、他人、仓库、已穿实例不能以默认状态应答。版本围栏、数量预算和允许NPC关联按正式policy/可信调用方约束，当前没有网络路由或资产修改。

本批模型实查原字节SHA与数量见npc-identification-domain-source-audit.json，范围是当前启动模型和原费用目录，不是存档迁移或真人库存审计。

## 原费用已证与未证

原cnpcidentifyneedmoneyconfig精确键为1、10、20、30、40、50、60、70、80、90、100、110、120、130、140、150。原getter到精确lookup及record+4读取已由研究执行；level51缺行实际拒绝，未发现向下取整到50的这条路径。选择fixture中的wrapper+0x28并未闭合到真实CItemAttr.needLevel/equiplevel复制，因此不能把这些键自行命名为真实装备需求等级或更改物品元数据。特殊完整kind的bean+d0分支也未授业务资格。费用、货币、鉴定结果和绑定由root在原源/攻略核对后集中裁定。

## 已实现的纯协议Interface

npc_identification_protocol.py仅表达原wire：decode_identification_query(body,*,max_items)返回冻结item_keys有序tuple、完整64位NPCkey及mode；encode_identification_states(npc_key,states,mode,*,max_items)保留有序(key,state)vector；decode_identification_request(body)保留三个signed32，字段为item_key/auxiliary_argument/mode。NPC确认实填(item_key,0,1)，原包没有NPCkey、column或报价。第二字段的通用业务含义未命名，不把另一路mode2赋予NPC。

max_items由调用方显式给，协议Module不选择服务预算。查询wire保留负数/重复等原codec值，业务仍须验证；回复原codec要求key>0而不限制state/mode枚举，Module保持该契约。实际状态查询只能发送已知0/1，不从宽泛wire值推实际装备权限。请求/回复向量不是map，不能自动排序或去重。原三个缺入口红例保留，六组协议检查含原decode→同对象marshal独立oracle、空/127/128元素、64位高位及signed边界、截断/多余/预算和冻结/无I/O。

原NPC10890装备鉴定师和1007原摆放是client_verified，NPC→495关联仍unknown；540是买符父菜单，不当鉴定授权。协议绿不开放服务、不给可信来源能力、不扣款或更新详情；后续实际状态查询、付费结算、完整刷新、共享Peer、发布与GUI分别验收。

方法：research沿原映像/原PFS与当前持久模型分别取证，限制fixture外推；tdd先缺协议入口再逐公开Interface转绿；codebase-design把wire保真、NPC证明及资产权威分开；writing-for-agents把可用字段、未知来源与下一步完成条件共置。未操作真人库、客户端或服务进程。
