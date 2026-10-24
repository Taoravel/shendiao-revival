# 邪兽战后的CG10001：原始来源与接线输入

2026-10-24；本地神雕侠侣1.6.1端游 / 网络版本601。本批只新增此Markdown，不改策略数值、Task、World、main engine/storage/shared或任何已封签输入；不开游戏、不连服务、不读真人库、不运行战斗，不唤醒Battle的paused长期goal。当前P0首战、教学与发布不等待本研究。

方法：沿用已完整读取的research/codebase-design，重读当前AGENTS、ARCHITECTURE、DESIGN_AUTHORITY及前批[NEXT_DREAM_BATTLE_SOURCE_ROOT](D:/神雕侠侣/revival/evidence/NEXT_DREAM_BATTLE_SOURCE_ROOT.md)。research落实为原PFS CRC/BXML、电影原行、原代码/现有离线consumer反馈及官方原页；codebase-design落实为将真实任务提交、CG许可、客户端临时布景和权威位置分别放在Task、角色/连接、原CG消费者和地图Module，避免由一个CEnd或脚本Setmap同时改任务、奖励与世界归属。没有再委派或新建研究代码文件。

## 1. 直接结论：本节点不同于10019

client_verified：十条CG10001节点都是type10、NPC10084/模板1501、ProcessBarTime0，**没有Start/Finish/Note列表**。从其原phase2继续/耗尽路径会直接发CCommitScenarioQuest0xc4a44(taskID,NPCkey,option0)，phase2关闭不发CQuestDialogEnd。不能复用首战100107的“Finish两句→phase3关闭→DialogEnd”作为本CG必要启动条件，否则可能等待本节点不会发出的请求。

client_verified：state1无Finish/Note的后置路径把10001存进**任务manager+70**；该pending dispatcher对小于20000早退。本批重新用100161/10001实测，没有依据10019类推。显式SStartPlayCG10001的原Process可把10001交给CG入口，但这仍不能证明原服由谁、何时发包，或任务应在CG前还是匹配CEnd后完成。

client_verified：movie/10001.txt只有**一条Setmap**，L1为临时1006/132,33，L16 Start、L177 Return time100、L178 End；全文195物理行（最后15行是动作枚举说明）。它没有把服务器位置从本人私有1501迁到公共1006的授权。最终主角演员L167移到134,41也不是服务端落点。

unknown：本CG原服启动桥、许可/完成事务先后、结束/跳过/中断区分、重连恢复与精确移动恢复门槛。以下提供可执行设计输入，不替root决定这些规则。

## 2. 十条原任务、奖励和全部边

本批从config.pfs的cmainmissioninfo2460原记录逐条读前边、Post与后继，表内每条均唯一；没有按ID规律推导。十条完整record在附录A，字段缺省与显式0保留。

| 唯一前驱AI8027 | CG任务type10 | DisPlayNPCID | 唯一后继type40 | 后继的Post（第一次梦醒） |
| ---: | ---: | --- | --- | ---: |
| 100190 | 100161 | [10596,10597] | 100110 / AI8002 | 100111 |
| 100290 | 100261 | 缺省 | 100209 / AI8002 | 100210 |
| 100390 | 100361 | 缺省 | 100309 / AI8002 | 100310 |
| 100490 | 100461 | 缺省 | 100409 / AI8002 | 100410 |
| 100590 | 100561 | 缺省 | 100509 / AI8002 | 100510 |
| 100690 | 100661 | 缺省 | 100609 / AI8002 | 100610 |
| 100790 | 100761 | 缺省 | 100709 / AI8002 | 100710 |
| 100890 | 100861 | 缺省 | 100809 / AI8002 | 100810 |
| 100990 | 100961 | 缺省 | 100909 / AI8002 | 100910 |
| 103290 | 103261 | [10596,10597] | 103210 / AI8002 | 103211 |

十CG原共同字段：MissionType10、ActiveInfoNpcID10084、ActiveInfoMapID1501、ScenarioInfoAnimationID10001；AIInfoAIID0、ProcessBarTime0、BranchNpcID0；ExpReward/MoneyReward/PetExpReward/ShengWang/SMoney全0；RewardMapJumpType/MapID/X/Y全0。没有RewardItem、ScenarioInfoNpcConversationList、ScenarioInfoFinishConversationList、ScenarioInfoNpcID、ScenarioInfoFinishNpcID、Note或Branch子列表，ProcessBarText也缺省。**没有Start/Finish文本，不应把TaskInfoDescription当成原Start补播。**

原TaskInfoDescription去样式的中文全文为：

> 不错不错，你就是我要找的人了。黄药师就在陆家庄内，你快去找他吧。当然，在此之前里面似乎还有人需要你的帮助。行侠仗义的时间到了，$NAME$！

Purpose原文为帮助陆家庄内的陆立鼎，Trace同义；原富文本和全部0值见附录，不填造读条时间、金币或回图奖励。100161/103261有Display[10596,10597]，其余八条缺该list；不能为共用实现强改成十条完全相同。

