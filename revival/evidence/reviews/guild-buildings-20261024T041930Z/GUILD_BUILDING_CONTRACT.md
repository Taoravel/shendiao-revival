# 帮派建筑状态、建设选择与进度

读取条件：整合建筑Module、采用building_policy、接建设任务完成或注册原建设NPC前。第24批在全量社交目标内恢复建筑事务和当前原生查询；此批不完成整个帮派发展、任务玩法或正式激活。

## 原依据与采用范围

GUILD_BUILDING_MAINTENANCE_SOURCES.md提供包内与官方机制。新核原SRequestFactionBuildData 0xc5628，marshal0xe92d80发selected i32和list；FactionBuildInfo 0xe92c70依次发类型/等级/建设度三个i32。完整Process0x1495020把类型0..2映射manager+338/+33c起的三对缓存，selected写+334；原UI名查找0x14aa1b0分别取cstringres819/820/821，绑定聚义厅/工坊所/练功房。

client_verified：原0x1486d70建设需求为(level+2)×50；0x1486d00资金为(level+5)×[100000,300000,400000]；0x1486d50人气200。三者level>=20的原分支返回0。离线执行15组类型/等级矩阵、完整原消息/缓存、三个原数值控件读取片段及独立layout列，核实各值用途；这不证明原服绝对上限。实现只支持显式政策采用的0..20已核计算范围。

原CRequestFactionBuildData 0xc5627为空body，原管理菜单检查帮主或副帮主mask32/bit5。服务端查询复核当前租约、guild/family-member双代次及同一bit5；building_data只给当前管理者。CChooseBuildConstruct 0xc5631为Q+i32，原选择按钮保留dialog+20/+24上下文和行+c0的0..2类型。纯decode_choice保留完整Q，不把解码当NPC授权；该收费选择包未注册到通用线包路由。

## 新建状态与设计

building_policy默认None。只有真实新建帮派并显式提供versioned政策才创建三建筑等级/进度、人气、selected=-1、generation=0和recipe指纹；旧帮派读档不补初始值。缺行、畸形进度或指纹变化明确拒绝；旧成功建设凭据可在政策变化后只读重放，不按新曲线重算旧结果。

初始等级/人气、按帮派等级的建筑cap及维护预估系数是designed，全部来自调用方显式政策，冻结指纹包含revision/origin及每个参数。测试使用(1,1,1)、人气2000、caps(4,8,12,16,20)、维护base10000/per-level(1000,2000,3000)，都只是隔离夹具。未写共用baseline、生产政策或自动激活开关。主策划正式采用前需统一登记唯一政策及适用档案，不能把测试值作为默认值。

以下是本Module采用的designed语义：每次新目标选择支付该目标当前等级原计算全价和200人气；换目标不退款，逐建筑进度保留。选择需资金覆盖立即扣款和升级后12小时预估正常维护费。预估用该建筑升一级后的三建筑等级及扣人气后的余额，base+各等级×系数；人气<1000时×1.5向上取整，最后×12。原文本仅证明12小时储备及低人气50%机制，此具体时点/取整不是原服事实。该预估不执行小时维护，也不替代正常维护的48倍资金机制。

## 所有权、稳定源与事务

guild_buildings只使用调用方事务；不开连接/commit、不写角色钱包/任务，不发送。既有帮派唯一Owner执行OrganizationCommand.choose_building，当前成员及建设授权、资金、人气、cap均在事务内核验，选择/代次/人气、帮派资金ledger/revision及原命令receipt共同提交。重复同键返回原结果，不再收费；不同键重复同目标拒绝。

ConstructionWork(guild,generation,request_id,deadline_ms)是可信任务事件消费Interface；每事件固定+1，无外部可选点数。生产者负责证明真实任务完成并跨Owner持久outbox/inbox，当前没有该生产者，测试明确使用事件夹具。普通线包/NPC不能提交ConstructionWork。Stable request_id必须在同guild命名唯一真实源；同键换generation冲突。旧成功源只读原凭据；新源须当前active帮派、selected和建设代次匹配。退出/任务资格由任务生产者证明，不用一个任意客户端“完成”包代替。

每次有效+1同时写建设度、组织revision及guild_construction_receipts；达到原需求则只升一级、进度归0、selected=-1、generation再递增，关闭该轮。选择目标也推进generation，过时任务不能贡献到新目标。升级/换目标后其他角色实际任务取消仍须任务Owner接入，不因代次拒绝就称任务清理完成。组织历程模板7、建筑对资金上限/产量/研究力影响和帮派升降级仍另补。

## 当前投递与验证

默认可选BuildingSnapshot挂入既有GuildProjection；旧三位置构造兼容。已授权管理者经原GuildWake在目标角色Owner读取当前状态，编码完整三行0xc5628。登录、c5627查询、选择、建设事件和重登均走现有有界Owner/IO/连接加密流；过期租约/代次、撤权和离家重入拒绝旧建筑投递。已提交后的展示SQLite/背压错误仅延后通知，原查询可恢复；真正事务失败继续上报。原空c5628只改selected，不清旧等级缓存，故不发空表或伪造零基线；未知旧档不生成建筑响应，旧GUI缓存清理/完整GUI须后续实测。

verify_guild_buildings公开Store/Runtime/Peer检查新建/重启、授权、收费/储备边界、切换/保留、150次可信源夹具升级、幂等/乱代次/过期、晚receipt回滚、旧未知/缺行/畸形凭据/换recipe、终末旧凭据、当前原查询/面板/重登、8次同源竞争及受控阻塞时另一family命令/4字节心跳继续。verify_guild_buildings_native核原body、完整无GUI实例receiver、算术/控件/名称及选择按钮；UI边缘和网络出口有Adapter。

实际方法：codebase-design把建筑规则与状态集中一Module；tdd逐公开Seam先红（缺building_policy参数、choose_building未支持、缺ConstructionWork、缺原codec、Runtime无building_policy）再实现。其余为补充故障/边界检查。按钮close的无参返回、先清未读通知再测畸形查询、心跳必须4字节为夹具修正，不记功能红灯。code-review按第23批r3固定源对照，两轴独立；writing-for-agents将采用条件/真实源责任/完整验收边界共置。GUI、正式NPC115、真实建设任务及小时维护/研究联动、生产数值与商业容量仍未验，游戏/真人库/实际服务和main共享入口均未操作。
