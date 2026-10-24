# 私有场景投递终止路径审计

2026-10-24。本批按根AGENTS、ARCHITECTURE及Matt Pocock research/diagnosing-bugs/codebase-design执行：先读当前实现和既有验证，以实际公开投递Interface建立确定性取消反馈，再用正常对照区分终止路径。根窗口是共享入口唯一写者；本窗口没有修改shared、政策、旧验证或运行服务，没有GUI、真人、战斗、socket或真实角色数据库。

初始授权仅本文，根任务随后明确授权新增独占[research_world_scene_delivery_abandonment.py](../research_world_scene_delivery_abandonment.py)及结构化结果，供同一私有snapshot红→绿验证。**本文不是生产修复完成声明。**

## 已执行发现：批次中尚未入队的后缀丢失终止所有者

**当前源存在P2可用性缺口：整批私有回复先取得ticket/pin，在首条容量拒绝的cleanup等待处取消producer，未offer的余下回复没有终止清理者。** 这不是提前释放后卸载的安全漏洞；恰好相反，未知投递保持围栏，却永久占用该投影的pin与场景ticket。

实际根因位置（`game_runtime.py`，本批读取的72d7…与当前0d36…三处循环相同）：

- `GameRuntime.scene_messages`（约1233行）逐条`begin_delivery`，返回已登记完整批次。
- `ConnectionOwner.receive`（约1100行）逐条`await offer_message`，没有保护未交付给queue的剩余批次。
- `ConnectionOwner.run`的tick回复循环（约1127行）有同一缺口。
- `ConnectionOwner._send`的`scene_sent`后续回复循环（约1088行）有同一缺口。
- `offer_message`对**当前被拒绝的一条**调用`cleanup_delivery`；后者经`RuntimeStoryMaps.finish_delivery`shield/track接管实际终止。producer取消不抹掉这条当前清理。
- `ConnectionOwner.close`只处理活动pump与`self.queue`，没有拿到尚未offer的批次后缀，因此不能清它。

### 同一反馈的6组实际结果

[默认安全红结果](world-scene-delivery-abandonment.json)、[精确缺陷复现结果](world-scene-delivery-abandonment-expect-leak.json)。两份均为当前`game_runtime.py=0d36cf6a…`且执行前后源hash稳定；默认exit1，`--expect-leak` exit0。原先先行两组在72d7…也已实跑红，但不把它说成最新源结果。

| 实际producer | cleanup等待中取消 | 关闭后queue/bytes/member/finish tasks | pending scene tickets | 公开可取pin名额/64 |
|---|---|---|---:|---:|
|receive|否|全部0|0|64|
|receive|是|全部0|1|63|
|run tick|否|全部0|0|64|
|run tick|是|全部0|1|63|
|sendpump barrier回复|否|全部0|0|64|
|sendpump barrier回复|是|全部0|1|63|

每例恰好预登记2条真实ScopedSceneMessage；首条使用真实`ConnectionOwner.offer`容量拒绝。raw真实SerialOwner的`finish_scene_delivery` handler受控hold；取消被观察后才释放hold。候选若在finally等待后缀清理，probe也允许它等到hold释放，**不要求正确实现提前取消完成**。barrier模式由真实`close()`单次cancel真实sendpump，不额外double-cancel。

随后probe等待原producer、真实close、全部`manager.work`和raw SerialOwner queue终止，再经公开`inspect_lifecycle`读取members0/pending1。另用公开pool Interface独立取pin：只有63个请求成功，第64个精确报`Story pending operation capacity`；不是只读private dict得出的泄漏断言。可信clock从1000推进至61000后，公开`begin_unload`仍拒绝`Story projection still has queued/in-flight operations`。围栏确实保留，单纯等满60000ms不能恢复。

probe最后手工清理保存的批次引用，仅为测试环境无残留退出；生产中丢失这些引用正是缺口，不把测试teardown当自动恢复。没有以等待时长推定后台工作已经结束。

### 可复跑Interface

```powershell
# 当前源：预期安全默认断言，实际exit1；先写结构化JSON再raise。
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_world_scene_delivery_abandonment.py

# 当前源：严格要求上述6组差异，实际exit0。
& 'C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B revival/research_world_scene_delivery_abandonment.py --expect-leak --report revival/evidence/world-scene-delivery-abandonment-expect-leak.json

# 根窗口可对私有候选执行同一默认安全断言并另存结果。
# ... -B revival/research_world_scene_delivery_abandonment.py --runtime-source <候选源目录> --report <独立结果路径>
```

`--runtime-source`在任何game_runtime导入前统一选择源目录，避免只别名加载ConnectionOwner造成`ScopedSceneMessage`类型身份不一致。也可`await check()`获得完整观察，再`assert_expected(report)`作默认安全断言；`check`本身只返回观察。每份结果保存实际导入路径、hash、probe hash及`sources_stable`，默认红也落盘。

