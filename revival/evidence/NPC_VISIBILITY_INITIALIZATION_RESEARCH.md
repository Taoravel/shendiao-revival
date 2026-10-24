# 普通 NPC hide 初始化与真实可见性门控

2026-10-24。本批闭合了此前消失研究留下的最窄初始化链：原 `cnpcconfig.hide` 数值写入配置 bean `+0x108`，普通 `CNpc` 从原配置 getter 查行并调用原复制器，将其保存为对象 `+0x258`。它是多值配置，不是最终可见 bool；实际可见 setter 写另一个字段 `+0x18`。原任务状态更新会按不同分支调用该 setter，同时保留 hide 原值。

本批按 [research skill](D:/User/Documents/Codex/.codex/skills/research/SKILL.md) 执行受委派的离线一手研究，先读 ARCHITECTURE、DESIGN_AUTHORITY、world_npcs.py 及旧消失研究。方法实际用于选择“字段读取→配置复制→真正可见 setter”的纵切，保留数值 0/1/2/4/5，避免按字段英文名或内存偏移猜可见性；任务资格未闭合时保持事实与服务端授权分开。只新增本文、研究脚本及 JSON/TXT，未改生产、政策、旧研究、共享入口、运行库或客户端，未操作服务。

## 来源与复跑

映像 `evidence/native-image.bin` BASE=`0x400000`，SHA256=`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。重新读取原 `artres/config.pfs`，每条经目录、解压长度、CRC 校验与 BXML 解码；所有 attributes/lists 与保存 catalog 逐项相等，不比较 XML 美化空白：

| 原条目 | 行数 | CRC32 | 解压 SHA256 |
|---|---:|---:|---|
| autoconfig/knight.gsp.npc.cnpcconfig.xml | 4127 | 3426975251 | b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85 |
| autoconfig/knight.gsp.npc.cscenenpcconfig.xml | 7592 | 3779954048 | b7198e7dfab00009aa9f2bc8d2b187d51ada4c7c84e4e68bd2f703a26027d852 |
| autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2460 | 1065007027 | ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706 |

从项目根复跑：

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B revival/research_npc_visibility_initialization.py
```

170 例通过：10 个真实定义的初始化赋值纵切、160 个原可见性分支案例。脚本生成 [JSON](npc-visibility-initialization-native.json) 和 [原反汇编 TXT](npc-visibility-initialization-native.txt)；`--disasm hide_loader|ordinary_init_lookup_copy|ordinary_config_copy|config_getter|hide_nonzero_predicate|visibility_update_entry|visibility_other_branches|visibility_setter|scene_refresh_caller|instance_refresh_caller|task_display_loader|task_display_vector_consumer|task_refresh_caller|disappear_compare|original_config_table_type` 可单独复读原指令。

## 执行：hide 字段到普通 CNpc +0x258

原字段名 UTF16 `hide@0x2265018` 在原读取段 `0xbaeccb..0xbaecf7` 传入字符串构造器，再交数值读取函数 `0x409ce0`，缺省参数为 0；真实原赋值 `0xbaecf7` 写配置 bean `+0x108`。本批数值读取函数只适配为该真实 PFS 行的 hide；字段名、读取调用参数和最终赋值均从原指令执行并观察。

普通初始化 `0x1201c44` 调原 getter `0x89df90`，后者实际取 `global[0x2945aec]+0x9e8`，再通过表 `vt+8` 按实例 info `+8` 的配置 ID 查行。`0x1201c56..0x1201c5d` 把返回配置交复制器 `0x11f3000`，目标明确为 `NPC+0x150`。

复制器的 `0x11f30e5..0x11f30eb` 执行 `source+0x108 → destination+0x108`，因此实际写入 `NPC+0x150+0x108 = NPC+0x258`。这个赋值没有被主机代码替换；与其不相交的字符串、vector 复制才使用依赖适配。分别先放置不同哨兵，要求 loader 与 copy 都实际覆盖哨兵。原 `0x11fc200` 的非零判据也继续执行，返回原 `hide != 0`，但这个函数不是把全部数值压成 bool 的配置 loader。

