# 宠物普通/超级还童来源调查

父窗口原生后续已纠正本报告调查阶段的590猜测：真实PetSuperReturn/Wuxing控制读1160（Pet bean+38），590为独立旧字段。已执行的消费者/绑定与来源边界见PET_TRAITS_INTEGRATION及pet-traits-native.json；悟性原范围/分布仍未知。超级原kind2门禁已由pet-kind-native.json闭合，kind3不进入该特定分支，仍不代表完整资格。

日期2026-10-23，目标为本地1.6.1、网络版本601端游。采用 Matt Pocock research 方法：直接原包优先，官方同款PC交叉核对；依DESIGN_AUTHORITY区分client_verified/guide_supported/inferred及unknown，不用手游或后来合成系统补旧规则。已重读research SKILL、ARCHITECTURE及来源优先级。本批唯一新增产物为本文，未改生产/shared/政策或原始资源，未操作客户端、服务或真实战斗。原native请求与消费者由父窗口调查，本文不能代替其协议证据。

## 优先交给实现方的发现

- 普通31002/高级31087分界在原物品说明明确为**宠物参战等级**95以下/95及以上，不是宠物当前练到的level，也不是人物等级。原cpetnamebattlelevelconfig的battlelevel与158行cpetattr.uselevel逐ID全等。原物品needLevel=1、level=0不能误当宠物95门槛。
- 普通还童会重置成长、五资质、悟性、技能、属性点、寿命、忠诚并回0级；宝宝保颜色、血脉等级和进化等级；野生额外重置颜色与血脉，并转宝宝。XP具体归零、认证、扩格、绑定、时限技能、年糕等没有完整原字段规则，不得默默称已证。
- 超级31576只重置成长/资质/悟性，原帮助13143明确等级、技能不刷新；**先预览、再确认保存，保存时清年糕**。146746有未保存方案提示，说明候选方案是独立状态，不能预览时直接覆盖当前宠物。
- 神兽类及野生不能超级还童有原提示146589；普通是否同禁、仙兽kind3是否属于这句“神兽类”仍unknown。普通还童没有本批文本证明也有预览/保存两阶段，不能把超级流程默认套给普通。
- 五资质上下界、成长5档及候选天生技能存在，但**抽样分布、技能个数/抽选、悟性范围均未由这些表证明**。不得将数组当等概率或默认把所有候选技能都给到结果。

## 直接PFS复核与方法

对原 `artres/config.pfs` 调用现有只读PfsArchive.read（local/central一致、展开长度及CRC校验），BXML重新解码；逐行将全部attributes/lists与既有catalog比较，全等。不是只复述缓存JSON。根目录原文件没有写入。

| 原包autoconfig下表名 | 行数 | 展开字节 | CRC32 | 原条目SHA256 |
|---|---:|---:|---|---|
| knight.gsp.item.citemattr.xml | 12280 | 4096369 | a3add081 | 974a3b38049c5f5f7cdae418718ffadd2741d373a5846a40fb71289af25e726f |
| knight.gsp.item.cpetitemeffect.xml | 1056 | 100317 | 30662a78 | 0be68069f620854ff0f81f0a01170fa5bf86ed4ccd7ce324cb29043cf1920b05 |
| knight.gsp.pet.cpetattr.xml | 158 | 76736 | 9fc172d4 | 89d947b24d2e61cfe38f8e0ff24ea8ae6ad12410e8ae73e95256a1f1de9b00c8 |
| knight.gsp.pet.cpetnamebattlelevelconfig.xml | 158 | 8277 | aa3c09c1 | e5bd43175f7b720a0415d330d5c501c36b6b3a52b403c7da07d22a2a9ef95a11 |
| knight.gsp.servant.bookanswerconfig.xml | 2123 | 1391956 | db4543ec | 5676da882382a3c4e23221a35e0911a3bed1c6ab4e1c6364d9826a912267bf4c |
| knight.gsp.message.cmessagetip.xml | 11267 | 2516503 | b6871af3 | d0cfc9cb4613442be0bb8ec9262bf6db7f2c7fcb5ad28df05e150c4b0503fa20 |
| knight.gsp.message.cstringres.xml | 2904 | 126182 | 146da741 | 269e18f659ed1ec19984714faab798d2fa8449392e5d4b5b65d566d12adb2aae |

额外直接重读并全量比较8张相关表：cpetaptconfig 8行/CRC7df7b630；cpetaptadance 6/33e82d86；cpetgradecfg17/aadc82eb；cpetgradelevelcfg7/d16165b1；cpetproportion5/06471cd0；cpetqizhi6/fdf20fe3；cpetcake100/6b37f0b7；cpetevolution158/d388af2c。没有从这些表读出还童随机分布。cpetqizhi是气质造型buff，不是悟性随机表；cpetgradecfg是评分系数，不等于颜色抽取概率；cpetcake有ratio/percentage字段，不能在未查调用处前当还童概率。

