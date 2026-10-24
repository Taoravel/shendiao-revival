# 仓库银两：原生入口与待接线契约

2026-10-23，NPC窗口。冻结期间完成原生取证；冻结解除后已完成NPC所属存取款事务及必要检查。共享RoleOwner分发尚待原始窗口集中接线，真实客户端未验。当前交付见[NPC_DEPOT_MONEY_INTEGRATION.md](NPC_DEPOT_MONEY_INTEGRATION.md)。

原映像SHA256：2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791。执行结果[npc-depot-money-native.json](npc-depot-money-native.json)。

| 操作 | 类型 | 构造 | marshal | unmarshal |
|---|---|---|---|---|
| CDepositMoney 存入 | 0xc03fb | d8fc20 | e4be80 | d8fcd0 |
| CDrawMoney 取出 | 0xc03fc | d8fef0 | e4bf00 | d8ffa0 |

两种payload均为16字节：BE64 NPC实例key + BE64 amount，amount为正signed64。原约束不允许0/负数，不能用负存款代替取款，不能截成32位。原CDepositDrawMoney确认分支10ca451检查mode+20：非零构造CDepositMoney，零构造CDrawMoney；从对话对象+28/+2c拷贝NPC key，输入解析结果EAX/EDX为amount。类型RTTI分别为.?AVCDepositMoney@item@gsp@knight@@与.?AVCDrawMoney@item@gsp@knight@@。

离线原marshal/unmarshal各验证三组key/金额：1、超过32位的0x100000007、signed64最大值0x7fffffffffffffff。反序列化对象保留完整64位key/amount和协议ID；两种decoder都拒绝0、-1和截断。此处只证明协议域；不能据最大线值承诺真实钱包都可接收该金额。

实现复用既有角色仓库访问权限及新地图证明，取得显式已知npc_depot_profiles.cash和当前钱包。携带现金、仓库余额、统一命令指纹、审计收据同事务修改，任一余额不足或目的余额溢出整体拒绝；接受命令重试不会二次转款。旧档未知仓库余额仍需可信迁移，不能填0。

携带/仓库余额下行各发当前值：SRefreshMoney.kind1写+b0，kind2经10a0da0写+b8；verify_npc_depot_money_native已执行原handler到字段写入（观察者前停止），校验不覆盖另一槽。既有column2也写wallet+b8。仓库访问过期、移动、换图、战斗/loading及旧epoch继续限制。currency-v1的npc_depot_transfer已获主策划认可为同角色cash↔显式仓库cash、等额无费、不替代绑银、不跨角色；具体政策由主策划维护。冻结期间未修改该配置，冻结解除后的追加与主策划审阅交错，已收到保留当前内容的明确统筹裁定。

必要完成条件：原请求经真实RoleOwner执行存/取；零/负/截断/越权/未知基线拒绝；超过32位金额保真；双方余额保持总额；余额不足、溢出、晚期失败均回滚；同键重试一次、冲突重试拒绝；移动/重连取消旧访问；两类原下行解码及当前余额重连一致。现场GUI另验。codebase-design用于维持角色资产事务Seam，原编解码作为独立价格/协议oracle，未为冻结期间的取证建立新运行时Module。
