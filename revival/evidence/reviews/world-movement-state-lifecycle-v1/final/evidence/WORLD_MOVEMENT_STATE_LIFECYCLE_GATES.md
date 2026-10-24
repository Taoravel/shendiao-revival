# 移动状态的入场、屏障与剧情终止：原生证明边界

本批只新增本文与 `../verify_world_movement_state_lifecycle_native.py`。已沿用本批完整读取的 Matt Pocock research/diagnosing-bugs、根AGENTS、ARCHITECTURE与DESIGN_AUTHORITY：以第一方原指令建立事件偏序，用单变量prior/A/map反事实区分“收到包”“执行setter”和“当前仍为该状态”。既有35例状态转换文件保持冻结；未改生产/shared/政策或存档，未启动GUI、客户端、网络服务或真人玩法。结果不构成部署或实机验收。

## 结论

**目前没有一个已证通用上行，可以无条件宣告“当前场景成功且主角状态现在是0”。** 首入 C003d、普通SceneSendBarrier、首Start清黑幕、电影CEnd各自有更窄的含义；不能互相替代。已有普通成功Scene A0赋值是原生事实，但服务器何时据此建立一份可信state声明、何时撤销，以及特殊/未知分支如何恢复，仍须由main明确裁定并版本化。

本批初始7例、补充21例，最终 **28例离线原生验证全部通过**，stdout结构化输出：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_movement_state_lifecycle_native.py
```

本批事实可直接支持“在场景、租约、位置版本和相关转换范围内有条件声明”的架构，但不制定任何全图0默认值，也不把一个客户端无字段空包当服务端资源证明。

## 各事件能证明什么

|事件|原客户端事实|不足以证明|
|---|---|---|
|普通成功Scene A0|符合非1404/非516023等前提时，原+184→setter把+218写0|加载一定成功、所有后续状态仍0、输入可用|
|首入CAfterEnterWorld C003d|原Scene函数在reason516015的末段构造空body发送|精确匹配某次Scene/版本、所有地图都执行了setter、现在状态0、GPU可见|
|普通SceneSendBarrier|服务器实际发送结束的host事件，现政策明确designed|客户端已运行Process/资源成功、通用客户端ready、原生状态反馈|
|CG首Start|App+3d8清0、Scene+39c清黑层；既有原解析可达|电影结束或普通输入已允许、+218被归0|
|CG Return|请求恢复保留home资源/主角位置；本批原体重放不改218|原资源成功、所有辅助回调已结束、state归0|
|CEnd/manager cleanup|本批原cleanup发C0018且清manager+3c，不改218|完整演出期间从未改变218、回图必成功、state归0|
|JumpStop|已证由当前原maze flags与prior重选或保留218|报告byte等于最终state、终点合法、所有结果0|

## 首入 Scene A0 → C003d 的严格顺序与反例

沿 [SCENE_READY_NATIVE.md](SCENE_READY_NATIVE.md)、[SCENE_READY_RESEARCH.md](SCENE_READY_RESEARCH.md) 及 [WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md](WORLD_SCENE_MOVEMENT_STATE_RESEARCH.md)：

```text
SRoleEnterScene.Process 11e3140
  早退gate App+20 / Scene为空
  A严格等1归一 → 同步 Scene 11e21f0
    Scene+30/+34先写新scene（早于资源加载）
    load 11e0310 → AL保存到frame+17
    11e269b..26a5 加载失败跳11e2e7a，不走该末段确认
    reason516023 或 map1404 跳过+184赋值
    普通成功分支11e26dc → Main1213b80 → 1205c80写218
    其他场景/显示/初始化调用
    11e2d00 若reason516015 → 11e2d33发空C003d
