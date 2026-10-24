# 特殊修理：原服务树、NPC分配缺口与界面筛选

2026-10-24。本批为 research Skill 的后台研究，按第一方原PFS和原x86指令核对。只写独立脚本及本报告/JSON/反汇编四文件；没有修改NPC、Inventory、装备规则、共享入口、政策、真实存档或服务，也没有打开游戏或执行战斗。资料、受控原指令、正式授权与GUI分开记录。

## 可以采用的结论

1. **原客户端服务树不能给出服务93/160/855的真实NPC分配。** 本批逐一重读 `config.pfs` 内全部50份 `knight.gsp.npc.*.xml`，另读完整 `citemattr.xml`，每条按PFS长度/CRC读取，再对全部属性、列表和嵌套子项与缓存逐行比对（只忽略格式化产生的结构空白）。4127条CNpcConfig仅有pinyin/chitchatidlist/voices子项，没有NPC→service ID列表；`leaveservice`是离开文案。5531条CNpcServerConfig是服务文字及childservice树。50表逐字段清单、原条目SHA/CRC在JSON的sources/npc_table_scan中，不根据NPC名字或商店货架补映射。[S1]
2. 855的完整已查祖先路径只有 **1774“我喜欢配饰”→855“我要修理配饰”**。1774的原完整子列表为548、747、855、748；93、160和513没有其它服务父项，本身为树根。根节点不是NPC ID，1774也不是一个已授权服务器功能。没有从这些表查得可合法指定的NPC或placement，JSON两个列表明确为空。[S1]
3. 原855与513分支都以 **method2和完整NPC key** 调同一 `16299a0` 开启修理界面。本批实际执行两分支到该调用，所得三参数完全相同；在这个调用边界没有携带service ID来区分配饰/普通修理。它不证明没有任何上层全局状态，更不证明服务器应将855视作513别名。[N1]
4. 原修理窗口两份列表的枚举器具有相同的类型谓词：低4位=8且`itemtypeid & 0xf0 <= 0x50`直接选入；否则只有include-extra参数非零才调用原 `10745a0`。后者要求低4位=8、分类位不大于0xa0，且ConfigManager+0x770关联lookup返回的行首为-1。本批实际执行原getter和谓词，只把该配置lookup适配成明确missing/present两种依赖。[N2]
5. 因而受控分支上，tag6..10在missing依赖下可被选入、present时拒绝；tag11（真实模板48010/type184）在此额外谓词直接拒绝，未查询配置表。**不能把先前特殊报价tag6..11的范围，当成该窗口完整可修范围。** ConfigManager+770的表身份和真实行集合本批没有闭合；missing fixture不代表任何真实角色的真实物品获准。[N2]

## 原列表、column与共同界面

`10dce00`调用`109c810(vector,1)`，后者枚举容器key3；`10dce60`调用`109ca00(vector,1)`，后者枚举容器key1。这里的容器key和网络column分别追踪，不凭同值猜映射。两条item筛选实际执行区域分别为 `109c914..109c959`、`109cb04..109cb49`，同一原 `10745a0` 读取wrapper+8的类型和bean+0xc的lookup key；原getter `89daa0`实取全局ConfigManager+770。执行中的lookup记录和每个真实模板均在JSON中。[N2]

另外实际执行两个列表点击回调的**尾段**：`10ddc78..10ddc89`写UI+1c4=1，`10dddf8..10dde09`写=3，再用同一对象执行原确认回调`10dda40`及原marshal`e4cf30`，分别确实发送column1/3、method2、完整高32位非零NPC key和item91。适配了选中item、网络提交捕获及重绘；没有运行完整点击前置或完整CEGUI。本批只证明这两个入口的column，不排除其它入口的column4；不修改旧96例人工column1/4搬运证据，也不否定已有运行时column4纵切。[N3]

原 `10de1e0` 保存method到UI+1c0，调用共同重置，再保存NPC key到+1b8/+1bc；上述类型筛选本身没有读取method或service ID。原SVisitNpc是按NPC key携带服务vector的服务器下行，UI `1635f10`将第一vector交菜单构建；原channel已由既有 `TASK_DIALOG_PROTOCOL.md` / `WORLD_ENTITY_PROTOCOL.md`核验。本批只重读相关原字节供定位，**没有把这些既有codec例计为新运行例**。没有原服菜单下行，就不能由本地树决定93/855归属。[N1、既有菜单证据]

## 新验证范围、复跑与未验证范围

运行 `research_npc_special_repair_menu.py` 得到 **112个新受控原指令例**：13种原模板类型（tag0..11各一条、非装备类型一条）×两枚举器×include-extra0/1×lookup missing/present=104；四个null item例；855/513共同开启调用两例；column真实尾段→确认→原序列化两例。旧96例和656例均未重跑，原八文件SHA与全部NPC生产模块、Inventory/equipment_condition、鉴定ready9b05和方向ready761c在本次前后保持；准确散列在JSON的watched_sha256。

每种类型的wrapper id/type均由原 `1080720→1072890` 从真实CItemAttr整数前缀复制，进入wstring复制之前停止；bean的lookup key为明确依赖夹具。没有替换原10745a0、89daa0或类型比较，也没有假装完成原wrapper/完整详情/真实已存实例构造。枚举器探针从单个item谓词起，到append或skip边界停止，不执行整个STL遍历/append；尾段column探针同样只覆盖其声明边界。

未验证：93/160/855真实NPC及placement、ConfigManager+770表身份/真实行、完整窗口物品选择/鉴定/耐久/额度/组织资格联合流程、特殊资产合法生成、付款币种/材料/概率与服务端结算、共享路由/部署、GUI。不能凭本批开放855、给93套普通权限，或扩大现有普通六槽Inventory判定。当前正式版是否拒绝特殊service由主窗口独立的 `npc-special-repair-published-activation-audit.json`证明，本批不将该运行时审计计作自己的native例。

方法影响的决定：research把“本地服务树存在”与“真实NPC授权”分开，拒绝据1774或名字造绑定；原类型分支与特殊报价范围分开，保留tag11和未知lookup；使用真实整数复制和原谓词而非Python模拟。产物为本报告、独立脚本、完整JSON和反汇编；这些结果是后续服务/资产接口设计的输入，尚未实现或发布特殊修理。

来源索引：S1=`artres/config.pfs`中全部50份npc表及citemattr，逐条SHA/CRC见JSON；N1=原映像 `1639cec`、`1638029`、`10de1e0`；N2=`10dce00/10dce60`、`109c914/109cb04`、`10745a0`、`89daa0`；N3=`10ddc78`、`10dddf8`、`10dda40`、`e4cf30`。映像SHA `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本批摘录见 `npc-special-repair-menu-disassembly.txt`，结果见 `npc-special-repair-menu-native.json`。
