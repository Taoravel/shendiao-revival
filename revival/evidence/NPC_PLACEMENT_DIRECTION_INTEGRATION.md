# NPC原摆放方向投递

2026-10-24，NPC所属实现候选，尚未发布。R2固定1607输入，主窗口及Standards/Spec各六项检查全部通过（共18次），两轴各0；ready为npc-placement-direction-ready.json，审查在reviews/npc-placement-direction-20261024-r2/REVIEW.md。R1缺历史v1测试配置的失败保留，R2只补验证资源，三份范围源码不变。原字段服务器采用方式待root裁定、实际发布闭包待main另验，不由本域ready推定。当前共享优先真人100107说书人战斗链，成员绑定仍为必要基础；本片不并发发布，已封鉴定9b05不变。

## 来源与采用范围

World已交WORLD_NPC_DIRECTION_NATIVE、WORLD_NPC_SHAPE_DIRECTION_NATIVE的19+10原例；NPC补充NPC_ORIENTATION_NATIVE_RESEARCH的102例，研究者停写后主窗口原样复跑、四产物SHA一致。原304个world记录逐map XML投影一致，3443方向值为0..7，其中13个0全部显式原字段。field_48→原NpcInfo+20→CNpc+120→方向setter/actor向量的通道为client_verified。

本实现选择将每一实际placement.direction原样填写现有NpcBasic.field_48；这是服务器采用原数据的实现选择，标designed adoption，提交root审验，不宣称取得原服历史线包。有效数据为精确int0..7；0保留原回退哨兵，不转成8/负数或强制actor enum0。非零2/6可与wire0经原XML回退后的形状分支不同；原shape/engine能力/特殊145xx后处理仍可能覆盖方向，禁止声称所有最终模型都等于raw dir或GUI已经恢复。

## 所属实现与完成条件

NpcPlacement在公共值对象入口拒绝非int或超出0..7的方向；Scene.spawn与Lifecycle的公共生成/当前snapshot/replay都把各自保留的direction写field_48。没有新增字段、网络请求、权限、货币、全局状态或热配置读取；其余NpcBasic值保持原defaults。动态NpcSpawn仍使用既有direction0，不新增未经设计的朝向控制或自动巡逻。

真实1002/NPC11206的p54dir7、p55dir1在旧Scene消息中经原SAddUserScreen decoder得到0/0，保留npc-placement-direction-baseline.json。修Scene后该例绿；随后旧Lifecycle当前snapshot的同一0/0红例及值对象接受-1红例分别保留，逐步修到绿，不伪称所有追加检查都曾红。

verify_npc_placement_direction.py直接读取原decoder链表节点，不用变长名称下的固定wire偏移：全部304地图/3443摆放通过Scene和Lifecycle当前snapshot，两条真实重复placement、13个原0、七种非法输入、remove后动态0及重复spawn的当前snapshot共六组通过。只适配外部CRT的既有原解码器fixture，不替换生产encoder/dispatcher。原模型完整构造、实际共享Peer/渲染与GUI另验。

## 两种基线，不整体覆盖

正式BASE023920/7456的world_npcs为177f55...，与本片Scene的真实base字节相同；因此静态发布候选只需这个NPC所属文件，不加shared。最终仍由main在届时实际BASE选择性取该差异，完整冻结回归/审查后唯一发布。

工作区Lifecycle的本片base是已审但未激活的strict-startup 8a0cd...；正式BASE的Lifecycle仍f5e077...。本片对8a域另补同一字段，不能整份8a或本片新文件覆盖正式f5而夹入未审闭包/启用动态生命周期。后续Life须连同严格loader/预算/可信来源和真正MapOwner投递独立复审接入。当前方向域审查也不授权World成员绑定、玩家AOI、鉴定收费或特殊855。

## 方法与验证边界

tdd在已有公开Scene/Lifecycle和原decoder Seam逐个红→绿；codebase-design把源值范围校验放进共享NpcPlacement、用既有两生成入口隐藏编码细节；research使用原PFS/原字节并保留模型分支和server选择的区别；code-review以177f/8a真实字节及新测试空base做非Git两轴；writing-for-agents将两种基线、零哨兵和未发布范围共置。双轴和固定输入结果以本片ready/审查报告后续记录为准，本页不代替验收。
