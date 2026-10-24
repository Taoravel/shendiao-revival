# 本版本原生认证协议证据

日期：2026-10-23（Asia/Shanghai）。方法：按 `research/SKILL.md`，只用本地原生映像追踪 RTTI、虚表、构造器和实际序列化/处理函数，避免套用其他游戏的同名协议。新的一手来源为 `native-image.bin`；地址均为 VA，文件偏移 = VA − `0x400000`。

本批只修改 `../research_auth.py` 和本报告及 `auth-disassembly.txt`，未访问、改写运行态，未运行原客户端。离线 CPU 仿真仅执行隔离的纯压缩函数。映像 SHA256 和可重放反汇编范围见 [auth-disassembly.txt](auth-disassembly.txt)。

## 协议号和字段

协议类型由构造器写对象 `+4`，由类 RTTI 与虚表交叉确定；不是沿用旧版 GNET 常量。`octets` = compact 长度 + 原样字节。`u32` = 4 字节大端值。

| 类 | type | 构造证据 | vtable | marshal / unmarshal | body 字段顺序 |
| --- | --- | --- | --- | --- | --- |
| `gnet::Challenge` | 101 / 0x65 | 0x78980a | 0x2471ddc | 0x789830 / 0x7898c0 | octets(+8), u32(+0x10), ServerAttr(+0x14) |
| `gnet::Response` | 103 / 0x67 | 0x772457 | 0x247187c | 0x772470 / 0x7725c0 | octets(+8), octets(+0x10), u32(+0x18), octets(+0x1c), u32(+0x24), octets(+0x28) |
| `gnet::KeyExchange` | 106 / 0x6a | 0x7720cf | 0x2471834 | 0x7720e0 / 0x772160 | octets(+8), u32(+0x10) |

字段含义在未明确证实时仍使用偏移名；不要将 Response 六字段贸然全部命名为某个既有协议字段。

Challenge 中 ServerAttr 的虚表 `0x2471790`，序列化 `0x7716e0`、反序列化 `0x7717a0`，顺序为 `u32, byte, map<u32,u32>`。map 的数量是 compact，元素键和值均大端 u32；map 读函数 `0x7787d0`，compact 数量适配器 `0x770c10`。语法上最小 ServerAttr 是 `00 00 00 00 00 00`，表示零 u32、零 byte 和空 map。**这只证明结构合法，未证明零值业务语义。**

`0x774a51–0x774a5a` 强制挑战 octets 长度为 16。

## 整数编码的一手确认

原生 compact 写函数 `0x7706b0` 使用：值小于 0x80 用 1 字节；小于 0x4000 用 2 字节（OR 0x8000，大端）；小于 0x20000000 用 4 字节（OR 0xc0000000，大端）；其余写 0xe0，再写大端 u32。读函数为 `0x7707a0`。

这为先前 BXML 推断使用的整数编码提供了本版本原生代码支持；仍不自动证明 BXML 编译器和网络协议完全共享同一实现。旧 `FORMAT_RESEARCH.md` 中“尚无对应原生代码”的表述仅反映当时尚未取得解包映像的研究阶段。

## Challenge 状态与版本

处理函数 `0x7770d0`：

1. 查到登录会话后，若 `LoginImpl+0xa8 == 0`（尚无此路径所需凭据），复制服务器属性，置属性已获标志，保存 Challenge 的版本 u32，并通知错误类别 6 / `server attr`；不生成正常 Response。
2. 有凭据且 `+0xcc` 校验标志非零时，将 Challenge 版本与 `+0xd0` 比较，不一致走 `version not match` 错误类别 4。
3. 特定认证模式 `+0xd8 == 1` 走另一凭据分支；普通模式调用 `0x774a00`。

`LoginParam` 构造器 `0x815850` 在 `0x8158ec / 0x8158f2` 将 `version(+0x90)=0`、`check_version(+0x8c)=false`；`0x775480` 将它们复制到 LoginImpl 的 `+0xd0 / +0xcc`。上层 `0x82af3b–0x82af4e` 仅在传入版本参数非零时开启校验。客户端发行版号 1.6.1 不能作为网络版本整数的依据；默认零版本是可验证的初始值，但运行时调用方可覆盖。

**当前实际登录路径的网络版本已进一步确证为 601 (`0x259`)，Challenge 应写大端 `00 00 02 59`。** 主任务实测零版本出现“版本号不匹配”，推动继续追踪调用方：函数起点为 `0x82acf0`，序言将栈减去共 `0x330`，因此 `0x82af3b` 的 `[esp+0x348]` 是入口第 6 个参数（入口 ESP + 0x18）。两个真实调用点 `0x82c460`、`0x82c6cb` 均在第 6 个参数位置传入立即数 `0x259`，对应 push 指令为 `0x82c44c` 和 `0x82c6a0`。这证明该路径覆盖默认值并开启版本校验；不能再以默认 0 作为当前登录路径的兼容版本。此结论来自调用点常量和栈布局，不是由 `.version.meta` 猜测。

## 普通密码分支与密钥派生

以下公式适用于 `0x774a00` 中外部认证辅助路径没有成功、会话 `AuthContext+4` 为 false 的普通 fallback。辅助认证路径存在，不能把下述公式推广到所有渠道、令牌或矩阵认证。

凭据获取回调 `0x776ce0` 返回两个 string，来自 LoginImpl secondary interface 的 `+0x90` 和 `+0xac`；Response 组装 `0x776d10` 将第一个写入首个 octets。依据调用关系，第一个为用户名、第二个为密码。

