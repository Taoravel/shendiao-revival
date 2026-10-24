# 参战选择与实际寿命门槛

普通参与/死亡养护结算后续已提供PET_BATTLE_CARE_SETTLEMENT.md：持久计数和入场三版本、≤30/神兽/擂台例外、原生当前重放与实际root source失败回滚均离线通过；实际战斗接线仍待集成，不以本Gate文末历史“每场扣1待恢复”否定新领域实现。

后续神兽批次：已核实原kind2→CStringRes2676永生分支，并在所属care结算恢复免损。现可使用`CareRules.battle_care_ready(care,template_id)`进行含真实模板分类的门槛判断；旧ordinary_battle_care_ready保留普通用途。kind2不受寿命最低50限制但仍需已知合法care/忠诚>0及其余出战校验；kind3沿普通规则明确designed。详细来源、历史回执、实际测试和未验范围见PET_IMMORTALITY_INTEGRATION.md，不再以本文早期“神兽分类待恢复”作为当前结论。

2026-10-23。原bookanswer36001/36002明确：寿命低于50仍可设为参战，但不会实际参加战斗。此原客户端帮助覆盖了早期恢复设计“寿命0不允许选择”；所属Inventory已修正，不覆盖任何宠物存档。实际战斗加入与结算仍由战斗/角色Owner集成，本文不声明宠物已完整参加战斗。

## 原来源和当前政策

本批直接原config.pfs读取knight.gsp.servant.bookanswerconfig，验证本地头/目录、长度CRC后解BXML；2123行全部attributes/lists与catalog一致，CRC db4543ec。原36001/36002还写参加一场消耗1寿命、死亡消耗50；36002说明神兽忠诚/寿命不减。证据和原文本均写pet-lifetime-source-audit.json.help_audit。来源为client_verified帮助文字，未冒充原服务器代码或本批原生战斗指令。

design/pet-care-v1.json.limits现在明确：普通宠最低实际出战寿命50，低于50的选择状态仍可保存；原有忠诚0选择门禁保持。无数据自动迁移，care.1既有feed/defeat/寿命食物的状态和回执计算不变。特殊永生资格、特殊战斗例外以及低忠诚不服从概率仍单独待恢复。

## 给战斗集成方的Interface

启动已冻结的`CareRules.ordinary_battle_care_ready(pet_state.care)`只检查普通宠养护资格：已知合法PetCare、loyalty>0、lifetime>=50；None或非法care拒绝。无数据库、I/O或状态变化。输入应为角色Owner同一fenced事务取得的冻结PetState.care；不根据客户端选择字段或另读一份寿命放行。

调用方仍须确认普通宠身份、当前HP>0、原uselevel/角色级别、当前确实选中、技能/期限和战斗归属；这个care-only结果不代表完整战斗快照可用。神兽不能直接套普通寿命门槛/扣损规则。战斗Module收角色Owner冻结快照，不直接读取/修改Inventory或数据库。

Inventory的原`fight_pet`和`receive(FIGHT_PET,body,precommit)`只维持选择，已移除寿命0拒绝，仍保留原有忠诚、归属和原生入口uselevel检查。低寿命宠可保持fighting=1，而战斗构建应按当前care gate排除；不以取消选择来代替拒绝实际参战。补寿命食品不重选宠物，但下次构建快照可重新满足care门槛。

验收条件：0/1/49寿命均不满足实际普通出战care条件，50/51满足；0寿命仍能从原FIGHT_PET获得选择确认并持久化。补到1000时care门槛改变、选择状态保留、HP与完整战斗资格仍独立。每场消耗1与死亡损失的同一settlement去重、神兽分类和真实战斗场景尚待接线，不用现有defeat调用猜测普通参与事件。

## 实际方法与验证

tdd沿已约定Inventory事务/快照/原生命令Seam先复现0寿命选择被拒绝，再按原证据修正后绿。codebase-design将普通养护门槛集中在只读CareRules Interface，让角色/战斗调用方不复制50阈值或混淆selection；writing-for-agents列出其余实际参战条件与完成标准。

verify_pet_battle_care及pet-battle-care-verification.json通过真实0寿命选择、原c07d9确认、忠诚0拒绝且不替换当前宠、六种颜色的0/1/49/50/51边界与未知care拒绝。真实32036食品将0→1000且fighting保持1，原完整刷新decoder读1000，重开保持。当前无服务改动、GUI或实际战斗执行。
