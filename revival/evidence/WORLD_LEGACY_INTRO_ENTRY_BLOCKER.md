# 首测阻断：旧角色无剧情却收到原生开场锁

## 最新共享源码已转绿，运行服/GUI仍须单独确认

主集成后当前GameRuntime为 `ccd2bbdea1d1e40638e9553ce1236a7d115e037208fae92ffe36ea1a205c36e1`，已含无章节intro1。父窗口直接运行 `verify_world_legacy_intro_entry.py --release-source D:/神雕侠侣/revival --report-suffix shared-current` exit0：真实隔离Owner登录后原intro/普通移动predicate不创建该黑幕、锁0、可移动，亦能清旧intro锁。记录 `world-legacy-intro-entry-shared-current.json`。未伪造剧情/任务，其他门控显式清除；不由此宣称GUI或当前服务已修复。后文0d36/72d7候选均保留同快照红→绿历史，首测状态应合读WORLD_SCENE_TERMINAL_CURRENT_ACCEPTANCE。

## 2026-10-24追加：主集成修改后的最新0d36基线复验

`verify_world_legacy_intro_candidate.py --base-source D:/神雕侠侣/revival --label source20261024r2 --with-native-check-arrival` 已通过。同一私有副本基线 `0d36cf6a940afdcb903c338f6e5a0fb48c48bb537276de824a3146db744bff25` 原旧角开场锁红；只改无章节intro分支0→1，候选 `0ab2e485f3bc058e80e3b78121b888cc97e737aacea675ae5913851391f23184` 旧角安全绿、新章7组及同原对象END/MOVE/完整定时CHECK/STOP/存档重连绿。1882份副本文件、140份静态import模块绑定。最新补丁 `world-legacy-intro-source20261024r2-candidate.patch` 与报告同前缀，current-interface.json已指此版。下方72d7及更早基线保持历史，不应覆盖主集成后续修改。

这是独立的一行intro候选，和WORLD_SCENE_DELIVERY_SUFFIX_HANDOFF的三批次清理候选分开提供；两者均未由世界修改shared或发布。主策划另针对实际不可变发布做的独立红绿以其报告为准，不能用本源码候选替代真实运行身份与GUI验收。

## 2026-10-24：最新共享源码同快照仍红，最小候选已转绿

重新执行 `verify_world_legacy_intro_candidate.py --base-source D:/神雕侠侣/revival --label source20261024 --with-native-check-arrival`。当前基线GameRuntime SHA256 `72d7f787f087ac6fc887d1d3534731d12d234267bb4b0bcf6e620fd46e7260e5`，精确一行候选 `711e8aed6a7ba4bec01a26d3c4bdf5c2224c15fbb0bbfddb2971272e0a53f9c8`；共享源码仍未改。报告 `world-legacy-intro-source20261024-candidate-verification.json`，可直接审查补丁 `world-legacy-intro-source20261024-candidate.patch`。

同一私有副本在替换前真实旧角色登录→原decoder/开场slice/predicate得到unsafe_entry_reproduced=True；只改无章节分支0→1后safe_entry=True，没有播放帧或虚构章节/奖励。两新章7组和同一原对象END/MOVE/完整定时CHECK/STOP/存档/重连全部通过。副本1808份静态文件、137个实际静态import闭包模块均有哈希；执行后基线仍与当前工作区相同。它已经包含本批NPCv2/剧情pool共享源，不能继续用832038旧基线候选作为最新字节。

此缺口只约束**无持久新手章节的旧角色**，不否认新建角色原开场/自然剧情已经通过的验证。真实发布仍由主集成统一处理，世界没有部署、启动游戏、操作真人角色或宣称当前GUI已修好。读此节可取最新补丁；后面早期哈希/PID均为历史，不代替当前发布身份。

## 当前源码复验与接线位置（2026-10-23）

