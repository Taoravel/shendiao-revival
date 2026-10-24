# NPC原摆放方向、wire0回退与模型分支

2026-10-24，NPC受委派的后台原生研究。只新增本文、research_npc_orientation.py及npc-orientation-native.json/.txt；未改生产/shared/政策/旧研究/服务/真人库或GUI。research方法用于先复用World已经闭合的19/10例，再补真实值域、全部原dir0与未执行的非3D分支；没有重做或改写已冻结的旧脚本/报告。ARCHITECTURE与DESIGN_AUTHORITY已读，普通CNpc与7592景物保持不同身份空间。

## 可交NPC所属窗口的结论

现有纯codec的NpcBasic.field_48确为原对象+48，经过原handler→NpcInfo+20→CNpc+120→原方向setter→actor方向向量。有效非零1..7在受测路径可原样进入setter；**wire0是高层回退哨兵，不是“让actor朝枚举0”**。原地图3443条dir实际值域为0..7，不是1..8；13条原dir0全部显式写了0，未把缺字段兜底算成真实0。

原651700的actor enum0向量是(0,-1,0)，但这不提供一个“非零wire也表示enum0”的编码。新增原指令诊断确认wire-1/8/2147483647都走默认零向量(0,0,0)，不能用8或负数绕过哨兵。原13个dir0在各自原地图、原默认shape的本批公共初始化路径均实际选择4，向量(0,1,0)；发送field48=0保留原回退语义，不能将它改名为强制enum0。

恢复服若选择将原placement.dir填入field_48，是采用已证方向通道的服务器实现选择；本批没有取得原服当年的SAddUserScreen字段取值，也不证明所有模型最终朝向必等于raw dir。尤其显式非零wire2/6直接选择2/6，而wire0→原地图getter得到2/6时会被原+98=1分支改为4。这两个来源不能混称为所有情形完全等价。

## 来源、原19/10与复跑

原映像BASE400000，native-image.bin SHA256为2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791。脚本fresh读artres/config.pfs中CNpcConfig、CNpcShape、CMapConfig三个原表，解压长度/CRC校验后按全部attributes/lists对照保存catalog。再逐304个world地图记录读取相应原map.pfs/npc.xml；291次原member读取经长度/CRC校验，其余无文件且保存摆放也为空；每一份原NPC数组与world投影完全相等。详细entry/CRC/长度/SHA按mapID保存，不把重复读取当不同物理文件数量。

