# 家族生产设置与维护接入

第十三批实现药品/特产独立开关、明确的新家族空库存基线、族长权限和家族资金扣费，并核对原按钮及面板格式。尚未接真实 NPC/线请求路由、小时产出、库存购买和完整维护，不能据此声称生产已在游戏内可用。

第十四批已另实现normal/simple小时维护、设计库存补满、降级与周期执行，当前状态以[FAMILY_MAINTENANCE_RUNTIME.md](FAMILY_MAINTENANCE_RUNTIME.md)为准。本页后续“未实现小时维护”保留为第十三批验证范围；NPC正式入口、购买、建设升级及完整解散仍未完成。

## 原版依据与设计范围

原 familyproduct.layout 将两行标为二级药品、家族特产，显示新增维护费用、剩余数量和开/关按钮；提示金额50000。原 family.layout 说明正常生产的资金门槛为维护费总和48倍、人气不足1000时维护费增加50%。这两个维护条件本批只保存证据，没有实现自动扣费/降级。

原 cfamilymaintainconfig 五行的 drugconsume 为10000/20000/30000/40000/50000，productconsume 为15000/20000/25000/30000/35000；数值为 client_verified。ProductPanel 直接采用当前等级未缩放原值作报价是 designed，尚未证明原服是否在此报价应用人气倍率。规则只在 OrganizationStore 启动构造时加载，热路径不读配置。

[官方端游家族资料](https://sdxl.wanmei.com/info/newplayer/20to29/20120704/132338.shtml)支持族长管理生产设置，以及关闭一次扣50000家族资金；该历史资料与1.6.1精确一致性未证明。新家族两项关闭/库存0、重复当前状态不收费均明确 designed，政策单一来源为 recovery-baseline.json.organizations.family_production；旧未知不套新建值。

## 冻结 Interface 与所有权

family_products Module 不建连接、不提交、不操作钱包和网络；prepare 只在组织启动迁移运行。family_products 表保存独立开关、当前总库存、revision、origin、recipe。现有 create_family 组织事务中写入新基线，与组织/成员/资金/共同创建凭据一起提交或回滚；initialize 不给历史家族补设置。

`OrganizationStore.family_products_snapshot(identity)` 是可信内部冻结读取，返回 FamilyProducts；不是面向玩家的授权 Interface。`family_products_panel(actor,epoch,identity)` 在同一只读事务检查当前租约、当前家族成员和族长，返回冻结 ProductPanel(state,level,drug_cost,special_cost)。它仍不能代替地图/NPC准入证明。

可信 `OrganizationCommand(..., operation='set_family_products', args=(drug,special))` 通过已有 OrganizationRuntime.command 按该家族所有者执行。只接受一项0/1、另一项-1的原按钮组合，严格整数、拒绝bool；整包重复依现有actor/request_id指纹取旧凭据，改意图拒绝。两项同时改变或全-1语义没有原按钮证据，本批不绑定。

族长资格在组织事务重验。开0→1不收费；关1→0扣50000家族资金并记原组织ledger；当前状态与目标相同不改产品revision、不收费（一般组织命令仍提高组织revision并记录受理凭据）。产品变更先在同一事务执行，再调用既有组织资金扣费；余额不足或晚期ledger/receipt失败整体回滚。不会改角色cash、绑定银、帮派资金或生产库存。

修改政策recipe不会默默迁移已有产品行：不匹配拒绝写入，需显式迁移。旧档没有产品行返回 family_products_unknown。stock字段目前只保存新建0，尚无产出/消费入口；不是已恢复所有药品或特产物品库存。

## 原线格式

原 CFamilyProductsSet type c5607、marshal e450f0，正文为两个BE i32，无NPC Q。原14cc580/14cc600分别发(1,-1)/(0,-1)；14cc670/14cc6f0发(-1,1)/(-1,0)。-1表示保留另一项，不能把它转bool而开启。

原 SFamilyProductsInfo type c5606、marshal e46090，为 `QiiQii`：药品维护费/剩余数/开启值、特产维护费/剩余数/开启值。1490820将两开启值等于1转bool后交148c780/14cc7e0，后者分别填两行费用/余量与开关。family_products_protocol.information 接冻结当前state和可信报价，保留64位费用，不插入family/NPC ID；decode_set严格长度与原按钮组合。

verify_family_products_native 实际执行原四按钮与两种序列化器，只适配网络取得/发送及CRT；结果5组通过。此为离线原x86检查，不是GUI。反汇编保存 family-production-native-disasm.txt。

## 真实入口的接入顺序

实际 family_products_protocol.SET_PRODUCTS 尚未加入 FAMILY_NATIVE_TYPES/SOCIAL_TYPES，也没有修改共享入口/NPC registry。原包没有NPC身份，接入方须先裁定原服务及打开面板的可信上下文：当前角色/租约、完整组织地图归属、NPC/位置/版本/期限与战斗/loading状态。完整组织地址政策见 GUILD_NPC_ACCESS_HANDOFF.md，不能仅按模板准入。

1. 已授权打开面板后，调用 family_products_panel，预编码 information，提交/检查仍有效后由目标连接发送。
2. 收到原按钮包时，服务器恢复当前可信面板/NPC上下文并复验，再解码两flags；家族ID从当前成员关系派生，生成稳定的已受理request_id。
3. 离开角色/地图事务，投递现有组织所有者命令；不持SQL/业务锁等待。完成后重新核当前上下文和族长，用当前panel回包。组织已提交而连接丢包时，新查询恢复当前状态，不能反向猜扣款失败。
4. 小时维护另提供持久批次/时钟、产出配方与上下线观测；必须覆盖不重复收费/产出、离线补算、正常/简易维护、低人气倍率、升级/降级和解散跨组织/任务交接，不能靠本开关接口冒充完成。

## 验证与余项

verify_family_products 七组通过：显式新建与未知旧档；独立开/关及家族资金单扣/当前状态无费；族长/成员/租约/输入与幂等冲突；余额不足和晚ledger故障原子回滚；原等级报价/格式；重启及替换租约；实际有界组织运行时两项关闭竞争最后50000，恰一项提交。没有把测试写入资金余额当作真实收入。

必要回归：家族/帮派资金11组、家族加密管理9组、组织运行11组、家族真实临时TCP6组、组织领域16组、研究启动3组、修炼丹7组、修炼NPC5组通过。均为临时数据库/模拟或本地临时端口，未改真实服和真人数据。哈希与报告见 family-products-batch.json。

方法：codebase-design 复用现有组织事务/所有者与资金ledger，小 Module 隐藏产品状态；tdd 依公开存储Seam逐条先红后绿（缺新建读模型、缺设置操作、缺族长当前面板）；writing-for-agents 将原证据/设计、接线与完成标准共置。原按钮/格式验证与补充回归不声称全部曾红，没有声称Standards/Spec双轴审查。

完整家族发展仍未完成：小时人气公式/维护结算/库存生成与购买、银箱建设、自动升降级与解散、原服务注册与场景准入、资源/任务/帮派代次协作和GUI。全量社交goal继续active。
