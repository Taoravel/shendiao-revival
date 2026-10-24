## Standards

# Standards

status: completed

固定对象：`changes.diff` SHA256 `ed037e464dc63db197b44fc8721ab26edf509d8187f0ba22a6c6964dd6cd1c3b`，1378项依赖。5个新增hunk与manifest一致，前批清单均缺席；没有既有production修改。无Git/tracker，沿用固定清单适配，未制造提交或issue。独立Standards轴，未读取Spec报告。

## 发现

硬性违反：0。判断性气味：0。本轴无最高严重项。

沿用已完整读取的code-review与codebase-design，复核本批AGENTS、GLOSSARY、ARCHITECTURE、DESIGN_AUTHORITY四份标准哈希与前批一致。

- 符合`ARCHITECTURE.md`的状态所有权与连接投递约束：唯一生产新增是纯数据Module，无数据库、连接、事务提交、网络或新权威状态。`carried_tip_reply`仅编码column1，文档要求调用方先取得当前角色租约下真实完整来源并核对模板/container，提交后交连接所有者投递；编码不成为权限。
- 符合`DESIGN_AUTHORITY.md`的原证据、未知与服务端实现区分：OrbTips明确背包4字段，SoulBean保留穿戴6字段；raw5/raw4交叉顺序有原码依据，raw6!=0只作有损显示投影，没有逆构造或历史值归一化。bag bit0与worn非零分别命名，未升级成完整旗标或绑定授权。
- 原码harness隔离等级/config的具体地址和固定值公开列明，仅核对字段放置、显示位与自然返回；未冒称本批认证等级、完整工厂、服务端准入或GUI。研究直接纠正近名对象和此前“背包六字段”措辞，原/设计/待验范围同Interface并置。
- codebase-design实际用于背包/穿戴类型和显示投影的Seam：调用方不会把16字节数据误当6字段资产来源；纯编码与权限分离。测试通过公开数据Interface与原码Adapter，独立字面bytes及16个原码fixture，不mock自身Module。

逐项判断全部12项气味基线，未见值得提出的问题。研究报告的原始复现片段是固定历史证据，未作为第二套生产实现。

## 实际验证

固定`current/revival`、指定Python、PYTHONUTF8=1，独立运行`verify_pet_soul_item_data.py`，exit0：原16字节codec、完整SItemTips、16个原parser/转换fixture、正负raw、交叉映射、bit0/非零差异、六字段误用、无效输入与截断拒绝均通过。

`verify_snapshot.py`验证前后均通过：1378项固定依赖和diff未改变；额外核对5个scope新增hunk与前批缺席证明。

未验证：实例持久化和完整旗标/品质、无损资产往返、宠物与槽位/战斗/技能权限、穿戴/摘除/融合扣料和幂等、宠物最终属性、共享/加密投递/部署/GUI/容量。没有启动服务/客户端、打开真实库或修改固定输入。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。


## Spec

# Spec

Status: completed

Independent Spec review using code-review and codebase-design already read in full. Fixed diff `ed037e464dc63db197b44fc8721ab26edf509d8187f0ba22a6c6964dd6cd1c3b`,1378 dependencies; five additions, no existing production changes, non-Git fixed-manifest adaptation without invented commits/tracker. Reviewed only manifest scope against `PET_SOUL_ITEM_DATA_INTEGRATION.md`, completed primary `PET_SOUL_ITEM_SOURCE_RESEARCH.md` and the architecture/design constraints. No Standards report consulted.

Findings: 0. No missing in-scope requirement, incorrect behavior or scope creep found.

The specified “仅16字节…累计经验、魂技ID、穿戴bean的raw5、穿戴bean的raw4” is implemented as four explicit integer fields with exact-length decoding and preserved signed trailing values. The distinct four-field Module avoids conflating carried item tips with six-field worn PetSoul data. The required “raw6!=0…显示标志” projection preserves the immutable original bean, exposes no inverse factory, and remains separate from the bag's unsigned flags bit0. None of these display values is treated as asset authority.

The “原column1的0xc03fe SItemTips” wrapper uses exactly column/key plus the sixteen-byte inner Octets; no template/raw6 or ordinary-equipment detail is inserted. Ownership, current container/source, transaction and delivery remain explicit caller requirements.

The native fixture driver compares original four-field codec and complete parent bytes, executes sixteen parser/converter cases including negative raw values, checks field placement and natural returns, and rejects six-field misuse, wrong lengths, boolean primitives, illegal keys and original-decoder truncation. Its fixed grade2 and31277/type2 host adapters are disclosed and do not certify XP calculation, complete item factory, gameplay admission or GUI.

## Independent verification

Fixed working directory: `current/revival`; `PYTHONUTF8=1`; interpreter `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.

- `verify_pet_soul_item_data.py`: exit0; original16-byte/full SItemTips, sixteen original parser/converter fixtures, signed fields/cross-order mapping, marker distinction and invalid/truncated refusal passed.
- `verify_snapshot.py`: passed before and after; all1378 frozen dependency hashes and diff unchanged.

No source/fixed input changed; no service/client or real role database opened. Unverified: item persistence/full flags provenance, lossless historical asset round trip, equip/remove/fusion permissions/materials/receipts, final pet battle effects, shared routing, encrypted delivery, deployment, GUI and capacity.

Spec summary: 0 findings; no worst issue within this axis.


Standards: 0 hard / 0 judgement findings; Spec: 0 findings. No worst issue in either axis. Full restoration remains active.
