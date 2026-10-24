# 嘉兴10083：100160与100106的原NPC显隐边界

2026-10-24。本批按research Skill后台委派做有界原生复核，复用[PROLOGUE_NPC_VISIBILITY_RESEARCH.md](PROLOGUE_NPC_VISIBILITY_RESEARCH.md)已定位的消费者。只读原PFS/BXML和原映像，内联Python `-B`执行隔离原指令；唯一新增本文，不改module、policy、shared或运行环境，不接触现场客户端、线上/真实DB，不运行战斗。

## 已执行的最短反馈

**对NPC10083，原mark结果依次是6、0、1、1。后继缺失不等于完成对白时必定隐藏。**

| 合成Scenario集合（其他任务集合均空） | 原1258df0返回mark | hide5 / flag0 | hide5 / flag1 |
|---|---:|---|---|
| 100160 active0 | 6 | 设为可见 | 设为可见 |
| 100160移除，无100106 | 0 | **保留原可见byte**：原0仍0，原1仍1 | **设为隐藏** |
| 100106 active0 | 1 | 设为可见 | 设为可见 |
| 100106 ready3 | 1 | 设为可见 | 设为可见 |

这里mark是NPC任务/显隐标记，**不是**Scenario bean的state。active0/ready3仅指该bean的原状态；未采用此前错误的active2。

实际执行了4个原完整计算器样本，以及mark0/1/6 × flag0/1 ×初始可见0/1共12个原可见分支样本。没有用Python条件替代原判定或直接写入期望输出；断言只核对原执行后的EAX与entity+0x18。

## 原字段、地址与校验

原`config.pfs/autoconfig/knight.gsp.task.cmainmissioninfo.xml`：2026233字节，CRC32 `3f7ab7b3`，SHA256 `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`。本批直接重读并BXML解码：

- 100160：type10、ActiveNpc10083/Map1006、Animation0、Process0、Jump0；Start3句、无Finish/Note，DisPlay=[10212]，原唯一Post=100106。
- 100106：type10、ActiveNpc10498/Map1006、Animation0、Process3、Jump3→1501 raw63,79；DisPlay=[10083]，原唯一Post=100107。
- 因而100160是“10083为任务目标”，100106是“10083为额外显示列表成员”，不是相同mark路径。

原`config.pfs/autoconfig/knight.gsp.npc.cnpcconfig.xml`：619832字节，CRC32 `cc437e13`，SHA256 `b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85`。10083为说书人，npctype4、hide5、Map1006；导航xPos21/yPos140不替代实际摆放。

原`map.pfs/map_1006_jiaxing/npc.xml`：3571字节，CRC32 `51217023`，SHA256 `72b66cc70e41d78997fb8369c74c5f21a69f500e790797718a41d56ff857752c`。10083实际record原序3，posx348/posy2244/dir3。

地址均绑定`revival/evidence/native-image.bin`，50675712字节，BASE0x400000，SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

### 原mark与可见性消费者

- 0x1258e6f..0x1258ecb扫描Scenario active集合。0x1258ecd先比config+0x168目标NPC；type10且任务ID在原主线范围时，0x1258ef9..0x1259027返回6：对应100160。
- 不等于目标时，0x1258f52..0x125901f扫描DisPlay；100106的10083在0x1259005..15设置mark1。它不属于本函数三个特殊任务state3分支，active0与ready3均返回1。
- 无相关bean、其他集合为空时，0x1259bec返回默认0。实际已完成日志不属于这里的active集合；本样本移除100160，而非保留一个state1 bean冒充完成移除。
- 原11fe390 mark0分支0x11fe43b..0x11fe473：hide5>1，仅flag1时调用vt+30(false)；flag0跳过可见性setter。mark1分支0x11fe478..490、mark6分支0x11fe5a6..5ba在hide>=1时调用true。
- CNpc原vtable0x22985e4的+30为**原11f6ee0**；0x11f6eef写实体可见byte+18，并向模型/附件传播。此次保留该真实虚函数，模型/附件设空，仅隔离GPU边界。

### 哪些已知调用使用flag0/flag1

state1 handler125c020先125bb30移除active bean，再125a950重算目标（0x125c10a..117）；125a950在0x125a9aa明确push0，于0x125a9af调用11fe390。因此若只有这一段mark刷新，原先显示的hide5不会因mark0立即变隐藏。

正确接收100106时，125d070的DisPlay循环0x125d1c3..217对10083调用125a950并尝试1132590；mark1会显式show。1132590只为npctype10创建本地type7实体，10083为type4，不代表新建或删除服务器NPC。