最新同一快照红→绿和完整定时CHECK/STOP候选结果为 `world-legacy-intro-current-check-candidate-verification.json`、补丁 `world-legacy-intro-current-check-candidate.patch`；复验用 `--label current-check --with-native-check-arrival`。该次已在替换前实跑同一私有源码的blocked反馈，再替换精确一行跑安全/两新章7组/实际Owner移动重连；不再仅依赖不同采样哈希的红反馈。基线/候选GameRuntime哈希仍为下文832038…/f04f5f…，共享文件未改。

当前源码已能正常导入；早期 task_conversation ImportError 已不是当前阻断。默认旧角安全检查在当前源码仍实跑退出1：无章节角色收到 intro0，原客户端黑幕与普通移动锁复现。

已更新 `verify_world_legacy_intro_candidate.py --base-source D:/神雕侠侣/revival --label current --with-native-arrival`，在独立临时副本通过旧角安全检查、两新章节7组，以及原生 END→MOVE→自然 STOP→存档→重连。结果为 `world-legacy-intro-current-candidate-verification.json`。本次候选的基线 GameRuntime SHA256 为 `832038f63f1df10536ebdba0f58503813e013f20b57570c97b292d1d3cf424b1`，候选为 `f04f5f6ff87b79d0172840d31e07816f8420e3db4ea0964edd7dceabafba98b6`；之前当前源码红反馈采样哈希不同，不冒称两次完整源码完全一致。

供共享集成方应用的当前补丁为 `world-legacy-intro-current-candidate.patch`，仅涉及 `RoleOwner.handle(load)` 中读取 newbie_state 后的一行 intro 选择（当前约270行）：无章节分支0改1；已有章节分支及 growth_snapshot 保留。世界窗口未修改共享文件；补丁不涉及 MapOwner/NpcLifecycle、NPC关仓、wild或battle区域。副本按实际静态导入闭包119模块及配置建立前后围栏，原生映像一并固定；报告保存1527份快照文件哈希。

只读检查时，本地运行进程10076使用 `runtime/deployments/wild-20261023T110855Z/run_release.py`；该发布源码仍为无章节 intro0。**当前候选通过尚不代表运行版已修复，也尚未做GUI验收。** 首测门槛仍是共享集成、必要回归和统一发布后，验证旧角画面/点地与新角本门派开场/结束移动；无需等全量地图完成才安排首测。

候选包装本批修正了静态映像副本缺失与快照围栏覆盖无关并行文件的问题；这些属于离线验证工具，不计作游戏根因。自然到达保存到 `(1100,1504,1152)`，重连保留；不据此扩张为真实客户端渲染或完整新手剧情已验收。

2026-10-23。**实际固定发布源码的隔离运行已复现：无章节旧角intro=0，原客户端创建黑幕且拒绝普通移动；同次登录无SStartPlayCG。** 服务器newbie_pending=False不能证明客户端可移动。本缺口应先于全地图扩展处理。

最小修正候选已在私有临时发布副本验证通过；共享源码、固定发布、运行进程和真实存档均未修改。共享修正及政策确认/发布归原集成窗口和主策划；候选绿不等于现场修复。

## 可重复反馈

```powershell
# 退出0表示准确复现缺口，不是可玩通过。
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_legacy_intro_entry.py --expect-blocked --release-source 'D:/神雕侠侣/revival/runtime/deployments/20261023T063445Z/source'

# 相同旧发布的默认安全检查已实跑退出1。
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_legacy_intro_entry.py --release-source 'D:/神雕侠侣/revival/runtime/deployments/20261023T063445Z/source'

# 仅私有临时副本应用一行候选，旧角及两新章检查已实跑退出0。
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/verify_world_legacy_intro_candidate.py
```

当前工作区初次执行遇到task_conversation导入不存在的supports_npc_progress，未修改任务模块或假称工作区已跑原生检查；随后明确转向固定发布的完整源码复现。这个ImportError不是黑屏反馈。共享接线后不带 `--release-source` 运行第一脚本默认模式，必须绿。

## 实际观察及原指令范围

