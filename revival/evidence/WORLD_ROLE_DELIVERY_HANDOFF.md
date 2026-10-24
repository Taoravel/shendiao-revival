# 玩家视野投递：目标连接收件箱接线

2026-10-23。world_role_delivery提供目标连接执行者持有的RoleViewInbox，承接world_roles.RoleScene真实输出，处理成员/连接代次、顺序、重复和有界逻辑队列。它不持Session/writer、不编码RC4/MPPC、不调用网络或数据库；共享运行时尚未接入。

## 接入步骤

1. 仅在可信MapOwner活跃join完成后，用bind_role_view(presence,connection.generation)建立冻结RoleViewBinding，并为该角色/连接当前视野建立RoleViewInbox(binding,message_capacity=...,byte_capacity=...)。容量必须显式提供，测试值不是生产配置。loading Location不能建立绑定。绑定含MapAddress、地图Owner generation、role/epoch、membership_revision及connection generation；移动沿用同一绑定。
2. 路由时先在源地图执行者核RoleScene.delivery_is_current，再把逻辑RoleDelivery和可信在线目录中匹配的当前绑定交route_role_delivery。该冻结RoleViewRoute在跨执行者之前捕获连接代次。不能在迟到消息到达时按新连接重新包装旧route；原线包没有这些字段，也不能由来包创建绑定。
3. 目标连接自己的执行者调用inbox.offer(route,current=trusted_current_binding)。accepted表示整份逻辑投递已进入队列；duplicate表示本绑定内该sequence已接收，不重复排队；stale表示别的成员/连接route，不影响当前队列；resync_required表示本收件箱永久失效。只接受从1开始连续sequence；缺号、非法数据、超容量会清待发队列并记录failure。它不是发送ACK或跨进程可靠outbox。
4. 在同一连接执行者调用pop(current=trusted_current_binding)，得到下一份冻结RoleDelivery；取出时再次核当前绑定。每份含一批或多批原消息，pending按packet数量及sum(len(body)+10)记账，pop释放记账。字节数是逻辑预算，不是常驻内存或压缩后线包长度。任何绑定变化都会永久清旧箱，迟到调用不能恢复它。
5. 下游ConnectionOwner发送队列必须携带同一binding，并在真正RC4/MPPC编码之前再次检查。现有ConnectionOwner.offer/_send只核epoch，不核玩家成员绑定，**不可直接丢掉本信封后声称接线完成**。pop不是网络确认；若下游一批中途offer失败，调用inbox.close并关闭/重建该连接，不能只丢剩余入屏继续发移动。下游可能已发送前缀，所以这里的整批原子性仅指本收件箱准入，不是网络原子广播。
6. 同epoch往返同图、换连接、换实例或Owner重建时，旧箱关闭，新可信join安装新绑定/sequence起点。不能从第一条未知投递推断起点，也不能简单重用旧presence去复建中途连接快照；断开重建仍由角色/地图归属协议负责。已经writer.write的字节依赖既有场景发送屏障和严格顺序，本Module不能撤回。

## 验证和完成条件

verify_world_role_delivery对真实RoleScene输出，按基础接收→代次/成员隔离→连续序号/去重→满载→关闭→loading门控逐条先红后绿。九组通过：接收和消费两次核绑定、同epoch新成员与旧socket信封拒绝、重复不重发、缺号不复活、packet/byte边界、2批入屏整份拒绝、另一收件箱继续、关闭不可复活、畸形/可变数据拒绝和无热路径文件I/O。

verify_world_role_delivery_native将实际RoleScene→route→inbox→pop的入屏/移动/移除3条输出按sequence1/2/3交原完整decoder，角色列表1/NPC0、roleID2和目标(124,100)全部正确。此为原codec核验，没有运行GPU或实际双客户端。

codebase-design将顺序/代次/队列失败局部化在目标所有者Module；tdd的公共Seam验证目标逻辑投递，不访问私有队列或伪造Session。完成共享接线仍需连接send前绑定围栏、生产容量策略、两连接/换图/慢队列全栈和真客户端同屏。未修改共享入口、发布副本、在线服务或真实角色，未把本地收件箱称多人已上线。
