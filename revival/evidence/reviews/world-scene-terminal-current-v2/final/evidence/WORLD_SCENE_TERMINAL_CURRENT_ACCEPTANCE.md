# 世界场景终止：最新共享源码独立验证

2026-10-24。先读本页或 `world-scene-delivery-current-interface.json` 判断后续集成状态；`WORLD_SCENE_DELIVERY_SUFFIX_HANDOFF`、`WORLD_STORY_CLEANUP_FAILURE_OBSERVATION`及其固定审查保留原基线/候选/历史缺口，不代替本页当前结果。

## 当前代码与已执行反馈

本轮验收固定GameRuntime `ccd2bbdea1d1e40638e9553ce1236a7d115e037208fae92ffe36ea1a205c36e1`、RuntimeStoryMaps `fc4ba947c79c4a0414bcec82d41ca8687b50b52e6e676964698fd156a064e3af`。前者逐字节等于已审私有suffix候选5bbf51ac…加上旧角intro一行0→1；共享改动由主集成完成，世界仍只写所属验证/证据。主集成连续编辑期间捕获完整不可变源码/配置/原映像副本，再从该副本统一执行下列四项；原始路径、逐文件manifest、实际加载模块路径/hash与前后不变围栏全部在 `world-scene-terminal-frozen-current-verification.json`。这是捕获时点的共享源码验收，不保证随后工作区或运行进程仍是这些字节。

1. `research_world_scene_delivery_abandonment.check/assert_expected`：固定副本真实receive/tick/send_barrier正常与取消六组全部0pending/free64；早期0d36…三取消遗留1的反馈仍保留为红基线。
2. `verify_world_legacy_intro_entry.check`：固定副本真实隔离Owner登录及原intro/移动predicate得到intro1、不创建该开场黑幕、锁0、普通移动允许，已有旧intro锁也可清除；无伪造CG/任务。其它门控显式清除，GUI仍须另验。
3. `verify_world_scene_delivery_terminal.check`：固定副本实际加密Owner与初始私有检查点夹具下10组常规终止检查通过，覆盖范围详见WORLD_SCENE_DELIVERY_SUFFIX_HANDOFF；并非全部故障/商业容量证明。
4. `verify_world_story_cleanup_recovery.observe`：固定副本真实维护定时器分别遇到ConnectionError/TimeoutError，GC仍运行；保留原退休占用，重试close时取消外层collect仍保持围栏，另一地图继续；实际原Adapter成功终止后原槽释放、registry只忘记一次、同地址可载入新generation。两组通过。

上述四项统一结果见同一frozen-current报告，不混用不同源码的单项绿。早期 `world-scene-delivery-shared-current-verification.json`、`world-story-cleanup-recovery-verification.json`及各直接运行结果绑定adfe946…等早期采样，仅保留为历史；不能用它们替代fc4ba947…的统一复验。资源Adapter保留原客户端ROOT，但所有政策/catalog/JSON和原映像从被冻结OUT读取；未修改该副本或原资产。

维护重试验证使用可信目录/catalog及close故障Adapter；失败发生在实际资源终止前。第二次close也在受控门处暂停，然后调用真正SerialOwner.close，断言实际task成功终止后才重载。测试不伪造MapRetired或强行释放pool，也不通过修改生产状态补救通过。未验证真实I/O故障、持久目录授权、任务进入资格、全部异常类或商业负载。

## 证据层级与审查

原f03a978…维护观察证明其当时不能恢复，不能继续拿它说最新adfe946…仍永久围栏。新两组只覆盖上述前置失败和实际close重试；其它未知结果仍须保持围栏，不能推断所有终止异常均已恢复。

suffix六文件与原维护观察两文件的双轴0分别只覆盖其固定快照；本页及新recovery verifier的独立补充审查见 `WORLD_SCENE_TERMINAL_CURRENT_REVIEW.md`。初版Spec P2发现参考d316…与执行adfe…错配；现以同一fc4…固定副本统一实跑，并为复审冻结完全相同的reference，未把错配当通过。本窗口没有部署、重启、打开游戏、登录真人或修改存档。当前源码通过不证明运行进程包含这些字节，尚未进行真客户端画面/移动验收，全量地图与怪物目标仍未完成。
