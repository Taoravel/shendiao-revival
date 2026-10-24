# Spec 独立审查

本轴采用 `code-review/SKILL.md` 的 Spec 方法；仅检查冻结新增文件的需求缺失、越界与错误实现，未读取 Standards 报告。非 Git 固定清单适配：无虚构提交或 issue；固定 diff SHA256 为 `6204e48e00f7b1b528937abe8d651da1f7b6300dff5efa9e2d36d7cc2cde761a`。

## 正文

未发现本片范围内可证实的 Spec 问题。

依据 `current/revival/evidence/EQUIPMENT_GEM_SOCKET_FOUNDATION.md:3`：“本批实现完整普通未培养210行规则、纯计划、显式来源CAS及原详情扩展；尚不是收费镶嵌/摘除action ready。”对该片要求，未发现缺失或部分实现，也未发现行为越界。

核对第7、11、13、19、21、23、25行合同：原 source0/1 精确定位 column1/4；单摘模板与全摘 -1；按等级替换保持序号并验证结果族集合；现金仅报价、双工具及降级返还仅计划；缺档保留未知；完整当前实例/库存版本/原 JSON/详情来源比较后只作下一版本 CAS。调用持续检查当前角色租约。原生编码保留基础属性与独立宝石效果、顺序和清空行为，不由列表猜测 score。未找到与这些约定矛盾的实现。

第35—40行列明的收费控制器、评分颜色来源、人物最终属性和资源、共享入口及真实 GUI 仍属后续闭包；代码未启用生产路由，亦未宣称可玩验收。本次通过不证明这些全量目标已完成。

## 独立验证

- 指定 Python、UTF-8，在冻结 `current/revival` 独立执行以下四项，均 exit 0：`verify_equipment_gems.py`、`verify_equipment_gem_detail.py`、`verify_equipment_gem_storage.py`、`verify_equipment_gem_requests.py`。
- `verify_snapshot.py` 验证 1320 个冻结依赖及 diff SHA；另逐项验证 10 个本片文件 SHA，全部一致。
- 检查了纯规则/编码/存储与四项测试正文。存储验证含实际 SQLite 写入故障和已编码后的外层失败回滚、旧 epoch、移走移回版本、三份原 JSON 变动及只读重开。请求验证含 6 次原 codec；详情验证执行完整原 parser，并保留配置终端 Adapter 边界。

## 未验范围

未独立重跑研究报告中的全部发送矩阵或评分消费者调查；未执行真实角色、收费材料/钱包事务、根资源投影、共享发布、客户端 GUI 或完整配置对象生命周期。装备栏样例仅是临时容器 fixture。未更改 source、策略或生产数据库。

## 计数

Spec：缺失/部分 0；scope creep 0；错误实现 0。合计 0。
