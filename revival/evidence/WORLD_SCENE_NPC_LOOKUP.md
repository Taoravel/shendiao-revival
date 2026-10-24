# 原Scene NPC容器注册、完整key查询与模板选择

2026-10-24。本批采用已读Matt Pocock research的后台第一方追溯、diagnosing-bugs的确定性反馈与单变量夹具、codebase-design的纯容器Seam/显式Adapter；遵循根AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。仅新增本脚本/本文/JSON，不改旧Motion、生产Module、共享、政策、存档；没有客户端、GUI、运行服、战斗或真实网络。

产物：[research_world_scene_npc_lookup.py](../research_world_scene_npc_lookup.py)、[原生执行结果](world-scene-npc-lookup.json)。映像SHA256=`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`；JSON另录脚本、复用研究脚本、原1006 maze/RMP哈希和相关原指令字节。

## 交付结论

**原`11d1870(templateID)`取NPC有序容器中第一个匹配模板的对象，顺序为有符号64位实体key升序；它不按距离、插入先后、可见性或active状态选择。** `11d5260(q64 key)`在同一Scene容器中精确查询完整key，没有仅低32位或配置ID别名。以上排序/查询/注册/移除均已执行原指令，不是Python字典模拟。

独立`NaturalLookup`继承上一批Motion，移除了`11d1870/11d5260`两个查询Adapter：一条原公开导航自然运行至完成consumer，用真实原查询在两个同模板、相同低32位而高32位不同的NPC间选较小完整key，真实CVisit发送仍保留该完整key。另一条**单独的非零metadata consumer Seam**精确选中了较大的key；这条是host显式调用consumer，不冒称第二次自然到达。

## 原索引ABI与可执行注册Seam

来源是原映像中[首师父key审计](FIRST_MASTER_NATIVE_NPC_KEY_AUDIT.md)定位的场景实体链；本轮重新反汇编并执行：

| 原入口 | 本批执行范围 |
|---|---|
|`11d8b40`|原同布局有序容器构造；调用`11ce540`原分配/初始化哨兵|
|`11d9f25..11d9f30`|CNpc初始化成功之后的真实注册slice，含`11d8b70`与原`mov [eax],edi`对象指针写入|
|`11d8b70`|按q64键的原operator[]：查找/分配/插入/红黑树维护，返回value槽地址|
|`11d1870`|完整原模板查询|
|`11d5260 → 11d42d0 → 11cc0a0`|完整原key查询、lower_bound与相等检查|
|`11c79d0`|原迭代器后继，记录实际容器遍历顺序|
|`11cf1f0`|原单节点erase，更新树/计数并释放节点|
|`1174ee0 / 1174ed0`|原实体key setter/getter；非host截断/重建key|

Scene容器在`scene+0x68`；+0x6c为head，+0x70为count。node+0/+4/+8为树链接，+0x10/+0x14是完整key低/高32位，+0x18为实体指针，+0x20为树color，+0x21为nil标记。`11ce540`分配0x28字节节点；原构造器设置head三个链接指向自身、nil=1、count=0。

本批调用原同布局容器构造器，**未执行整个CGameScene构造器，也未另证明Scene+68初始化时具体选用哪个等价构造入口**。但该布局由实际Scene查询/注册原指令共同使用，全部反馈已过。

注册slice的输入是host提供的已初始化实体/键info：ESI=info，EBX=scene，EDI=entity；从`11d9f25`执行到`11d9f30`，原体自然调用operator[]并写value。host不建立树节点、不决定树链接/顺序，也不伪造查询返回。完整上游`11d9c70`在`11d9ef7`构造CNpc、`11d9f1f`调用虚槽+184初始化，成功后才到此slice。**本批未执行完整CNpc/render初始化，不把它写成已经重现的render失败；选择此纯容器Seam是有限研究范围。** 删除也只做容器节点erase，不调用实体析构或演出/渲染清理，因此不是整个实体销毁生命周期已恢复。

## 排序、模板命中与过滤

原lower_bound `11cc0b7..11cc0cc`比较key高32位时用`jg/jl`，高位相同才以低32位`jae`比较；`11d42fd..11d4312`再执行等值判定。因此它是signed64顺序，高位有符号、低位无符号。

原模板getter：`11d1873`从head的最小节点开始，`11d18ba`读node+18对象，`11d18c1`只比较object+150与目标模板；匹配马上返回，否则`11d18cd`调用原后继继续。没有读取角色位置、NPC位置、可见/active flag，也没有调用过滤虚函数。这是本函数完整原体的静态证据；查询是否被调用、实体是否先被注册/移除，则属于外层条件。

有限执行反馈共8组：

