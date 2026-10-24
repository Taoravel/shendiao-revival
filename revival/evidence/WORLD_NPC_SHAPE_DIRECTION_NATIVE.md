# CNpc+98 的原shape来源与11206方向分支

本批作为后台原生研究，沿用上下文完整读取的 Matt Pocock research/diagnosing-bugs、根AGENTS、ARCHITECTURE与DESIGN_AUTHORITY。方法实际用于：原parser字段→原复制器→原模型ID选择→原+98写入→已冻方向Seam；以毒值0/1/255和仅改变shape3d空值的反事实否定“host固定98=1”。来源只用当前原映像及fresh原PFS，不以手游或另一个模型名称代替本版本事实。

只新增本文与 `../verify_world_npc_shape_direction_native.py`；旧19例脚本/报告及其余冻结35/28例保持不变。未改NPC窗口所属模块、菜单/政策、生产/shared、服务、存档或真实库；没有启动客户端/GUI。

## 可以收窄到什么程度

**11206 的默认modelID为6027，原6027的shape3d非空，因此原创建函数会写CNpc+98=1。** 本批没有再用host固定该byte；原指令从污染值255真实写出1后，接上一批实际方向分支与actor向量更新，验证两个placement的wire0/显式dir差异仍成立。

该结论前提是没有非零NpcInfo+40模型覆盖，并使用这一默认shape创建路径。当前spawn的NpcBasic.field_4c默认0，已知handler把该槽传到info+40；本批没有新增覆盖，也未复原所有变身/后续换shape。因此这证明默认11206资源路径的方向分支适用性，**不是完整CNpc/render构造或GUI朝向验收**。

## 第一方原资源

fresh读取 `runtime/client/artres/config.pfs`，PfsArchive核长度/CRC，原二进制XML由现有bxml解析；表记录保留原字符串值：

|原记录|本问题相关字段|
|---|---|
|CNpcConfig id11206|bodytype=0，npctype=4，modelID=6027，mapid=1002，hide=1，actionname=0|
|CNpcShape id6027|shape=`gaibangnandizi`，shape3d=`3ds_BN014_gaibangnandizi`，dir=4，combatmodel=1|
|大胜关npc.xml第54条|id11206，posx1286,posy3455，dir7|
|同文件第55条|id11206，posx950,posy3438，dir1|

原hide=1这里只作为资源值，不推断该NPC已经可见或应该无条件生成。6027的shape.dir=4与两个placement.dir7/1是不同来源；不能混成同一方向值。旧19例来源与方向向量定义见 [WORLD_NPC_DIRECTION_NATIVE.md](WORLD_NPC_DIRECTION_NATIVE.md)。

## 原字段数据流

1. CNpcConfig parser `bae966..bae992` 以原字段字符串 `modelID@225ac38`调用属性读取，写row+0c。原 `11f3000` 从bean复制首4个dword到CNpc+150，所以modelID落在CNpc+15c；ID/bodytype/npctype分别在+150/+154/+158。原 `1201c44..1201c5d` 是查配置后调用该复制器的静态上游。本批对typed原row执行复制器前段到11f3025，断言+15c真实得到6027；没有执行后续所有字符串/容器复制。
2. 原 `1201e01..1201e18` 先看NpcInfo+40模型override；非0选override，否则取CNpc+15c。当前fixture明确override0，使用原默认6027。
3. actor尚未创建时，原 `1201e18..1201e33` 根据EAX=0走vt+fc，CNpc继承槽指向 `11fb330`。本批执行从1201e01到这个原创建函数前半，不host直接调用+98赋值。
4. 原 `11fb362` 调ConfigRoot getter `89e010`；其原体取global2945aec再加a28。这是CNpcShape表。其vt+8 provider边界用typed原row返回6027；请求的shapeID由原模型选择代码产生并记录。
5. CNpcShape parser `baf3a4..baf3d8` 原字段 `shape3d@226b408`对应row+b4的wstring。原 `11fb375..11fb38f` 比较该wstring与空串，非空走 **11fb398：byte[CNpc+98]=1**；空走 **11fb5e6：byte[CNpc+98]=0**。
6. 原shape创建后才继续方向选择。为了不把庞大的图形创建Adapter算成已验，本批在+98写完后的11fb39f或11fb5ed停下，随后通过明确engine actor创建Seam提供上一批最小actor，保留刚由原函数写出的+98，接原方向消费者。此处没有再用host重设+98。

因此+98至少在这条初始化路径上表示原模型shape3d分支选择结果，而非packet byte、placement.dir、隐藏标志或服务权限。本文不为所有类/阶段给该byte起更大的业务名称。

## 实际执行的10例