实际执行：真实ConnectionOwner三处producer/offer/cleanup/close、真实GameRuntime.scene_messages、真实RuntimeStoryMaps/ProjectionPool、真实MapOwner/SerialOwner登记、终止与leave、真实帧解析。Adapter：合成可信角色/目录/地图bounds初态，无账号授权和数据库；dispatch只供应2条逻辑回复；role.mailbox只供应tick/scene_sent的2回复；Reader受控首次TimeoutError；Writer为无socket transport；MapOwner handler只在真实finish操作前hold。使用发布64pin/64ticket预算，连接byte_capacity=1为明确的局部测试容量。没有运行完整登录、RC4/MPPC交换或原客户端。

### 建议交主集成的最小修复方向

把整批逻辑回复的终止所有权放到一个ConnectionOwner批量投递Interface：正常逐条handoff给queue；异常/取消时，只为iterator中**尚未offer**的后缀立即建立cleanup任务，并shield其实际终止；当前被拒绝项的cleanup已由offer_message/finish_delivery接管，已入queue前序仍归pump/close，不能提前清除它们的pin。保持receive原有barrier对应scene_generation推进语义。

同一helper须接receive、tick、send_barrier三处，否则其中一处绿不能关闭另两处。根窗口已提出`_offer_batch`私有候选；本窗口没有实现shared补丁。6组反馈允许根在同一snapshot默认安全红→候选默认绿，不以`--expect-leak`的绿冒充修复。

## 其他投递终止路径：事实与验证范围

以下为当前源码审计；“已有验证”仅表示本批读取了对应程序/结果，不冒充本窗口本轮重新执行。根窗口正在另补实际ConnectionOwner终止矩阵。

| 路径 | 当前终止/围栏行为 | 本批证据范围 |
|---|---|---|
|begin_delivery前pool容量拒绝|未取得新pin，未提交地图登记|源码；不是本批6组中的连接容量拒绝|
|raw mailbox拒绝/已出队deadline拒绝/地图登记明确失败|register捕获Exception释放刚取得pin；无成功ticket|源码。`SerialOwner.call`等待shield reply，没有“观察超时即返回”的wait_for；deadline仅开始执行前检查。因此不能把原先“观察超时提前放pin”的旧问题再套到当前这里|
|begin_delivery外层取消|register task继续；cancel_late得到迟到ticket后finish_delivery|源码；本批未单独执行此分支|
|正常drain完成|活动消息finally cleanup；barrier后续批次还需独立终止所有权|源码；本批实际barrier trigger经过drain，未覆盖真实socket|
|epoch过期/scene fence变化/closed跳过|`_send`在写入前continue，但finally仍cleanup当前ticket|源码；本批未另做真实epoch/fence矩阵|
|drain抛错/3秒超时|finally cleanup当前消息，outer标closed/close writer；queued残留由close处理|源码；本批未注入drain异常/超时，不把6组的容量拒绝算作drain失败|
|pump被close取消|活动消息finally cleanup，close等pump结束，再清queue与disconnect|源码；本批send_barrier取消实际执行此路径，但特定后缀缺口如上，不覆盖任意queued消息矩阵|
|finish_delivery等待者取消|真正finish任务被shield/track，地图确认后才release pin|源码与6组中首条finish取消观察的实际后续完成；不是只因外层awaiter结束便释放|
|finish ticket地址/generation错误，或地图清理未知失败|finish在release前抛错；ConnectionOwner cleanup捕获ValueError/KeyError/TimeoutError/Backpressure并记恢复日志，不强释放pin|源码。安全围栏保留；没有凭失败日志宣称资源清理成功|
|scene_messages构建部分失败/中途fence过期|catch BaseException，向已append消息提交finish_delivery并gather；未登记成功的begin失败由register清其pin|源码；本批未执行容量/构建错误矩阵。cleanup返回异常被return_exceptions接收，未知项仍fenced，不能声称所有失败都已恢复|
|close本身的调用者取消/连续多次取消|现有close没有整体shield；全部终止行为未由本批反馈证明|明确未执行范围，不据静态猜测另报已复现漏洞|

本批读取`verify_private_scene_delivery_runtime.py`：它覆盖真实私有NPC回复慢drain后close清活动和queued ticket、成员退出，但没有覆盖“已经登记、尚未入queue的批次后缀”。读取`verify_runtime_story_pins.py`及`verify_world_runtime_story_pins.py`：它们覆盖实际SerialOwner执行/排队deadline、取消观察者、unload cleanup保槽；这不等于新6组已由旧验证覆盖。未重复旧已修结论。

## Maintenance异常与永久围栏：静态事实，尚无本批执行复现

`RuntimeStoryMaps._collect_one`（约117行）成功`retire_idle`拿到receipt后，依次`forget_map → await owner.mailbox.close → pool.finish_unload → loaded.pop`。这遵守“清理确认前不释放槽”的安全顺序。

但源码同时有一个明确运维能力边界：