```

本批分别执行原Scene加载后成功切片与原确认条件切片，3例最小对照：prior2、reason516015不变，map1100/A0结果0且ACK分支发C003d；仅A1则结果1且同样ACK；map1404/A0则**保留2且同样ACK分支发C003d**。这里是两个明确分开的原切片，不冒称中间大量UI/引擎调用已全部连续执行；静态原控制流证明1404跳过setter后仍进入同一后续主路径，并未改变reason。第4例reason0的原ACK分支不发C003d。

所以对于已知客户端、正确非特殊map和A0、成功走同一次Process，C003d在控制流上晚于该setter；但空body不含scene、A、位置版本、request ID或generation。接收端不能从任意空C003d推回“这是这次A0的成功确认”。尤其首次map1404、旧/重复确认、其他未证特殊路径不能获得相同声明。其余Scene处理中也存在虚调；本批不声称setter到ACK之间所有潜在间接写入已穷尽。

当前 `game_runtime.py`（本次读取SHA `ccd2bbdea1d1e40638e9553ce1236a7d115e037208fae92ffe36ea1a205c36e1`）AFTER_ENTER_WORLD分支在约424起，检查空body、拒绝正在普通transfer、joined则忽略，然后初始化joined/profile/NPC/任务/CG等。它不是精确initial Scene发送屏障，并没有原协议关联字段可以补造。这个源码观察不等同发布快照已改变或main应直接补某个state默认。

## 普通屏障与声明不能换名

普通reason0没有上述首次ACK，既有研究也未找到可证通用加载ACK。`SceneSendBarrier`/`scene_sent`是当前服务端设计契约，绑定连接generation、transfer、位置version和发送body；它能排除一部分旧Owner工作并保证已发送批次终止，但不能观察客户端load AL。源图声明何时失效、目标何时允许采用已发A0的状态，需要main按所有者/版本明确设计。没有原生证据支持把initialScene也假装已有同样屏障，或把普通C003d/心跳/CHECK绑成精确ready。

`SRelocateRolePos`→`CRelocateRolePos`是可观察当前位置/场景/布尔状态的独立渠道，仍不是ready。普通+13c=0时flag取218!=0；+13c=1/2时flag取3d6!=0并报告对应保存位置。报告会丢失原218=1/2/255的区别，并且没有唯一查询序号/场景世代。即使采用单未决查询和连接绑定，也属于额外server策略；不能未经裁定当成状态权威恢复或加载证明。

## CG完成会不会自动归0

本批 `StateReturn` 在原ReturnReplay的真实MainCharacter对象+218分别初始化0/1/2；原 Setmap wrapper12bc780→完整Scene11e0c70→原 Return12c0bf0→完整Scene11e0a80均执行，并监视所有覆盖该byte的写。随后单独调用原公开cleanup12c0970，令其manager active=1/movie11001，观察原send对象C0018/movie11001与manager+3c清0。3例均**保持原218且没有写入**。场景loader是既有捕获请求/返回成功Adapter，Scene辅助服务与UI/音频仍按旧夹具边界适配；这证明已执行的核心没有reset，不否认未执行的资源/辅助代码会影响角色。

这一补充没有假装原cleanup直呼等于完整播放或自然CEnd。自然原事件→Return/End队列→CEnd生产已经由 [WORLD_INTRO_DISPATCH_RESEARCH.md](WORLD_INTRO_DISPATCH_RESEARCH.md) 的11001受控0x7b8a4事件验证，但该批mainchar global=0，Scene恢复是Adapter。因此两批不能拼成“一整个真实主角电影自然结束且state0”。[WORLD_INTRO_RETURN_RESEARCH.md](WORLD_INTRO_RETURN_RESEARCH.md) 与 [WORLD_FIRST_PLAYABLE_NATIVE_CHAIN.md](WORLD_FIRST_PLAYABLE_NATIVE_CHAIN.md) 的资源请求与Owner链边界保持不变。

原 Start清锁12bc870只涉及App+3d8和Scene+39c，不直接写218。原CEnd cleanup12c0970主要发结束、清manager active/intro锁、恢复Scene显示；本批没有找到明确无条件state0赋值。CG dispatcher12c4140在有mainchar时还执行vt+b4、1140b50和1210030；既有原13例没有覆盖此主角存在分支。电影脚本后续演员/动作或其他本地转换是否会改真实主角状态，不由本批7例穷尽。因此保守事实是：**CG结束不是一个已证自动重置218的事件，也没有证明所有CG均保持218。**

若main选择在受授权CEnd后重新声明，必须将声明来源与条件单独标designed；不能将本批“未改”当native reset。若考虑补发真实SSetRoleLocation flag0，原handler确会写0，但它涉及位置/队列/伴随角色与特殊gate，既有纠正报告已说明不是无条件完整resync；是否采用及何时关联仍需main裁定，本批不新增发送或默认。

## JumpStop与必须保留的未知

冻结35例见 [WORLD_MOVEMENT_STATE_TRANSITIONS_NATIVE.md](WORLD_MOVEMENT_STATE_TRANSITIONS_NATIVE.md)。原12126d0读取同源map+84 maze；flags0/1→state1、8→0、flags同时含1和8则保留prior。越界或缺World map返回ffffffff，故两mask均命中也保留。fresh嘉兴墙byte11实际保留prior2，报告CRoleJumpStop.byte却在选择之前从3d6!=0生成。

所以单独收到JumpStop不能知道最终218，也不能拿该byte更新可信state；知道受信原grid和位置/模式还需要完整起跳/授权/结束生命周期才能复现其适用前提。当前只恢复普通地面移动时，拒绝/失效未知转换直到另有匹配声明，比假装已恢复跳跃生命周期更符合证据；这是一项需要main明确裁定的服务器处理选择，不是本文擅自下的新政策。

## main待裁定项（与原生事实分开）

1. 首次入场尚无精确发送barrier时，用哪一个服务器已提交/投递事实建立声明；必须记录其不是客户端加载ACK，并绑定login epoch/完整地址/位置版本/具体Scene投影值与前提。普通首次1404等不能套普通分支。
2. 普通transfer从源冻结到目标激活期间，旧state声明在哪个权威事件撤销；发送屏障后采用什么有界声明与拒绝规则。取消或失败不能继承其他scene的已知0。
3. 获准CG开始是否使旧声明失效，匹配CEnd后需要重声明、查询或显式纠正哪条策略；明确其设计来源、原特殊gate和未知演出限制。后续main/root已提出“匹配END持久后，以原SSetRoleLocation0重新声明并精确write/drain”的设计候选；下节只交此命令的原消费者验证，不把它提升成原服政策或部署状态。
4. 原Jump/JumpStop及其他未恢复转换是拒绝、保持unknown还是实现完整授权重算；不得仅按上行byte宣称已知0/1。

这些只给决策边界，不设置超时、自动解锁或全图默认，不新增第二个世界状态写入者。

## main新候选的原消费者纵切：显式位置/状态命令0

本节按main新增要求补21例，不修改冻结35例。对prior0/1/2分别执行三种Scene加载成功后切片：普通map1100/reason0、map1404、reason516023。先断言普通A0归0、两种特殊路径保留prior；**随后执行完整原SSetRoleLocation Process11d7a20**，输入原Pos(100,100)、byte0，进入主角1213b80/1205c80，再执行原getter/mask selector。9例全部state0、mask1、实际current(100,100)。前置Scene为旧资源成功切片而非完整地图加载；后置location Process和状态/位置setter原体执行。

因此“发了显式flag0命令后建立normal0”与“特殊场景天然就是0”是不同主张：本批只支持前者的受测对象/分支语义，后者仍无证据。location0不依赖Scene原来是否绕过A setter，亦不是将地图1404的原天然状态重新解释成0。

另6例分别令vt+158或+15c的原消费者通过role+2c0=1或+2cc=1返回true：原location Process仍写+218=0，原selector仍mask1，但 **actor current停在(8,8)，主角target+328已为(100,100)**。这是实际执行反馈，不是只看字段赋值；不得把state声明成功当位置纠正成功。main若补发currentpos，需保留命令与当时权威位置/版本的关联，不因这项测试取消原特殊gate或放过空间不一致。

最后6例role lookup为空或Scene global为空，prior0/1/2均保留，current仍(8,8)，没有位置命令成功。role lookup为沿用旧Reconciliation的明确查找Adapter（本批不重复Scene容器研究）；Scene null是原handler gate。`11d7a29..11d7a3c` 两处早退与结果一致。命令bytes经write/drain只证明投递终止，不保证目标角色已存在并执行这条赋值。

本节没有模拟END→服务器持久→发送屏障的Owner实现，也没有把普通命令重声明命名成client ACK。main新设计若采用此路径，其声明来源应记录“服务器显式normal0命令”，绑定完整地址/epoch/位置版本/实际发送终止；不得记成“客户端回报normal0”。原packet flag严格等1才1，其余值包括本候选0均0，沿用已证handler比较规则。

## 源码与未验证

原映像SHA `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

|文件|SHA256|
|---|---|
|本批lifecycle verifier（28例）|`2bde30c97d093f276cfdb4c8855cbe0bdad42059b5359d69ff4ad3ada3ee62a8`|
|verify_world_scene_movement_state_native.py|`3d0291df5fab9d1cb3962a4eee72e371a41ff594b283639011fed1594bcbe80e`|
|research_scene_ready.py|`60de991c1689bd9b87abaedebe9780f07629b71815f9c3f938021f998ae7d40f`|
|verify_world_intro_return_native.py|`fb5fc621085f65e913c69482ab38170ff1d0665da71a4c8556baafd0542b45e6`|
|verify_world_intro_dispatch_native.py|`dbe914b50cc6fedb0f757ca5841a5ad896c52724482604daf68a5c01d750682f`|

本批不重写上述依赖；stdout report同时记录实际hash。未验证完整Scene主函数、真实initial发送/ACK关联、原上层调度FIFO、全部CG演员/动作/辅助Scene、完整Jump授权和所有218写入者、原服务器规则或真实用户现场。原方法可执行事实、静态调用顺序、服务器designed声明选择始终分别标注。最终28例已重新完整执行PASS，未重跑或改写冻结35例产物。
