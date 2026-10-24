# 电影 Return 的地图身份、资源与位置恢复

2026-10-23；沿用已读 Matt Pocock research 的后台第一方研究及 diagnosing-bugs 的单变量反事实。已读根 AGENTS、ARCHITECTURE、DESIGN_AUTHORITY。本批只新增独占脚本、结果、本文；没有改已冻结 intro dispatch、生产/共享/政策/配置/存档，没有启动客户端、服务或 GUI。

产物：[verifier](../verify_world_intro_return_native.py)、[八例结果](world-intro-return-native.json)、[原指令](world-intro-return-disassembly.txt)。映像 SHA-256：`2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

## 结论

**原 Return 请求参数1009是正确的电影当前地图身份，不是恢复目的地。** 在真实原方法中，1100入场→电影1009→Return(1009)，最终提交 engine world loader 的目录是 `map_1100_gumupai`，maze是 `map_1100_gumupai/maze.dat`，位置来自保留的主角引擎位置。旧 dispatch fixture 保持 Scene+110=1100并非这里的夹具错误；其 Scene恢复 Adapter 截断了这条后续链，不能从所捕获的1009推断错误恢复。

本批执行原方法直至 engine load 边界，补齐**原恢复请求的身份/路径/位置来源**，仍不是实际图形加载、地图显示或点击移动验收。不得把旧 dispatch 的自然 CEnd结果与另外的 home-map点击fixture拼成“已在真客户端返回原图”。

尤其不能“修复”manager+40或Return参数为1100：只改这一项的反事实使原 Return走“不需reload”分支，留下movie地图，正好破坏原行为。

## 三种身份及原调用契约

| 保存位置 | 真实职责 | 原地址与行为 |
|---|---|---|
| Scene+110 | 角色当前场景配置的map ID | 原电影Setmap/Return不覆盖此字段；本批原场景ID和resdir是fixture初始化状态，被测方法执行期间监视写入，未重放登录/入场来源 |
| Scene+168 | 上述原场景配置的resdir | +168 = +110 + CMapConfig.resdir偏移+58；原表parser `0x879f4e..0x879f78`用`resdir`字段读入bean+58 |
| MovieManager+40 | 电影当前所在地图，初始为原Scene ID | `0x12c4341..0x12c434d`从Scene+110保存初值；每次Setmap后`0x12bc7a2`写本次movie目标ID |

`0x12bc780(movie_target_id,x,y)`先读取旧manager+40，调用：

```text
Scene::0x11e0c70(movie_target_id, previous_movie_map_id, x, y)
manager+40 = movie_target_id
```

因此第一次1100→1009，原调用四参数为 **[1009,1100,240,2192]**；第二个1100表示上一个电影场景身份/初始原场景，而不是“将原场景字段设为1100”的setter，也不是另一个服务端传送请求。若随后电影切到1007，第二次四参数变为 **[1007,1009,240,2192]**。

`0x11e0c70`的第一参数进入CMapConfig表getter `0x89dd50` 的虚表+8查询；原复制器 `0xc34710`把结果放入**栈局部临时配置**。`0x11e0dbb..0x11e0de7`比较第一、第二地图ID：

- 不同：原 `0x11e0e28..0x11e0e64`用临时配置resdir构建`resdir/maze.dat`，请求engine world load，位置采用x/y；不改Scene嵌入原配置。
- 相同：`0x11e0e9e..0x11e0f17`调整当前world camera；不重载map资源。这条相同分支也实际执行过。

本批内存写入监视断言：上述原方法执行前后，Scene+110至+183（含ID和resdir所在区间）无原指令写入。保留原图身份/路径并非Adapter主动改回。

## Return实际加载哪个目录、使用谁的位置

原 Return section start `0x12b99d0`进入 `0x12c0bf0`。后者在清电影资源后，从**当前manager+40**取值，传给Scene **`0x11e0a80(current_movie_map_id)`**。

Scene Return原流程完整执行，关键位置：

1. `0x11e0ac7..0x11e0ada`通过主角虚表+d4取位置对。
2. `0x11e0adc..0x11e0aec`比较**Scene+110**与传入的**当前电影地图ID**。
3. 不同则 `0x11e0b5e..0x11e0b8e`取**Scene+168**，拼接常量`0x2296cb4=/maze.dat`，把原主角位置对放入point参数，调用world虚表+4原load入口。
4. 相同则 `0x11e0c23..0x11e0c43`只恢复camera跟随主角的render对象；不reload目录。

因此1100/1009不同触发的调用为：

```text
directory = map_1100_gumupai
maze_path = map_1100_gumupai/maze.dat
position  = 主角vt+d4输出的位置对
flag      = 0
```

这里**没有用Return参数1009查恢复目的地配置**。若原场景为临安1007，同一Return(1009)请求目录变为 `map_1007_linan`。

主角真实RTTI `CMainCharacter` 的vt=`0x2299344`，+d4=`0x12060d0`。本批使用原虚表、真实getter和普通未骑乘分支，继续执行 `0x11f6450`，后者从主角+48的引擎角色对象调用虚表+38取实际位置。仅这个引擎对象的虚方法是Adapter；没有host替换整个主角getter。原getter还含骑乘/其他角色位置分支，本批未覆盖其全部模式。

fixture引擎位置选择 **[1800,1200]**，所以Return请求相同位置；只把该引擎getter的输出改为 **[1920,1280]**，Return的位置也随之改变，而电影camera位置仍是[240,2192]。这否定“Return恢复电影开场位置或把movie落点当主角坐标”的解释。**这些是有意区分来源的测试值，不是原服出生坐标、服务端逻辑坐标或发布默认值。** 原入场`0x11e0386`会把逻辑x乘1.5后交给引擎；本批没有重放完整入场，也没有把这里的引擎像素直接作为wire位置写回。

## 八个已执行反事实

| case | 原Setmap后 | 原Return时实际world load请求 |
|---|---|---|
| home1100→movie1009 | Scene配置仍1100/home，manager40=1009 | **home1100**，位置[1800,1200] |
| home1007→movie1009 | Scene配置仍1007/临安，manager40=1009 | **home1007**，同一主角位置 |
| home1100→movie1009→movie1007 | 第二次previous参数=1009；Scene配置仍1100 | **home1100**，不是最后movie1007 |
| home1100→movie1100 | 相同地图分支；只调整camera | 不reload；维持home1100 |
| 仅把Scene+110改为movie1009 | Scene.resdir仍home，manager40=1009 | ID相等，**跳过load并留movie1009** |
| 仅把Scene+168改为movie目录 | Scene.id仍1100，manager40=1009 | 真的加载movie目录；说明恢复路径来自Scene+168 |
| 仅把manager+40改成home1100 | Scene配置仍home1100 | ID相等，**跳过load并留movie1009** |
| 仅改主角引擎位置输出 | Scene、manager、movie不变 | 加载home1100，位置随getter变为[1920,1280] |

后三种身份突变仅存在离线counterfactual内存中；没有注入客户端。每例原Setmap/Return后都有Scene原配置区无写入断言，不仅对照最终对象快照。

## Seam与Adapters

这是在已冻结 [WORLD_INTRO_DISPATCH_RESEARCH](WORLD_INTRO_DISPATCH_RESEARCH.md) 自然队列证据之后，针对原请求1009的窄下层契约验证。新脚本继承该研究的堆/字符串/GUI等库Adapter，但**覆盖掉旧脚本对`11e0c70`和`11e0a80`的整方法Adapter，保留并执行这两个原函数体**。原manager构造、Setmap wrapper `12bc780`、Return wrapper `12c0bf0`、CMapConfig复制器、普通MainCharacter位置getter也执行。

原PFS重新读出CMapConfig的1007/1009/1100记录；配置表getter/lookup提供typed bean，读取到的resdir使用原值，其他未被本链读取的字符串置空，不声称完整配置加载。**Scene+110的origin ID与Scene+168的origin resdir均由fixture提供初始状态，不能算真实登录/入场初始化的原生证据。** 被测原`11e0c70`内部执行`c34710`将movie配置复制到栈局部，随后Movie/Return原体不覆盖所监视的Scene配置区；这两项才是本批有关配置复制与保留的验证范围。即便fixture建立初态时调用原复制器，也不提升为真实入场路径证明。

明确保留的边界：world虚表+4 loader捕获目录/maze/point并返回成功，外部camera/调度器接口、引擎截图texture、临时电影camera actor创建/可选缺失分支、Scene移除临时actor/transition effect/goto重建为Adapter。world loader的host状态投影只用于辨别“本次请求home还是movie”，**不代表地图已从磁盘成功装载、异步timer已完成或GPU已显示**。Return后`11dec90`的真实goto/场景内容重建不在本批执行范围。

原动态`Setmap`没有改Server Owner位置，Return也没有在本文生成跨图网络包。不能自行把临时movie scene ID写进角色持久化或强行发一个新home入场来替代此原恢复链。服务端授权、自然CEnd与实际客户端点击，仍应各自保留验收范围。

## 验证

```powershell
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' revival/verify_world_intro_return_native.py
```

实际执行 exit=0：`cases=8, passed=true`；Python编译通过。原13例dispatch脚本保持冻结，未修改或重新定义其结果。本文回答原Return传1009的原因，并补可复跑的恢复请求证据，未宣称真实地图/坐标/点击已经端到端验收。
