# 本批测试就绪核对

## 2026-10-24 14:04 北京时间：当前首轮测试状态

本次沿用 diagnosing-bugs 的固定运行版本与证据分层方法，只读核对实际监听、进程命令行和发布记录，不启动客户端、不改真实角色、不启停服务。实际唯一 127.0.0.1:28993 监听 PID37096，进程启动于13:50:16，运行 task-pve-20261024T053218Z/run_release.py，与 latest-deployment-verification.json 一致。该记录包含启动输入1454项匹配、未认证心跳通过、数据库quick_check通过，明确 native_gui_verified=false。

因此现在可以开始首轮人工测试：角色登录/出生、开场是否正常结束、点地移动、首个NPC和引导、普通切图。此处的测试范围是需要实际确认的行为，不宣称这些GUI检查已经通过。新手完整流程、全地图和全部怪物尚未完成；不要求用户等全量目标才开始首测。当前世界同址恢复模块的11组及SQL9组离线检查通过，但shared_runtime_integrated=false、live_server_changed=false，不算本次运行服的新功能。

下文“目前不宣布用户测试版就绪”保留旧候选时点的判断；不能据此否认此后已发布并正在运行的首测版本。当前仍没有全量完成日期或真客户端黑屏/移动通过的证据。

同日后续独立核验：原 `verify_world_runtime_join_context.py` 在上述准确task-pve发布五组全部通过、1454生产输入前后稳定；重复或拒绝join不再误撤当前移动声明。结果 `world-runtime-join-context-task-pve-20261024.json`，受控完成回调的范围见WORLD_RUNTIME_JOIN_CONTEXT_BLOCKER最新节，不把它当成真人点击或全部不能移动现象已通过。

方法：沿用 diagnosing-bugs 的精确复现、固定版本和证据分层方法。原生客户端画面验收与离线运行时检查分别记录。

目前不宣布用户测试版就绪。world-collision-20261023T200906Z 是未启动的旧候选；跨聊天集成方报告该候选因重复 CEnd 再声明位置等问题被拒，后续修复需冻结新候选并重新绑定检查。此处未独立复现该重复 CEnd 问题。

已有独立证据：world-movement-delivery-boundaries-exact-candidate.json 在上述旧候选通过早到 ACK、joined 后发送完成门槛、合法移动、墙内 CHECK/STOP 拒绝与重连。该结果不能转签后续候选，更不代表真实客户端黑屏或整个新手流程已经验收。

本次全 302 图检查会话 95187 已结束，exit 0；最终输出 all_passed=true、maps=302、npc_placements=3443、native_npc_batches=294。报告为 world-resource-runtime-exact-movement-verification.json，绑定上述旧候选；不能转签新候选，不能据此宣布客户端测试版就绪。

本批产物：research_world_scene_delivery_abandonment.py 的 send_barrier 测试夹具使用真实 ENTER_SCENE 编号 0xc0fa9，与 SceneSendBarrier.body 精确匹配；不修改或弱化生产检查。文件 SHA256 为 a18e4745159e8cdb299fffde3fad531b5fc082cad3065016d3b0957be0987dce。原始基线保存在 reviews/world-runtime-movement-acceptance-v1/base/research_world_scene_delivery_abandonment.py。

验证：当前工作区 game_runtime.py e6f8fc93ba9763803e602436e289e3bc2713f5a741317a8cebb744f98b0fc540 上，world-scene-delivery-typed-barrier-verification.json 六例全部通过，源文件前后稳定，待完成投递为零，公开空闲槽均为 64。未在后续冻结候选重新执行；不将此结果算作旧候选或新发布版本验收。

首轮用户测试范围：新角色出生、开场黑幕结束、点击移动、首个引导和切图。还需最终候选通过对应检查、完成集成并确认启动版本；没有足够证据给出具体交付时间。本批未打开游戏、修改正式存档、启动或替换服务。
