# MissionType22 道具使用任务：原上行、范围与完成显示

2026-10-23，Asia/Shanghai。沿用本批上下文完整的research技能：追溯原PFS、RTTI、parser、调用处和少量原指令，不从请求名字猜网络字段。已重读 `ARCHITECTURE.md`、`DESIGN_AUTHORITY.md`。当前为委派背景研究，不递归派代理。

本批约定只写本文：没有创建/修改.py、policy、catalog、共享入口、运行时或在线状态。必要探针以内联 `python -B` 运行，不保存脚本或pycache，不启动/控制当前客户端、服务或战斗。解除源码冻结的通知没有扩大本批写入范围。

## 结论与适用范围

1. **本映像未找到名为CUseScenarioQuestItem的RTTI或ASCII字样，不能为它虚构包型。** 已定位常规type25任务物品本地handler **0x10a5a80**；它最终仍构造普通库存 **CUseItem0xc03ff**：`BE i32 instance_key + BE i32 target_kind + BE u64 target_id`，共16字节。所查任务物品路径target_kind=0、target_id=完整roleID；**没有taskID、NPC、地图、坐标、数量或计时凭据**。[N1、N2、P1]
2. **58条任务中55条物品为itemtype25，另3条是itemtype73轻功秘籍。** 对0x10a5a80的控制流结论限于已查常规任务物品路径，不能扩大成58条全部使用机制。type73已定位独立QingGongMiJiObject类，但实际使用发送链尚未闭合，明确保留缺口。[S1、S2、N4]
3. 原物品 `CTaskRelative` 的准用地图/矩形与任务 `CMainMissionInfo.ActiveInfo*` 范围是两套资料。58条全部能联查TaskRelative，但其中41条的原地图/四边组合不同。不能以“可在此使用物品”直接证明该任务目标达成。[S1–S3、N1、P1]
4. 常规物品usemap>0时四边×16、左上包含右下排除，并检查精确地图。usemap<=0的一般分支跳过地图/矩形；**但50081/50029/50204/50205有先行特殊分支，不得概括为所有usemap0都任意位置可用**。本表涉及的50204会取特定任务的动态矩形。[N1、P1]
5. 物品readtime>0先开本地进度条种类2；其完成发送尾段仍发同一个CUseItem，**没有另一个“使用成功/CG结束/任务完成确认”上行**。这个本地等待过程本身没有给服务器提供可信经过时间或成功凭据。[N2、P1]
6. 原 `SUseTaskItemFail0xc4a53` 为空体，仅提示并清理本地交互；泛用任务完成仍通过已证实 `SRefreshScenarioQuestState` 等同步消费。**没有从客户端取得服务端扣量、扣除时机、战斗/动画与任务提交的完整规则**，不能把一次CUseItem当完成授权。[N3、S1]

## 一手来源

均从 `D:/神雕侠侣/artres/config.pfs` 经原记录长度/CRC校验、完整BXML直接重读：

| 来源 | 条目 | 解压字节SHA256 |
|---|---|---|
| S1 | autoconfig/knight.gsp.task.cmainmissioninfo.xml | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |
| S2 | autoconfig/knight.gsp.item.citemattr.xml | 974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f |
| S3 | autoconfig/knight.gsp.item.ctaskrelative.xml | f7fd09554140c4964a59fe59800d8da4a2a6630a5f29bc922a5d3ad7ff52b913 |

原映像 `D:/神雕侠侣/revival/evidence/native-image.bin`，base0x400000，以下均VA。既有同一映像SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本批没有重新采集运行进程。

相关既有证据：`INVENTORY_INTEGRATION.md` 的CUseItem目标含义、`TASK_DIALOG_PROTOCOL.md` 的状态显示、`TASK_REGION_OBJECTIVES_RESEARCH.md` 的type56范围；后者**不能直接充当type22服务端完成规则**。主线程另维护 `evidence/task-use-item-catalog.json`；本批不创建或覆盖该JSON。

## 原58条静态范围