1. 空容器按key/模板均返回0。
2. 同模板10498，先注册key`0x200000001`，再注册key1；模板查询选key1。key1对象+18/+148置0仍命中。**字段业务名不作为本轮新结论；这不是用伪造model距离证明远近，而是查询原体根本不读位置/这些flag。**
3. 两个Scene注册相同key1而指向不同对象；查询各自只返回本Scene对象，另一个空Scene查询不会串到首Scene。
4. 同key1再次注册新指针，原operator[]复用节点，count不增，后续查询返回新指针；这是此注册slice的行为，不表示完整高层add handler对重复包一定销毁/替换已有对象。
5. 删除低key1后精确查询缺失，模板getter选余下高key；重复删除返回“未找到”，不调用非法erase。另一Scene同key仍保留。
6. 插入非排序键：`0x100000000, -1, INT64_MIN, 0xffffffff, 0, INT64_MAX, 1`；原迭代器顺序严格为signed64升序，每个完整key精确查询成功，缺失`0x100000001`返回0。模板选INT64_MIN。
7. 逐一原erase至空，模板/key均缺失、count0、原迭代器结果空。
8. public构造参数使用实际格式key`(1006<<32)|13`，原setter在原注册之前执行；对象getter、原模板查询和原key查询都返回同一完整身份。这里只验证构造/查询契约，没有另跑第二条完整运动。

负key仅用于容器signed64边界，不代表CVisit非负wire允许负key；自然Visit例只使用非负signed64 key。也不能由本轮“首key”反推原服务器发放key应按placement排序。

## 独立自然运动wrapper与非零metadata

[WORLD_NPC_APPROACH_MOTION](WORLD_NPC_APPROACH_MOTION.md)的主体保留冻结。本批新增wrapper在构造期间注册：主NPC key=`0x5060708010203040`，重复NPC key=`0x0102030410203040`；两者CNpc/model初态沿旧Motion（同模板10498、原placement1668/970）。**两key低32位都为0x10203040**，可检验完整高位是否保存。

主链仍从`1142620(auto,1664,960,1006,10498,0,0,1)`开始；只运行上一批的radius1/方向0一例，不重做选点/距离枚举。两个actor tick后自然到达原`1672,1016`，队列清空；原`12172f0`的无metadata分支在`1217427`调用原`11d1870`，实际返回较小key对象。其后原`1215790`/构造/发送捕获的CVisit key为`0x0102030410203040`，不是host的查询Adapter或手造Visit。

独立wrapper对`11d1870/11d5260` hook只记录入口/参数并返回到原指令执行，明确避开继承类旧Adapter。engine事件中的额外`11d5260`缺失key查询也实际执行并返回0，而非继续旧“总是无特殊实体”的Adapter。

随后**单独consumer测试**：host显式填role+314=10498、+318/+31c=`0x5060708010203040`，直接调用`12172f0`。这是consumer Interface测试，不声称发生另一次导航/运动到达。原`12173f3`调用真实`11d5260`，返回较大key对象，`1217402`核模板后自然调用Visit，捕获第二个完整key恰为高key；最后314/318/31c都由原指令清零。这闭合了旧报告中未执行的非零metadata分支，尚未证明哪一条原UI入口会供应这些metadata。

## 可复用Interface与Adapter

集成方只需本独立wrapper，无需改旧Motion：

```python
from research_world_scene_npc_lookup import NaturalLookup

run = NaturalLookup(grid, render_size, final_radius=1, final_side=0,
                    npc_key=(1006 << 32) | 13)
initial = run.navigate()
# 后续仍用原actor tick；捕获在run.messages / run.real_lookup_entries。
```

`npc_key`默认保留旧Motion的`0x5060708010203040`；`duplicate_key`默认None，只注册一个对象。如研究重复再显式给distinct非负signed64键。public构造先用原`1174ee0`写实体key，再用原slice注册；**注册后不要只改object+10/+14，会造成对象身份与树键不一致。** 当前Interface不为生产Scene设计新key规则。

纯容器测试的Adapter仅为映像/对象/栈内存及CRT分配/释放、安全cookie；容器构造、插入、指针写、查找、比较、遍历、erase都执行原体。实体和scene初态是host fixture，未执行完整构造。自然wrapper保留旧Motion明确记录的动画/渲染/引擎环境、actor→role关联、rand/clock、sender等Adapter，只有两种NPC查询已替换为原体；未证明完整App/GUI或生产网络。原1006 maze结束逐字节未变。

## 验证与剩余范围

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_world_scene_npc_lookup.py
```

预期并已实跑：8组容器/构造契约、一条自然运动查询链、一条单独非零metadata consumer，全部断言通过。JSON记录公开输入、原lookup caller/参数、实际消息key、原容器遍历顺序、完整key身份与原字节/哈希；不是仅检查未崩溃。

未验证：完整SAddUserScreen handler/CNpc构造/渲染资源、真实Scene注册与销毁外层副作用、同配置/不同位置的原服务器key发放策略、全部NPC类型/可见生命周期/条件、哪个UI入口提供非零metadata、跨图/私有实例、GUI/在线服务/Owner加密投递。父窗口可用public `npc_key`在原注册前注入实际恢复服绑定key，再对真实Owner独立验证；本批没有代替该验收。