公开AccountStore在安装章节政策前创建legacy角色，不删除新角色chapter、不手改出生/任务。再走真实runtime_storage.prepare、GameRuntime、加密GrowthPeer.login。真实SEnterWorld由原0xfe4630 decoder解码，所得对象交原0x83380a..83384c开场分支及0x1211db0普通移动predicate。

|观察|固定发布旧角色|私有候选旧角色|
|---|---:|---:|
|持久章节 / 服务器newbie_pending|无 / False|无 / False|
|原decoder得到intro q64 +48|0|1|
|原Scene+39c黑幕创建|是|否|
|App+3d8即global2945438|1|0|
|原普通移动predicate|拒绝|允许|
|实际SStartPlayCG / 任务journal|0 / 空|0 / 空|
|实际位置|1007,8480,6976|1007,8480,6976|

另执行只改变intro q64的原指令反事实，黑幕/移动锁随之消失。真实EXP槽+f8独立，不用XP=0推断新手；没有给旧角补root、完成章、奖励或改位置。其他独立门控在fixture中明确清除；这证明该开场锁因果，不证明真实加载/鼠标/渲染全部正常。

追加原指令检查从初始App flag1收intro1，实际清为0且输入允许；83381c置bl0、83382b无条件覆盖该标志。因此不能声称必须重启才清App锁。该fixture仍未证明旧Scene黑幕容器的完整销毁/重连渲染；不据此承诺同进程画面即时恢复，也不向在线内存写0或发无授权假CG。

## 集成候选与界限

共享RoleOwner.handle(load)当前分支：

```python
intro = 0 if self.newbie_chapter is None else self.newbie_chapter.intro_discriminator
```

候选只把无章节分支改为1。已有章节仍由持久phase投影pending0/完成1，pending后续必须得到可信播放。补丁 `world-legacy-intro-candidate.patch` 待原集成方接线。

这是“无授权开场不请求客户端开场锁”的线Adapter候选，不将旧角持久章节标completed。主策划确认该恢复约定后由原集成局部修改；不在world_snapshot编码器里猜角色来源/XP、吞掉显式0或普遍改所有调用者的默认值。

候选脚本读取固定发布，复制代码及完整静态design/catalog/evidence到私有TemporaryDirectory，只替换精确一行。旧角安全检查默认绿；另调用既有verify_newbie_runtime.check执行古墓/少林两自然新章7组，不覆盖root自有报告。pending intro0/匹配CG、错误/截断/重复END、并行心跳/地图、pending重连、completed重建intro1、任务与原0XP均保持；没有通过统一跳过新手让检查绿。

候选包装最初两次缺__file__相对静态资料，补完整静态副本后通过；这些是fixture缺失，不计为生产根因。没有复制或访问真实角色数据库。

## 证据与下一完成条件

- `world-legacy-intro-entry-baseline-release.json`：旧发布unsafe_entry_reproduced=True。
- `world-legacy-intro-entry-verification-release.json`：旧发布默认检查实际红，safe_entry=False。
- `world-legacy-intro-entry-candidate.json`：私有候选实际登录/原指令safe_entry=True。
- `world-legacy-intro-candidate-verification.json`：精确替换、原/候选哈希、两新章7组结果及范围。

基线game_runtime SHA256为 `3e9e60da29e2ba4da4cac2d5a281523e99408d4246856d9c3dc6df5bf541323f`，原映像为 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。工作区同一分支由只读源码确认，但私有副本结果不冒充当前shared或运行进程已绿。

完成条件：主策划记录legacy Adapter约定→集成修当前shared并过默认反馈及新章必要检查→统一发布→用户验旧角首次可见/点地、新角本门派开场/结束移动。当前未执行GUI/客户端启动、部署、真实角色读写或战斗，完整世界目标继续。

方法：diagnosing-bugs把实际服务器入场接原客户端锁判据并以单变量验证；codebase-design保留任务持久章节、共享选择线投影、世界原codec/判据的归属；writing-for-agents共置红反馈、可审候选、验证范围与真正发布条件。