| 原 NPC | 名称 | 原 hide | loader bean+108 | 原 copy 后 NPC+258 | 原非零 predicate |
|---:|---|---:|---:|---:|---:|
| 10000 / 10003 | 张世杰 / 仓库管理员 | 0 | 0 | 0 | 0 |
| 10006 / 10017 | 李莫愁 / 门派传送人 | 1 | 1 | 1 | 1 |
| 10380 / 10142 | 女大夫 / 说书人 | 2 | 2 | 2 | 1 |
| 10259 / 10512 | 青年 / 公孙曌 | 4 | 4 | 4 | 1 |
| 10082 / 10083 | 说书人 / 说书人 | 5 | 5 | 5 | 1 |

本次原定义全表分布为 `0:2819、1:1268、2:29、4:3、5:8`。配置名 getter `0x87ecd0` 返回的原 UTF16 字符串为 `knight.gsp.npc.CNPCConfig`。这些证据闭合本字段真实配置来源，不把另一个也含 hide 文本的 loader `0xa6a192` 当作当前 CNpc 的 bean 布局。

**执行边界：** loader 段、初始化查行/复制段、非零 predicate 是明确手工连接的入口切片；不是原引擎完整调用时序。查表适配提供原配置身份；只对 hide 字段做真实 XML 数值读入，其他配置字段未逐一执行完整 XML loader。所执行的初始化切片在 `0x1201c62` 停止并进入 predicate，没有调用可见 setter。这只证明该切片负责配置复制，不能据此声称整个建模初始化不设置可见性、默认必可见或必不可见。

## 执行：hide 模式与最终可见字段是两份状态

普通 CNpc 虚表 `0x22985e4` 的 `vt+0x30` 指向 `0x11f6ee0`。本批实际执行原 setter：`0x11f6eef` 写 `NPC+0x18 = 传入参数低字节`，然后原代码检查次模型 `+0x48` 和主模型 `+0x44`，分别向模型 `vt+0x54` 传递同一参数。本批两个模型边界只记录，不伪造 GPU/绘制；setter 本体的赋值、条件、调用顺序都执行原字节。参数 0/1 是该原路径的实际调用参数，不等同已经看见/看不见真人 GUI。

原更新函数 `0x11fe390` 将第一实参保存到 `NPC+0x144`；`0x11fe41e..0x11fe434` 对它做 0..6 的原 switch。第二实参只按原字节比较是否恰好 1，完整业务名称尚未确认，本文称“调用方 flag”。本批进入完整原更新函数的 prologue，关闭无关电影覆盖条件，执行原 switch 与分支至台词/标记文字构造之前；没有用主机预期挑选跳转目标。

| 第一实参 | hide | 调用方 flag | 本批观察的实际 vt30 调用 |
|---:|---|---|---|
| 0 | 0 | 0 或 1 | 不调用，保留旧 +18 |
| 0 | 1 | 0 或 1 | setter(0) |
| 0 | 2 / 4 / 5 | 0 | 不调用，保留旧 +18 |
| 0 | 2 / 4 / 5 | 1 | setter(0) |
| 1..6 | 0 | 0 或 1 | 不调用，保留旧 +18 |
| 1..6 | 1 / 2 / 4 / 5 | 0 或 1 | setter(1) |
| 7 | 全部五种原 hide | 0 或 1 | switch 范围外，不调用，保留旧 +18 |

共 `5 hide × 8 第一实参 × 2 flag × 2 原 +18 初值 = 160` 个案例。每例都校验：实际 setter 调用列表、原 +18 结果、两个模型转发参数、+144 的状态保存、**+258 原 hide 始终未变**。状态 1..6 的其余标记文本逻辑未执行；不据 switch 编号自行命名“可接/完成/失败”等任务业务状态。

静态调用关系另记录：Scene 刷新循环 `0x11d366c..0x11d3693` 先从 `0x1258df0` 获取状态，再以第二实参 1 调此原更新；实例更新路径 `0x11d9ccd..0x11d9cf7` 同样先调对象实例更新 `vt+0x184`，再调状态提供者及可见更新。任务侧直接调用 `0x125a9aa..0x125a9af` 则传第二实参 0。本批未执行这些上层循环/实例完整构造或任务状态提供者，不能将原 flag=1 的局部效果直接认定为所有 NPC 进图的最终表现。

