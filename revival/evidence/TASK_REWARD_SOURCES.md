# 任务奖励与升级来源核查

日期：2026-10-23。对象：本项目 1.6.1 端游客户端、网络版本601。仅研究及撰写本文件，没有修改奖励实现、入口或存档，没有启动客户端验证或增加运行测试。

## 本批方法与决定

沿用已完整读取的 `research/SKILL.md`：一手本地配置 → 原生读取代码 → 同端游官方历史资料；未知项不从手游补齐。沿用 `codebase-design/SKILL.md`：奖励字段解释与升级消费规则分开，不让任务 Module 的 Interface 承担未经确认的升级状态机。已读 `../ARCHITECTURE.md` 和 `../DESIGN_AUTHORITY.md`；奖励事务和幂等凭据由角色资产所有者负责。

直接读取：`../catalogs/knight.gsp.task.cmainmissioninfo.json`、`../decoded/config/autoconfig/knight.gsp.task.cmainmissioninfo.xml`、`../catalogs/knight.gsp.role.cresmoneyconfig.json`、`../catalogs/knight.gsp.servant.servantchat.json`、`../catalogs/knight.gsp.task.carroweffect.json`、`../catalogs/knight.gsp.servant.bookanswerconfig.json`，以及 `native-image.bin`。本批没有重跑全量 PFS/CRC；原包核验参考既有 `design-client-audit.json`，本文件不宣称独立复核了原包。

## 四个原奖励字段

`CMainMissionInfo` 原配置解析函数使用 UTF-16 字段名，通过 `0x409db0` 的64位读取返回 EDX:EAX，写入下列位置；因此不是从英文名臆造出来的字段，也不能截成32位。

| 字段 | 原字符串地址 | 原读取/写入地址 | CMainMissionInfo 内偏移 | 支持强度 |
|---|---|---|---|---|
| ExpReward | `0x226c54c` | 读取 `0xbb5ae7`；写 `0xbb5af0 / 0xbb5af6` | `+0xa0/+0xa4` | 名称、值、64位存储 `client_verified`；人物基础经验解释为强 `inferred` |
| MoneyReward | `0x226c534` | 读取 `0xbb5b2e`；写 `0xbb5b37 / 0xbb5b3d` | `+0xa8/+0xac` | 名称、值、64位存储 `client_verified`；具体货币渠道未确认 |
| PetExpReward | `0x226c518` | 读取 `0xbb5b75`；写 `0xbb5b7e / 0xbb5b84` | `+0xb0/+0xb4` | 名称、值、64位存储 `client_verified`；宠物经验解释为强 `inferred`，归属规则未确认 |
| SMoney | `0x226c4f4` | 读取 `0xbb5bfb`；写 `0xbb5c04 / 0xbb5c0a` | `+0xc0/+0xc4` | 名称、值、64位存储 `client_verified`；不能据 S 猜绑定渠道 |

`ExpReward` 与 `PetExpReward` 同时存在且独立读取，为区分人物和宠物基础奖励提供很强支持；但本轮未追得该字段至原服结算，也没有证明显示值必然等于所有条件下的到账值。是否受组队、倍率、活动、等级、上限影响应另记。若实现采用 ExpReward 原值入人物经验银行，应将“原字段值”与“本地采用的到账政策”分别记录，不能称为已经实测的原版结算公式。

主表非零统计：ExpReward 863 条，PetExpReward 549 条，MoneyReward **0 条**，SMoney 307 条。例子：

| 原任务 ID | ExpReward | PetExpReward | MoneyReward | SMoney |
|---|---:|---:|---:|---:|
| 100105 | 120 | 0 | 0 | 0 |
| 100107 | 120 | 0 | 0 | 400 |
| 100192 | 150 | 0 | 0 | 0 |

所有字段中的明确0都是原数据，不代表缺失，不能触发“未知奖励比例补全”。MoneyReward 在本表全0也不证明该字段永远不用；SMoney 的非零值并不足以把它直接映射为绑定银。

原帮助表 `bookanswerconfig` id2001 区分可交易银两，id2003 区分不能玩家交易的绑银；这证明客户端确有不同资产渠道，**不证明 MoneyReward/SMoney 与两个渠道一一对应**。因此当前未确定货币映射时保留 pending，不能合并进统一余额。PetExpReward 的“出战宠物/携带宠物/全部宠物/无宠物处理”等本轮未确认，也不应自动转给人物。

## nextexp：索引已取得的证据与限制