复核工具：[pfs.py](../pfs.py)、[bxml.py](../bxml.py)、[catalog_rows](../inspect_client.py)。原行可复现于对应 [物品catalog](../catalogs/knight.gsp.item.citemattr.json)、[宠物物品效果catalog](../catalogs/knight.gsp.item.cpetitemeffect.json)、[宠物catalog](../catalogs/knight.gsp.pet.cpetattr.json)、[帮助catalog](../catalogs/knight.gsp.servant.bookanswerconfig.json)、[消息catalog](../catalogs/knight.gsp.message.cmessagetip.json)。

## 原物品与提示

三物品共同itemtypeid33、battleuse0、outbattleuse2、needLevel1。31002/31087最大叠加9999，31576为99。cpetitemeffect三行都为petskillid0、petbangding0、effecttype=[0]、effect=[0]。这些零不是重置后的属性值，也不能解释成“还童清空绑定/技能”。

| 原ID | 明确语义与来源 |
|---|---|
| citemattr31002 | 参战等级<95；普通重置字段如矩阵；野生额外重置颜色与血脉；链接帮助13002 |
| citemattr31087 | 参战等级≥95，其余重置/保留说明同31002；链接帮助13503 |
| citemattr31576 | 只改资质、悟性、成长，食用年糕失效 |
| bookanswer13002/13503 | 找宠物加强师选还童回0级；旧措辞只说95级以下/以上，不如物品说明明确。95边界采用31087的“及以上”，不因13503写“以上”制造95无人可洗的空档 |
| bookanswer36005 | 普通还童重置所有技能、初始基本属性、各项初始资质、成长；野生转宝宝并可重新生成一次颜色；右键物品打开还童界面 |
| bookanswer13143 | 超级仅刷新资质/悟性/成长，等级技能不刷新；预览→确认保存；保存后年糕清0 |
| cmessagetip146589 | 神兽类或野生不能超级还童；尚未知道代码kind分支 |
| cmessagetip146590 | 保存超级结果的确认框，提示清除已食年糕 |
| cmessagetip146591 | 超级保存后成长/悟性/资质重新生成的结果提示 |
| cmessagetip146746 | 某宠物还没有保存超级还童方案的提示 |
| cmessagetip149193 | 统御状态不能还童；提示未明确普通/超级触发范围，父窗口核原消费者 |

citemattr31339、31782/31783/31784等宝宝袋明确赠送特定技能，而另加还童后技能会改变的提示。这支持普通重洗不保礼包固定技能；不证明认证/扩格如何处理，也不证明新的候选技能抽样概率。

## 字段矩阵：已证与未知分开

下表“只改三项”的保留含义可由文字限定推断，但不能把未命名的独立持久元数据都升级成client_verified。

| 字段/状态 | 普通31002/31087 | 超级31576 |
|---|---|---|
| 五项基础资质 | client_verified重新生成；最终资质应重叠保留的血脉/进化效果，原具体计算流程另验 | client_verified重新生成；五资质上限/血脉叠加顺序另验 |
| 成长率 | client_verified重新生成 | client_verified重新生成 |
| 悟性 | client_verified重新生成，范围/分布unknown | 同左 |
| 当前自然等级 | client_verified回0 | client_verified保留 |
| 当前经验XP | 回0级意味着成长经验需有一致重置状态是inferred；原精确XP字段行为unknown | “只改三项”支持不改XP是inferred，原字段流程unknown |
| 初始五维/已分配潜能 | 原物品重生属性点，官网说此前已获/已分潜能清零；回0级初始数值及血脉奖励重建规则unknown | 只改三项支持保留已分点是inferred，派生值必须随新资质重算；未知不可重置整个成长账本 |
| 当前技能列表 | client_verified重新生成全部技能，不保礼包固定列表 | client_verified技能不刷新 |
| 技能认证/保护/扩格/学习进度/到期数据 | 未找到独立字段规则，unknown；“所有技能重置”不能直接假定全部metadata清0或保留 | 技能列表保留明确；附属metadata是否保留虽合理但仅inferred，需native/服务端设计 |
| 宝宝颜色 | client_verified保留 | “只改三项”推定保留 |
| 野生颜色 | client_verified重新生成一次，抽取分布unknown | client_verified存在野生拒绝提示，不进入重洗 |
| 宝宝血脉 | client_verified保留等级；原物品写血脉等级，官网进一步说明当前值及上限保留 | 只改三项推定保留，原power字段未直接命名 |
| 野生血脉 | client_verified重置，但准确power/奖励潜能处理unknown | 不适用 |
| 进化等级 | 普通物品client_verified不影响；野生例外只列颜色/血脉，没有说回退进化 | 只改三项推定保留 |
| 野生→宝宝 | client_verified普通后转宝宝；原标志编码由父窗口查 | 野生拒绝 |
| 绑定/拥有权/名字/参战选择 | 未见重置或改绑原条款；不得拿petbangding0擅自解绑 | 同左；保持无关身份为实现应遵循的边界，非原服完全已证 |
| 寿命 | client_verified重新生成；虽然模板life均6000，是否还童结果按颜色修正/随机unknown | 只改三项推定保留，不据此治疗 |
| 忠诚 | client_verified重新生成；取颜色上限/固定值/随机unknown | 只改三项推定保留 |
| 当前HP/MP/死亡 | 原明确重置/保存时治疗规则unknown | unknown；重算上限不自动证明回满或复活 |
| 年糕 | 普通是否清0无明确本批条款 | client_verified保存时清0；预览不清 |
| 未保存方案 | 普通尚无预览确认文本证据 | client_verified有候选和确认；取消/断线/更换宠物/重复生成的寿命与扣物时点unknown |

