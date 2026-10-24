# Standards

status: completed

硬性违反：0。判断性气味：0。本轴无最高严重项。

独立采用 code-review 与 codebase-design，只审固定 manifest 的4个新增路径；没有读取 Spec 报告。无 Git/tracker，沿用固定清单适配：diff SHA256 `dfc4f1b66713c13ddc98030655b9186740cf6f0c5bcf9c6c44d0f6453dcf09b6`；4路径在前批 manifest 均缺席，全部1378个既有输入hash继承，没有制造提交或issue。

按 `current/AGENTS.md`、`GLOSSARY.md`、`ARCHITECTURE.md`、`DESIGN_AUTHORITY.md` 核对：

- `pet_soul_item_storage.py::_owned` 复用公开 Inventory 当前事务快照；该 Interface 实际检查活动角色租约及账号/角色。当前basis包含完整物品、库存版本及原始来源，下一版本CAS与库存版本更新同事务，异常交调用方回滚。没有连接、提交、发送或额外资源存档；配置/DDL仅在load/prepare。
- 来源四项、明确flags及精确retained_raw6集中在冻结OrbSource；None明确无历史且没有默认值。未知记录返回None、详情拒绝。flags/raw6在变更时保持；通用物品更新触发失效，绑定ABA不恢复旧来源。重复已知导入读取当前而不重置。
- 源证据与设计CAS/失效策略分开；受限flags可保存但不作为操作授权；共享、paid资产、GUI、战斗、容量及旧档迁移均明确未完成。没有修改共享Inventory或七个既有鉴定/合成生产文件。

逐项考虑12项气味基线，未发现值得报告的气味。构造器校验与数据库读取资格校验分属两个真实输入Seam，未将必要验证重复当作抽象机会；小Interface集中当前来源和详情，未复制资源写入或添加假设性资产控制器。

## 独立验证

固定 `current/revival` 内，`PYTHONUTF8=1`，使用 `C:/Users/11950/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，均exit0：

- `verify_pet_soul_item_storage.py`：真实实例持久化、当前tips、完整CAS、负raw6/flags保留、未知不补零、只读导入、2处SQL故障及编码后异常回滚、绑定ABA、过期租约。
- `verify_pet_soul_item_data.py`：原16字节及完整SItemTips、16个原parser/converter组合、交叉字段/显示位差异及无损原raw6。
- `verify_snapshot.py`：运行前后均通过1382个依赖和固定diff；另直接核对前批清单与4路径缺席证明。

仅报告文件写入；未修改固定输入，未启动服务/客户端或读取真实角色库。未验实际资产穿戴/摘除/融合、当前源生成渠道/迁移、shared/加密投递/GUI/战斗/容量。

Standards：0 hard / 0 judgement findings；本轴无最高严重项。
