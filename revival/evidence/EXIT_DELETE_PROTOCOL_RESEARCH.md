# 退出、重新登录、返回选角与删除角色：原客户端协议核验

2026-10-23。任务范围：仅离线原映像/解码资源；未操作 GUI、游戏进程、监听服务或现场数据库，未执行角色删除。

## 方法与证据边界

应用 research 方法，直接追溯一手客户端 RTTI → 虚表 → 按钮回调 → 原编解码 → 下行 Process；使用已有 `native_gameplay_probe.probe` 在 Unicorn 内执行原 x86 编解码，避免仅凭连续协议编号猜语义。诊断实际 Owner 缺路由的红绿检查由集成方负责，此报告不宣称复现了真实 GUI 点击链，也不宣称修复完成。读取 AGENTS.md 与 ARCHITECTURE.md，输出仅本报告，未改共享实现。

主证据为 [native-image.bin](native-image.bin)（映射基址 0x400000），复核工具 [native_inspect.py](../native_inspect.py)、[native_gameplay_probe.py](../native_gameplay_probe.py)。下面地址均是该原映像 VA；它们是原客户端证据，不是当前恢复服务实现地址。

## 可直接接线的协议

| 操作 | 上行 | body | 下行 | body |
|---|---|---|---|---|
| 退出游戏 | CRoleOffline 0xc0011 | 空 | SRoleOffline 0xc0031 | 空 |
| 重新登录 | CReturnToLogin 0xc0032 | 空 | SReturnLogin 0xc0033 | 空 |
| 返回角色选择 | CReturnRoleList 0xc002d | 空 | SReturnRoleList 0xc002e | 与现有 role_protocol.role_list 完全兼容的列表体 |
| 确认删除角色 | CDeleteRole 0xc0028 | BE64 正角色 ID，8 字节 | SDeleteRole 0xc0029 | BE64 正角色 ID，8 字节 |

严格长度检查应在恢复服务边界补上：原无字段 codec 本身只是不消耗字节，并不证明原 decoder 会拒绝尾随垃圾。删除原约束为 signed64 > 0；不要接受高位符号为负的角色 ID。已有 CSendIgnoreRole 0xc0078 是进入前预检，绝不是删除。

### 退出游戏：原按钮确实等待服务器回包

[exitgamedialog.layout](../decoded/ui/layouts/exitgamedialog.layout) 指明 `ExitGameDialog/back/button` 文案“退出游戏”。原初始化 0x15f92c8 引用该路径，0x15f9307 将控件存 this+0x20。0x15f9e41 将回调 0x15f62c0 绑定到同一控件；回调 0x15f62e3 构造虚表 0x224cc50、type 0xc0011，于 0x15f630c 调发送虚函数。

CRoleOffline RTTI 为 `.?AVCRoleOffline@gsp@knight@@`，ctor 0x8131e0，marshal 0x813200，unmarshal 0x813210，均无业务字段。

SRoleOffline RTTI 虚表 0x22706b4，ctor 0xd562e0 写 type 0xc0031，marshal/unmarshal 0xd56300/0xd56310 均空。Process 0x8137c0 在 0x8137de 压入 Windows 消息 0x10（WM_CLOSE），0x8137e1 调导入函数发给原游戏窗口；不存在窗口对象时走 0x8137ea 后备分支。这是服务器确认后客户端关闭自身窗口的链，恢复服务应先完成当前角色退出持久化/释放，再将逻辑响应经当前连接发队列排出，不能仅断 socket 冒充原确认，也不能杀所有客户端进程。

### 重新登录与返回选角

同一 layout 的 button1 文案“重新登录”，Return 文案“返回角色选择”。初始化分别存 this+0x24 (0x15f934d)、this+0x28 (0x15f9393)；0x15f9ed2 绑定 button1 回调 0x15f6330，回调写 type 0xc0032。Return 在 0x15f9ff4 绑定 0x15f6a00，该函数的 0x15f6a7c 路径构造 CReturnRoleList 0xc002d；可见客户端战斗等本地守卫，服务器也必须按可信状态自行守卫。

CReturnToLogin 虚表 0x226ff08，ctor/marshal/unmarshal 0xd51280/0xd512a0/0xd512b0。SReturnLogin 虚表 0x2270678，ctor/marshal/unmarshal 0xd560e0/0xd56100/0xd56110，type 0xc0033。Process 0x813800 调 CGameApplication 虚表 +0x54，参数 false/0，走原回登录应用切换。

CReturnRoleList 虚表 0x226fedc，ctor/marshal/unmarshal 0xd51190/0xd511b0/0xd511c0。SReturnRoleList 虚表 0x22865f4，ctor 0xfbf2e0（0xfbf326 写 0xc002e），marshal 0xfbf7d0，unmarshal 0xfbf8a0，Process 0x1007fc0。下行字段依次为：BE64 上次角色、byte 标记、compact count + 原 RoleInfo 列表、BE32 尾字段；原 Process 0x1008065 将 CGameStateManager 状态置 1，重建角色选择资料。现有 [role_protocol.py](../role_protocol.py) `role_list(last_role_id, roles)` 生成的体已实际经该原 decoder 验证，空列表及包含高位 ID/中文名的一行均通过；只需使用正确下行 type，不能仍发 0xc0002 期待其自动切 UI。

