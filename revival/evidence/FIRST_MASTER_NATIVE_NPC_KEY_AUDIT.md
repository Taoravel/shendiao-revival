# 首师父实机交互：原生 NPC key 审计

**最新现场方向已改变**：后续人类截图在古墓坐标109,46能够打开陆无双对话，原文为“你现在还没有完成此任务。”。下文早期key/距离候选只保留历史排查，不代表当前仍卡在NPC访问。本批追加原生追踪将这句精确定位到**任务UI分类2的进行中提示**；普通type10的state0会走此提示，state3才走Start对白。当前优先核对实际任务ID、state3下行和Start对白链，停止扩张距离数值猜测。详见文末最新追加。

**后续原生反馈已红→绿**：独立`research_task_existing_quest.py`已证已有state0再收SAccept3仍state0/UI2；Accept3后再收SRefreshState3才state3/UI3。该确定的原接收行为可解释目前实现重复Accept3无法打开Start的错误模式；修复后的生产部署/人类点击尚未由本文验收。

2026-10-23。本批只读原映像、原地图/PFS、当前world_npcs/world_entity_protocol及已有原生证据，唯一产物为本文；未读取在线角色数据库、操作当前客户端/进程、改共享入口或地图Module。已读research和diagnosing-bugs两份SKILL、项目AGENTS及此前已读ARCHITECTURE/DESIGN_AUTHORITY。工作区根未找到GLOSSARY.md。

## 当前能确认什么

**不能把“原静态NPC点击发NPCconfigID，而服务器只认大key”写成已定位原因。** 原npc.xml没有key；所追SAddUserScreen创建的CNpc会保留服务器给的完整64位key，后续原请求路径也不截断为配置ID。SAddActivityNpc只提供配置ID和位置到地图标签路径，本轮没有发现它创建可点击CNpc或为CNpc改key。

所以合成验证用`(mapID<<32)|placement_id`可以证明服务器自己发行的key在自己绑定中可用，**不能证明人类点击时发出的实际key等于它**；反过来，截图中有NPC/任务追踪，也不能证明客户端生成了configID key。需要一条实际解密CVisitNpc的完整8字节和ValueError具体原因才能缩小现场失败分支。本研究没有这条实际body，未宣称重现115次错误或已经找到现场根因。

diagnosing-bugs的“能使同一现场故障转红的反馈环”在本批尚未建立：本任务明确只读离线研究，未获实际payload/具体异常文本，不能用另一条合成key通过来代替。本批执行的是原生身份保持的窄离线对照，未进入生产修复、实机回归或宣称故障关闭。

## 陆无双的原配置、摆放和合成key

原`artres/map.pfs`条目 `map_1100_gumupai/npc.xml` 经PfsArchive.read本地/中央目录、解压长度和CRC检查，再BXML解析：54条、2819字节，CRC32 `80cd63d1`，SHA256 `d6b6644e6db00944372f6d07cc104a58b3e597ae291229544ee070134b08b3e8`。

古墓派任务师父陆无双为NPC配置 **10014**；原摆放为全表第44条：

```xml
<record id="10014" posx="1764" posy="765" dir="5" />
```

原`knight.gsp.npc.cnpcconfig`10014：npctype1，modelID6088，name陆无双，foottitle古墓派任务师父，mapid1100、xPos110、yPos47、hide0。这里的config坐标与npc.xml坐标不同，不可把110/47作为最终实际像素交互位置。地图第2条10058是“古墓派首席弟子”，**不是陆无双**。

同名NPC另有10445（hide1、map0）、13321（hide1、map1006）、13655（hide1、map1012）、13664（hide1、map1627）；本轮古墓1100的实际摆放唯一命中10014。按当前`load_placements`一基顺序，placement_id=44，题设合成key为4724464025644，BE64 body是`0000044c0000002c`。若客户端实际发送配置ID10014，其body会是`000000000000271e`。这两个十六进制值是便于核对的**候选**，不是现场抓到的body。

npc.xml这54条的属性只有id/posx/posy/dir，没有q64实例key或mapID高32位的规则。因此`(mapID<<32)|placement_id`是服务器发行策略，不能称为原客户端静态key算法。

## 原SAddUserScreen如何保留key

第一方映像 `native-image.bin` SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。已有WORLD_ENTITY_PROTOCOL记录原codec，本批重新检查实际process和对象key读写：

