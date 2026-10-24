# 普通六槽人物投影v2接线

2026-10-23，根数值窗口。启动选择普通六槽policy、保存1240基线、组合普通人物属性或迁移装备规则前读本文；来源先读ORDINARY_EQUIPMENT_ATTRIBUTE_RESEARCH、ORDINARY_EQUIPMENT_ELIGIBILITY_AUDIT与ROLE_RESOURCE_STORAGE_INTEGRATION。政策单一来源design/role-equipment-v2.json。本文交纯计算及实际调用方事务验证，**当前默认v1、共享角色policy选择、新建授权与现场发布未改变**。

## 模板与可信实例范围

原1038六槽非神兵中973有非空已知flat基础项；64缺列表、1件49192带percentid102仍不恢复此公式。973中212有非零suiting，原套装语义及公式未闭合，当前v2最终投影明确拒绝，保留原元数据；761条无该待恢复元数据也仍须满足角色、等级及可信实例资格。不能将973或761写成全部角色已经可穿、全部属性已恢复或当前运行已开放。

六槽为武器0、护腕1、项链2、衣服3、腰带4、鞋5。每件ItemState属于当前角色、数量1、装备槽不重复，原背包记账slot=-equipment_slot-1；读取自同事务Inventory的冻结快照。EquipmentDetail需已初始化的可信clean origin及已知版本，identified1/prefix_quality1/score0、原有效基础map完全一致、无食品quality，EquipmentCondition已知且color1。纯DTO不自行证明持久origin，调用方不能拿模板给未知旧实例补一份干净详情。

武器roleNeed为空不限，非空是原ID的OR；49197的20/21原样保留，现十形象无法匹配，不裁剪为1..10。非武器原穿戴分派不检查roleNeed，本批这些模板原列表也为空。sexNeed0不限，其余等于原shape导出sex：末位1..5→1，0/6..9→2；30形象逐个核对。level门槛用原needLevel，采用当前Inventory相同的服务端恢复政策，不能把item.level拿来代替；其原服检查证据边界见资格审计。

模板flat值及numid映射为client_verified，服务器以裸身+实际装备平加、耐久0不贡献及窄clean范围仍为designed。护腕1241映射独立1240，不是已有1230；两项裸身基线都需明确。新恢复角色0/0及成长不加是设计值；旧角色缺1240保持None/拒绝，不从构造默认值推0。原研究三组示例误抄已由root独立CRC/BXML纠正并保存ordinary-equipment-example-correction.json，运行表未改。

## 当前公开Interface

`load_ordinary_equipment_attribute_rules()`只在启动明确加载v2，包含原slot、needLevel、sexNeed、roleNeed、suiting和原flat配对；其templates保留973条，投影阶段拒绝212套装待恢复条目。默认`load_equipment_attribute_rules()`继续只取v1十件师承。

`EquipmentAttributeBasis(..., seal_resistance=known_value)`新增可选字段，None在v1仍表示未定义1240，不改变v1普通20map；v2必须给出已知值。v1带非None1240、v2带None均拒绝混用。持久JSON旧记录缺字段会解析为None，不构造新基线或修改旧记录。

`project_equipment_totals(naked_attributes, actual_inventory_snapshot, basis, rules)`沿原Interface计算九项总属性、1230及已知1240；来源仍携带当前成长、基线、装备政策和inventory revision，不增加第二份HP/MP。旧`project_equipment`混合裸身/vitals包装拒绝v2，避免先套裸身资源上限。v2经resource_caps_from_projection→装备/成长原因计划→apply_resource_transition后，使用combine_equipment_resources或current_resource_profile严格同source/caps组合。

`EquipmentTotals`及`EquipmentRoleSnapshot`新增seal_resistance=None。非None时growth_refresh发送21项普通map，role_detail_profile填RoleDetail index15，role_detail_equipment_fields额外返回(15,current_resistance)。最终所有v2数值遵循signed32、精确float32；HP/MP上限始终与最终资源一致。v1的None继续20项及原三条equipment entry覆盖。

资源变更顺序、完整before、当前租约、领域重试、晚期编码及外层提交规则全部复用ROLE_RESOURCE_STORAGE_INTEGRATION。依旧按角色所有者和有界I/O执行，不新增世界锁或全服队列。角色同一笔事务有六次独立穿戴时，每个实际数值上限变化各推进一次资源version；只改来源不虚增，不能用一个固定“每套+1”覆盖六次明确领域过渡。

## 实际验证

- verify_ordinary_equipment_projection：缺v2 loader红→聚合/原21map接线后绿；用原负slot记账后再次捕捉v1硬编码-1红，修正各槽后绿。六件原49001/42000/43000/44000/45000/46000给caps120/110、攻45/防55/命中60/闪30/速14/内攻35/内防15、封印8/抗性6。已知70/40穿戴不治疗；119/109脱至100/100，穿回仍100/100；同装备原120XP成长后80/130HP46/116MP。已知抗性11→17、未知None拒绝；性别/level/20或21、套装/百分比/空列表/高级实例及不精确数值拒绝。
- 原x86普通map编解码器接21项，原SEnterWorld解码器实际确认70/120/120/40/110和攻防、封印及outer+8c/index15=6。没有执行真实游戏画面。
- verify_ordinary_equipment_storage：临时库显式注入v2及已知basis，实际Inventory授予/穿戴六槽、负slot、当前source与唯一资源同txn。先真实编码后人为末端失败全回滚，同批原装备/资源request身份随后成功一次；另真实native signed16五维溢出使六件穿戴、caps、source、版本共同回滚。正常70/40+caps120/110经历三次实际数值caps变化为version3；真实120XP成长L2/31/free5后80/130HP46/116MP/version4；旧装备receipt不覆盖后来成长，新lease读回严格相同profile。
- 必要v1兼容verify_role_equipment及NPC新资源客栈通过，保留旧20map和其真实late float32编码失败回滚，未为v2提前改变v1编码时点。

## 后续完成条件

1. 共享启动保留v1/v2冻结规则并按角色存储basis及显式创建来源选择，或提供可信显式升级事务；不能全局换loader使已有v1基线登录失败，也不能给已有来源凭空补1240=0。当前root未交这种升级/选择开关，测试中的store赋值只是临时库显式注入。
2. 实际Inventory穿戴还须采用确证sexNeed门禁，可信详情/耐久来源及全部新profile资产、修理消费者同事务已接后，再验六槽Owner穿脱/药品/客栈/成长/损坏修理/重连与原编码失败回滚。现Inventory._equip尚未内查sex；当前最终v2投影虽会在外层事务拒绝，也不能据此宣称所有独立穿戴入口已补。
3. 新建0/0基线须绑定新的显式装备policy及创建凭据，不能将原v1记录的None解释为已知0。六槽物品获取、实例生成、套装、prefix/score、强化宝石及百分比独立恢复，不由本次基础投影补发装备。

方法：research后台重读原包、实际穿戴/性别/roleNeed消费者及官方端游来源；codebase-design沿已有纯投影/调用方事务Seam扩展，计算不造vitals或重复存储；tdd以真实六槽→最终原编码纵切红后绿，后续在公共Interface核对必要guard与实际回滚；writing-for-agents共置Interface前提、数值出处和后续激活判据。未部署、未改真实角色、未启动GUI或实际战斗；商业数据库与容量仍未验证。
