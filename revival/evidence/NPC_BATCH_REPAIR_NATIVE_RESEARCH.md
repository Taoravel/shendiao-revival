# 原生批量修理与普通 NPC 修理的边界

本批方法：research。只读第一方客户端映像、RTTI、原 x86 codec 与按钮消费路径，使用离线 Unicorn 执行原指令；不运行客户端、不连接网络、不读取真实角色数据库、不修改生产源码/政策/发布。结论与运行时接入、部署、GUI 验收分开。

## 直接供接入方采用的结论

**`CRepairEquipItemMulit`（原拼写）不是普通 NPC 服务 513 的批量版本。** 它属于 `CEquipCarryWithRepairDlg`（随身修理），用 `EquipRepair.layout`；服务 513 打开 `CEquipRepairDlg`，用 `EquipmentRepairSmiple.layout`。不得因名称接近把无 NPC 标识的批量请求接成已授权的 NPC 普通修理，也不要给该请求假造或截断 NPC key。

| 协议 | type | 线体（BE） | 原生地址 |
|---|---|---|---|
| CRepairEquipItemMulit | 0xc050f / 787727 | int32 method（仅 0/1），compact count + int32 key 列表，compact count + int32 key 列表 | ctor e6c6b0；marshal e6c880；unmarshal e6c780；vtable 2281560 |
| SRepairEquipItemMulit | 0xc0510 / 787728 | 两个 compact count + (int32 key,int32 result) map | ctor efe8c0；marshal efe9a0；unmarshal efea30；process 10ce270；vtable 2284478 |
| CRepairEquipItem | 0xc0413 | int32 method，int64 NPC key，int32 column，int32 item key | marshal e4cf30；vtable 2276c04；普通 UI callback 10dda40 |

请求没有 NPC key、column、客户端事务 ID；两列表不是 map。原内存为 `std::list<int>`（对象+c/+18，哨兵指针+4、长度+8），节点12字节，next/prev/int32；原 `82db40` 顺链表编码，离线样例 `[91,7,91]` 顺序与重复值完整保留。业务按钮先遍历 UI 两个 map，按其迭代顺序追加 key 到这两个 list；因此该按钮产生有序来源，但协议本身不强制排序或去重。signed32 负值通过 codec 只证明布局，**不代表应允许负资产 key**。

## 为什么不属于 NPC 服务 513

原菜单的第二跳表在 `1637fad`，513−0x117 的分类字节为35，跳向 `1638029`；原分支读取 `[esi+d4]` / `[esi+d0]`（NPC key 高/低），push method2，调用 `16299a0`。该函数 `16299eb` 调 `10dc9b0`，构造 `CEquipRepairDlg`，RTTI vtable `228e5f8`；对应布局字符串 `228e590` 的引用在 `10dc5a0`，为 `EquipmentRepairSmiple.layout`。随后 `10de1e0` 保存 method 于 UI+1c0，NPC key 于 +1b8/+1bc。

普通选中物品确认回调 `10dda40` 直接建立 vtable `2276c04` / type `c0413`，从该回调子对象保存的 method/key/column 和选中真实 item bean 的 key 构造单件请求，`10ddabe→813860`、`10ddacf` 提交。离线执行该原回调验证 method2、column4、item91 及高32位非零的 NPC key `1234567800000004` 全部保留；依赖适配仅为 UI 选中物品、网络经理返回值、提交捕获，提交前原构造和字段搬运指令均真实执行。提交后的 UI 重绘未执行，不能当 GUI 验收。

批量业务 ctor 直接调用在 `10cc28c`，所属 `10cc250`（其函数指针引用在 `228dad0`）。同类原构造 `10cc920` 写 `CEquipCarryWithRepairDlg` vtable `228dae0`；布局初始化 `10cbc60` 引用 `228daa8=EquipRepair.layout`。`10cc250` 仅当传入参数==0x21 时构造/发送；method 用 `[UI+b4]` 指向控件的 byte+530 做 `setne` 得0/1。`10cc2c6..10cc3b8` 按两 UI map 的 key 遍历并追加请求列表，任一非空才在 `10cc3d9` 提交。这里未发现 NPC key 搬运。

原 `EquipRepair.layout` 含 choose1“普通修理”、choose2“幸运修理”，但本批尚未追出 UI+b4 与这两个命名控件的精确绑定，**0/1 与普通/幸运的对应保持未知**；不得仅凭默认0或控件顺序推断。`TheWearRepair.layout` 是另一条布局引用（字符串2291738→1126a10），不能凭名称把它当本批类。

## 回执消费：不是仅发耐久就等价

`SRepairEquipItemMulit::process` 在 `10ce270` 检查全局 `29457d0` 是否有随身修理 UI；存在则把两 map 引用转交 `10cdb00`，不存在直接返回。第一 map 在 `10cdbb1..10cdbc1` 用 key 与固定 column1 调 `1091670` 取物品；第二 map 在 `10cde95..10cdea8` 用 column3。map value==0 与非0走不同反馈分支（第一map在10cdc59），原逻辑还删除待处理 UI map 对应 key、更新控件/汇总文字。因此这是**逐项结果**，并非一个总成功 bool；不能用单个成功提示替代 map。不能从本客户端处理推断服务端逐项独立提交或整批原子性。

第一 map 失败路径用文本ID27c1、成功用27c0，反馈列表不同；本批没有以未核查文本含义推断额外错误码。原 native codec 只确认两map的 int32 值，业务分支仅区分0/非0；不得宣称已恢复所有原错误枚举。普通 NPC 单件路径的反馈/耐久由既有单件交付验收，本报告没有把批量 S 回执强加给它。

## 复现及产物

在项目根以已配置 Python 执行 `-B revival/research_npc_batch_repair.py`。脚本实际完成：6组请求原 decode→原 marshal（0/1、空/乱序重复/符号边界），2组非法method原生拒绝，2组回执原 decode→原 marshal（非空乱序map排序、空map），1组普通NPC原UI真实构造发送，共11项。结果通过，原映像 SHA256 `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。

- [可重复脚本](../research_npc_batch_repair.py)
- [执行结果与具体线体](npc-batch-repair-native.json)
- [本批原指令摘录](npc-batch-repair-native-disassembly.txt)
- 第一方原文件：`revival/evidence/native-image.bin`；原UI资源 `artres/ui.pfs` 的已解码 `revival/decoded/ui/layouts/equiprepair.layout` / `equipmentrepairsmiple.layout`。本批布局命名通过原指令字符串直接绑定；未重读整个PFS CRC，已解码文本仅作按钮文案补充，不作为0/1绑定依据。

影响决定：不新增“NPC批量修理”事务、不改现有method2普通修理授权；批量属于随身资产玩法，后续应交装备/物品所属领域恢复其授权/费用与原生逐项回执。复用 `equipment-condition-v1` 之前先确认该政策是否适用于随身普通/幸运两种模式，本批不拟新费用/概率。

未验证：随身0/1精确控件绑定、费用/成功率含义、服务端逐项/整批提交模型、真人GUI与真实网络、实际随身修理接线/部署。没有修改或重启 PID33072，也未宣称当前运行服包含本研究产物。
