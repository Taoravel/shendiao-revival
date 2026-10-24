# 实际维护失败观察
用真实RuntimeStoryMaps定时维护、MapOwner/pool和显式目录/catalog/close失败Adapter，观察ConnectionError/TimeoutError在retire→forget→close处发生后的安全与恢复状态。公开get_map不能重复载入旧地址，槽保留且另一独立地址仍可推进；后续collect是否重试、gc是否终止必须实际观察，不能只查catch关键词。
这是观察与交单，不实现新的恢复协议，不把fixture teardown称生产恢复；明确静态依据、动态证据、来源hash/稳定范围/未验证GUI。未知清理继续fenced是安全行为，但不能把其写成完整可用性恢复。不得改shared/服务/存档/GUI。