原 `knight.gsp.role.CResMoneyConfig` UTF-16 名称地址 `0x225e150`；配置 getter `0x89e660` 返回注册表 `[0x2945aec]+0xd74`。`nextexp` 字符串地址 `0x225e100`，原解析 `0x88bb12..0x88bb40` 调 `0x409db0`，把64位值存入配置 bean `+0x10/+0x14`。

**可以证明按当前等级查表，而非按当前等级+1：**

- `SEnterWorld` handler `0x833f0d` 调 getter；`0x833f14` 从 RoleDetail 外层对象 `+0x34` 取当前角色等级，`0x833f1a..0x833f1d` 直接以该值查行，`0x833f1f / 0x833f29` 读取配置 `+0x10/+0x14`。此字段的角色等级身份已有 `WORLD_PLAYER_INITIALIZATION.md` 记录。
- 属性更新路径 `0x113f6b1` 以属性ID `0x1ea`（490）取等级，`0x113f6bf..0x113f6cc` 以原值查同表，`0x113f6ce..0x113f6da` 把 nextexp 写入客户端人物对象 `+0x90/+0x94`。同路径没有加1。

原配置 id1/2/3 的 nextexp 为89/195/373。所以客户端**当前1级对应89，当前2级对应195**的读取口径有直接证据。

仍未证明：服务端消费经验的扣除算法、累计经验还是单级余额、溢出结转、连升循环、手动升级校验、等级封顶与化境索引。这些不会因查表 key 已确认而自动成立。使用当前级 `nextexp` 作为“本地升级成本”仍需明确剩余来源状态；本轮主模块仅存 EXP bank、不自动升级，因此无需靠未知算法发放等级。

## “10级自动/手动升级界限”未证实

本地直接文本：

- `knight.gsp.servant.servantchat` **id31** 提示当前经验已足以升12级，并指示之后经验满时要手动升级。这是本版本资源内存在的文字，`client_verified`。它倾向于11→12这一阶段的手动引导，不能支持“10级起必定手动”。
- `knight.gsp.task.carroweffect` **id30007**，`button=UserPeticon/levelup`，是手动升级箭头提示；该记录没有等级字段。
- 原角色 `CLevelUp` RTTI 虚表 `0x226fbf4`；发送入口 `0x161c000` 在 `0x161c02b` 写 type `0xc0009`，`0x161c04c` 提交发送。这证明手动升级请求路径存在，不证明何时开放或服务器何时停止自动升级。

提示资源可能是未启用或历史遗留；本批没有证明 servantchat id31 的实际触发条件，因此也不将“12级”直接裁定为完整运行规则。**10级界限未知，12级引导文本存在，两者需明确区分。**

针对未知界限已检索同端游官网“手动升级/自动升级/12级”，并阅读下列历史官方页面，未取得人物自动升级转手动的确切界限。只查端游资料站，不将手游新闻或《神雕侠侣2》作为依据：

- [2012-06-29《怎样获得大量经验》](https://sdxl.wanmei.com/info/newplayer/oneminute/20120629/132123.shtml)：支持经验可被人物升级、经脉、技能消耗，反对把人物经验只当累计终身积分；不提供扣除公式或手动等级界限。`guide_supported`，历史版本，未证明与1.6.1完全一致。
- [2012-06-26《人物属性》](https://sdxl.wanmei.com/info/newplayer/1to9/20120626/131944.shtml)：给出升级潜力点规则，没有手动界限。未据此在任务模块自动加属性。
- [2012-06-26《10–19级主线任务》](https://sdxl.wanmei.com/info/newplayer/10to19/20120626/131956.shtml)：列任务等级与前提，没有自动/手动升级规则；目录“10–19级”不是升级分界的证据。

## 交付与未验证范围

本批只产出本证据文件。完成了原字段解析偏移、四字段非零分布、当前等级查表调用链和手动升级资源提示的静态核查；没有穷举底层比较，没有增设测试或修改实现。

建议最小接入：保留原 ExpReward 值进入人物经验银行；PetExpReward、MoneyReward、SMoney 在缺少归属/渠道证据时保持可追溯待结算；人物升级和属性变化由独立角色成长 Module 处理。以上是依据证据限制选择的小 Interface，并非新增原版规则。

未验证：原服到账倍率与上限、MoneyReward/SMoney渠道映射、宠物奖励归属、升级经验扣除、自动升级界限、真实客户端经验/等级显示、实际提交后资产事务与重登结果。事务/幂等实现验证由主任务记录，本研究未重复或代替其验收。
