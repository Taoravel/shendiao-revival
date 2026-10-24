# 全资源地图实例与原传送点执行核验

2026-10-23。此批将地图/view命令的执行范围扩到全部302张资源可用图，并对原有向跨图边逐组选择可验证落点。**源码离线检查，不是全图客户端游玩验收；完整世界仍未完成。**

## 可重复入口与真实来源

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_resource_handoffs.py
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/audit_world_special_portals.py
```

前者产物 `world-resource-handoffs-verification.json`，后者 `world-special-portals-audit.json`。两项已实际执行，退出0；特殊入口脚本的 `diagnostic_reproduced=true` 表示缺口复现，**不表示同图传送修好**。

资源来源为原 `config.pfs/autoconfig/knight.gsp.map.cmapconfig.xml` 及 `map.pfs/<resdir>/goto.xml`。特殊审计重新从PFS读取，每份均经原长度/CRC，再逐项比对全部地图attributes与goto原行等于工作目录catalog，共6275行。输出保留原entry、行数及SHA256；不是只验证生成JSON能读。地图边界与maze仍使用启动加载的原RMP/maze。1302/1307缺资源保持不可用。

## 已执行范围

302图每图建立两个不同instance的实际MapOwner/RoleScene。受控角色在明确state0可走格加入，与本实例同伴互相入屏，执行原STOP位置更新、生成peer SRoleMove、退出并生成移除；另实例同role_id的权威和view保持不变。实际输出的Move和本图SEnterScene均由原完整decoder消费，核mapID与坐标；命令期封锁文件打开。每图记录具体fixture/step与结果。

这项一像素移动只验证每图的原资源边界、节点碰撞、版本/view发布和实例隔离，不是走遍地图或证明原寻路、速度、输入/相机/天气/渲染成功。RoleBasic的shape9、packed0x71及固定名字均为受控fixture，没有变成生产外观政策。SEnterScene里的普通A0/B0保持现有codec；map1404等特殊分支仍按WORLD_SCENE_MOVEMENT_STATE_RESEARCH限制解释。

212个不同源图→目标图组合另执行：选原portal格周边可走起点，先验证原DDA有向段到portal；实际move_with_view产生原target offer→reserve/freeze/activate→源finalize/view移除→目标ready/双方入屏→目标原落点一像素可走更新。每组只选一条原格代表，目标坐标原样使用，不靠自动挪落点通过。目标scene由原decoder核对。此项持久提交为显式受信fixture前提；真实SQL事务/故障/重登仍查对应存储和共享宏验证，不以这里的领域链替代。

## 原入口的互斥分类

分类顺序为边界/资源→同图→源state0→目标state0→局部见证，计数互斥：

| 原portal格分类 | 数量 | 当前含义 |
|---|---:|---|
| 可构造普通state0源/目标见证 | 5141 | 从中选212有向组合执行；没有逐个行走5141格 |
| 源格state0阻挡 | 160 | 此顺序下不包含已分类的同图格；不据此移动原入口 |
| 目标state0阻挡 | 224 | 源已通过，目标不能作本批普通state0行走fixture |
| 同图特殊入口 | 650 | 1594家园小区625、1627碧水寒潭25；需要分别恢复语义 |
| 边界/资源不符 | 100 | 1595/1596/1597/1598→1594各25，保留原住宅问题 |
| 合计 | 6275 | 原goto全部行均已分类 |

按catalog含全部原边得到227组，其中212组执行通过、15组仍未覆盖。此前223组是通过资源/边界后的静态边，不能混作本批212组成功或误称两套计数矛盾。

## 需处理的15组

9组原目标对state0不可作行走落点：1301→1100、1304→1103、1305→1104、1306→1105、1308→1107、1309→1108、1393/1394/1395→1007。1309这组有24格归目标阻挡、1格先归源阻挡；其他每组25。原生路径核/目标调整来源需要继续核验；阻挡观察不证明原服落点有错，也不授权最近清格、改坐标、切mask8或放宽穿墙。

原路径核6212f0与压缩包装6138d0的18例已独立执行：能绕墙，原blocked-goal明确失败；同图角点在kernel与wrapper DDA捷径有不同结果。后续普通点击修正23例亦已实际执行，但它不是场景落地消费者，不能套到portal。WORLD_SCENE_LANDING_RESEARCH另有18例由父独立复跑：真实普通成功setter不查询maze、不调用点击调整；9组受控dest×16场景消息保持原点且原maze byte均11，mask1/8同时阻挡。排除了这些具体自动纠正/换mask解释，没有证明原服实际下发该坐标或授权移动原目标。原图9组仍未完成。

4组住宅返回越界是1595–1598→1594；还须原社区/房间/实例及坐标转换来源，不能无条件把原dest数值当普通世界像素。

2组同图入口已从公开MapOwner复现：原move会给出同map target offer；向同一MapAddress调用reserve被 `Invalid transfer target` 拒绝。拒绝前后inspect_transfer一致，角色仍active并保留源portal报告点，没有冻结或写到目标。当前shared采用同map同实例的路由，因此不是一个“另建实例就算修好”的问题。该反馈用临时角色与空history的受控报告、当前无maze构造，未证明真人自然抵达。

1594的原destx/desty是相同的1..25，25种各覆盖25个格；当前catalog乘16后成为(16,16)…(400,400)，该普通转换不能作为住宅进门语义。后续WORLD_SPECIAL_PORTAL_CONSUMERS_RESEARCH的25结构例及25原表匹配已由父独立复跑：destx是CHouseWeiZhi房屋位置键，Scene+454以该键查服务器住宅信息，非零身份才创建marker；原表xchuansong/ychuansong与25个门口中心精确一致。1594加载请求空body的CRequestXiaoquMapInfo，回表消息为map<i32,MapHouseInfo>；第一q64参与身份关系比较，不能当scene ID。住宅所有权、社区/实例选择、访问权限和实际出口落点仍未恢复，desty业务仍未独立证明。

1627原dest是(101,115)，catalog为(1616,1840)，原dynamic0、加载及marker均走普通分支；实际同图SRoleEnterScene Process接受并转交普通Scene入口，但fixture止于回调边界，原服触碰该入口后的消息序列仍未知。不能因客户端可接同图消息就把同实例reserve直接放行，也不能新建虚构实例来绕过。住宅与1627需要不同的受信交接合同。

## 结论和接线条件

这批新增的可执行证据覆盖302资源图的实例生命周期、212普通有向跨图代表、全部6275原入口分类、两支同图实际拒绝。完成条件尚缺：共享AOI发送前围栏/生产外观与容量、上述15组的正确语义、特殊移动/量化连续路径协调、两缺图、NPC/怪物跨系统与真客户端逐项验收。相关Interface见WORLD_MAP_VIEW_HANDOFF，原目标与住宅规则不在此脚本中补造。

方法：codebase-design沿公开MapOwner/RoleScene Seams核状态所有权及实例隔离；diagnosing-bugs把同图拒绝转成可重复反馈，当前仅定位并保留缺口；research重新读取原PFS资料，后台另追原寻路和量化producer；writing-for-agents将正向范围与失败分类放在同一交接。此批是扩大既有实现的证据核验，没有冒称TDD修复、全量运行时接线或GUI通过。没有部署、重启、开游戏、真实角色/资产或战斗操作。
