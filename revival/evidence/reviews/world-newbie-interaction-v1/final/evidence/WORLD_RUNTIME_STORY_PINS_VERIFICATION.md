# 共享私有地图：实际邮箱pin与卸载终止验证

2026-10-23。世界新增 `verify_world_runtime_story_pins.py`，复用已约定的真实GameRuntime/MapOwner邮箱与目录Seam；共享实现仍由主集成单写。实际执行exit0，六组通过，九份输入执行前后稳定；源码SHA与范围存于 `world-runtime-story-pins-verification.json`。这是这一份源码的行为证据，不表示后续改动或已发布服务自动通过。

临时SQLite自然创建两角色并完成开场，以公开目录分配；初始私有检查点是明确受控fixture，不执行血手印入场或战斗。可信服务器clock Adapter与公开collect驱动时间，关闭周期调度以隔离时序，因此没有验证周期timer。故障门放在实际SerialOwner handler和原Adapter close的Seam；解除后继续原delegate，不替换命令结果。

六组反馈：

1. 空地图邮箱的实际命令已开始执行后，取消外部observer；原执行仍暂停，pool.begin_unload必须拒绝，pin未提前释放。
2. 同时第二张私有图的实际location查询及原加密四字节heartbeat继续完成。
3. 另一过期命令在真实队列中等候，出队时在MapOwner.handle之前拒绝；handler计数不增加，后续卸载成功证明其terminal路径也释放pin。
4. 最后操作结束重新起算完整60000ms，59999时collect不卸载。
5. 到60000时原地图retire并开始实际close；close被门暂停时，128槽计数仍包含该投影，同地址重新acquire拒绝。取消collect的外层observer后仍占槽，原维护工作继续。
6. 另一地图查询/heartbeat在close暂停时仍完成；原close真实终止才释放槽，旧Adapter拒绝，真实登录以原持久地址和新map generation重建。

报告中全部Location/初始检查点fixture已经标明。未验证：初次/换图场景投递ticket所有退出分支、实际128个地图负载、真实进程崩溃、动态NPC/怪物持久恢复、周期调度、客户端自动运动/GUI或发布。原WORLD_STORY_SHARED_HOOK_AUDIT是旧源gap清单，不能用它否定本次实际已接路径，也不能用本六组覆盖其所有未验项。

方法：diagnosing-bugs从旧接线缺口构造有实际终止门的反馈，codebase-design观察真实两个地图所有者独立推进，验证既有公开Seam而不改shared；writing-for-agents将注入条件和能力边界共置。本批不是对共享实现的功能TDD，也没有让离线角色位置夹具冒充自然剧情流程。
