# Spec 轴：r2定向复核

结论：**旧P3已解决；当前未解决Spec发现0项。** 原发现及其依据保留于[上一版spec.md](../task-dream-return-dialogue-20261023T180738Z/spec.md)，不删除历史。

沿code-review独立Spec轴，仅核correction.diff、r2目标SHA及旧/新字节差异。manifest全部source SHA匹配；只有verify_task_prologue_return_dialogue.py变化，精确等于原文件两处字符串替换，Module及验证逻辑字节未变。新verifier SHA256为`dd9dcf202041780ba4b91e8b6c528f0fff1253e93580614d4fd58c4b8f7cf7af`。

第111行已改为“combined inactive/missing-predecessor first-family context refuses”，准确表达组合缺前提的拒绝；第116行明确有效post-AI8002及独立combat-predecessor负例均未验证。它不再将该组合负例冒称单项战斗前驱围栏已证，原P3准确收口。

承继上一版对20任务/43路线、来源/目录/NPC与世代围栏、只读raw intent的功能审查，无新增(a)遗漏、(b)扩域或(c)实现错误。未运行DB、线上或客户端；五组复跑结果为主任务提供，本轴未重复执行。第一族上述两项、完整自然故事与GUI仍未验；结算/传送政策/shared/deploy仍在本批范围之外。
