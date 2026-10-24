# 怪物区域到暗雷玩法：CMineAreainfo原消费者研究

2026-10-23。部署冻结期间仅新增本文。沿用research的一手原包/原映像溯源和diagnosing-bugs的确定反馈：对“原byte直接查表”“先转signed再查表”“仅为编辑配色资料”三个候选分别查调用点、原字段解析和原缓存查找。未写入或新建Python、配置、世界Module、共享入口或政策；所有临时程序从标准输入运行，使用Python `-B`避免生成字节码缓存，未操作服务、客户端或GUI。

**结论：找到并验证了CMineAreainfo的原表注册、getter、字段解析和查询；没有找到monster区域到运行时暗雷/怪物组的消费链。原表只有id、colour、discribe，不能据此生成怪物。将高位byte直接转成signed后查本表仍全部无效；正区域值也存在跨地图复用，不能仅凭表描述决定怪组或地图身份。** “这只是编辑器颜色表”目前仍是字段支持的推断，没有原编辑器调用链，不能升格为已证实排他用途。

## 本轮直接读取的一手来源

- `runtime/client/artres/config.pfs` 的 `autoconfig/knight.gsp.map.cmineareainfo.xml`：重新PFS长度/CRC检查、BXML解码，49行id0..48，原条目SHA256=`502beba81d948a30af9d8df4984b59477cda433c1e9f268cdc95211660441151`。原解码文本从 [CMineAreainfo:3](../decoded/config/autoconfig/knight.gsp.map.cmineareainfo.xml:3) 起。
- 同包 `knight.gsp.map.cmapconfig`：用原resdir连接场景资源，只用于确认地图ID/原名与文件的关系，不把说明文字当服务端触发公式。
- `runtime/client/artres/map.pfs` 的44份monster.dat全部重新CRC读取，共869,260条原记录。沿既有观察结构`<4I>`头后每条`<HHB>`，保留顺序和raw byte；本轮没有找到原文件消费函数，不能将此结构称作已执行原loader证明。此前12份重复/陈旧尺寸异常继续按 [SCENE_GRID_PROTOCOL](SCENE_GRID_PROTOCOL.md) 原样保留。
- `evidence/native-image.bin`，BASE0x400000，SHA256=`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本轮没有重复做monster.dat明文搜索，而是沿已知RTTI追原表所有者及调用。

## 原生表身份、注册和加载链

原RTTI名称保留大小写：`CMineAreainfoTable@map@gsp@knight`，公开表虚表0x224ff48；实现类`knight_gsp_map_CMineAreainfo_table_implement@XMLCONFIG`虚表0x2259b00。

|地址|原指令/对象关系|能证明的范围|
|---|---|---|
|0xd42c0c..0xd42c1b|调用0xc9f890取得缓存；Config+8d8写vt0x2259b00、+8dc写缓存指针|配置根注册此表|
|0x89dd70..0x89dd7a|`mov eax,[0x2945aec]; add eax,0x8d8; ret`|原表getter和根字段位置|
|0xc9f8b6|常量0x2259b0c为UTF16 `knight.gsp.map.CMineAreainfo`|缓存工厂按该表身份查资源|
|0xc9f8ed..0xc9f940|有预处理资源则建CBeanCacheFile；否则建CBeanCacheMemory|文件/内存两种缓存Adapter，不是两种遇敌玩法|
|0xd45b30..0xd45b39|Config+8d8传0x9c1cd0|统一配置载入路径|
|0x9c1d39→0x9a47e0→0x95de50|按表名寻找/读配置并遍历记录|通用配置读取|
|0x95dfd1|调用0x87a9b0解析CMineAreainfo记录|本表具体字段解析器|
|0xc9885e..0xc98869|Config+8d8调用0x87aad0|销毁/释放表实现|

0x87ab40和0x87ab50分别转调缓存虚表+0xc/+8；本轮实际查记录使用`87ab50→CBeanCacheMemory::c365c0→原树查询c36350`。这些地址是表访问基础设施，不能因为其中出现“查区域”就称为角色移动触发怪物。

## 原字段只含整数ID和两份字符串

记录解析器0x87a9b0：

- 0x87a9d6使用UTF16常量0x24609c0=`id`，0x87a9fa调用整数读取0x409ce0，0x87aa07写记录+0。
- 0x87aa17使用常量0x2256880=`colour`，0x87aa26取记录+4，0x87aa41调用字符串读取0x409cc0。
- 0x87aa58使用常量0x2251cd0=`discribe`，0x87aa67取记录+0x20，0x87aa82调用同一字符串读取。

0x8abaf0构造记录+4和+20两份wstring；0xc35ee0复制同样字段。文件缓存读取0xaf8f25/0xaf8f33也分别向+4/+20读字符串。本表中没有原生解析的怪物模板、战斗阵容、等级、数量、触发率、步数、冷却或奖励字段；`colour`此处尚且是字符串，不是已在本解析器转换的区域判定掩码。

原表 [id0:3](../decoded/config/autoconfig/knight.gsp.map.cmineareainfo.xml:3) 为colour0、discribe“清除刷”；[id1:4](../decoded/config/autoconfig/knight.gsp.map.cmineareainfo.xml:4) 起为半透明十六进制颜色字符串及地图区域描述。字段形态、重复颜色与“清除刷”支持它可能来自区域绘制调色板的推断（inferred）；**没有执行编辑器，也没有找到colour用于渲染区域、discribe用于编辑器列表的实际消费者，故不能判定其仅能用于编辑器，更不能反过来声称它已连接暗雷。**

## getter引用审计：未发现玩法消费，不等于证明不存在

对整个映像扫描目标0x89dd70的E8 rel32 call、E9 rel32 jmp和绝对32位指针引用，三者均为0。对Config字段偏移0x8d8做补充检查，已建立同一Config根来源的命中是注册0xd42c11、统一载入0xd45b30及销毁0xc9885e；其他对象也有相同数值偏移，不能当成本表消费者。

找到的0x2259b00虚表引用也集中在构造、注册、销毁；0x87ab40/+50的绝对引用来自该表虚表本身。**本轮没有找到“角色位置/步数→monster区域byte→CMineAreainfo→战斗请求/怪物生成”的连接。** 计算出的虚调/运行时反射、别的DLL、原编辑工具或服务端代码可能绕开这些直接引用扫描；因此不将0引用写成“整个产品绝不使用这张表”。

## signed解释的原查询反证：转换本身不能补出缺失关联

原内存缓存0xc365c3先比较整型key是否为-1；-1直接返回默认无效记录。随后原0xc36350在树节点+c作signed32比较并查**原整数键**，没有byte符号扩展、取绝对值、取低位或加减256。0xc35ebf给默认记录id=-1。文件缓存0xaf8e70同样把-1视为无效/不查找入口。

本轮在隔离Unicorn内存中，以刚从原PFS读到的49个键0..48构造合法只读树形fixture，实际执行原getter、原虚表转调、原缓存和原树查找，共24次。没有替换查询、比较或返回逻辑；fixture只保存原ID及树链接，不声称执行了原XML加载或怪区消费。

|查询key|原返回记录id|
|---|---|
|0、1、48|各自0、1、48|
|49|−1|
|244、245、246、249、250、251、252、253、254、255|全部−1|
|−12、−11、−10、−7、−6、−5、−4、−3、−2、−1|全部−1|

所以原raw255若先转signed变-1，反而直接命中缓存无效入口，**不会自动映射到雷峰塔一层**。raw244转-12等也不会凭空变成表中有效ID。这个反证仅否定“直接以raw或signed key查本表即可恢复所有怪区”；它不否定尚未发现的服务端负区域命名空间，也不证明原monster loader到底用movsx还是movzx，因为该loader仍未定位。

## 原资源关联：有匹配，也有明确复用/不匹配

雷峰塔一至七层资源`leifengta1..7/monster.dat`主要值依次255..249，另各含少量0。按二补码转换恰为−1..−7，这是观察规律，不是类型证明。

|原资源/地图|非零raw byte|二补码解释|CMineAreainfo同raw键|
|---|---|---|---|
|雷峰塔1..7，map1200..1206|255..249|−1..−7|均不存在|
|副本雁门关1527，fubenyanmenguan|246|−10|不存在|
|鲁班坊1207，map_1207_lubanfang|246|−10|不存在|
|雪怪巢穴1655|245|−11|不存在|
|浩劫之地1656|244|−12|不存在|

raw高值记录量：244=14,896；245=2,816；246=4,200；249=14,228；250=14,192；251=14,216；252=14,129；253=14,066；254=14,165；255=14,086。raw246在两个不同资源共用，故它本身不能唯一标识地图。raw0共14条，本轮不擅自将其解释为删除、空地、避怪或遇敌概率0。

正值关联也不能直接升级为全球怪组ID：百花幽谷1..5分别用1/25/26/27/28，与本表描述一致；但还有下列确切反例。

|原地图/资源|raw|表同ID原描述|含义限制|
|---|---|---|---|
|[葬剑魔窟六层1543](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:186)，map_1543_shilianfubenliuceng|44|葬剑魔窟五|本表45虽有“葬剑魔窟六”，该文件实际没有用45|
|[碧水寒潭1627](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:268)，map_1627_bishuihantan|9|终南山|另一份碧水寒潭1019资源用48；不能只按显示名或raw归并|
|[花果山1658](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:299)，map_1658_huaguoshan|11|百花林地|同raw还用于百花谷野外1011|

这里能证明区域标记被复用、资料可能有历史/复制来源，不能证明“这些地图应生成相同怪物”，也不能静默把44改45、9改48、11改新ID。路径/地图行源可查 [CMapConfig:32](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:32)、[鲁班坊:39](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:39)、[副本雁门关:170](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:170)、[雪怪巢穴:296](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:296)、[浩劫之地:297](../decoded/config/autoconfig/knight.gsp.map.cmapconfig.xml:297)。本轮从原PFS重新连接，非仅引用之前导出目录。

原CMapConfig雷峰塔一层Introduction确写“暗雷区”，fightinfor=2；副本雁门关fightinfor=1、浩劫之地fightinfor=0也有monster数据。这些字段值保留为client_verified原值，但本轮未追到fightinfor的枚举消费者，不能据此把0/1/2直接命名为某种触发模式或用monster文件存在性代替玩法资格。

## 交给主策划的精确输入缺口

目前可直接消费的只读输入是：map/resdir、原始有序坐标/byte记录、地图描述资料、NPC/战斗其他目录既有模板。还缺以下**关联与规则**，应分别寻找原来源或由主策划明确designed，不应让区域解析器暗中补值：

1. 区域键作用域：按map/resource或副本实例加raw键，还是另有signed/特殊命名空间。如何解释0与高位byte，以及何时升级到新的真实消费证据。不能用直接CMineAreainfo查找结果代替。
2. 同坐标重复、声明宽高陈旧和越界原记录的有效性/优先级。保留原始资料只是取出成功，不是已确定“最后一条覆盖”或“越界忽略”。
3. 区域到真实战斗阵容/怪物模板集合的绑定，包括等级段、队伍组成、每次数量与抽取权重。CMineAreainfo没有这些字段；区域显示名也不能充当模板ID。
4. 暗雷触发所需的权威动作：按实际行走距离/格数还是周期、地图/任务/活动资格、冷却、保护及避怪效果。原monster byte没有给出这些参数，不在本批创数值。
5. 战斗Owner、角色Owner与地图Owner之间的触发票据、归属/租约版本及唯一结算来源。冻结期间不接线，后续仍遵循ARCHITECTURE，不把区域扫描或战斗奖励变为全服锁/全局队列。

上述缺口中，“signed转换后就能查表”的捷径已被原缓存执行反证；“同value必同地图/同怪组”的捷径被原资源关联反证。除此之外本批没有宣布某个未找到的机制不存在，也没有发布新的遇敌政策。

## 只读复现摘录：原查询24例，不创建脚本文件

以下Python可通过标准输入在工作区运行，使用已有解释器`C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B -`。程序不写文件；只建隔离Unicorn内存中的树fixture。原字节、配置key和查询代码均保持可审查。

```python
import sys, struct
sys.path.insert(0, 'revival')
from pathlib import Path
from pfs import PfsArchive
from bxml import decode
from native_inspect import BASE, DATA
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import (
    UC_X86_REG_ECX, UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP)