```text
P = MD5(username_bytes || password_bytes)
Response_digest = HMAC_MD5(key=P, message=server_challenge_16_bytes)
K_client_output = HMAC_MD5(key=P, message=username_bytes || server_nonce)
K_client_input  = HMAC_MD5(key=P, message=username_bytes || client_nonce)
```

证据：`0x774930` 对两个 string 依次调用 MD5 update `0x773660` 并 finalize `0x773790`；`0x774a00` 以所得摘要初始化 HMAC 后喂入 Challenge。HMAC 初始化 `0x7738a0` 有 64 字节块、0x36 / 0x5c 内外填充，终结 `0x7739a0` 进行 inner/outer MD5。

KeyExchange 处理 `0x774e00` 普通分支调用 `0x7746a0`，以 P 为 HMAC key、用户名和 nonce 依次作为 message。客户端 nonce 由 `0x774900` 生成 16 字节；研究没有替换或操纵随机源。

## 加密方向与切换时序

- `ARCFourSecurity` 的 RTTI / vtable 为 `0x294216c / 0x2472044`；`0x78cd00` 构造 security type 2。
- `DecompressARCFourSecurity` 的 RTTI / vtable 为 `0x29420d4 / 0x24720c4`；`0x78d600` 构造 security type 6。
- `CompressARCFourSecurity` 的 RTTI / vtable 为 `0x2942104 / 0x24720a4`；其 Update `0x78d510` 先压缩再调用内部 ARCFour。解压类 Update `0x78d670` 先 ARCFour 再解压。

普通 KeyExchange 处理中先用服务器 nonce 派生的 key 经 callback+0x18 (`0x776ec0 → 0x77c740 → 0x781bb0`) 安装到 socket session `+0x58`，type 2，即客户端输出纯 RC4。随后生成客户端 nonce，以其派生 key 经 callback+0x1c (`0x776ee0 → 0x77c670 → 0x781b30`) 安装到 socket session `+0x54`，type 6，即客户端输入解密后解压。

之后才执行 callback+0x20 (`0x776f00`)，组装客户端 KeyExchange。发送路径为 `0x776690 → 0x770fc0 → 0x77c370 → 0x781fa0`；`0x782005` 明确取得当前 `session+0x58` 并调用 Update，之后 `0x7820da` 才调用 send。

**因此普通路径客户端 KeyExchange 响应本身就是新 RC4 输出流的第一段。服务端应先用 K_client_output 解密该响应，取出 client_nonce，然后为下行建立 K_client_input 的压缩后 RC4 流。之后两个方向各自保持 RC4 状态，不能按包重置。** 服务端初次 KeyExchange 在这个切换发生之前，使用此前未加密状态。此结论是静态调用顺序证明，仍应由当前运行态收发实测核对。

KeyExchange 的服务器附带 u32 在 `0x777420` 处理函数中没有读取；客户端回复的 u32 在 `0x776f60` 由 LoginImpl 主对象 `+0xd4` 的 byte 归一化为 bool。语义尚未确认，不能称为可控制压缩的开关。上述普通分支始终安装 type 2 / type 6。

## 压缩流的独立离线判据

纯原生压缩例程 `0x1918cb0` 已通过 Unicorn 离线 CPU 仿真执行。其 literal 编码：低于 128 的字节写原值 8 bit；高位字节写 `10` + 低 7 bit；块尾写 `1111000000` 并零补齐字节。原生解压代码 `0x78c4ac–0x78c579` 与 literal 分支和零距离结束标记相互吻合。

`research_auth.py --self-check` 对 7 字节混合样本、0–127、128–255、0–255 四组输入，将 literal-only 编码与实际执行的原生压缩器逐字节比较，全部一致。示例 `010203807f80ff → 010203803fc02ffe00`。包含大量重复字节时原生压缩器会使用回溯引用，因此它的压缩结果可与合法 literal-only 表达不同。

连续块、分片与原生解压器的更完整验证由主任务另一个压缩研究子任务处理；此处没有重复或冒称其尚未传回的结果。

## OnlineAnnounce 与业务状态交接

主任务同步的原生证据：OnlineAnnounce type 110 / 0x6e，vtable `0x2471eb4`，构造 `0x78a730`，marshal / unmarshal `0x78a760 / 0x78a8c0`，body 为 6 个大端 u32。Process `0x777500` 将最后字段写入 LoginImpl `+0x15c`、设置 5000 毫秒计时，然后调用 `LoginImpl+0x3c` 所指上层 interface 的 `+0xc`，参数来自第 1、4、5、6 个 payload 字段。该上层 interface 不是 LoginImpl 主虚表，存在多重继承，不能用错误虚表猜函数。

本研究未证明 OnlineAnnounce 后所有业务流程均停留同一 TCP，也未证明之后不会迁移游戏服；主任务正依据实际 CRoleList 与角色流程继续核验。本批没有确认进游戏状态、角色创建成功或长期会话行为。

## 产物与未验证范围

产物：`research_auth.py` 的只读字符串/引用/RTTI/反汇编探针、纯原生压缩函数离线执行入口和 4 组比较检查；`auth-disassembly.txt` 保存本地源码证据等价的机器码反汇编和映像 hash；本报告记录实际决定、字段、验证结果及界限。

未验证：外部认证辅助路径、矩阵/令牌认证、非 ASCII 用户名与密码的实际编码、真实在线双向切换数据、登录后的建角/场景协议。当前调用方覆盖的网络版本值已确证为 601，601 的实际握手结果交主任务核验。没有从其他游戏协议补齐未知项。