运行：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_npc_shape_direction_native.py
```

最终实际 `all_passed=true, case_count=10`，约1–2秒。只stdout JSON；结构包含原配置与shape记录、读取entry hash、实际原+98写入PC/值、shape lookup、后续原wire/向量结果及依赖hash。

4例真实资源纵切均以+98旧值255开始；原写入观察均为 `PC11fb398,size1,value1`，随后方向链直到actor向量结束仍为1且没有第二次+98写入：

|placement|真实pos|wire field48|原取得shape|原写98|原方向选择|
|---:|---|---:|---:|---:|---:|
|54|(1286,3455)|0|6027|1|7（本图首条）|
|54|(1286,3455)|7|6027|1|7（wire直通）|
|55|(950,3438)|0|6027|1|7（本图首条）|
|55|(950,3438)|1|6027|1|1（wire直通）|

这些是两个真实摆放+真实默认shape的数据flow及原分支执行反馈。过去“98=1是否适用于真实11206”已经由上述有界原创建前段收窄；剩余阻碍是完整图形创建/其附带副作用，不是仍靠host指定98=1。

另6例：poison0/1/255分别配真实非空shape3d或仅把该字段改为空的离线typed row。非空均原写1；空均由11fb5e6原写0。变空是明确反事实，不是修改原包或声称6027实际没有3D模型。空值对照仅验证+98写入，不冒称已完成+98=0后所有方向分支。

## +98 的其他已定位写入与局限

静态核对还定位：

* `11fb700`为已有actor更新shape路径，`11fb759..11fb775`同样比较row+b4；非空11fb77b写1，空11fb80c写0。
* `11f5e80`的另一模型创建路径在 `11f5ed0..11f5ef6`以row+b4非空写1；空分支后续资源链本批未执行。
* 本批仅限定11f0000..1203000附近常见byte-store模式与这些实际消费者，不声称所有别名/内联/构造写入穷尽。后续换shape可重新决定+98，不能把初始值当永久模型属性。

方向的+98=0支在旧文仅称shape+100分支；本批另核原parser **baf573..baf59f**，将原字段字符串dir写到row+100。因此那是CNpcShape.dir，不能与combatmodel混名。实际6027 dir4，但真实+98=1分支不会走这个读取；不能因shape.dir4就让两个placement都朝4。+98=0的actor+138能力分支、随机3/5、shape6100/6126强制方向等尚未实执行，本批不扩大为全shape恢复。

## Adapter与原体边界

* typed CNpcConfig/Shape bean由fresh原PFS行按原parser已证offset初始化；不称整个ConfigManager/二进制XML parser在CPU中执行。CNpcShape表root getter89e010执行，provider lookup只负责返回该typed row。
* 原wstring不等于空串的库导入是host ABI Adapter；参与比较的shape3d来自原字段；选择分支和两处+98写入原体执行。没有将该比较的结果当作host直接填98。
* CNpcConfig复制器只执行首四dword到11f3025停止；默认模型选择1201e01开始的原控制流执行；完整CNpc前面属性/服务/名称/注册与后面图形创建没有执行。
* engine actor由明确fixture边界在原98写完后提供；随后复用已冻结19例脚本的原codec、handler切片、NpcInfo复制、完整原Scene dir getter选择、原方向setter/向量写入。其XML load/attribute ABI、CRT/wstring/sqrt边界全部沿用，不因为本批增加shape来源而被提升成原完整模型/VFS/GUI。

首轮反馈停在原复制器选定停止地址，旧execute helper只接受正常ret导致断言红；改为显式切片runner并断言原停止地址后复跑10例全绿。没有改原映像指令、旧19例或生产实现来获得通过。

## 来源hash

|来源|SHA256|
|---|---|
|原native-image.bin，BASE400000|`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`|
|本批verifier|`893aecd8ce515b46a06fbfc335691283aba1337dcf72f395ba812a9b9a542384`|
|冻结verify_world_npc_direction_native.py|`1580ec34fe3c363b41077af71f45334b8d0d75c547ee7ff2ea5ae1aa178582bc`|
|world_npcs.py|`177f55e34168229665586f9fef6ddee3fcdeef17c3c47fde716ad7353ac7d1c4`|
|world_entity_protocol.py|`d4977aa707e2e0c3d1cbca6bb11ddafa39f678ef3457128d13f9e5db8d66f964`|
|config.pfs autoconfig/knight.gsp.npc.cnpcconfig.xml|`b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85`|
|config.pfs autoconfig/knight.gsp.npc.cnpcshape.xml|`13366e08aa18cf6b56ee0de3b61ce2708fd6c84f216a04da617ee289c04d6773`|
|map.pfs map_1002_dashengguan/npc.xml|`ff846a28ce43322a89af9e2e4c68a0e5469ac88a8cafeace6b2074a3261d9ad4`|

未验证：完整CNpc构造/模型资源实际成功加载、整个SAddUserScreen Process、所有+98写入/后续shape切换、actor非中立gate、全3443placement真实视觉、NPC可见/任务服务权限与运行服发布。可交NPC所属窗口的结论是默认11206形状的+98来源和方向分支已获更强原生证据；采用field48或修改生产投递仍由所属窗口与main审查/接线。