全表使用Animation10001共11条，额外 **101004→101005→101006** 的CG是101005；它不属于本次十条自然族，不因电影ID相同开放。全表AI8002也11条，除上述十后继外是101006；同样不能扩准入。

### 原后继AI8002身份

十条后继为100110/100209/100309/100409/100509/100609/100709/100809/100909/103210，原NPC10084/Map1501、MissionType40、AI8002、Animation0、Jump0、Process0；ExpReward400、SMoney1000，MoneyReward/PetExpReward/ShengWang0。原Start三句（speaker10084/10006/10006），Finish一句（speaker10006），叙事为陆立鼎等人对抗李莫愁。它们的BattleInfoMonsterNum/目标ID/目标数仍0，**没有给正式敌阵或数值**。CG完成不等于AI8002获胜，不提前发这400/1000，也不直接激活梦醒奖励。

其Display顺序也非全同：100110/103210为[10006,10596,10597]；其余八条为[10084,10596,10597,10006]。这仍是原场景列表，不是战斗阵位。古墓链为100190→100161(CG10001)→100110(AI8002)→100111梦醒，后续按原边继续，不从CG直接梦醒。

## 3. 陆立鼎的真实原摆放与实例层次

原cnpcconfig10084：name/minimapquery/minimapshow均陆立鼎、modelID6097、npctype4、bodytype0、area1colour1/area2colour0、mapid1501、xPos137/yPos50、hide1、zaxueid-1、actionname0；leaveservice告辞，pinyin=[luliding]、chitchatidlist=[197,197,197]。hide1只是原值，本批不以它发放可见/交互许可。

原cmapconfig1501为“梦境嘉兴”、resdir=fubenjiaxing、dream1、findpathin=false、bShowInWorld=false；1006为“嘉兴”、resdir=map_1006_jiaxing、dream0、findpathin=true。私有实例/角色归属来自已采用服务器目录设计，原地图字段并未提供实例ID。

直接解码map.pfs的**fubenjiaxing/npc.xml第一条**：
`<record id="10084" posx="2201" posy="814" dir="7" />`。
按现load_placements同一原序枚举是placement1。应使用该实际摆放，不把CNpcConfig格坐标137,50乘16后拿2192,800替代2201,814；也不拿CG演员的132,33当NPC世界位置。NPC原source和私有MapAddress、当前成员许可、实际key/新鲜距离证明仍各有用途。

map.pfs两套map.rmp、maze.dat和npc.xml均实际存在并CRC读取：1501与1006的map.rmp SHA不同，maze SHA相同；这不表示它们是同一服务器实例，更不允许绕过目录/handoff。正文没有试探真人当前位置或改变其checkpoint。

## 4. 原movie10001全文与资源端点

原movie成员9004 bytes、UTF16；CRC424d12bc、SHA c539ab40…，完整逐物理行内容保存在附录B。

| 原行 | 端点 / 原字段 | 限制 |
| ---: | --- | --- |
| 1 | Setmap id1006 pos132,33；全文件Setmap字样只1次 | CG临时布景，不是服务器公共MapAddress或Task Jump |
| 7 | 陆立鼎演员model6097，132,33 | 电影演员坐标，不覆盖原摆放2201,814 |
| 8 | 主角演员id0/model6092，100,71 | 仅原脚本文字；原id0演员与真人外观替换细节本批未闭合 |
| 16 | Start | 原CG段标记，不能当服务端许可或已完成确认 |
| 167–169 | 主角MoveNPC至134,41/time1000，镜头134,41，SetDir2 | 不是服务器落点，也不是胜利/任务结算 |
| 177 | Return time100 | 原time字面，绝对单位本批不新增证明；调用恢复保存布景的原消费者 |
| 178 | End | 文本结束标记，不等于服务端可伪造CEnd或奖励完成 |
| 181–195 | eAction枚举说明1..15 | End后的脚本附注，不计为需服务器兑现的剧情动作 |

演员创建引用的model为6097/6092/6078/6079/6053/6025/6030，L69/L113/L141的李莫愁为不同局部varname/id但同model6030。PlaySound L4/L40/L63分别引用“梦中幻境”“死神来临”“步步紧逼”，由L39/L62/L173 StopSound对应停止；SetSE共8项，字面为“御蜂术3d”“受击3d”“传送”。这些是CG本地表现引用，不是创建真实战斗Fighter、扣HP、改NPC表或发任务奖励的命令。

本批对sound.pfs名称及effect.csound表、effect/3deffect.pfs名称及effect.ceffectconfig表做了这些中文字面端点的有界查找，未直接闭合对应文件/别名链；**不据此称资源缺失或本CG不能播放**。没有执行音频/模型/特效加载或GPU，未扩成全资源追踪。已确认的地图资源端点及其原字节SHA在附录C。

## 5. 原提交/暂存/显式播放/结束：分别举证