1. NpcBasic对象+8是完整q64 key，+0x10是NPC配置ID；在STL node内分别为node+0x10/+0x14与node+0x18。原SAddUserScreen handler `0x11e7124..0x11e7131` 将node的两32位原样写内部info+0/+4，`0x11e713f..0x11e7142` 另写配置ID到info+8。二者没有混用。
2. `0x11e7227..0x11e7235` 将此info交 `0x11d9c70`；后者`0x11d9cb5..0x11d9cbe` 按info+0/+4完整key查NPC实体索引。缺失时`0x11d9ed8..0x11d9ef7` 分配CNpc，构造虚表为0x22985e4；`0x11d9f14..0x11d9f1f` 交虚槽+0x184初始化。
3. 虚槽+0x184为`0x1201bd0`。其`0x1201c36..0x1201c3f` 先用`0x11fd140`复制info到对象+0x100区域，保留两32位；随后`0x1201c77..0x1201c85` 从复制后的info取原key，交对象虚槽+0x3c。
4. CNpc虚槽+0x3c指向`0x1174ee0`：只把两个参数写对象+0x10/+0x14。虚槽+0x38指向`0x1174ed0`：从对象+0x10/+0x14返回EDX:EAX。不做配置ID替换、取低32位或加地图号。
5. 场景“按配置查NPC”的另一路`0x11d1870`遍历NPC实体，比较对象+0x150（NPC配置ID）；这不是key getter。任务查目标配置后取得对象，再取对象key，可以正常使用服务端大key，不能把这个config查询误读成网络key=配置ID。

由此可证：**经本轮追踪的SAddUserScreen创建路径，若服务器发大key，原CNpc对象保存并返回相同大key**。未证明当前现场究竟接收/显示了哪一个对象、是否已有重复对象或命中另一条受保护点击路径。

## 原CVisitNpc从哪里取key

- CVisitNpc构造`0x120eea0..0x120eebd`写type0xc2329、原两个i32到bean+8/+0xc。原marshal`0xe52020`是已有证实的非负q64体（8字节），没有mapID或NPC配置ID字段。
- 原任务/NPC衔接路径`0x1644c8f..0x1644c9e`取得目标CNpc虚槽+0x38的EDX:EAX，再原样传上述CVisitNpc构造。这里读取的是对象完整key。
- 另一原NPC UI发送路径`0x164936b..0x16493a2`从UI+0x38/+0x3c取保存的两32位，构造并发送CVisitNpc。其保存对象的来源需另追，不可将这两32位自行命名为configID。
- 映像中还有0x29c/0x29d区域的受保护/跳转混淆调用片段。本轮没有完整解释它们，未把已读的任务/UI路径说成人类鼠标点击的全部调用链。

窄离线对照已运行一次：Unicorn执行CNpc真实虚槽+0x3c setter和+0x38 getter，分别输入10014与4724464025644，输出严格相同，并给出上述BE64候选体。运行结果：`10014→10014`、`4724464025644→4724464025644`，两例断言通过。只替换对象/栈内存，不替换原指令。该probe只证明身份保存，不产生实际点击，不能作为现场绿灯。

## SAddActivityNpc与原npc.xml消费者

SAddActivityNpc handler`0x1230b20`的两个vector是配置ID与Pos，不是key。`0x1230bd8`按配置ID查活动项；`0x1230c12..0x1230c2d`按配置查NPC定义；`0x1230cda..0x1230ce8`向地图标签容器（this+0xc8）追加项，再`0x1230d17`刷新。此直接路径没有CNpc分配/初始化调用，也没有写CNpc虚槽+0x3c。之前将activity activation当作3D实体发放的假设不能从这个包获得支持。

原`/npc.xml`字符串地址0x2297270。已读`0x11dab..0x11dad..`、`0x11dae..0x11db0..`、`0x11db1..0x11db2..`、`0x11db4..0x11db5..`的几个消费者，它们读id并按NPC配置/类型筛选，再读取posx/posy返回位置；没有为这一路配置行生成q64对象key。`0x1230329`附近也是读取文件后构建地图标签；另`0x11df5c6`附近按id构建地图相关位置容器。

这证明本轮找到的npc.xml消费者并不提供题设静态key算法；**不构成“客户端绝不本地生成静态实体”的全映像否定证明**。本轮仍未找到并闭合“原静态NPC本地加载→CNpc实例key生成→人类点击”完整原生链，因此静态key为configID、负configID或其他值都不能作为已证修复前提。

## 服务器当前校验与下一条有效证据

当前`world_npcs.NpcScene.interact`先检查请求期限、expected/current位置快照及active场景，再检查角色位置可用，解8字节key后查`_bindings`；缺key抛`Unknown NPC entity key`，之后才有NPC位置可用与距离检查。`world_entity_protocol.read_visit_npc`另可能抛体长错误或负key错误。顶层只记ValueError不能区分这些分支。

需要由获准的集成窗口采集一条：CVisitNpc解密body的8字节十六进制、当前场景/map及位置version、具体ValueError文本、这次绑定的目标key和placement。只采这条信号，无需暴露登录凭据或全量日志。之后可在隔离临时环境用同body回放真实interact，并保持原位置/版本/绑定条件，形成现场错误能转红的回归；不能再用验证脚本自己生成大key替代真实body。

