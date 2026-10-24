# 自然序章实际共享创建与Owner入口

2026-10-23，原始复原集成窗口。仅源码与临时存档限定检查，未部署、重启服务/客户端、操作GUI或运行战斗。政策为design/newbie-opening-v1.json；任务和世界Interface分别见TASK_NEWBIE_CHAPTER_INTEGRATION、NEWBIE_WORLD_HANDOFF。

## 方法及关键决定

codebase-design用于保留状态所有权：任务Module持久来源/章节/奖励，地图Module提供冻结Location，RoleOwner仅持冻结章与IntroTicket，连接只排队逻辑消息并顺序加密压缩。数据库线程每次创建局部NewbieFlow，公开from_ticket恢复source/request身份；不将角色持有的可变flow跨线程，不访问私有_ticket。首登先兑现成长、再激活root，避免既有防重复初始化拒绝任务进度。没有新增世界锁或电影等待线程。

diagnosing-bugs采用根窗口已运行verify_newbie_runtime --expect-missing的原缺口反馈：实际新角仍临安1007/无journal/无CG，预期为本门派设计出生/原root/intro movie。自有检查聚焦共享创建、门禁与晚期事务失败；根窗口维护独立红绿入口，本窗口不修改或执行该脚本。本批未采用TDD或双轴code-review。

## 实际接线

- runtime_storage.prepare启动加载地图/maze、43原路线和章政策；validate_birth_sites按明确设计state0/mask1、交互半径32、预算100000校验全部出生到真实首NPC的路径见证，任务规则另核原边界/资源。schema仅启动准备，成功后才发布创建依赖。
- AccountStore.create_role同事务写角色、现有growth来源、独立newbie来源和一次设计出生/位置version1；出生取movie演员终点，明确不是已证明原服务器出生。既有growth-only/钱包来源不补新章。
- load_role在有效租约事务先兑现显式人物基线，再通过事务局部flow初始化root offer/accept与authorized章节。RoleOwner读冻结章节，以持久phase提供world_snapshot独立intro0/1；真实经验仍在native+f8，无章旧角兼容且不从XP推断完成。
- 首次世界ACK恢复当前人物/任务/地图初始化后，取MapOwner真实Location及当前连接generation，持久授权成功后才返回root bean和SStartPlayCG。角色只保存返回的冻结ticket；只播intro_movie_id，200xx successor_card_effect_id绝不发成CG。首次ACK本身不完成任务。授权拒绝需重连恢复，不能把joined而无播放许可的连接留作正常可玩状态。
- 角色开场门禁覆盖线包的移动/NPC/背包/用药/任务/成长及其他玩法，也覆盖trusted settle/initialize_wallet/offer_task/scene_sent写入口；允许load/close、首次初始化、tick控制和匹配CEnd。tick不推进玩法，期限到只丢本地许可，不完成root；重连重新授权。
- CEnd须精确4字节正movie。地图Location、当前epoch/generation、冻结ticket及持久许可交任务Interface交叉校验；root完成、原唯一角色后继、原奖励和稳定章凭据同事务。提交成功后另起fenced事务重读固定宠物接受者（如有）及当前人物状态，再清角色ticket/发布快照/排队逻辑消息。失败只丢事务局部flow，角色原ticket可重试；完成重放不再次发奖/CG。CG内部Setmap/Return不写服务器权威位置。

## 自有必要检查

新增并运行verify_newbie_owner_contracts.py，证据newbie-owner-contracts-verification.json：

- 通过实际AccountStore.create_role和首租约load_role覆盖全部43路线，出生、冻结route和唯一active root均正确；每个账户使用正常三角色上限，未为检查放松生产限制。
- 创建在独立来源写入后故障，角色/growth来源/newbie来源/位置全部回滚；首租约在root激活后故障，growth/属性/root/chapter及兑现凭据一起回滚，已提交创建出生位置保留。
- 实际Peer/ConnectionOwner/RoleOwner入场，开场门禁拒绝玩法线包及可信资产/钱包/任务写入。相同播放授权用冻结ticket恢复事务局部flow，source、deadline、chapter revision不变。
- 完成在root/后继/奖励/章写入后故障，事务全部回滚，角色原ticket保留、root仍active且无奖励渠道凭据；同原许可重试成功后门禁解除，实际背包查询正常返回。持续RC4/原生MPPC解码通过。

根窗口随后独立运行verify_newbie_runtime默认模式全部通过，证据newbie-runtime-verification.json，本窗口已读取核对：古墓11001/少林11032自然创建、对应root与角色9唯一后继；没有trusted offer或手工改出生；错误/截断/重复CEnd无任务资产变化；pending新连接重播、completed重连与重建runtime不重播；原root零XP、intro0→1及原生codec/持续RC4/MPPC通过。开场拒绝trusted offer期间，旧角色heartbeat和不同MapOwner.location仍可推进。根维护的缺口反馈已由missing基线转绿，本窗口没有为登记再运行检查或全回归；不等于GUI/部署/战斗验收。

## 明确限制

原任务/路线/电影ID来自客户端；章持久阶段、state2初态、出生选择、30分钟许可期限、0/1投影和匹配声明可跳过均为批准的designed Adapter。CEnd无nonce/终止原因，不能证明自然完整观看，也不能彻底消除同movie相同迟到正文歧义。

未验收原客户端自然CG/Return/输入解锁/走到师父，用户黑屏和移动不能标为实机修复；首师父武器卡、装备type59及车夫任务传送尚未在本批接入。装备数值不会因找到modifier字段直接累入人物总属性。旧角色显式迁移、真实后段战斗、商业存储/容量和完整序章仍未完成。
