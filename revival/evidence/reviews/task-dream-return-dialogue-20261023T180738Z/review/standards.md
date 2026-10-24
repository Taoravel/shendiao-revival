# Standards

**结论：0处硬性标准违反，0处需单列的判断性建议。** 本结论只针对Standards轴，不替代Spec审查或运行时验收。

范围为两个新文件相对空基线的367行diff。已核对manifest全部源码/上下文SHA，重建`difflib.unified_diff([],source)`与changes.diff逐字相同；无Git历史或提交列表。规则来源为冻结source中的AGENTS、ARCHITECTURE、DESIGN_AUTHORITY；无另行提供的CODING_STANDARDS/CONTRIBUTING。

## 硬性规则核对

- `task_prologue_return_dialogue.py`新增hunk：启动资源loader冻结定义与43路线映射；运行路径不读配置文件或建表，符合ARCHITECTURE:22、40。
- `ReturnDialogueTicket`、`RawDreamReturnIntent`均冻结；后者明确`coordinate_space='original_reward_fields_unresolved'`、`settlement_authorized=False`。未把客户端提交升级为传送、完成或奖励授权，符合DESIGN_AUTHORITY来源分级及未知字段不猜测的要求。
- `_scope`、`_context`及公开transaction函数使用调用方db、当前租约和不可变NPC/Location凭据，只调用冻结依赖的读取Interface；这些读取没有任务/地图/资产写入。模块未自行connect、commit、send、申请跨Owner锁或持有地图可变对象，符合ARCHITECTURE:7、13、23–26及AGENTS共享分工。
- `verify_task_prologue_return_dialogue.py`新增hunk明确区分临时库、晚期剧情/接近fixture与真实GUI；报告保留shared/传送/结算未接入状态，符合ARCHITECTURE:57与DESIGN_AUTHORITY交付分层要求。

## 判断性建议

按完整12类smell baseline逐项检查，未发现值得单列的问题。角色/租约/世代字段与原始Jump四元组是已有跨Owner、原协议Interface的显式信息，不单凭参数多或原语类型判为Data Clumps/Primitive Obsession；集中两族元数据判断未形成重复分派。未把既有紧凑格式或工具可强制项当问题。

方法为code-review Standards与codebase-design的Owner、冻结快照和Seam检查。验证仅哈希、精确diff重建、AST解析与静态依赖阅读；未运行verifier、数据库、客户端或服务。唯一新增本审查文档，未改源码/政策/shared。