候选解释及可证伪预测（不是已定位原因）：

1. **客户端对象key与server binding不同**：真实body解出的key不在当前绑定，具体异常为Unknown NPC entity key；若body恰为已绑定大key则否定这一解释。
2. **距离/位置坐标不同步或单位/世代不同**：body是合法已绑定key，但异常为range、stale scope或invalid position；改key不会解决。
3. **客户端重复/旧对象或服务器场景绑定生命周期错误**：真实body指向先前发行对象，当前场景绑定已替换；需将同key的下发/离场/场景世代与当前关联对照，不能不校验直接接受任意配置ID别名。
4. **报文长度/解码错误**：实际body非8字节或为负key，发生在绑定查询前；原生体及当前decoder的独立比较可排除。

这些解释尚未通过同一现场反馈环验证；本文只交原证，不授权放宽绑定、忽略距离、让客户端注册静态映射或同时绑定含歧义的NPC配置ID。任务的实际第一步可玩仍以真实点击→合法NPC事件→任务菜单/对白为验收范围。

## 方法、验证及未验证

research实际从原包摆放/配置与NpcBasic原字段、CNpc key setter/getter、原请求构造交叉核对，拒绝从名字或画面推出key。diagnosing-bugs实际决定是保留“缺真实payload的红环”这一缺口，将具体异常与8字节body作为下一条必要信号，不把合成测试作现场证明。

已验：map1100原npc.xml CRC/BXML和陆无双唯一摆放；原SAddUserScreen完整key数据流；两个原getter/setter用例；SAddActivityNpc直接消费者。未验：全部本地静态实体加载/受保护点击路径、115次live错误的具体分支、实机body、生产修复及当前客户端通过。本批未运行在线服务或修改任何生产Module。

## 追加：截图位置与原交互距离的调查

根任务补充的人类截图读数为古墓派cell `(102,51)`。若仅作`×16`估算，角色逻辑坐标约`(1632,816)`，原陆无双摆放为`(1764,765)`；两者距离为`√(132²+51²)=141.5097`逻辑像素，而当前服务器NpcScene采用欧氏radius32。这说明“原客户端已发visit，但服务器距离策略更严或位置不同步”必须进入优先核对范围；**截图取整坐标不是当前服务器authoritative Location**，不能直接当已经复现range异常，更不能据此宣称正确原半径一定是160或200。

本轮继续扫描CMainCharacter原生区域中的整数/浮点比较并追各自用途，所得可排除的误读：

- `0x12189dc cmp eax,0xa0` 位于Windows输入消息switch，之前`0x12189d7`减消息基数0x201；不是160像素交互距离。
- `0x1215f40..0x12160a0` 确有从两个实体位置计算欧氏距离并比较double208.0（常量0x2299330）；但近距离分支`0x121606a`构造type **0xc07e8**，不是CVisitNpc0xc2329。不能将该宠物相关操作距离208迁移到NPC访问策略。
- `0x1212240..0x121237d` 的180.0比较限临安map1007、特定NPC10565及角色等级条件；它不构成陆无双普通访问阈值。
- `0x1217dbd` 的48.0比较属于另一实体操作/跟随分支，本轮未追得其为CVisitNpc专用判定；也不能代替已知服务器32政策。

已确认的任务/UI CVisitNpc构造路径没有在发送紧邻位置统一检查一个160/200半径。人类鼠标点击的自动接近/到达后发visit还有受保护/跳转混淆路径，本批未闭合，故原客户端**普通NPC自动接近的停靠阈值、单位及是否允许141.5像素直接发送**仍未知。这里是明确研究限制，不发布猜测数值或建议放宽生产半径。

下一条现场最有区分力的证据现在应同时包含真实`key`与两端位置/平方距离及具体异常：若body已绑定且拒绝原因为range，key算法假设即可暂时排除；若body未绑定，先处理key/生命周期；若位置/场景版本stale，则距离估算也不足。当前原生研究与截图只改变了排查优先级，未代替这一反馈环。

## 最新追加：原“还没有完成此任务”明确属于进行中分支

根任务最新传入的人类截图：古墓坐标109,46，陆无双对话明确显示“你现在还没有完成此任务。”，右侧tracker仍为`[主线]序章缘起 去拜见任务师父陆无双`。这推翻了“现在完全无法打开NPC对话”的继续假定。具体任务ID及收到的状态包仍未由截图证明，不能据中文同名代替ID。

原文本来自 `artres/config.pfs → autoconfig/knight.gsp.message.cmessagetip.xml`，id **141714**（hex **0x22992**）、type1、msg精确为`你现在还没有完成此任务。`。本轮直接PFS长度/CRC/BXML校验：展开2516503字节、CRC32 `b6871af3`、SHA256 `d0cfc9cb4613442be0bb8ec9262bf6db7f2c7fcb5ad28df05e150c4b0503fa20`。

