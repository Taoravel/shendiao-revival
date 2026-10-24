# 出生地/任务寻路见证：可信交互判据

2026-10-23。按 `NPC_INTERACTION_CELL_DECISION.md`、`design/npc-interaction-v2.json`，世界只改自有 `world_newbie.py`；NPC维护规则及实体复核，主集成唯一接共享入口。

## Interface

```python
check_birth_site(route, catalog, maze, placements, *, state_byte,
                 interaction_radius=None, max_visited, interaction_allowed=None)
validate_birth_sites(routes, catalog, grids, placements, *, state_byte,
                     interaction_radius=None, max_visited, interaction_allowed=None)
```

交互目标二选一：旧显式 `interaction_radius=<非负int>` 保留原圆形检查；新目标传 `interaction_radius=None, interaction_allowed=rules.allows`（省略radius也可）。两者并用、都未提供、非callable、bool/负半径或非正整数预算拒绝。回调严格返回bool，传入原冻结NpcPlacement及完整 `(map_id,x,y)` tuple；不传二元点。异常直接传出，不把无效规则伪装成no_witness。

新调用示例（依赖已启动冻结）：

```python
walk = check_birth_site(route, catalog, maze, placements,
    state_byte=0, interaction_radius=None,
    interaction_allowed=store.npc_interaction_rules.allows,
    max_visited=100000)
```

生产启动的validate_birth_sites与后续check_birth_site用同一rules.allows。世界不加载政策、不复制格公式、不从v2.radius_for派生208圆或临时标量。原bounds、mask、DDA、visited预算、目标NPC筛选与只返回冻结见证不变。不同角色共享同源起点/NPC的启动检查仍在单次调用内去重；callback是可信服务器依赖，不来自客户端。

## 验证与完成边界

新增 `verify_world_newbie_interaction.py`：首次check_birth_site缺keyword实际红→实现绿，再validate_birth_sites缺keyword红→转发绿；6组覆盖非圆精确点回调/完整坐标、启动转发、旧半径不同目标、碰撞/预算保持、非法或非bool判据、无热文件读取。既有verify_world_newbie原章节/43路线及audit_newbie_birth_sites旧半径43路线/10起点回归通过。

这6组是受控小maze和精确点谓词。随后已实际执行 `verify_world_newbie_interaction_policy.py`：正式冻结v2下43路线及血手印均有见证，每个点/边保留mask1/DDA、每处目标经当前NpcScene公开spawn/interact准入，无热文件读取。血手印从1006/360,2264得到末点1512,1096；同脚本旧32仍no_witness44928。5组报告 `world-newbie-interaction-policy-verification.json` 绑定本批源码与v2；这些Location仍为显式离线夹具，不冒称真实角色自然到达或共享/原生导航完成。

主集成须将runtime_storage启动validate_birth_sites及所有自然任务见证改传同一启动rules.allows。现有显式radius调用不会自动切规则，旧红例脚本可以继续显式旧半径作历史反例；完整链转绿需读对应实际共享报告，不能由本Interface存在推定。真实角色、GUI、运行服和自动行走仍独立验收。

参数Seam沿用主策划已明确约定；方法为codebase-design集中判据/冻结依赖，tdd分两条公开Interface红绿，diagnosing-bugs保留旧圆差例，writing-for-agents共置调用与边界。世界未改shared或NPC规则文件。
