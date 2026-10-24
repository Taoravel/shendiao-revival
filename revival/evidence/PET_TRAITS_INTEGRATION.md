# 还童前置：悟性与野生／宝宝身份

后续超级候选/保存事务现已实现并离线验证，当前接口、原score/年糕及未验范围见PET_SUPER_RETURN_INTEGRATION.md。本文保留此前字段证据，不再代表超级业务尚无实现。

2026-10-23。本批继续全量恢复，已实现所属存档、冻结快照和原生字段；未执行还童、未改shared、未部署或操作真实客户端。还童资料矩阵见PET_REBIRTH_SOURCE_RESEARCH.md，超级请求/预览布局见pet-rebirth-native.json。完整随机方案、扣丹、预览/确认事务仍继续恢复，不以此前置替代还童功能。

## 纠正旧字段名称

原Pet bean+38经SRefreshPetData raw+40、1135361..1135373写attr1160。原PetSuperReturn通过143d6ab读取1160作为整数；构造绑定143e4cb使用ASCII `PetSuperReturn/Wuxing`，143e513保存dialog+68，显示末端143d72e也使用+68。**这是悟性，不是旧研究误命名的根骨。** 普通PetReturn也将Wuxing绑定+68。research_pet_traits.py执行原codec、刷新赋值、原getter及原绑定literal→member store，不是由字段相邻猜名字。

bean+a8/raw+b0→attr590是另一独立字段，旧cattributedesconfig称躲闪资质，不能替代悟性。12组探针故意把590设987654，悟性分别0/1/73/255/1000/signed32最大，原还童getter始终读1160。本批修正research_pet_blood及血脉交单的rootbone标签；power1140、cap1150和颜色/潜能算术未改。

原Pet bean+b4是i32，raw+bc低字节经11353c9..11353dd写pet+29；143c940将2对应CString2138“宝宝”，1对应2139“野生”。petreturn/petsuperreturn布局经PfsArchive直接读取校验，分别为普通还童与超级保存方案。kind1/2/3分类和野生/宝宝是两件事；其他origin值未知，不作为完整身份接受。

## 存档Interface与来源

Inventory.prepare启动冻结TraitRules并创建inventory_pet_traits。冻结`PetTraits(version,origin,insight)`要求origin严格1/2、insight为非负signed32原整数。该范围只证明编码容量，**不是原生成范围、单位或概率**。原help36028仅证悟性影响升级领悟技能机会，未证原分布或影响成长率。

新本地恢复发宠在现有创建/奖励事务标new_restoration_pet，使用单一政策design/pet-traits-v1.json的宝宝2/悟性0，明确designed基线。旧实例不回填0/2，snapshot/read_pet_state的traits保持None。可信完整旧值经`Inventory.initialize_pet_traits(db,pet_id,origin,insight)`在当前角色fenced事务一次导入，标explicit_known_import，已有不可覆盖；不会补care/growth、回血、改血脉/技能/模板。

PetState新增末尾可选traits，仍是冻结跨Owner消息。现有Inventory当前读取、查询、喂养、技能、NPC恢复、任务宠物XP及野外奖励均经完整dict/vars传递。Pet编码将insight写tail16（bean+38）、origin作为BE32写tail125（bean+b4），没有误写tail113的590或只改i32首字节。

发宠、traits、其他子状态、inventory_revision和奖励回执一起保存，无内部commit/连接/发送或热DDL/文件。旧paid奖励只回历史created IDs，不借重试初始化新字段。权限由当前角色Owner/epoch/FencedConnection持有，客户端没有设置悟性或来源的入口。

## 已验证与剩余

先用真实grant_pet→公开snapshot→原codec/UI读取复现新宝宝默认origin0，再实现明确身份后绿。verify_pet_traits覆盖新宝宝2/0；旧未知None；旧野生1/悟性73一次导入且其余未知成长仍未知；无热读/嵌套连接；bool/范围/未知origin/归属/重复初始化拒绝；traits写入后真实后续发宠失败整体回滚，同奖励重试一次；实际食品SRefresh同时保留宝宝2/悟性0及野生1/悟性73；外层导入失败、opaque当前/过期租约和重开。单纯0无法发现丢字段，因此额外验证非零73。

research_pet_traits的12组原native字段/getter/绑定store、research_pet_blood改正语义后的113组通过。实际source、历史只读消息、战斗养护、完整冻结快照、食品、血脉、技能/到期及NPC/任务XP回归见本批json。没有现场显示或部署声明。

方法：research原包/官方PC及父窗口原指令；tdd沿既有Inventory事务/快照/消息Seam先红后绿；codebase-design集中完整traits和一次导入，既有快照自然传递，不在每个食品/NPC调用方硬编码身份。产物为单一policy、领域模块、native探针、公开验证和本交单。

尚未完成：悟性原抽样/领悟概率、普通还童完整随机重置、超级候选保存/取消/清年糕、完整评分、其他身份/进阶、shared接线/发布/GUI。下一步继续还童状态机；未知数值按DESIGN_AUTHORITY集中补全，不把0基线当原范围，也不以未知score伪造预览。