1. `forget_map`之后close若抛TimeoutError或其他异常，pool仍为unloading、loaded字典仍指向原owner；receipt只留在已失败协程局部，没有保存为可重试清理状态，也没有公开`retry close → finish_unload`恢复Interface。
2. maintenance done callback会移除已失败的task；下一collect重新取原owner。若原owner已retired，`MapIdleSnapshot.idle`为false，`_collect_one`在退休前检查处直接return，不会重新跑close/finish_unload。因此“下次GC自然恢复”不是源码已提供的保证。
3. `_collect_loop`只捕获ValueError/TimeoutError。遇这两类，循环继续但上述unloading fence并不会因此解开；遇RuntimeError、Backpressure等未捕获异常，周期gc task可直接结束。RuntimeStoryMaps没有自动重启gc的逻辑。
4. 若forget_map自身抛错，close也未运行；未知结果仍保留unloading槽，不应直接cancel_unload复活已退休owner或假定清理结束。`stop()`对已有maintenance用gather(return_exceptions=True)，也不提供丢失receipt的自动恢复。

这几项是**完整源码分支的静态事实**，本批未注入maintenance close timeout/RuntimeError，也没有对其提供原进程故障恢复证明。它们不是本批新的已执行P2复现，不与上面的6组缺陷混为一个发现。主集成若后续需要恢复能力，应保留准确retirement receipt/cleanup阶段，并设计明确的同generation终止确认；本窗口不制定新恢复协议、超时释放政策或shared补丁。清理未知继续fenced是当前正确安全底线。

加载部分失败同样区分：当前`_load`对已返回owner先关闭control mailbox再forget，只有清理完成才finish_load_cancel；close/forget失败则保留取消中槽。当前GameRuntime工厂在MapOwner构造返回后才注册，MapOwner的SerialOwner在构造末尾创建；本批没有构造一个实际资源遗留并证明它被提前释放的反例。不能从泛用factory可能部分失败，直接升级为当前生产工厂已证泄漏。

## 源快照与方法记录

本批6组最终执行读取的SHA256如下；所有执行路径实际import来源亦存各JSON。最初两组game_runtime为`72d7f787f087ac6fc887d1d3534731d12d234267bb4b0bcf6e620fd46e7260e5`；后续唯一共享写者更新后，本批复读并将6组固定在下列0d36…上，未混用两份代码的结果。

| 源/已读验证 | SHA256 |
|---|---|
|game_runtime.py|`0d36cf6a940afdcb903c338f6e5a0fb48c48bb537276de824a3146db744bff25`|
|runtime_story_maps.py|`f03a97820d6c314b8756edc984093dce093f4cadab767330af0b1c4c58e6070a`|
|runtime_core.py|`13fd69a1433b3d0d4f7c3ca4ad5d210c9067799e5d9fb634cd265cd6ca6b8476`|
|world_owner.py|`3a893ec87feab966adf4f07f1917779296669f143177cb78da580758c3ef4d5b`|
|world_story_projection_pool.py|`3fdedb540a7c1157c1e3b1984d0242fc96e22848903ef4f3897ee87fa5c2bd9b`|
|world_story_instances.py|`f8a817fb68aed25df3cfec580fe5731ce9659743aa252bdff538b2d0eb8b6268`|
|connection_codec.py|`b6eb545cb3ce00a10d6cfde0b5584d0d1fdd1e93201e6d259df40b93e75bdcfe`|
|wire.py|`3b6369a332b05f061866090aba312956d3804c0b577b06c7860e61fce51de050`|
|verify_private_scene_delivery_runtime.py|`dad062f0bb952419242f38c1c18b32206f9196b9accacdcabf90a6a84153eaac`|
|verify_runtime_story_pins.py|`cdb85761046054c3b1d115af1df480983b73325004180fcd8c829bc8fdfae46c`|
|verify_world_runtime_story_pins.py|`8b3f80cf10255e1904c91489bef11e288052a787cc438b48241bb2bdde748402`|
|verify_runtime_story_lifecycle.py|`88e1b613d3aea3ba0082d9b6821bc450c8371f45a84d8c64988bef60c4d8b759`|
|design/story-instance-v1.json|`80490752053ce7b43209f3ad82de348eb6c43e482d797552a9ddd19c90f1d5a6`|
|research_world_scene_delivery_abandonment.py|`bb1fd784f11caeb4a7c8c82eebd8c830255b7cd5e93548f34b7b932e32d43d98`|

research以当前第一方源与单一MD记录事实/未知；diagnosing-bugs以默认安全红命令和正常控制构成快反馈，最小差异仅取消边界，未从“队列清空”推论投递终止；codebase-design把批次尚未handoff、已入queue、地图ticket和pool pin分别归属，建议单一批量投递Interface承担异常终止，不在业务回复模块复制cleanup。未进入共享修复阶段；候选/发布/GUI验收由主集成另行证明。