## 资格与95门槛

158行cpetnamebattlelevelconfig.battlelevel与cpetattr.uselevel完全相等；比如500001小灰狗uselevel5，而500043霹雳炮手/500044不死兵魂uselevel95，500040受刑者uselevel85。不能因当前把小灰狗练到100级就要求高级丹，也不能因95模板当前0级就允许普通丹。这是原物品“参战等级”用词与原模板字段交叉所得，具体native读取位置仍由父窗口验证。

普通文本明确允许宝宝和野生，野生会转宝宝；没有在普通说明中找到神兽/仙兽排除，也没有证明它们全部允许。超级有神兽类/野生拒绝消息，但“神兽类”是否包括kind3尚unknown。种类kind1/2/3不是野生/宝宝标志。不可把二者混为一列或按名字判定。更不能把31576的拒绝规则无证移植给31002/31087。

## 随机范围：原表能提供什么

原cpetattr提供五项资质min/max、growrate五元素列表、addpoint五元素、skillid候选列表及life。例500001小灰狗：攻1040–1220、防1130–1340、体840–1080、法585–730、速1025–1220；成长档986/996/1006/1016/1026；skillid200091/200061。这些是范围/候选的client_verified值，不证明均匀、独立、端点包含与抽样权重。

原500069麒麟五项min=max（攻1440、防1440、体1520、法1500、速1200），五成长档均1300；原500050囚龙·仙法资min=max1600、其他资质仍有区间，成长五档均1300；原500090九尾灵狐·仙攻资min=max1560，五成长档均1305。不能用这些范围存在与否推允许还童，也不能用“恒定成长”推其他属性无需随机。

定向原配置扫描pet/game/item/message/servant.book中的悟性、还童、认证、拓格、绑定、保存与有关英文key，未找到明确还童抽样分布/悟性区间。cpetaptadance的advance/divisor/multiplier和cpetgradecfg的评分coefficent都不是已证抽样权重。growrate档与颜色的相关性、资质是否受颜色联动、天生技能的出现概率/个数、野生颜色分布均unknown。应由主策划在针对性调查后集中design登记，不能隐藏在调用默认参数里。

## 官方同款PC交叉验证

