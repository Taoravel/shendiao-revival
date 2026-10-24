# 帮派完整详情与三驻地标识

读取条件：发送帮派完整详情、绑定1393/1394/1395驻地或接研究/修炼面板前。第二十批只恢复原生详情codec及原消费/gate证据；服务器完整详情状态、组织空间准入和实际NPC路由仍未实现，不能把本交单当可玩帮派或上线闭包。当前固定交单指针guild-details-current-review.json。

## 原消息与消费链

SFactionDetailedData原构造0xf91cce写type0xc5624，vtable0x2285d74，marshal0xf91f00；内嵌FactionDetailedData vtable0x2285d4c，marshal0xf90c50。原handler0x14a43a0复制0xc8字节bean，经0x14a34f0消费。基础SUpdateFactionData0xc5616没有三驻地字段，不能向旧基础bean随意追加三个Q。

FactionSceneID独立bean vtable0x2272f0c，marshal0xe46020为三Q。它嵌在详情+a0，其+a8/+b0/+b8经原consumer写manager+230/+238/+240。0x148dac0根据当前原模板1393/1395/1394分别选择slot0/1/2，要求manager+228非零且完整Q与world+30/+34相同。原map catalog的pinyin分别juyiting/gongfangsuo/liangongfang；1394练功房确实使用第三个值。高32位不同、另一标识、无组织及其他模板的离线原指令负例已执行。

GuildSceneIDs(hall,workshop,practice)冻结且三个值均须显式提供，Python服务器标识约定为非负signed63；原wire宽度是64位，不能把本地约定说成客户端仅63位。0是显式未绑定值，绝不是准入许可。该bean不包含完整MapAddress或组织/成员代次，不从guild ID、模板、地址hash或入包生成资格。

## 完整原布局与纯Interface

guild_detail_protocol.GuildDetails为kw-only冻结快照，所有字段必填。guild_details(view)只校验并编码body，调用方自行形成(type0xc5624,body)逻辑消息；无DB、状态写者、Session、cipher或发送。未知数据不能靠填0/空串拼出貌似完整的面板。

| 原bean偏移 | 已核验wire形状 | 当前Interface |
|---|---|---|
| +4 | UTF16 Octets字符串 | unbound_header，业务意义未绑定 |
| +20 | map<i32,FactionBulletinDetail> | 冻结(key,GuildBulletin)元组，原map按key升序；两个字符串仍unbound |
| +2c | vector<CourseInfo> | GuildCourse，ID1一个参数、2..6两个、7三个；与家族模板7不同 |
| +3c/+40 | 两i32 | raw_i32_at_3c |
| +48/+50 | 两Q | raw_u64_at_48；不从字段宽度推断资金用途 |
| +58/+5c | 两i32 | raw_i32_at_58 |
| +60/+68/+70 | 三Q | raw_u64_at_60 |
| +78/+7c/+80/+84 | 四i32 | raw_i32_at_78，不预先命名建筑/级别语义 |
| +88 | list<FactionSkill>，每项五i32 | GuildSkill(skill_id,unbound_values四元组) |
| +94 | list<FactionPractice>，每项两i32 | GuildPractice(skill_id,status)，非零status不强行改成1 |
| +a0 | FactionSceneID，三Q | scenes；上述原消费链已验证 |
| +c0 | i32 | raw_i32_at_c0 |

内存+44的对齐空位不发到wire。未知i32原样保留signed32；未知Q保留完整unsigned64位模式，包括最高位，不将其当财务/资源业务范围授权。已知实际金额/等级仍由所属领域验证，再形成快照。前置不确定的槽位保持raw偏移名，没有按看似合理的金额、等级或研究XP名称猜绑。

原c5624 size policy0xf91d40接受0..65535字节，拒绝65536，本codec同限。公告32、历程100、技能/修炼各64、普通字符串4096字符/历程参数128字符及重复键/技能拒绝为designed局部输出预算，非原服玩法上限；最终包长度也必须满足原65535。公告/技能/修炼/历程分别校验冻结容器，拒绝bool标量、未知None和畸形形状；map有序编码，原list/vector保持顺序。所有业务状态与权限由上游拥有者承担，不能将codec验证成功当审批或购买成功。

## 验证与后续接入

verify_guild_details_native使用原映像临时bean、原map/list/vector及CRT Adapter，执行完整原详情marshal、c5624 wrapper、三Q消费与原驻地gate。非空公告/历程/研究/修炼、不同大于32位Q、UTF16长文本/非BMP、signed32边界及opaque Q最高位均比对；并拒绝重复/可变/未知/超预算输入。原consumer在第一次字符串复制调用前停止，证明三Q存储，不声称执行整个GUI初始化。参数与原bean字段分别来自原serializer、RTTI和cfactionprogress；测试101等数值仅隔离占位，不是任何玩法设计值。

继续完成的步骤：先追各raw字段的原控件/业务消费者，补家族/帮派真实详情状态和各Owner生产者；再由main统一建立组织→完整地址/驻地代次/三Q绑定、当前成员与角色租约/位置及NPC资格，并接c5624/原查询或NPC响应。修炼现金/丹仍须当前唯一source precommit和角色同事务结算。实际Peer、重连/权限变化、故障恢复与原GUI须按准确整闭包另验。该新Module当前无生产caller，不添加未知旧档默认值、注册NPC或共享路由。

方法：codebase-design将原布局集中为纯codec，显式保留未绑定语义，避免把客户端gate当服务器授权；tdd沿既有公开原生codec/x86临时验证Seam，实际红灯为缺Module/完整详情/GuildSkill/GuildCourse/GuildBulletin，然后逐切片实现，补充负例不冒称全先红。review准备时把猜测意味的raw组名改为原偏移名；code-review按第十九批固定源独立两轴；writing-for-agents共置来源、实际验证范围和接入完成条件。未改执行数值policy、shared、已有家族/帮派实现，未部署、开游戏、实际战斗或真人数据；全量goal继续active。
