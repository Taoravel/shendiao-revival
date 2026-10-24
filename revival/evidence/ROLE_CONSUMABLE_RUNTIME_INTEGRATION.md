# 角色世界用药接线

2026-10-23。范围为共享RoleOwner路由及这一条必要临时库/原生解码检查；不运行战斗、不部署、不打开客户端或修改在线角色。

## 方法与具体决定

沿用codebase-design，将上下文接入已有Inventory.receive_role_consumable Interface，不重复实现药品公式、品质、属性资源或扣药事务。阻塞调用仍经角色所有者有界io路径，结果仅为逻辑消息，由目标ConnectionOwner保持持续RC4/MPPC及发送FIFO。

按diagnosing-bugs在实际GameRuntime→RoleOwner→Inventory Seam建立反馈：verify_role_consumable_runtime.py先在未改入口运行，确切报`Role use-item context handler not connected`。原kind0落到二参数receive的pending分支；这是直接已证的缺失路由，未扩展多假设插桩或完整TDD流程。补线后同一检查通过。

## 实现

- 先经过已有非战斗/非传送门禁，再处理CUseItem（0xc03ff）。仅接受完整16字节`>iiQ`，实例key必须正数。
- target_kind=0要求目标为服务器所属role_id，然后把body、当前epoch、可信cmd.request_id交给receive_role_consumable。epoch与结算键不由包字段提供。
- target_kind=1保持原receive路径；其他未恢复目标仍由原Interface拒绝/pending，没有混用角色资源。
- 角色属性基线、伤势、实例品质及效果规则由Inventory已有权威接口读取；不以训练100HP代替缺失基线。效果、扣药、vital版本与领域回执仍由原事务一起保存。
- 返回原世界0xc32c8 HP60/MP70与背包逻辑回复。重试按同一可信命令键确认既有扣药，但重新读取当前伤势；不将历史回执HP/MP写回或刷到客户端。
- 原生CUseItem没有客户端重试ID。服务端受理命令的内部重试保持cmd.request_id；新的相同线包仍是新操作，不能擅自把连续点击按正文合并。领域回执不声称已经实现跨模块公共结算/跨分片恰好一次。

## 本次必要验证

只运行verify_role_consumable_runtime.py（修复前红、修复后绿），临时SQLite与内存Writer，无在线端口、GUI或战斗实例：

- 临时角色显式属性基线HP上限500、当前1，固定药32000使用后HP201、库存3→2；这些值是隔离夹具，不是用户角色基线或训练fallback。
- 真实ConnectionOwner持续RC4/原生MPPC解码，实际回复再由原x86属性map及背包decoder完整消费。
- 相同可信请求键重试不重复扣药；后续伤势HP10保留，回复当前10，不回复历史201。
- 截断、他人目标、缺属性基线均不扣药；战斗/传送门禁用哨兵验证，不启动对应系统。
- 宠物种类1仍调用原receive，不额外改变宠物玩法。

结果为role-consumable-runtime.json。未重复运行战斗、全运行时或原药品模块完整套件；原模块事务失败回滚、品质公式等已有报告仍归道具窗口，不写作本次重跑。

## 未验证范围

尚未部署，未进行原客户端UI画面/点击验收；普通人物属性初始化、成长完整刷新和黑屏前置问题仍待处理。本次没有给已有角色自动建立属性基线、补药或修改资源。SQLite单文件单写限制不变。
