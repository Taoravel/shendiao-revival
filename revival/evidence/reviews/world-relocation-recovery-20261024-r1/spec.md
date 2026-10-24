# Spec review: exact old-member relocation recovery

2026-10-24。读取 `code-review`、AGENTS及本批交接规格，对真实 Owner/RoleScene before→after 做 `git diff --no-index`，新增验证/交接按空基线审查。after Owner `8739863…`、RoleScene `5bf03c3…`、验证 `0b70745…` 均按固定 manifest 核验；未混工作区后续修改。

## Findings

- **[P2] 空重试分支绕过了捕获投影的生命周期身份。** 规格明确：“捕获时使用了投影的请求不能在清理时丢掉它或换成另一个空投影。” `after/world_owner.py:846` 取得current后，`:847–852` 在角色/关系/记录/offer/presence均空时允许 `current != expected` 并直接返回空成功，未单独核对 `projection_generation`。full-AOI场景先用正确view完成首次清理，再拿原snapshot以 `view=None` 或另一同地址空RoleScene重试，均被接受。正确view下的空幂等应保留；但捕获的非空投影代次应在空分支前仍匹配实际view代次，空投影不能抹去该身份。现有projection组只验证首次清理前的替换/丢弃，未覆盖首次清理后的空重试。此反例没有删除任何新状态，不扩大为已发生位置损坏。

## Independent verification and limits

独立运行冻结reference的全部11组，exit0，结果为 `spec-independent.json`；执行前后逐项核1418文件与after清单，实际生产导入均来自reference。引导初次因reference未含native-image.bin而在导入前失败；随后从reference预载native_inspect、仅从原workspace读取并核对映像SHA `2b49e95d…`，再切OUT=reference完成验证，没有补写冻结文件。

另独立执行上述空投影反例，原view、丢弃view、foreign空view三种重试均返回空成功；结果存 `spec-empty-projection-counterexample.json`，记录实际两投影代次及准确Owner SHA。其余所审合同对应明确实现：实际成员nonce、准备身份、旧epoch与Owner围栏、foreign pending拒绝、SQL决定后同Owner清旧、后来完整实例保持；Map不读SQL、不加入authority。

未独立复跑旧10/9/5回归。SQL事务提交与旧写者冻结仍是公开可信Adapter前置条件；shared/cache、真实发送、政策及GUI继续未验。本轴只新增报告/独立证据，没有改源、冻结、正式存档或服务。

Spec findings: **1 P2 open**。
