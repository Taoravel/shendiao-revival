# Spec review — complete

状态：complete。方法：code-review 的独立 Spec 轴；采用非 Git 固定 manifest，逐项把需求映射到六个新增文件，未读取 Standards 报告、未改源码。

冻结依据：diff SHA `7262f905d9e0508bf2d182a789b1d3e946372d2f6c8942cb159819cdb426258b`；`verify_snapshot.py` 通过 1329 项依赖与 diff；另核对全部 6 个 scope SHA。

(a) 本片缺失或 partial：未发现。`EQUIPMENT_GEM_SCORE_DESIGN.md:3` 明确“没有接生产写入、收费、人物投影或共享入口”；第31行列出的公开 writer、收费 controller、完整修饰、root/HP/MP、登录重连、共享投递、发布和 GUI 仍属全量未完成目标，不计作本片已交或本片缺陷。

(b) 越界：未发现。按 JSON `activation` 的“pure candidate rules”，新增实现没有激活共享路径、扣款、修改资源或覆盖旧评分来源；50..120 保持标为 designed，未把400/420解释为原普通宝石公式。

(c) 实现错误：未发现。按设计第11、17、19行，`project` 从 plain_score 加完整列表贡献重算，验证当前 score/color、角色实例、policy、下一 gem 版本和溢出；通过 dataclass replace 仅改 score 及必要颜色，保留耐久和其余字段。按第21、23行，存储复用当前租约 socket 快照，拒绝 unknown/reset，只保存基准元数据；no-change 投影结果不保存，同基准重入只读。删除及模板/归属变更触发清理，普通移动/耐久不清理。

验证：在冻结 `current/revival`，用指定 Python `-X utf8` 独立运行 `verify_equipment_gem_score.py`、`verify_equipment_gem_score_storage.py`，均 exit 0/PASS，覆盖原 native 分数/颜色、保留耐久、拒绝分支、真实 SQLite 失败与外层回滚、只读重入及旧 epoch。

未验证：清理触发器与全字段保留另经静态核对，未新增行为测试；未做真实角色、生产接线、收费、资源闭包、部署或 GUI 验收。

计数：缺失/partial 0；越界 0；实现错误 0；合计 0。结论仅适用于本片，不能推定全量宝石玩法完成。