| 项 | 原资料结果 |
|---|---|
| MissionType22 | 58条 |
| ActiveInfoUseItemID | 41种，全部能联查426条CTaskRelative表 |
| itemtypeid | 25:55条；73:3条 |
| ActiveInfoNpcID / TargetID / TargetNum | 全部0 |
| ActiveInfoMapID | 15种；0有8条 |
| 关联物品usemap0 | 按任务关联计数34条；其中有50204动态例外 |
| 任务范围与物品范围不同 | 41条（比较map/L/T/R/B的原值） |
| 任务ProcessBarTime | 0:53条；3:5条 |
| 物品readtime，按任务关联计数 | 0:14；1:10；2:12；3:12；4:1；5:6；15:3 |
| ScenarioInfoAnimationID | 0:51；其余10009、60013、10022、10008、11041、11046、60027各1 |
| ActiveInfoTimeLimit | 0:54；30:4（323002/323102/323202/323302） |
| RewardMapJumpType | 0:56；1:2 |
| AIInfoAIID非0 | 9条，不能按纯使用/纯对白一概完成 |
| FinishConversation非空 / NoteInfo非空 | 26 / 22条 |

物品类型73的精确例外：

| task | item | 原物品名 |
|---:|---:|---|
| 206104 | 50190 | 轻功一级秘籍 |
| 206204 | 50191 | 轻功二级秘籍 |
| 206304 | 50192 | 轻功三级秘籍 |

CTaskRelative有记录不代表所有itemtype都调用同一handler。类型、物品使用数据、任务目标和发物来源需要分别联查。

## N1：常规任务物品的准用判定

CTaskRelative getter **0x89da10** 返回配置root+0x728，原root初始化 `0xd42626` 写该表实现vtable0x2257d78。原handler入口 **0x10a5a80**，`0x10a5ae7–0x10a5af9` 以当前物品模板ID查此表。本文先前口头交流中“0x10a5a90附近”只是定位范围，准确函数头以0x10a5a80为准。

### 原字段/对象布局

| CTaskRelative字段 | parser存值地址 | 对象位置 |
|---|---:|---:|
| readtime | 0x873aa3 | +0x24 |
| readtext | 0x873abf–0x873ada | 字符串+0x28 |
| usemap | 0x873b16 | +0x44 |
| ltx/lty | 0x873b4c / 0x873b82 | +0x48/+0x4c |
| rbx/rby | 0x873bb8及后继parser | +0x50/+0x54 |

库存物品对象创建路径 `0x1080f6d–0x1080f9d` 将原readtime复制到物品+0x74、readtext复制到+0x78；getter `0x1072f20/0x1072f30` 正是后续读取本地进度条的数值/文字。任务表ProcessBarTime并不是这段物品handler读取的计时来源。

### usemap与坐标

- `0x10a5dd8` 读usemap；常规usemap>0转受限范围路径。
- `0x10a6001–0x10a6025` 读取CTaskRelative的四边，逐个 `shl4`，即×16后与角色逻辑坐标比较。
- `0x10a603c` 取角色位置；`0x10a6047` 调原矩形函数 **0x5f8240**。
- 该函数 `0x5f8246–0x5f825a` 是 `L<=x<R && T<=y<B`，左/上包含、右/下排除。
- `0x10a6054–0x10a6060` 还比较当前地图与usemap是否相等。
- 常规usemap<=0路径对几个特殊ID排除后，直接到 `0x10a5e0f` 判断readtime，不读位置或矩形。50065为本批已执行原指令的样本。

**特殊ID不得省略**：50081、50029、50204、50205在 `0x10a5de3–0x10a5e09` 有先行分流。它们可以从任务/物品实例生成动态地图和矩形。对于本批涉及的50204，`0x10a5f4d–0x10a5f94` 从323002开始按100递增至323302查active任务，首个找到后读该任务ActiveMap与四边，再×16到共同范围判断。它不是在usemap0时跳过所有限制，也不使用50057那种较大的CTaskRelative静态矩形。

### 50057的两套范围：直接反例

原炸药50057：CTaskRelative `readtime=3, readtext=填埋炸药, usemap=1013, ltx/lty/rbx/rby=76/47/145/80`。物品准用逻辑像素范围 **[1216,2320)×[752,1280)**。

原任务102109：ActiveUseItem50057，目标map1013，任务四边 **80/55/90/65**，即若按这些字段作位置目标则为[1280,1440)×[880,1040)。102110和102111/102119还有各自小矩形。

