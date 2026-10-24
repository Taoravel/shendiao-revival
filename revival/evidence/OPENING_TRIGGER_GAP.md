# 原主线开场触发接线缺口

2026-10-23。主策划已明确100192来自100112，不能给全部新角色直接发测试任务代替自然主线。客户端root100101为type50、无incoming、ScenarioInfoAnimationID=11001，后继100184–100187等；角色分支与梦境1501仍须保留原关联。

本批research后台已在当前映像取得以下直接证据：

- SStartPlayCG=0xc0017，BE i32 movieID且必须>0；Process0x12c43b0取+8，沿CSceneMovieManager 0x12c4140→0x12c3f10→0x12c3be0加载`/config/movie/<id>.txt`。
- CEndPlayCG=0xc0018，同样BE i32 movieID；0x12c0970以当前movieID构造，0x12c0a24–0x12c0a3e发送。
- 零经验新手分支只已证实安装遮罩，没有找到其自动offer100101或直接启动11001的证据。不能把经验为零等同于服务器已授权开场任务。

现有TaskDomain可消费可信scenario_finished证据，但还缺原开场激活条件、CG中地图/位置权威同步、章节实例/播放凭据与后继选择队列。当前没有把任意CEndPlayCG直接认作可信任务完成，也不自动改用户出生地图或已存故事状态。待主策划裁定未知服务器触发语义并取得电影脚本迁移范围后，再复用既有任务事务、交接和奖励Interface接线；不另写一套影子任务系统。

本批不部署、不启动游戏、不操作用户角色；没有新增测试发奖。当前黑屏/不动优先，静态遮罩证据和反证见BLACK_MOVIE_MASK.md、BLACK_ENTRY_MESSAGE_AUDIT.md。