raw = PfsArchive(Path('revival/runtime/client/artres/config.pfs')).read(
    'autoconfig/knight.gsp.map.cmineareainfo.xml')
keys = sorted(int(r.attrib['id']) for r in decode(raw))
u = Uc(UC_ARCH_X86, UC_MODE_32)
u.mem_map(0, 4096)
u.mem_map(BASE, (len(DATA)+4095)&~4095)
u.mem_write(BASE, DATA)
u.mem_map(0x5000000, 0x200000)
obj, head, conf, stack, stop = (
    0x5001000, 0x5002000, 0x5003000, 0x5100000, 0x500f000)
def w(a, *vs):
    u.mem_write(a, struct.pack('<'+'I'*len(vs),
                              *(v&0xffffffff for v in vs)))
def read(a):
    return struct.unpack('<I', u.mem_read(a, 4))[0]
nodes = {k:0x5010000+i*0x80 for i,k in enumerate(keys)}
def tree(ks, parent):
    if not ks:
        return head
    mid = len(ks)//2
    k, p = ks[mid], nodes[ks[mid]]
    left, right = tree(ks[:mid], p), tree(ks[mid+1:], p)
    w(p, left, parent, right, k, k)
    return p
root = tree(keys, head)
w(head, nodes[keys[0]], root, nodes[keys[-1]])
u.mem_write(head+0x4d, b'\1')
w(obj, 0x226d088, 0, head, len(keys), 0xffffffff)
w(conf+0x8d8, 0x2259b00, obj)
w(0x2945aec, conf)
def call(a, ecx, arg=None):
    w(stack, stop, *(() if arg is None else (arg,)))
    u.reg_write(UC_X86_REG_ECX, ecx)
    u.reg_write(UC_X86_REG_ESP, stack)
    u.emu_start(a, stop, count=10000)
    assert u.reg_read(UC_X86_REG_EIP) == stop
    return u.reg_read(UC_X86_REG_EAX)
table = call(0x89dd70, 0)
assert table == conf+0x8d8
queries = [0,1,48,49,244,245,246,249,250,251,252,253,254,255,
           -12,-11,-10,-7,-6,-5,-4,-3,-2,-1]
for q in queries:
    ident = read(call(0x87ab50, table, q))
    ident = ident if ident < 2**31 else ident-2**32
    assert ident == (q if q in keys else -1)
print('PASS', len(queries), 'original typed-table lookup cases')
```

本研究窗口已实际运行临时标准输入代码，并从本文提取上述代码再次执行，均输出`PASS 24 original typed-table lookup cases`。临时程序未落盘为Python脚本，也没有新增JSON或修改既有验证程序。**这24例仅指本表的原查询，不是已有独立位置纠正脚本的23个handler加5个codec共28例，也未声称父线程已经独立复跑本批。** 父线程可按本节命令和内嵌代码复现，结论以实际原查找返回id为反馈。

未验证原monster loader、编辑器显示、客户端暗雷触发、战斗生成、概率/奖励、服务器运行时或并发容量。研究到此明确停在缺失的消费链，而非用参数猜测完成全量怪物恢复；本批收口后不扩大搜索，继续遵守部署冻结。