P1的位置(x1300,y800)会通过50057物品准用检查，却不在102109的小矩形内。这证明不能把本地CUseItem合法发送直接当102109的正确埋炸药结果，也不能简单把两套范围合并成一种。

### 任务矩形在客户端的另一消费者：提示而非完成包

原函数 `0x1257f30` 扫active任务，以MissionType整除10的商==2筛20–29类；匹配任务地图后，`0x1257fcb–0x1257fe5` 四边×16，`0x1257fee–0x1258002` 同样半开判断。命中时 `0x125802e` 调交互/UI函数，`0x1258033–0x1258040` 把ActiveInfoUseItemID(config+0x1ac)交 `0x1749260` 的本地UI/引导消费者；本段没有构造网络包。

这只证明任务小范围参与本地提示/引导。**未找到原服务端使用此范围完成type22的比较代码**；因此不把type56的“全零矩形不命中区域轮询”推广成“type22全零范围绝不能使用/完成”。例如物品50065的usemap0普通路径就不依赖该任务矩形来允许玩家发使用请求。

## N2：实际使用包与本地时条

### CUseItem 的原布局

RTTI `.?AVCUseItem@item@gsp@knight@@`，vtable0x2277200；constructor **0xd986f0**，原type0xc03ff；marshal **0xe4d740**，decode **0xd987a0**。辅助构造器 **0x10729f0** 接收并写入相同字段。

```text
BE i32 instance_key | BE i32 target_kind | BE u64 target_id
共16字节
```

原marshal `0xe4d776/0xe4d781` 写两个BE i32，`0xe4d790` 写BE u64。原validator检查实例key>=1、目标ID为非负signed64域，未给target_kind做完整业务枚举验证。已知目标种类0为角色、1为指定宠物的调用证据见库存研究；**不存在由本批证明的“任务使用专属target_kind”**。

普通任务物品直接发送路径 `0x10a60ca–0x10a610a`：从当前库存物品对象取+0x14实例key，target_kind写0，target_id来自人物+0xf8/+0xfc的完整角色ID。不是物品模板ID，不是NPC key；该字段与同宽u64的其他协议字段不能互换。

### readtime与时条完成

readtime<=0时直接构造上述CUseItem。readtime>0时 `0x10a6068–0x10a60c5` 或无地图限制的 `0x10a5e11–0x10a5e81`：

- 将物品实例key作为进度条关联值；
- 将readtime整数转浮点，readtext交UI；
- 以本地进度条种类 **2** 调 `0x8114a0` / `0x16c4140`。

`0x16c4140` 把传入duration写+0x4c，清已累计+0x44；update `0x16c49c0` 累加引擎frame事件+0xc的浮点delta，达到duration后调用 `0x16c4490`。本批没有继续证明该上层delta的物理单位，故原readtime3/2在本文保留为本地duration原数值，**不将秒/毫秒换算伪称已由本批完整核验**。已确认此链没有先×1000，也不把它编码进网络包。

种类2完成尾段 `0x16c4627–0x16c478a` 再取角色完整ID、保留关联实例key、target_kind0，经 `0x10729f0` 构造并发 **同一个CUseItem**。不是CQuestDialogEnd、CEndPlayCG或另一个“时条已完成”包；本地等待结束后的使用意图仍可被伪造/重放，不提供服务器可信经过时间。

204102是不能混用两个计时字段的原反例：任务ProcessBarTime3，但物品50122的readtime2。50057的两个字段恰好都是3，不能据此以为它们永远同义。

## N3：失败回包与任务完成链的边界

`SUseTaskItemFail@task` vtable0x227e920，type **0xc4a53**（构造0xdde1e0附近、type写0xdde1e8）；marshal0xdde200/decode0xdde210为空body。Process **0x1254ef0** 在UI/交互实例存在时取原提示文本ID0x22910，通过0x156d130显示，`0x1254f33` 调0x10ee140清理交互。它没有taskID/itemKey/失败原因数字，不能据此反推出成功奖励或具体扣物规则。

本批未定位专用“UseScenarioQuestItem成功”回包；通用 `SRefreshScenarioQuestState0xc4a47` 仍负责原任务状态显示，state1在 `0x125c020` 删除active任务后按配置优先FinishConversation、其次NoteInfo、最后后置表现。value同步0xc4a49是另一个原消息，不等于使用包自带进度。