原生直接调用链：

1. `0x1257b20`是任务UI分类器：有ScenarioQuest bean时，若任务配置MissionType==40（0x28），或bean.state==3，返回分类3；其余返回分类2（`0x1257b44..0x1257b66`）。普通type10的state0和旧state2都不是可交付分类3。
2. 对话分派 `0x164d846..0x164d84d` 仅在UI分类==2时调用 `0x164b2a0`，即进行中提示。此函数对少数type11/12/13专门处理；普通type10走fallback `0x164b4df..0x164b4f8`，**push 0x22992查原141714并显示**，正是截图这句。
3. UI分类==3则走`0x164d865..0x164d873`，设对白phase2，再调用 `0x164b530`读取任务原 `ScenarioInfoNpcConversationList`（Start）。这与进行中提示是不同分支，不能把“有NPC对话窗口”当Start对白已经成功。

本轮复用了既有research_task_display.classify的lookup适配，离线执行原`0x1257b20`两例：`type10/state0→UI2`、`type10/state3→UI3`，均断言通过。不启动客户端、不落新脚本/输出文件。结合精确message ID的原调用，最新截图强支持**点击时本地任务被归为分类2，尚未进入该任务Start对白分支**，但没有证明此bean的真实任务ID、服务端已发/未发哪个state或生产源码/部署版本。

当前下一步证据应改为：本次SVisitNpc第二vector实际任务ID、客户端已持有同ID的ScenarioQuest state、是否先送同ID state3再送任务菜单，以及本次点击的菜单分类/Start资源匹配。若服务端只发state0接取后从未对合法拜见任务送ready3，原截图提示正与原分支一致；若已送3，则核对不同任务ID、后续覆盖、部署与刷新顺序。上述是可证伪方向，不是本报告对未见报文的断言。

此后不再把109,46的新状态套用102,51旧截图的距离估算，不建议放宽半径或增加configID别名作为当前修复。实机成功标准仍为真实点击陆无双→正确任务Start对白→原卡授权等自然后续，而非“读到了一个NPC窗口”或合成脚本通过。

## 最终追加：已有任务不接受重复Accept覆盖状态

根任务发现当前open_master_dialogue输出为`SAcceptScenarioQuest(bean state3) → SVisitNpc`，且该任务之前已以state0在客户端建立。原指令与离线反馈现在闭合这一错误模式：

- SAccept process `0x125d5c0` 从packet+0xc取任务ID，`0x125d5cd`调用`0x1257ac0`查询已接bean；`0x125d5d2 test eax,eax`，`0x125d5d4 jne 0x125d5e5`，**已有bean立即return，不覆盖state、value或key**。只有缺bean才`0x125d5e0`调用`0x125d070`。
- SRefreshScenarioQuestState虚表0x227e4e0的process为`0x125ea00`，交任务ID/state到`0x125e660`。非另外两种任务时进入scenario方法`0x125c020`，查询原bean；找到后`0x125c0ee`从参数取新state，**`0x125c0f5 mov [eax+8],edi`真实覆盖bean.state**。state3继续经过原后续分支与UI通知返回。

在根任务明确授权后，新增独占的`../research_task_existing_quest.py`，没有改master/cart生产模块或既有验证。反馈命令：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_task_existing_quest.py
```

实际输出：

```text
原输出 Accept3 → Visit：Existing quest 100186 remains state0/UI2 at SVisitNpc
候选纠正 Accept3 → Refresh3 → Visit：state3 / native UI class3
```

这不是Python模拟“Accept忽略/Refresh覆盖”：Unicorn实际运行完整原Accept handler、原Refresh handler→dispatch→scenario state writer及原UI分类器；只hook外部查表与UI副作用（0x125a950、0x10907c0），未替换测试分支/状态写。任务类型10的配置lookup、现有bean和空显示NPC列表为受控fixture；wire体先用既有Python codec解码后装入原对象布局，本脚本未重复验证原unmarshal。

公开测试Interface `assert_ready_before_visit(messages,task_id,*,initial_state=0,quest_type=10)` 可直接消费生产master/cart逻辑包序列：每个Accept/Refresh都走原handler，到目标任务的Visit菜单时以原分类器断言ready3。目标菜单未出现也失败，不能只检查包能decode或最终有一个state3字段。返回trace/目标访问次数/实际bean state/UI class供现有验证纳入证据。

因此，保留Accept作为缺bean兼容、在其后Visit之前显式Refresh3，是本反馈已转绿的候选消息顺序。它没有证明具体生产输出已经改好、已部署、人类GUI已进入Start/卡授权；这些由主任务继续沿实际第一步验收。已有的key/距离研究不再作为当前故障解释。
