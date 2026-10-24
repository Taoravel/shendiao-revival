Spec复审：原P2关闭，新增0项可行动问题。

七个final文件实际哈希全部匹配manifest，地图及35例原生研究文件保持v1字节。

新增检查同时覆盖历史解码与expected receipt的三个epoch，拒绝bool/float；历史与expected改用规范JSON比较，避免dataclass数值别名。测试通过真实租约接口建立整数epoch1，并整体替换三处epoch，准确覆盖原漏洞；固定报告为9组通过，绑定最终storage65e2709c…。

当前checkpoint的完整地址、entry版本及其committed/ready来源检查未放宽；后来移动和同模板换实例仍返回当前状态，不重放旧目标。纯SELECT及调用方事务合同保持。

本次只读静态复审与哈希核对，未重新执行测试或修改文件。