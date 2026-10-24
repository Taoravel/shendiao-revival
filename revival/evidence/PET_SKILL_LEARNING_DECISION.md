# 认证保护、拓格概率与进度恢复裁定

2026-10-23，端游1.6.1/网络版本601。当前参数唯一来源为`design/pet-skill-learning-v3.json`，已学ID存档格式继续pet-skills-v1；绑定另归pet-flags-v1。领域、原生Adapter和必要离线验证完成，shared c07ff入口与实际GUI尚未验收。

到期技能/空格现由pet-skill-expiry-v1补齐，规则及可信时间接口见PET_SKILL_EXPIRY_DECISION.md。过期格复用保持本页扩格进度，原概率表用于真实扩格尝试；200534只作空标记。已学ID和到期map分别持久化，战斗取当前有效快照。

## 来源优先与本批纠正

客户端确认：秘籍/认证符模板和实例身份、精确受保护ID、血脉格数4/4/6/8/10/12、原拓格阈值表、进度按宠物实例保存及signed16显示。18组原map codec→窗口合并→按当前宠物查询→当前技能数选阈值→进度条算术通过，见`pet-skill-progress-consumer.json`。初/高级认证符原描述确认保护1/另1技能，拓格失败额外增加1/3点。

最初有针对性的“认证符/必成/拓格概率”检索未找到本版公式，曾使用25%和临时增幅设计。随后从[原端游技能资料](https://sdxl.wanmei.com/info/qita/pet/20120729/133549.shtml)的概率公示入口找到[官方概率表](https://sdxl.wanmei.com/news/gamebroad/20170614/203848.shtml)“宠物技能开格子”图片。已读取官方原图并留档`pet-skill-probability-2017.png`；出处、哈希与数字见`pet-skill-probability-source.json`。该表按当前技能数0..11和无认证/初级/初高组合分别给值，属于`guide_supported`，其与1.6.1完全一致仍未证明。依项目客户端→同款端游资料→设计的优先级，采用它替换统一概率设计；临时v2未发布或部署，已移除，当前为v3。

例如2技能无认证10%、初级20%、组合100%；3技能分别5%/10%/20%；11技能无认证0.02%。原表在1技能时初级10%低于无认证20%，因此不能把认证描述中“增大几率”机械实现成固定加法。保留原表所有值。服务器两次固定draw均使用0..9999，精确表示0.02%，不得再按0..999采样。数字源于官方端游公示，不冒称客户端原服算法。

## 仍需明确设计的状态规则

- 正确新宠明确初始points0；旧未知保持None，可信完整已学列表和历史points才能一次导入，已存在禁止重置。13行阈值按原值0/10/20/40/80/100/200/400/1000/2000/4000/10000/0保存。
- 仅未到当前血脉格数上限的新系学习尝试参与拓格。尝试前points≥当前技能数正阈值则强制追加；追加后points归0。失败本次达到阈值，下一次享受保底；这是designed服务器顺序，原客户端只证明阈值显示。
- 失败基础加1为designed，认证额外1/3保留原描述。points最多到当前正阈值且整体≤10000。升级同系、已经达到血脉格数上限时保持points；有限格数的保护仍可生效。
- 初级/高级实例必须是携带的自有31254/31255，每个正数选择对应一本认证符，且高级需要初级。可只使用认证符而不选保护ID；所选ID必须当前已学且不同，每项需要对应认证符。空技能列表拒绝浪费认证符，无认证首个技能直接学会。
- 拓格失败只从未受保护位置选择，位置顺序保留，第二个固定draw modulo可替换位置数。全部已学被保护时，技能ID保持、valid attempt仍消费并累积进度。相同/较弱/无效请求不消费。每次有效学习尝试增加技能版本；points版本仅在实际点数变化时增加。
- 高阶同系原位升级；如果该原技能被本次保护，认为意图冲突并拒绝，不浪费材料。保护其他技能不影响合法升级，也不获得拓格进度。
- 每次有效尝试扣1本秘籍和每种供给认证符各1；不另收现金/经验。绑定秘籍只在真正学会/升级/替换时置宠物bit1；全部保护导致没学会时不绑定。扣书、扣认证符、技能、points、可选绑定、资产版本和回执同事务。

上述保证顺序、基础进度、消费/失败/升级细节与family=ID//10、rank=ID%10均是恢复设计。官方公示只用于几率，不扩展成其未给出的服务端细节。Pet+c4到期map是独立状态，现归PET_SKILL_EXPIRY_DECISION.md。特殊保护表13个ID的原UI用途是查找未选保护的特殊技能并警示，未据此擅自把全部这些ID永久免替换。

## 接入与完成条件

1. `Inventory.prepare`启动加载只读LearningRules并准备inventory_pet_skill_progress；新宠与成长/养护/技能/flags一起初始化。`PetState.skill_progress`为可选冻结SkillProgress(version,points)。旧数据无记录保持None。
2. 既有`learn_pet_skill`参数不变，新增可选关键字`options=SkillBookOptions(...)`。调用方同一有效角色租约事务执行；draws来自服务器且固定在同一个受理命令，数量2、范围0..9999。当前普通RoleOwner仍需将c07ff路由到`receive_pet_skill_book(body,epoch,request_id,draws)`，避免普通receive的pending分支。
3. 全六项请求由decode_skill_book_request解码；保留旧decode_skill_book作为仅默认选项的兼容解码Interface。认证符实例、受保护ID、源技能/等级与进度在领域中再次校验；客户端不提供技能版本、随机数或阈值。
4. Adapter在提交前编码当前Pet、实际现金携带栏和当前受影响宠物进度；绑定变化按PET_BINDING_INTEGRATION额外编码完整栏。回执保存历史，不覆盖当前；指纹包含v3、固定draw和全部选项。旧v1无保护回执的原形状/指纹继续只读确认，不补历史points。
5. c0800空查询已加入INVENTORY_TYPES（当前16类），Inventory.receive通过可信构造epoch读取；或显式调用receive_pet_skill_progress(body,epoch)。`pet_skill_progress_messages(db,epoch,pet_ids=None)`可加入调用方事务，返回不可变逻辑消息。全查询遇旧未知即pending，不用0伪造；学习只同步受影响的当前已知key，原客户端按key合并。c07ff仍要求专用上下文Adapter，16类不等于16套玩法已实机完成。
6. shared接线处已有战斗/传送防护，还需world joined检查及固定随机数生命周期；命令ID对应一次服务器受理，不能把线包相同等同同一次请求。取消等待不能撤销已提交尝试，I/O不明则按现有Owner规则隔离并重读。新部署由集成方统一处理，本模块未修改shared/运行服或操控客户端。

验收通过：公开receive/snapshot和真实临时库验证认证保护/不受保护位置替换、单技能受保护五次失败→10点→下次保底、2技能组合100%、count2初级与count3组合的1999/2000边界、11技能0.02%的draw1/2边界、12格上限、绑定失败/成功、升级冲突、旧回执与当前状态、真实progress/receipt保存abort、外层失败/缺钱包、未知旧值/导入不重置、opaque fenced租约、重开。原进度codec/消费者/UI算术消费当前回复；相关背包/装备/成长/喂养/用药/任务经验回归通过。

仍未完成：shared c07ff随机/时间命令接线与现场部署、GUI确认/学习通知动画、到期定时刷新与内容渠道、被动/主动战斗效果、血脉和进阶。协议可解码和领域落盘均不作为完整系统完成。

## 方法与产物

diagnosing-bugs用原map真实消费反馈核对signed16及阈值，并以真实SQLite late abort验证整体回滚；codebase-design集中LearningRules/计划/进度存档，复用角色事务与冻结快照；tdd在既有公开snapshot/receive先复现无进度与认证拒绝，再分支验证；writing-for-agents集中来源、接入顺序、范围及完成条件。官方资料发现后实际替换较弱设计并重做边界测试，没有保留一套容易通过但不符合资料的旧概率。

产物：pet_skill_progress.py、pet-skill-learning-v3.json、pet_skills/pet_protocol/Inventory局部接入、research_pet_skill_progress.py、verify_pet_skill_protection.py及原生/事务结构化证据。旧equip/unequip/snapshot/双栏公开签名保持稳定。
