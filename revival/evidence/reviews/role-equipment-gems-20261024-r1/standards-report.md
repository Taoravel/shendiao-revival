# Standards

status: completed

固定对象：`changes.diff` SHA256 `2f177a88620ac8321acdfeab882412e27c183397260b34b63fe4796215bc2384`；1358 个固定依赖。无 Git/tracker，使用已授权固定清单、两份修改前字节与新增文件缺席证明；未制造提交或 issue。独立审查，未读取 Spec 报告。

## 发现

硬性违反：0。判断性气味：0。

已读 code-review、codebase-design，实际按以下标准核对：

- `current/AGENTS.md` 的模块分工及 `ARCHITECTURE.md` 的角色 `role_id + login_epoch`、同一调用方事务、启动时加载配置/DDL、连接所有者投递：新存档 Interface 经 Inventory 与根公开 Interface 校验当前租约；不创建连接、提交事务或发送；`prepare/load` 与角色路径分开；没有共享入口改动或全局队列/锁。
- 根唯一资源存档复用完整 before CAS、真实来源校验和原凭据；新增表只存六项基础属性。`read_profile` 和 paid 分支只读并拒绝待结算来源，未知基线不推零。
- `DESIGN_AUTHORITY.md` 的来源分类：原 numid 与原编解码证据和服务器设计相加/损坏/评分政策明确区分；共享、GUI、战斗、容量均未声称完成。
- codebase-design 的小 Interface 与 locality：角色资源 Adapter 集中来源组合和最终属性，原评分当前值校验提取后供存档与投影复用；无复制根资源写入逻辑。逐项判断全部 12 项基线气味，未发现值得提出的重复分支、假设性抽象、纯转发 Module 或继承误用。

原鉴定三文件与合成四文件的七个固定 SHA256 均与既有封签一致。

## 实际验证

在固定 `current/revival` 运行，全部 exit 0：

- `verify_equipment_gem_score_current.py` — PASS current known score at last valid gem version is readable without creating a next state

- `verify_role_equipment_gems.py` — PASS all14 gem families/extra totals,215/130 caps, broken/repair/unequip, no double count and unknown/stale policy refusals

- `verify_role_equipment_gem_storage.py` — PASS actual sole root carrier: HP caps100/148/203; no healing; downward clip; death preserved; 3 SQL faults and late caller rollback; strict paid readonly; stale lease refusal

- `verify_role_equipment_gem_protocol.py` — PASS 27-field original marshal/unmarshal; all21 existing fields preserved; signed6 extras assigned by original generic branch; invalid/truncated refuses; no GUI claim

- `verify_equipment_gem_score.py` — PASS designed score/native color, reversible baseline/no drift, preserved wear, unknown/stale/overflow refusals

- `verify_equipment_gem_score_storage.py` — PASS known score baseline failure/outer rollback, immutable no-reset, readonly reopen and current lease guards

- `verify_equipment_gem_presentation.py` — PASS paired score/color/gem CAS,3 actual write faults/late native rollback, immutable proof, readonly same-grade no-op and removal

`verify_snapshot.py`：PASS 1358 frozen dependency hashes, diff；验证前执行，完成后再次复核。

未验证：真实技能/请求授权、已付镶嵌控制器、共享接线、线上迁移、加密网络投递、GUI、实际战斗及并发容量。检查没有启动服务、连接真实存档或改共享源码。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。