### 删除角色

RTTI：CDeleteRole `.?AVCDeleteRole@gsp@knight@@`，虚表 0x226fa8c，ctor 0xd4ef20 写 type 0xc0028；原 marshal 0xe3fd30，unmarshal 0xd4efd0。字段只有 object+8 的 uint64 位模式，原合法性检查按 signed64 正值；0xe3fd5e 调原 BE64 输出 0x7709b0，0xd4efda 调原 BE64 输入 0x770650。

真正确认回调片段：0x13fa8e0 起检查本地确认输入是否匹配生成的确认值；匹配到 0x13fa9ad 构造 CDeleteRole，0x13fa9bd..0x13fa9cf 从 dialog+0x40/+0x44 取目标角色 ID，0x13fa9e4 发送。附近相似回调 0x13fa7f0 发的是 CFreePet 0xc07e4，不能因邻近将放生宠物误当角色删除前置。

SDeleteRole RTTI `.?AVSDeleteRole@gsp@knight@@`，虚表 0x2270254，ctor 0xd52fa0 写 0xc0029；marshal 0xe406e0，unmarshal 0xd53040。无状态码、倒计时、撤销字段。Process 0x101fce0 先关闭确认对话框，然后取下行 role ID 调 0x101f800；0x101f879..0x101f8b3 遍历选角资料并将对应 ID 两个32位字清零；0x101f8b6..0x101f8dc 同时清掉当前选中 ID（如果相同）。因此成功回包让客户端当场移除该角色，而不是显示一个已知的延时状态。

**边界：客户端这条链不足以证明旧官方服务器是物理删除、软删除或保留多少天。** 原协议未提供本报告可验证的删除延时/撤销业务字段，也没有在本次 RTTI 检索找到相关恢复协议。因此恢复服务采用可审计软删除、禁止进入和隐藏列表、保留资产/结算外键，是明确的本地持久化设计；不要标注为已还原官方删除保留政策。只能删当前认证账号拥有的离线角色，提交成功后才发成功响应；重复包可返回同 ID 成功但不重复破坏记录。未知 ID、他人 ID、在线租约和旧连接写入等由集成方做事务围栏与必要拒绝检查。

## 已排除的日志编号误认

| 十进制 | 十六进制 | 原 RTTI（虚表） | 结论 |
|---|---|---|---|
| 786459 | 0xc001b | CBeginnerTipShowed (0x226f9dc) | 新手提示上报，非删除或退出 |
| 790439 | 0xc0fa7 | CRoleTurn@move (0x2279038) | 角色转向，非退出 |
| 818433 | 0xc7d01 | CReqSW@shengwang (0x227ca28) | 声望请求，非退出 |
| 818435 | 0xc7d03 | CRefreshSWItems@shengwang (0x227c9fc) | 声望物品刷新，非退出 |

这些 RTTI 名字由原虚表之前的 CompleteObjectLocator→TypeDescriptor 指针读取，非根据业务编号猜测。退出弹窗还在 0x15f916f..0x15f91ea 发 CRequestExitGameInfo 0xc0022 与 CRequestLeftExitGameInfo 0xc0024，属于推荐/剩余信息加载；其响应分别 SRequestExitGameInfo 与 SRequestLeftExitGameInfo，不应当作关闭游戏确认。原真正退出按钮链如上已独立核定。

## 已执行的离线必要检查

在工作目录通过指定 Python 的 stdin 脚本调用现有 `probe(ctor, marshal, unmarshal, fields/payload)`，没有启动 Windows 游戏可执行文件。

- CDeleteRole / SDeleteRole：ID 1 与 0x123456789 原 marshal→unmarshal roundtrip 全通过；后一 wire 为 `0000000123456789`，证明不能截成32位；7字节删除体均被原 decoder 拒绝。
- CRoleOffline / SRoleOffline / CReturnToLogin / SReturnLogin / CReturnRoleList：原构造 type 与原 marshal/unmarshal 空体全部通过，type 分别 c0011/c0031/c0032/c0033/c002d。
- SReturnRoleList：现有 role_list 产生0行14字节及1行49字节体，均在原 decoder 消耗完整；type c002e、lastRole 高位 ID、count 0/1 和尾0全部正确。

这些 codec 结果证明 wire 结构，不证明当前服务已接入，也未执行真实下行 Process 的窗口关闭/切界面副作用。建议集成方必要临时检查：真实 ConnectionOwner 加密发送顺序；退出在落盘与发送完成后只清当前连接；返回选角后同一连接可删/建/入场；账号隔离/在线拒删/高位 ID/重复包/事务失败不发成功/重建 Runtime 后隐藏已删角色；原预检0xc0078仍无删除效果。GUI验收由用户后续实际操作确认。