58条中26条有FinishConversation、22条有NoteInfo、7条有AnimationID，表明完成显示不应统一当空通知。但没有证据要求所有type22必须先收到CQuestDialogEnd或CEndPlayCG才能结算；它们属于特定对白/CG消费者，本地时条使用链不发这些包。动画/AI非零任务的后续授权仍需分别调查。

原handler返回al=1至多表示UI处理了本次操作，不能解读为任务完成。服务器可能发失败、状态变化、库存变化等不同逻辑消息，**原服务端如何组合与何时原子提交未在客户端证实**。

## N4：轻功秘籍type73的有界缺口

原映像有独立 `.?AVQingGongMiJiObject@@`，vtable0x228c2a4，构造路径0x1074260附近；其数据序列化与普通任务物品对象不同。本批未闭合这三本书从实际右键操作到发包的完整路径，不能仅因它们也存在CTaskRelative记录，就套0x10a5a80的usemap/readtime控制流。

因此CUseItem常规任务物品发送证据适用于所定位type25路径；206104/206204/206304暂保持独立缺口。没有为它们猜CUseScenarioQuestItem、轻功学习协议或任务自动成功条件，也没有把“RTTI中未找到某名字”提升为所有版本绝不存在该协议。

## 扣物与奖励：明确不能推断

原资料直接反例：102108奖励50057×3（bind1），后续关联使用节点是102109→102110→102111→102119；102111还带AI8039，102111和102119目标矩形相同。**四个节点不等于每次必扣1**，否则原发放量无法直接对齐。原服可能存在战斗前后/失败/重新掩埋等时序，本批没有其服务端消费实现。

102396(type22)的原奖励又列50065×1（bind1），也不能把一次使用机械实现为“先扣当前1件，再按同名奖励补1件”，除非完成事务与物品实例语义另获确认。

CUseItem无数量/任务ID/请求nonce字段，原TaskRelative的bCanSale、CItemAttr.maxNum、readtime或usemap均不能自动证明扣除数量/是否消费。服务端需要根据权威实例、模板、合法任务阶段、地图位置、AI/动画政策、版本与租约建立独立使用授权/结算；客户端包不能授予该权限。训练/wild战斗或普通库存消耗成功也不能替代特定type22任务结果。

## P1：少量原指令验证，不落源码

以内联 `python.exe -B -X utf8 -` 执行，全部断言通过：

- 原CUseItem constructor/marshal/decode roundtrip，synthetic实例key123、target_kind0、roleID0x1122334455667788得到 **`0000007b000000001122334455667788`**，长度16；
- 真实直接发送片段0x10a60ca–0x10a610c与进度条种类2完成构包尾段0x16c4627–0x16c478c，都捕获同一CUseItem(123,0,完整roleID)，没有另造任务完成包；
- 执行真实CTaskRelative矩形消费与原5f8240：50057左上(1216,752)通过、x2319通过、恰右边2320不通过、恰下边y1280不通过、错误map1012不通过；
- (1300,800)通过50057物品准用，但明确不在102109任务小范围；
- 50065/usemap0样本直接到readtime判断，没有读取当前位置；这不是50204等特殊物品的测试结果。

host adapter仅提供内存配置对象、角色位置/ID、网络发送捕获；代码在命中/拒绝或发送后停止。没有真实进度条计时、GUI、库存使用、扣物、服务器响应或当前客户端执行。本批未测试type73实际使用、特殊50204动态任务选择的全部边界和任何原服消费规则。

## 交接与唯一写入记录

产物仅为本文。原58条/41物品完整审计归主线程的独立JSON；本报告不覆盖其输出或增加已加载catalog。写入时间随最终文件元数据在交接消息精确报告。

已确认：常规任务物品真实CUseItem正文与角色目标、物品准用范围×16半开比较、usemap一般/特殊分支区别、readtime与任务ProcessBarTime分离、本地时条完成仍发使用包、空体SUseTaskItemFail、通用任务完成显示边界。

未确认：type73完整使用链、原时间单位的上层delta契约、所有特殊物品UI路径、原服务器物品消费数量/时机、地图/任务目标之间的完成规则、9条AI关联的可信战斗时序、7条动画授权、任务回包/库存同步精确先后、重连/重复使用事务及真实GUI。没有把这些缺口填成猜测实现，没有任何在线状态变化。