正常CNpc创建/更新入口11d9c70汇合于11d9cda，0x11d9ceb重算1258df0，0x11d9cf2 push1后0x11d9cf7调用11fe390；场景批量恢复11d3620也用flag1（已知调用者12c0a4d为电影结束路径，不能冒称所有场景加载必调）。所以“无相关任务时某次flag1重算会隐藏10083”有原代码依据，**但本批没有现场证据证明真人对白之后实际发生了哪个flag1调用**。

## 完成后置的额外边界，不能仅靠mark推出GUI因果

100160原无Finish/Note/Animation/Jump，state1还会进入1255e70 fallback，按ActiveNpc查实体并可能调用**11fcc50**。本批只定向读了这一已知邻接函数：它在entity+28c为负且hide>=3时查询89dfa0返回的配置；hide5分支0x11fccde..11fcdb6把记录+4/+8各左移4，调用动作/实体/model相关方法并写内部时量字段。它不是上述mark setter的同义函数，未在此执行完整运动/生命周期。

另重读原`cnpcdisappearconfig.xml`，10083为para1=1/para2=149（626字节，CRC32 `59c595b2`，SHA256 `dd5dd417c2aa545662ce2ec05161ac3722597994a2ac3dbbc0e10e6ef730b852`）。**本批没有闭合89dfa0配置getter到该原表记录及完整运动/tick的桥，不据字段名把该数值宣称为现场消失/移动原因。** 不扩扫此分支，也不把mark范围的结论写成整个state1没有其他表现。

此外电影override（11fe3c9..3e4）、网络实体移除/重建、模型/场景实际状态、其他任务集合优先级、服务器NPC是否仍存在与允许交互，均不由本表单bean样本证明。源场景NPC本地可见性与服务器实体/交互授权、私有实例归属继续分开。

## 实际方法与未验证范围

复用`research_task_jiaxing_scenario.Probe`的离线映射、配置getter与原执行设施，内联构造manager+18/+24/+30/+3c四个sentinel集合；分别写入原任务的type/目标/DisPlay及state0/3，query key=0/NPC ID10083，执行**完整1258df0**至返回sentinel。getter只适配原表字段的内存位置，未替代原分支。

本批所读Probe脚本SHA256：`0ff37e3c5c4625007c8c1d14a768d50a32fe0580003ff7407d9f251f22475a47`。

显隐反馈执行上述三个原switch arm，ESI=CNpc样本、EBX=0、hide5，原虚表保留11f6ee0；flag写在原分支读取的栈位+cc，分别从可见0/1开始，在文字资源边界前停止。结果即首表；没有创建客户端窗口、加载模型或发送协议。只读工具源码，不调用会写输出的main；未另存研究.py。

父任务已提供“冻结旧runtime里100160完成后100106缺失”的独立证据；本批没有读取现场DB或重演旧runtime。这里证实它会改变此单bean条件下的mark，并证明后继正确同步时mark1路径可show；**没有证明它与真人画面消失构成充分因果，也不宣称入口修复已使GUI恢复。** 入口修复不依赖扩大本研究，继续由main按既有授权接线/验收。

唯一产物本文。已执行4+12原指令样本；未验证完整state1/对白/模型tick、NPC实际位移、网络到达顺序、所有静态loader、当前角色/其他任务组合、GUI、在线发布或战斗。

## 有界延伸：完成后置确有独立的位置/运动命令路径

本节追加于2026-10-24；保留上述原4+12样本及当时未闭合范围。沿89dfa0、11fcc50和紧邻typed-table/位置转换接口定向复读，新增两个隔离原指令样本。**现在已闭合getter的原表身份以及NPC ID查询键；这条路径不能归并为“无后继导致mark0隐藏”。但未证明真人画面中的实际位移、消失或删除原因。**

### 配置身份与记录选择（原代码已确认）