## DisPlayNPCID：确认直接消费者，未展开全部任务状态机

原任务表有 841 行非空 `DisPlayNPCID`，有序原列表完整保留于 JSON；如任务 100106 列出 10083，100110 列出 10006/10596/10597。列表本身不是服务端自动显示许可。

原 parser `0xbb6921..0xbb6941` 比较 UTF16 名 `DisPlayNPCID@0x226bd28`，匹配时选择任务 bean `+0x114` vector；`0xbb6afb..0xbb6b01` 交列表转换 helper。原状态提供者 `0x1258f52..0x1259022` 确实遍历对应 `bean+0x118` begin、`+0x11c` end，比较当前目标 NPC ID，还检查目标不等于任务 bean `+0x168`。匹配常规分支于 `0x1259005..0x1259017` 写局部结果 1，特定 ID `0x2b62` 写 2，并存在任务 ID/持久状态特例。

这一段说明显示列表参与**状态计算**，之后状态由上述调用者送入 `0x11fe390`；当前看到的更新逻辑调用可见 setter，**没有改 +258 hide 模式**。不能把列表存在、非空或某次匹配直接当作原整个状态提供者最终必返回 1：前后还有多容器、任务阶段及特殊分支。本批只对以上任务链作静态读取，未执行全部前置资格和列表解析函数；未实现任何服务器 DisPlayNPCID 自动显示政策。

## 与离场模式和活动/景物身份的界限

旧 [NPC_DISAPPEAR_NATIVE_RESEARCH.md](NPC_DISAPPEAR_NATIVE_RESEARCH.md) 已执行 `0x11fcc78..0x11fcc8c` 的 `NPC+0x258 >= 3` 门槛和 4/5 参数消费者，但将 hide 数值放入对象当 fixture，未闭合来源。本批补足了 loader/copy 的真实字段关系，因此已有 hide4/5 确为配置复制后可供该消费者读取的原值；**没有补足上层何时触发离场、是否全图 remove、任务回滚和重连的服务器授权**。>=3 的算术比较与可见分支中的 ==1、>1、>=1 都保留，不能将 +258 统一转换 bool 后继续解释离场模式。

7592 条 `CSceneNPCConfig` 景物独立经原 PFS 复核，但没有放入本批 CNpc 初始化或可见更新探针；原 `CSceneNpc` 与普通 `CNpc` 身份空间保持分开。`SAddActivityNpc` 列表已有研究只证明活动地图标签与配置 ID 去重路径，见 [WORLD_ENTITY_PROTOCOL.md](WORLD_ENTITY_PROTOCOL.md)；本批未执行该协议 handler，不能把服务器现有 `NpcScene.activation()` 输出视为已经修改普通 CNpc+258 或强制其最终可见。

`world_npcs.py` 当前保存 definitions 原 hide 字符串，静态摆放/活动编码本身没有本报告的原任务状态计算。研究不授权加一条 `bool(hide)` 过滤，也不撤销已单独设计开放的 10380/294 服务。服务器应何时展示公共/私有实例、向谁隐藏、何时重新验证交互及如何保存任务来源，仍由地图与角色所有权契约、明确政策和实际运行验收决定。

## 适配、产物与未验证范围

适配处：离线 Unicorn 映射原映像；外部字符串构造/copy/default constructor 边界；XML 数值读取提供真实 PFS hide；配置查表提供真实 ID 对应 bean；与 +108/+258 不相交的字符串/vector 复制；切片入口衔接；无关电影覆盖条件显式设为不在播放；模型 vt54 可见提交记录。原 hide 赋值、原 getter、原 copy 的数值赋值、原 predicate、原 switch/比较、原可见 setter 与模型转发条件都没有替换成主机算法。

产物：[研究脚本](../research_npc_visibility_initialization.py)、本报告、JSON、反汇编 TXT。170 例通过，三个原表全字段/列表一致。没有网络、数据库、服务或真实角色操作；未验证完整 CNpc 初始化/模型加载、默认可见值、任务状态提供者全部资格、活动协议显示、GPU、真人 GUI、服务器生命周期接入与部署。以上未证部分保持未完成，不用原模式值推定当前服务器已经完成全部 NPC 恢复。