- [官方《宠物还童》2012-07-29路径](https://sdxl.wanmei.com/info/qita/pet/20120729/133551.shtml)：普通NPC/右键开界面，重置基础属性/资质/技能/悟性及等级和此前潜能；宝宝保颜色/血脉上限与当前值，野生转0级并再生颜色。没有说明普通预览，也没有独立XP/认证/扩格/绑定规则。来源guide_supported，与本地重置主要范围相符；未证明所有1.6.1细节。
- [官方2013-07-24《7月25日更新公告》](https://sdxl.wanmei.com/news/gamebroad/20130724/147422.shtml)：明确该次客户端版本1.2.11；新增超级还童只改三项、等级技能不变、预览后确认保存、保存清年糕。与本地13143一致，故由本地证据确认该语义已随资源保留至目标客户端；不能把1.2.11全部规则直接当1.6.1。
- [官方2025-08-13合成预告](https://sdxl.wanmei.com/news/gamebroad/20250813/257899.shtml)：后来新增宠物合成和必带技能/扩格变化，明确属于另一时期；不用于本地还童后的必带技能或格数结论。手游及《神雕侠侣2》规则全部排除。

本次网页工具直接open前两页有不可访问/超时；使用标准库urllib.request常规HTTPS GET均获得200、UTF-8原文并在内存重读，未写额外快照文件。

| 官方HTML | 长度 | 响应原字节SHA256 |
|---|---:|---|
| 133551.shtml | 8419 | e0588c68e32962c432e7b4673bb3fe6d40b865105ecafcf952c1c3259c20730a |
| 147422.shtml | 13170 | 66d23e01210ac6e0dc57323f47b591df3475560f217e5cf485451fd5927e4565 |

另外定向检索官方PC“还童+认证/技能格/绑定/悟性/仙兽”。没有命中可解决认证扩格及绑定的可靠原规则；奖励同列神兽/仙兽与超级丹不证明该丹可喂同一获奖宠。

## 接口/状态设计建议及未验范围

普通与超级应拥有不同命令/结果范围。父窗口核定原生协议后，普通采用当前角色owner+epoch事务，原模板uselevel资格冻结、随机输入稳定绑定受理ID；候选随机结果与扣物/宠物重建/来源凭据原子提交。超级至少有当前状态与待保存候选分离，候选绑定pet_key、原版本/政策、稳定ID；保存时验证仍是同一基线并一次性替换允许字段/清年糕。预览扣物时点及取消重连语义未证，须显式design而非猜作原服。

不要通过删除宠物重建来完成还童（会丢身份、绑定/拥有权及未知子状态），不要把未知技能metadata静默清0；必须先列清当前已恢复领域状态的保留/替换计划。永久base资质与血脉/进化有效投影分开，重洗不重复发历史血脉潜能。配置及规则启动冻结，热路径无文件解析；所有状态与幂等凭据同事务，消息在提交前完成可编码验证，失败回滚。此为架构要求和实现建议，不是原服务器流程证据。

验证已完成：上述15表原包校验/字段比对、158项battlelevel/uselevel相等、重点帮助/提示及两官方原页200复读。未验证：原native完整请求字段、普通确认机制、服务器随机概率、认证扩格绑定/经验资源字段、神兽/仙兽全部资格、候选过期/扣物时点、生产接线/部署/实机和战斗结果。本批没有任何生产功能完成或线上验收宣称。

## 追加：悟性范围、单位与技能概率调查

父窗口已独立定位Pet bean+a8→消息+b0→属性590的原消费者及普通/超级不同布局，并交来SSuperReturnPetInfo的9个BE32及三个单key请求证据。本研究未重新执行其原生实验，因此仅作接口交叉线索，不用这些消息长度推悟性数值上限。

本批扩大到**原config.pfs中全部autoconfig XML记录**，重新BXML解码后扫描“悟性”。与宠物有关的直接命中为物品31002/31087/31576、帮助13143/36028/36034、消息146591和bookkeyconfig36024。另有task.ctiku217的一般人物对白和435的宠物技能格问答，没有数值范围。没有找到携带悟性上下界、单位或还童概率的原表行；此扫描不能排除二进制原生常量/无中文字段的服务器配置。

- `client_verified`：bookanswer36028说明悟性越高，每次升级领悟技能的机会越大。只证明方向和发生场景，不证明几率公式、每次升多少或最高几率。
- `client_verified`：bookanswer36034列悟性、资质、技能与成长率共同决定评分。不表示悟性提升成长率，也不表示二者抽样相关。
- `unknown`：悟性最小/最大、显示单位、是否百分比、档位、默认值及新宠/普通/超级还童各自分布。**不能造0–100、0–1000等原版范围**；BE32传输宽度也不是游戏合法区间。
- `unknown`：悟性是否影响打书扩格或技能生成数量。36028仅写升级领悟；不要把它扩展为秘籍学习成功率、格子上限或普通还童必带技能数。ctiku435把宠物悟性/名称颜色/进化/成长列为技能格选项，没有在该表提供正确答案索引，本研究不以题目本身认定正确项。
- `unknown`：悟性与成长的随机独立性、相关性。两者同被还童重抽不证明相关。

另一个应显式保留的冲突：本批直接原PFS `knight.gsp.item.cattributedesconfig.xml` 行590旧名称是“宠物躲闪资质”，numid591/percentid592；`cpetaptadance`590有advance0.0010/divisor1500/multiplier1500；`cpetgradecfg` id6/attrid590/coefficent0.2。父窗口原消费者将590定位悟性，旧表名不足以否定真实执行路径；反之这些advance/评分参数也不能直接当悟性抽样范围或单位。避免以旧名作第二个躲闪资质持久列。

官方补查使用sdxl.wanmei.com限定“悟性+100/范围/上限/越高/宠物/成长”。命中主要为2013超级还童公告和与宠物无关的周伯通文章，没有找到可解决悟性范围的PC一手数值资料。官方[宠物介绍133548](https://sdxl.wanmei.com/info/qita/pet/20120729/133548.shtml)的悟性段也仅描述悟性影响领悟技能机会，未提供数值边界。父窗口可继续查原UI格式化/比较消费者；在此之前悟性生成须由集中政策明确designed并与原范围未知并列，不能称还原概率完成。