原World闭包的来源与执行方法见WORLD_NPC_DIRECTION_NATIVE.md、WORLD_NPC_SHAPE_DIRECTION_NATIVE.md。新脚本在当前工作区直接执行两者公开check，19+10均过，旧两脚本/两报告SHA在新批前后不变。它们保留的scope仍适用；没有把后续公共分支验证升级成完整图形构造或GPU结果。

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B revival/research_npc_orientation.py
```

从项目根运行，结果102例通过，其中原19+10及新增73。JSON包含完整case、原wire、原+98写入、原setter入参序列、actor向量、XML请求/属性读取、源SHA和全部13个zero原行；TXT来自当前映像的原反汇编。工作区world_npcs/npc_lifecycle/protocol的前后SHA也固定；该字段明确是工作区输入，**不推strict-startup Lifecycle已经部署**。

## 全量原值域与零值

|原dir|0|1|2|3|4|5|6|7|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|3443原摆放数量|13|314|40|1273|761|757|50|235|

13个zero覆盖NPC12016、14623、13328、13324、11583、11581、13306、10650、13461、12455、12456、10642、12307。12个原默认shape3d非空，由原创建前段真实写CNpc+98=1后接原wire0及本地图getter；原getter读到0或偶数后都被原分支选4。10650在1100的首个同ID原dir为6，实际也选4，不是host事先给出的“0”。14623/shape5737为空shape3d，由原创建前段写+98=0，原shape.dir为1，后续原分支强制4。本批每例原shape写入由污染值255开始，复用已证原模型ID选择/lookup/写98，而非host设98。

有64组同图同configID、不同dir。原19/10已闭合普通11206在大胜关p54dir7/p55dir1：wire0两者都取原首条7，显式7/1才分别到原actor不同向量。本批13zero不是新增的全模型保证；仍仅在声明的公共模型路径、无覆盖和中立gate fixture成立。

## +98=0的新增原指令反馈

原120213f从实际CNpcShape表读row+100（shape.dir），保存至NPC+274。shape.dir是分支来源，不能与placement.dir或wire字段混为一份值。本批使用真实1002原NPC10903/shape5067(dir3)、11220/shape5190(dir1)、11361/shape5036(dir4)，三者shape3d原值为空，原模型创建前段都写98=0。

actor能力getter为原vt+138→6526e0，原代码读actor+1a8所指path+47。测试只给engine字段明确0/1，getter本体实际执行并观察返回；这不是从真实模型创建中恢复了该能力的生成规则。对每个真实row跑cap0/1×wire0..7，共48例：

|公共分支条件|实际原setter序列|
|---|---|
|shape.dir=1|任何wire/engine cap都为[4]|
|shape.dir非1，cap=0|wire0先把CNpc+120改4，其余非零原样；各一条setter|
|shape.dir非1，cap=1，wire1/2/3/5/6/7|非零原样一条setter|
|shape.dir非1，cap=1，wire4|先setter4，再setter3，最终向量3|
|shape.dir非1，cap=1，wire0|原本图getter的奇数1/3/5/7保留；其它值经原rand分支选3或5|

rand为外部CRT边界，输入0与1是明确fixture；原and/条件跳转及3/5入参选择全部执行。48例中使用rand0，另给10903同一原row/rand1一例，实际由3切到5。没有把此fixture称为原服务器随机分布。

新增8例用1100原14504的p32dir1/p35dir4，分别cap0/1和wire0/原dir。cap0的wire0均4、显式dir分别1/4；cap1的wire0均取首同ID的1，显式1为[1]、显式4为[4,3]。这是公共CNpc方向初始化部分。全部9个真实非3D重复不同dir组都属于145xx特殊创建路径；原11d9ff0→11fc5b0/子类vt2298414→11fc8d0→call1201bd0的链已静态列出，本批**没有执行完整子类构造和后处理**，不将它冒称已证明整个特殊NPC的最终朝向。普通/子类方向setter槽均为原11f5b00。

shape6100/6126在某些+98=0能力分支还有最终强制3，但它们原shape3d非空，本批不人为改空来将反事实当真实默认分支。非中立NPC gate、其他bodytype/后续换shape/完整模型副作用仍未验。

## 实现边界、适配与下一步

此批共102=原29+13真实zero+48真实非3D/engine能力fixture+1外部rand分支+8特殊子类公共段+3非法wire诊断。原codec/handler切片/复制器/shape flag写入/方向选择/actor能力getter/方向setter/向量写入均执行原字节。Adapter沿用旧IntroReplay的CRT/wstring、XML加载与属性ABI、外部sqrt；新增rand是外部平台依赖。engine actor/path是明确fixture，来源控制不是完整模型资源创建。

可供NPC所属窗口采用既有field48，保留原0作为原生哨兵；原资料值域与wire业务值域分开标注。Scene与尚未共享激活的Lifecycle要分别交付，不能借方向字段夹入strict-startup/动态控制片。发布前应对实际NpcScene输出经原完整SAddUserScreen decoder观察每实例field48，并保留不同key/重复ID/0值及错误输入的原子边界；已有方向研究不是这一步server投递验证。

未验证：所有3443实例完整原handler/构造/渲染、engine能力的真实生成、全部特殊子类后处理、原服wire选择政策、动态NPC运动/可见/权限、真人GUI、运行服投递与部署。本批没有任何游戏或数据状态变更。