原image为50675712 bytes，SHA `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`。本批只复用已有MasterProbe、NativeBattleDecoder、native_decode Interface做少量局部反馈，未保存新代码文件、未修改原指令；UI/配置/NPC查询/连接均为明确隔离Adapter，未操作真实客户端。

### 5.1 type10空Start发什么

以原100161配置的MissionType10/Process0/Animation10001/NPC10084为fixture，UI phase2、Start vector空，真实64位NPCkey用明确测试值0x1122334455667788。执行原164c3d6..164c584：

```text
sent type0xc4a44
body 00018741 1122334455667788 00000000
task100161 / npc_key0x1122334455667788 / option0
UI close phase2
```

该body是16字节BEi32 taskID + BEu64 NPCkey + BEi32 option，**不含movieID、完成原因、elapsed或胜利**。随后执行原phase2关闭1644c1a..1644cf8，本批实际没有新增CQuestDialogEnd。这里只从已建立的phase2开始，未验证点击陆立鼎→完整任务UI建立的GPU链；也不将测试key当真人实体key。

原1643360路径先核type10，16433af读Process；0走16433e9构造普通CCommit。10019对应的是type40完成后有Finish的phase3清理，原0xc4a52仅BEi32 task100107，两者不是同一Seam。没有证据要求本CG先收到DialogEnd，也没有证据把CEnd作为原客户端第一次任务提交。

### 5.2 state1做什么、没做什么

本批用同一100161原字段执行原125c168..125c1cd的无Finish/Note fallback，得到TaskManager+70=10001。另以明确pending10001 fixture执行完整12550c0(0)：pending仍10001、calls=[]、messages=[]。原12550d2比较20000，小ID跳125511c返回，不能因为state1已完成就声称电影已启动。

CGManager和TaskManager是两份原状态：TaskManager+70暂存动画；CGManager+38为当前movie、+3c播放位、+40保存原场景。不能把清CG播放位等同已清TaskManager pending，或把pending作为服务端已持久化许可。相关原路径逐项沿[CG1/CG2研究](D:/神雕侠侣/revival/evidence/PROLOGUE_STORY_EFFECT_RESEARCH.md:102)交叉，不套60001标题特效或>=20000的其它分支。

### 5.3 显式SStart10001对照

本批body00002711在原SStartPlayCG decoder d57540实际解成10001并消费4字节；原Process12c43b0在CGmanager存在的fixture上执行到12c4140入口，读取原栈movie参数确为10001，然后停止。入口/loader/GPU没有执行。原下行类型是SStartPlayCG0xc0017，body单一BEi32 movieID。

这证明显式消息可到达入口，不证明原服务器何时发送、是否先提交任务，或当前真人已经播放。原12c4140继续保存movie/active/原场景并经12c3f10→12c3be0加载movie文本的静态链与既有离线证据一致；本批不重新模拟全片。

### 5.4 Return、End与CEnd10001

本批重读原Return消费者：12b99d0清section局部状态后跳12c0bf0；后者在12c0c0d读取CGmanager+40保存场景，12c0c17调用Scene11e0a80请求恢复。它不是向服务器发送地图handoff的代码。

通用tick12c0b1f检查当前section完成，移除后看队列，空队列在12c0b52调用12c0970；该清理路径播放位非0时构造0xc0018，12c09b2从manager+38读movieID，写入结束包。没有按TaskID决定奖励。本文重读了这些实际原指令；通用自然结束/清理的动态证据沿[原CG研究](D:/神雕侠侣/revival/evidence/PROLOGUE_STORY_EFFECT_RESEARCH.md:148)、[10019独立结束研究](D:/神雕侠侣/revival/evidence/PROLOGUE_FIRST_BATTLE_10019_NATIVE_RESEARCH.md:70)与[开场研究](D:/神雕侠侣/revival/evidence/NEW_CHARACTER_OPENING_RESEARCH.md:7)，并未宣称本批实际播放10001整片直到自然末尾。

本批另外以原CEnd decoder d4f110实解body00002711为movie10001、消费4字节。**本批没有新跑active10001整片自然结束**；codec能解10001、原通用读取当前movie、文件含End，是不同证据，不能合成已看完CG的实机结论。共用清理可被中断等路径使用，CEnd只含movieID，不含taskID/NPCkey、permit nonce、角色/epoch/位置版本、结束原因或“完整观看”成功位。

## 6. 官方端游资料核对