- 89dfa0直接返回`[2945aec]+9f0`。原配置根初始化d42fe0..d42fef在该位置写入vtable225ad00与ca0930返回对象。
- 225ad00的原RTTI为`knight_gsp_npc_CNPCDisappearConfig_table_implement@XMLCONFIG`；ca0930于ca0956使用UTF-16字面量225ad10 `knight.gsp.npc.CNPCDisappearConfig`。这由原初始化、RTTI和工厂实参三者闭合，不按文件名猜getter。
- 该typed table的slot+8为87eeb0，转发到内部cache的slot+8。原file cache构造b08290写vtable2268ee4，其getter为b083e0；原memory cache构造c42ee0写vtable226d204，其getter为c43660。对应原RTTI均带`CNPCDisappearConfig@npc@gsp@knight`。
- 11fcc9d..11fccb2在原typed getter上传入`entity+150`的NPC模板ID。对本例为10083，而非任务ID100160或任务后继100106。记录id=-1时走11fceab缺记录分支。
- b08380..b083c5的原记录decoder依次写id到+0、两个i32到+4/+8，之后+0c为字符串；c436cd..c436d1返回tree节点+10的record地址。本次直接重读原PFS得到10083：para1=1、para2=149；同成员CRC/SHA与上文一致。

精确剩余边界：本次没有驱动完整XML属性名→record加载器，也未定位其逐属性赋值，因此“para1/para2名字严格对应record+4/+8的顺序”仍未由独立原XML解析执行证明；下面数值样本明确采用该原行按此顺序的内存适配。已确认的原消费是record+4/+8，不能把这项适配省略成已实测原客户端加载结果。

### hide5如何消费两个值与时量（原指令/两段反馈）

原11fcc50仅在entity+28c<0且hide>=3时进入；先写内部值1000。hide5分支11fccde..11fccfd取record+4/+8，**分别左移4（乘16）**，形成目标数值。11fccf9..11fcd18读取CNpc当前位置并计算到这两个目标的距离平方。

随后11fcd1f..11fcd2b调用CNpc slot+50，实参为动作号26和float1.0；11fcd2d..11fcd39调用slot+130，实参0。后者原11f6dc0会写entity+50并转发附件/actor接口；本节不把0命名为隐藏或销毁开关。

model指针entity+44非空时：11fcd42..11fcd6f将距离平方交给19196a4外部数学入口，再以原double常量2291b50=2000.0作除法，向model slot+154传float。本次未执行该外部数学函数、未把它的结果或2000擅定为“秒/速度”。11fcd71..11fcdb1继续把目标第一分量乘原float2923784=1.5，并由666b90作float→i32截断；1172b50把所得两个整数、0、0转交model slot+170。最后11fcdb6将entity+28c写为**1500**。1000/1500是已证内部整数，**本次没有tick/单位证据，不等于已证1秒/1.5秒**。

实际执行的新原指令反馈：

| 样本 | 执行范围/隔离边界 | 原输出 |
|---|---|---|
| A | 11fcc76→11fcdc0；保留原89dfa0和87eeb0 typed转发，只适配cache查询、位置读取、动作/actor边界；model设空 | 查询key10083；动作(26,1.0)；模式实参0；栈目标(16,2384)；entity+28c=1500 |
| B | 11fcd71→11fcdb6；输入A的目标(16,2384)，保留原666b90与1172b50，只在model slot+170截获 | 实际收到整数位置(24,2384)、尾实参(0,0) |

两样本均断言通过。B绕过距离/slot+154阶段，并非完整11fcc50或完整模型运动模拟；A的当前位置边界仅注入合成数值，不证明原placement与CNpc位置getter属于同一种坐标表达。此处原乘16和模型第一分量乘1.5是**这条hide5消费者自己的原指令事实**，不推广为世界传送/任务RewardMap的坐标规则。

### 对本问题的准确结论与仍需边界

100160的state1 fallback可能查到10083并调用本函数；在上述原门槛满足、记录有效且model存在时，客户端确有“取本NPC的Disappear表记录→位置数值变换→动作/位置接口”的独立路径。因而原节点具备命令说书人朝另一个位置处理的依据，不能将对白后“消失”单纯归因于100106缺失。此前mark6→0与正确后继mark1的4+12反馈仍准确，回答的是另一条可见性路径。

这里没有证明slot+170后模型最终抵达、1500到期后的处理/删除、GUI是否离屏、原NPC可交互性、服务器实体生命周期或真人当时走了哪个路径。也没有证实完整XML字段装载顺序、完整完成包时序、model/tick/GPU或现场因果；达到本次有界研究终点，不扩扫。

本次实际方法：定向原映像反汇编/RTTI和已知工厂链复核、原PFS成员重读CRC/SHA、内联Python -B复用既有Probe映射执行两个原片段；没有改写原指令或以Python实现替代其分支/乘16/乘1.5/截断。只有cache/引擎边界适配，无新研究.py；唯一写入仍为本文。无module/policy/shared/运行时写入，无客户端、在线服、真实DB或战斗操作。