本批做三条定向官方域检索：`site:sdxl.wanmei.com "陆立鼎" "动画"`、`site:sdxl.wanmei.com "序章缘起" "CG"`、`site:sdxl.wanmei.com "陆家庄" "剧情" "电影"`；实际打开[2012-07-09官方《独创梦境系统 内置剧情宽屏电影》](https://sdxl.wanmei.com/news/gamenews/20120709/132562.shtml)。其陆家庄段支持主角经历李莫愁伤人、介入剧情的定性内容，与脚本场景相合，属于guide_supported；没有任务数值ID、SStart/CEnd、服务端许可或完成先后规则。未用宣传中的同屏/性能说法当本项目容量证据，也未用手游或后期副本代替原CG契约。历史URL日期不证明本地1.6.1逐项同版，未知仍交root明确设计。

## 7. 下一可执行设计需要root明确的最小集合

以下是unknown/inferred接入影响，不在本文件发放许可或选择时间/数值：

1. **入口与完成时点**：只从精确十任务、真实AI8027前驱已结算、本人当前private1501目录、实际陆立鼎placement1/key、当前租约/成员/连接/任务版本和原CCommit0触发。是先完成零奖任务再持久化等待CGcontinuation，还是先存CG permit等匹配CEnd才完成，由root选择；两种都不能伪称原服务器桥已恢复。不可要求phase3 DialogEnd。
2. **许可与重试**：单一角色当前电影/任务/流程身份及有界期限，SStart的真实发送屏障、早CEnd/错movie/旧连接/旧epoch/过期/取消处理。CEnd原包无nonce，同一连接两次同movie的迟到字节存在语义歧义；服务端至少须有明确permit状态、代次和不重开已完成任务的规则，必要的恢复/换连接策略由root裁定，不宣称能从相同body辨出新旧。
3. **任务与恢复**：入场permit、所采用policy/source fingerprint、零奖励任务终态、唯一AI8002 successor active0及outbox/发送continuation如何同一角色事务保存；事务提交后断线只恢复当前权威，不重付、重播历史状态或完成AI8002。零奖励不等于可以跳过幂等与故障恢复。
4. **权威位置不改**：CG10001本行Jump0，电影临时1006、演员100,71→134,41、Return原场景都不构成源1501离开/加入公共1006。若恢复策略决定重新发送Scene，应是按当前已保存MapAddress重投影，不能把CG坐标做reserve/activate或当新的持久checkpoint。后续真正梦醒的Jump与既有dream-return政策是另一任务。
5. **角色/地图/连接隔离**：获准CG开始撤销旧移动声明和成员许可/未付服务票据，跨Owner等待不持全服锁。当前成员投影、flow和连接控制按已定Interface处理；不让早/迟回执重新安装旧许可。源private地图保持正确生命周期归属，不能因本地临时布景把它视作无人而提前退休。
6. **Return后的可玩门槛**：CEnd并不证明CG自动将真实主角状态+218变0或资源加载成功；[WORLD_MOVEMENT_STATE_LIFECYCLE_GATES](D:/神雕侠侣/revival/evidence/WORLD_MOVEMENT_STATE_LIFECYCLE_GATES.md:58)已给原Return/cleanup反例。后置是否以当前未变权威位置发送原SSetRoleLocation0并等精确write/drain、是否需Scene重建，由root明确来源与失败策略；发送屏障只是服务器已写/排空，不是客户端完成资源/渲染的通用ACK。
7. **与下场战斗分开**：CG10001匹配完成最多按政策使本人当前流程进入原AI8002任务的可交互阶段，不能生成battle_won、直接梦醒、授技能或重复AI8027奖励。AI8002 roster/公式另配方；DisplayNPC和CG演员不自动变成战斗阵型。
8. **原包/画面验收**：脚本文本、原局部consumer、正式共享事务/发送恢复、真实客户端从陆立鼎播放电影再能移动/访问下个任务，分别验收。声音/特效别名、资源失败/中断、主角存在分支和全部原Scene辅助回调仍未闭合，不能凭decoder绿灯宣称完整电影可玩。

SceneBarrier应继续绑定当前Connection generation、场景/flow、完整地址和具体发送内容；它不是电影End的替身，也不能用固定等待或心跳伪造完成。本CG自身不需要从脚本推导服务器跨图；若因断线/实际其他流程导致世界归属已变，要拒绝原permit而按持久化恢复处理。

## 附录A：十CG原完整record的重建数据

common_attributes是十条所有共同属性；rows列出每行剩余属性及所有子列表，合并即原record。common_lists为空，不把缺省Start/Finish或Display硬补空数组。

```json
{
  "common_attributes": {
    "MissionName": "[主线]序章缘起",
    "MissionTypeString": "主线剧情",
    "MinLevel": "0",
    "MaxLevel": "0",
    "TransMinLevel": "0",
    "TransMaxLevel": "0",
    "TransformID": "0",
    "ExpReward": "0",
    "MoneyReward": "0",
    "PetExpReward": "0",
    "ShengWang": "0",
    "SMoney": "0",
    "RewardMapJumpType": "0",
    "RewardMapID": "0",
    "RewardMapXPos": "0",
    "RewardMapYPos": "0",
    "ProcessBarTime": "0",
    "MissionType": "10",
    "ActiveInfoNpcID": "10084",
    "ActiveInfoMapID": "1501",
    "ActiveInfoLeftPos": "0",
    "ActiveInfoTopPos": "0",
    "ActiveInfoRightPos": "0",
    "ActiveInfoBottomPos": "0",
    "ActiveInfoTargetID": "0",
    "ActiveInfoTargetNum": "0",
    "ActiveInfoMiniStep": "0",
    "ActiveInfoStepProbability": "0",
    "ActiveInfoMaxStep": "0",
    "ActiveInfoTeamState": "1",
    "ActiveInfoTimeLimit": "0",
    "ActiveInfoIsRestartTimer": "0",
    "ActiveInfoGiveBackMoney": "0",
    "ActiveInfoGiveBackPetID": "0",
    "ActiveInfoUseItemID": "0",
    "ActiveInfoOtherType": "0",
    "QuestionInfoNpcID": "0",
    "TaskInfoDescriptionListA": "<T t=\"不错不错，你就是我要找的人了。黄药师就在陆家庄内，你快去找他吧。当然，在此之前里面似乎还有人需要你的帮助。行侠仗义的时间到了，$NAME$！\" c=\"ff12c4ff\" ></T>",
    "TaskInfoPurposeListA": "<T t=\"帮助陆家庄内的\"></T><G t=\"陆立鼎\" npcid=\"10084\"></G><T t=\"。\"></T>",
    "TaskInfoTraceListA": "<T t=\"帮助陆家庄内的\"></T><G t=\"陆立鼎\" npcid=\"10084\"></G>",
    "AIInfoAIID": "0",
    "AIInfoBattleResult": "1",
    "AIInfoDeathPunish": "0",
    "AIInfoTeamSteate": "1",
    "BattleInfoBattleMapType": "1",
    "BattleInfoBattleZoneID": "0",
    "BattleInfoDrop": "0",
    "BattleInfoBattleTimes": "0",
    "BattleInfoMonsterNum": "0",
    "BattleInfoDropItemID": "0",
    "BattleInfoDropItemNum": "0",
    "ScenarioInfoAnimationID": "10001",
    "ScenarioInfoBranchNpcID": "0"
  },
  "common_lists": {},
  "rows": [
    {
      "attributes": {
        "id": "100161"
      },
      "lists": {
        "PostMissionList": [
          "100110"
        ],
        "DisPlayNPCID": [
          "10596",
          "10597"
        ]
      }
    },
    {
      "attributes": {
        "id": "100261"
      },
      "lists": {
        "PostMissionList": [
          "100209"
        ]
      }
    },
    {
      "attributes": {
        "id": "100361"
      },
      "lists": {
        "PostMissionList": [
          "100309"
        ]
      }
    },
    {
      "attributes": {
        "id": "100461"
      },
      "lists": {
        "PostMissionList": [
          "100409"
        ]
      }
    },
    {
      "attributes": {
        "id": "100561"
      },
      "lists": {
        "PostMissionList": [
          "100509"
        ]
      }
    },
    {
      "attributes": {
        "id": "100661"
      },
      "lists": {
        "PostMissionList": [
          "100609"
        ]
      }
    },
    {
      "attributes": {
        "id": "100761"
      },
      "lists": {
        "PostMissionList": [
          "100709"
        ]
      }
    },
    {
      "attributes": {
        "id": "100861"
      },
      "lists": {
        "PostMissionList": [
          "100809"
        ]
      }
    },
    {
      "attributes": {
        "id": "100961"
      },
      "lists": {
        "PostMissionList": [
          "100909"
        ]
      }
    },
    {
      "attributes": {
        "id": "103261"
      },
      "lists": {
        "PostMissionList": [
          "103210"
        ],
        "DisPlayNPCID": [
          "10596",
          "10597"
        ]
      }
    }
  ]
}
```

## 附录B：movie/10001.txt完整物理行

前缀`NNN|`仅为本研究标注物理行号，不属于原文件。空行、缩进、重复局部演员、End后动作说明均保留；原UTF16字节只由PFS原件与附录C的SHA绑定，不以Markdown换行编码替代。

<!-- BEGIN ORIGINAL MOVIE10001 LINES -->
```text
001|Setmap id=1006 pos=132,33  
002|
003|   
004|PlaySound id=1 res=梦中幻境 repeat=0       
005|
006|MoveCam pos=132,33
007|CreateNpc id=2 varname=LLD pos=132,33 model=6097 npcname=陆立鼎 tile=8 dir=3
008|CreateNpc id=0 varname=主角 pos=100,71 model=6092 npcname=主角 tile=8 dir=1
009|CreateNpc id=3 varname=WSN pos=123,34 model=6078 npcname=武三娘 tile=8 dir=3
010|CreateNpc id=4 varname=LEN pos=133,27 model=6079 npcname=陆二娘 tile=8 dir=3
011|CreateNpc id=5 varname=BN1 pos=132,45 model=6053 npcname=婢女薇薇 tile=8 dir=1
012|CreateNpc id=6 varname=BN2 pos=144,35 model=6053 npcname=婢女琴琴 tile=8 dir=5
013|CreateNpc id=7 varname=AG pos=170,70 model=6025 npcname=阿根 tile=8 dir=3
014|
015|
016|Start
017|
018|Wait time=2000
019|MoveNPC varname=LLD pos=137,33 time=1500
020|
021|Say varname=LEN text=……
022|Wait time=700
023|Say varname=WSN text=……
024|Wait time=800
025|
026|MoveNPC varname=LLD pos=127,39 time=2000
027|Wait time=1000
028|SetDir varname=LEN dir=5
029|Wait time=1000
030|
031|MoveNPC varname=LLD pos=132,35 time=1000
032|Wait time=500
033|SetDir varname=LEN dir=3
034|Wait time=500
035|Speak head=9125 name=陆立鼎 text=如今能做的都做了，剩下的就等那女魔头来了……
036|Speak head=9022 name=李莫愁 text=问世间，情是何物……
037|
038|
039|StopSound id=1
040|PlaySound id=2 res=死神来临 repeat=0
041|
042|
043|Say varname=LLD text=！！
044|Say varname=WSN text=！！
045|Say varname=LEN text=！！
046|Say varname=BN1 text=！！
047|Say varname=BN2 text=！！
048|SetDir varname=LLD dir=3
049|SetDir varname=WSN dir=3
050|SetDir varname=BN1 dir=3
051|SetDir varname=BN2 dir=3
052|Wait time=1200
053|
054|MoveNPC varname=LLD pos=143,43 time=2500
055|
056|
057|MoveCam pos=166,71 time=4500
058|
059|
060|
061|
062|StopSound id=2
063|PlaySound id=3 res=步步紧逼 repeat=0
064|
065|
066|
067|SetSE name=御蜂术3d pos=179,78 repeat=1
068|Wait time=1000
069|CreateNpc id=8 varname=LMC pos=179,78 model=6030 npcname=李莫愁 tile=8 dir=7
070|
071|
072|Speak head=9022 name=李莫愁 text=直教人生死相许……
073|PlayAct varname=AG id=9 dir=3 end=1
074|Speak head=9145 name=阿根 text=是谁？
075|
076|MoveCam pos=143,43
077|Wait time=200
078|Speak head=9125 name=陆立鼎 text=阿根退开！
079|
080|MoveCam pos=166,71
081|MoveNPC varname=LMC pos=173,73 time=300
082|Wait time=300
083|
084|
085|
086|
087|
088|PlayAct varname=LMC id=8 dir=7
089|
090|SetSE name=受击3d pos=170,66 repeat=1
091|
092|PlayAct varname=AG id=7 dir=3 end=0
093|PlayAct varname=AG id=13 dir=3 end=0
094|
095|MoveNPC varname=LLD pos=165,63 time=1200
096|
097|
098|
099|
100|
101|
102|Wait time=100
103|
104|Wait time=1000
105|SetDir varname=LLD dir=3
106|Speak head=9125 name=陆立鼎 text=可恶！慢了一步！
107|Speak head=9022 name=李莫愁 text=今天陆家庄里的人，一个也别想跑掉！
108|DeleteNPC varname=LMC
109|
110|MoveCam pos=141,39 
111|
112|Wait time=300
113|CreateNpc id=9 varname=LMC1 pos=135,48 model=6030 npcname=李莫愁 tile=8 dir=7
114|SetSE name=传送 pos=135,48 repeat=1
115|Speak head=9125 name=陆立鼎 text=小心！
116|PlayAct varname=LMC1 id=8 dir=7
117|MoveNPC varname=LMC1 pos=131,44 time=300
118|SetSE name=受击3d pos=132,45 repeat=1
119|MoveNPC varname=LLD pos=137,50 time=1500
120|PlayAct varname=BN1 id=7 dir=3 end=0
121|PlayAct varname=BN1 id=13 dir=3 end=0
122|Wait time=300
123|
124|PlayAct varname=LMC1 id=8 dir=1 end=0
125|MoveNPC varname=LMC1 pos=141,38 time=300
126|PlayAct varname=BN2 id=7 dir=7 end=0
127|PlayAct varname=BN2 id=13 dir=7 end=0
128|Say varname=LEN text=住手！
129|MoveNPC varname=LEN pos=139,30 time=1000
130|Wait time=300
131|SetSE name=受击3d pos=144,35 repeat=1
132|DeleteNPC varname=LMC1
133|
134|Wait time=100
135|SetDir varname=LLD dir=1
136|Wait time=100
137|SetDir varname=LEN dir=5
138|Wait time=100
139|
140|
141|CreateNpc id=11 varname=LMC3 pos=141,39 model=6030 npcname=李莫愁 tile=8 dir=3
142|SetSE name=传送 pos=141,39 repeat=1
143|Speak head=9022 name=李莫愁 text=两个女孩儿呢？
144|
145|SetDir varname=LMC3 dir=7
146|MoveNPC varname=WSN pos=138,36 time=500
147|Speak head=9021 name=武三娘 text=女魔头，看招！！
148|PlayAct varname=WSN id=9 dir=3 end=0
149|Wait time=300
150|SetSE name=受击3d pos=141,39 repeat=1
151|PlayAct varname=LMC3 id=11 dir=7 end=0
152|Wait time=300
153|PlayAct varname=LMC3 id=9 dir=7 end=0
154|Wait time=300
155|SetSE name=受击3d pos=138,36 repeat=1
156|Wait time=300
157|MoveNPC varname=WSN pos=134,32 time=100
158|Wait time=100
159|SetDir varname=WSN dir=3
160|PlayAct varname=WSN id=7 dir=3
161|PlayAct varname=WSN id=13 dir=3
162|Wait time=800
163|
164|MoveCam pos=100,71 time=500
165|SetDir varname=LMC3 dir=5
166|Speak head=0 name=主角 text=住手！休得再伤人性命！！
167|MoveNPC varname=主角 pos=134,41 time=1000
168|MoveCam pos=134,41 time=1000
169|SetDir varname=主角 dir=2
170|Speak head=9022 name=李莫愁 text=居然还叫了帮手？也好，那我便一并取了你们小命罢！
171|
172|
173|StopSound id=3
174|
175|
176|
177|Return time=100
178|End
179|
180|
181|eActionStand,		1//普通站立
182|	eActionStandRandom,	2//站立随机动作
183|	eActionBattleStand,	3//战斗警戒
184|	eActionWalk,		4//走动
185|	eActionRun,			5//跑步，不存在左腿还是右腿先跑
186|	eActionBattleRun,	6//战斗中跑
187|	eActionOnHit,		7//受击
188|	eActionAttack,		8//攻击
189|	eActionMagic,		9//施法
190|	eActionRunaway,		10//逃跑
191|	eActionDefence,		11//防御;
192|	eActionDodge,		12//闪避
193|	eActionDying,		13//倒地
194|	eActionDeath,		14//死亡
195|	eActionRoll,		15//击飞
```
<!-- END ORIGINAL MOVIE10001 LINES -->

## 附录C：原资源与本地输入SHA

以下成员都由PfsArchive直接读取，实际检查本地/中央目录、原长度、解压完整性、CRC；BXML记录按表名/id定位，不虚构二进制资源文本行号。map.rmp/maze这里只做字节/CRC端点核验，未渲染或重跑碰撞长模拟。

| 原包 / 成员 | bytes | CRC32 | 原解包SHA256 |
| --- | ---: | --- | --- |
| artres/config.pfs / autoconfig/knight.gsp.task.cmainmissioninfo.xml | 2026233 | 3f7ab7b3 | `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706` |
| artres/config.pfs / movie/10001.txt | 9004 | 424d12bc | `c539ab40e437da8d2a8bd5efc5dd914a54a1b719427bb7c2b991a657df207c67` |
| artres/config.pfs / autoconfig/knight.gsp.npc.cnpcconfig.xml | 619832 | cc437e13 | `b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85` |
| artres/config.pfs / autoconfig/knight.gsp.map.cmapconfig.xml | 91110 | 3325016f | `374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814` |
| artres/config.pfs / autoconfig/knight.gsp.task.cquesteffect.xml | 2476 | 81ba986b | `8fbbda8366389fe8da2635a4f4160717a6c30b25f3d969f163906366243c9e45` |
| artres/map.pfs / fubenjiaxing/npc.xml | 888 | 06370594 | `3e96b678f8213459052fcf8c9fccc9c1eb7222ac33672d2a966600513f7b32fa` |
| artres/map.pfs / fubenjiaxing/map.rmp | 102575 | dbcce0a5 | `6392a2ce42b4a88622b7f249deecc95992c00e8e7e31f85ba859c449756fa239` |
| artres/map.pfs / fubenjiaxing/maze.dat | 113676 | cda771b4 | `6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351` |
| artres/map.pfs / map_1006_jiaxing/map.rmp | 102575 | 6b6542f0 | `4ff957ef8bca5c8a3a739cf9ee00687ea37aeefb244706a4381b6d4550ae7214` |
| artres/map.pfs / map_1006_jiaxing/maze.dat | 113676 | cda771b4 | `6f81a7407738d6ce9b7ca167c82c28849dea1db12e7f2aa7fe1285e747698351` |
| artres/map.pfs / map_1006_jiaxing/npc.xml | 3571 | 51217023 | `72b66cc70e41d78997fb8369c74c5f21a69f500e790797718a41d56ff857752c` |
| artres/config.pfs / autoconfig/knight.gsp.effect.csound.xml | 439 | 03763c91 | `1c486c020114109d835b44ac8b3a29fca7fe3f428df0b43691da82f0542ef4da` |
| artres/config.pfs / autoconfig/knight.gsp.effect.ceffectconfig.xml | 7990 | 52d4cb99 | `af8a63e7b49e24e43a414db3234a156fba621369ee9c213e095d8cb91eee97de` |

本批本地consumer、政策约束与既有证据输入：
 
| 输入 | SHA256 |
| --- | --- |
| AGENTS.md | `8c47404ca7b4d8cc4eef07afb4ca242b9d6a006f2b20db00817e4bbb562d4630` |
| GLOSSARY.md | `cc1fe0dc7ec653b87935881e5b958aead7d1367270745712e5ff28c29c86db80` |
| revival/ARCHITECTURE.md | `0b98c5d027f33cf99071c2a316b77dbcd6a2a785b6658987209321bbadfc1d7d` |
| revival/DESIGN_AUTHORITY.md | `820829778bcd632f2963eebc5f3106600c873481212fa8542cdd144a2e0ecf5f` |
| revival/pfs.py | `d4c9a5f6080276ab51886fdd4f1d7e7c1618715f870cbce84c916cf03b163352` |
| revival/bxml.py | `ba61810a10fede4305075efd7120429fb165af90fdbb4fb94697862a30c8b66d` |
| revival/native_inspect.py | `0793e525a8e06fe8e6a216b3509202244463dc4bd469c7e87950edb03810b6a0` |
| revival/research_first_master_dialogue_end.py | `faba83a1122258cad0a0d03738f098b00033ee8d52fe2da850fec62f6cd71fbb` |
| revival/research_task_jiaxing_scenario.py | `0ff37e3c5c4625007c8c1d14a768d50a32fe0580003ff7407d9f251f22475a47` |
| revival/research_story_opening.py | `353fe4f74237a5539bafbc960c113ea54ee9047cbaea2bd80c29eced1245e36b` |
| revival/research_battle.py | `4aa276ece9ea4a9f13d9c4f9a0de2900f97cf77ff3783aeecc92e7d5f3a47b45` |
| revival/staging/research_prologue_first_battle_10019_native.py | `63100b9539912a725401df5d91eadf11b848da2bc6709e8dbc85bc4e443e6690` |
| revival/evidence/native-image.bin | `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791` |
| revival/evidence/NEXT_DREAM_BATTLE_SOURCE_ROOT.md | `70d345271193234a1f47e4e50e96402804bc4556bf0682deb64d8c510dcf6668` |
| revival/evidence/PROLOGUE_DREAM_RETURN_RESEARCH.md | `e91a556e91ebd6da8b2d9f5674cf2b6bf658c8169ad94264c3d4f00a9458fbb9` |
| revival/evidence/PROLOGUE_STORY_EFFECT_RESEARCH.md | `9911e9b51056edafd5b3dd75db29be34dbc039333c1746a7a62d4389e42ac5fc` |
| revival/evidence/PROLOGUE_FIRST_BATTLE_10019_NATIVE_RESEARCH.md | `4e8c5b02ce6141efceb8280e8135ed2bc29d10f49c20da82dacd15f8300c44c1` |
| revival/evidence/WORLD_MOVEMENT_STATE_LIFECYCLE_GATES.md | `c48aeca05dd95aefdb3bef564d0d6a0f821cdbf9d470f8d6453e8a32cd4e8cf8` |
| revival/evidence/MEMBER_BINDING_DECISION.md | `482be66d276a7ae6b647dc83726dc225538940dec0918ed11e5ec053cf455d29` |
| revival/design/newbie-dream-return-v1.json | `fd369d20ba847764eb6436f83819628b52f7f8bc54c743669c708d22edf304f4` |
| revival/design/scene-transition-v1.json | `f1c4b7ac3922caa59ad404bc3fd633dacdf1de9292d07069e5ee6edff529c9d8` |
| revival/evidence/NEW_CHARACTER_OPENING_RESEARCH.md | `84f4b5ba950e69c330b33af54fa4fad78ccd35b2280efe5c59d31f0371dbbc38` |

本批实际反馈为：原任务/配置/摆放BXML与完整电影原行；100161 empty-Start原CCommit及phase2无DialogEnd；state1存pending10001、完整pending dispatcher早退；显式SStart10001原decoder/Process到入口；CEnd10001原decoder；少量Return/tick/CEnd原指令复读；官方原页与有界检索。没有新代码/策略文件，没有运行监听、正式或临时DB、真人角色、游戏进程、GUI/渲染/音频、整片电影或任何战斗，未修改生产和已封签输入。

交付前重新读取十三原PFS成员，全部SHA与首次一致；二十二项本地输入SHA亦前后一致。从本Markdown的JSON附录合并十条CG record，与原属性/全部子列表逐项比较10/10一致；剥离附录B物理行号后，与原UTF16解码的195行逐行一致。

未验证原服务器桥、真实permit、完整10001自然结束、故障恢复/共享事务/真实SceneBarrier、重复恶意输入和商业容量；只交资料及待设计集合，不把它们标为已实现或已发布。没有为结束/恢复/任务完成新增任何原版推定规则。

