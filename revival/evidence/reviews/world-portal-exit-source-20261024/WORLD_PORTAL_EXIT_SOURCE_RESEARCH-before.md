# Nine blocked portal exits: original-source follow-up

2026-10-24, independent research branch. This report extends the resource handoff and Scene landing research without changing production behavior or earlier evidence.

Methods: Matt Pocock research follows claims to original PFS entries/native instructions; diagnosing-bugs keeps the exact blocked landing and changes only controlled mouse input. The delegated researcher is the background research worker. No GUI, service, formal database or combat is started.

Resource audit: [script](../research_world_portal_exit_sources.py), [structured result](world-portal-exit-source-audit.json). Native longitudinal probe: [script](../verify_world_blocked_exit_click_native.py), [structured result](world-blocked-exit-click-native.json). A controlled clear mouse destination is an input fixture only, never a proposed replacement landing.

## Finding

No replacement server landing coordinate was established. The original held-click consumer adds a useful distinction: two of these unchanged blocked starts can produce an original MOVE whose source remains the blocked landing; seven reject before path entry. Thus neither “the Scene setter corrects all blocked starts” nor “the first MOVE always carries a corrected clear source” can justify accepting these nine portal landings.

This is an offline research result, not a reproduced GUI black-screen fix or an original-server capture. The current World exclusion remains a policy question for root/planner; this batch changes no production behavior.

## Fresh resource facts

The audit opens original `artres/config.pfs` and `artres/map.pfs`, validates each read through `PfsArchive` CRC/length checks, and records original entry SHA-256. It enumerates 304 configured map rows, 140 available goto tables, all 9677 paths rows, 575 config XML entries, and each of the nine source NPC tables. All nine interiors have zero incoming goto rows across the complete configured goto scan. This proves no reverse goto entry supplies another coordinate; it does **not** prove those interiors are obsolete or inaccessible through NPC/task/server flows.

| Source → target | Original goto dest x,y | Existing ×16 hypothesis | Exact paths xPos,yPos | Native held-click outcome |
|---|---|---|---|---|
| 1301 → 1100 | 39,75 | 624,1200 | 38,65 | MOVE, CHECK, STOP |
| 1304 → 1103 | 55,26 | 880,416 | 9,77 | No MOVE |
| 1305 → 1104 | 115,27 | 1840,432 | 3,50 | MOVE, CHECK, STOP |
| 1306 → 1105 | 74,53 | 1184,848 | 3,61 | No MOVE |
| 1308 → 1107 | 108,38 | 1728,608 | 15,83 | No MOVE |
| 1309 → 1108 | 40,66 | 640,1056 | 60,57 | No MOVE |
| 1393 → 1007 | 145,214 | 2320,3424 | 19,80 | No MOVE |
| 1394 → 1007 | 145,214 | 2320,3424 | 21,56 | No MOVE |
| 1395 → 1007 | 145,214 | 2320,3424 | 19,62 | No MOVE |

Every exact paths coordinate coincides with the center of the **source** map’s 5×5 goto patch. These rows therefore supply no independent target landing. The script retains their exact original field names `sourceMapID`, `destMapID`, `xPos`, `yPos` and every original goto row rather than synthesizing a route.

The six school interiors remain present in original `CShimenXunlu.map` lists. `SchoolInfo` explicitly pairs school 11→1100/1301, 13→1103/1304, 14→1108/1309, 15→1105/1306, 18→1107/1308 and 19→1104/1305. An additional row id 111 pairs 1110/1305; this anomaly is retained, not interpreted as an alias. `CMainMissionInfo` has seven `ActiveInfoMapID` references to these interiors (316202, 316402, 316502, 316602, 316902, 317002, 317502). Their `RewardMapID`, `RewardMapXPos`, `RewardMapYPos` are all zero. These rows establish continuing data references, not server exit values.

The map/scene attribute scan also finds 11 `CNpcConfig` records in 1393/1394/1395. Their positions are NPC placement fields in those **source** interiors. Each original source `npc.xml` is preserved in the result; for example 1301 NPC 10014 at raw 778,631 and 1304 NPC 10195 at raw 754,731 agree with the task NPC IDs. No scanned record supplies a new target landing. The scan matches attribute names containing `map`/`scene` with an exact nine-map value; it does not prove absence in opaque scripts, prose, indirect IDs, or unexamined native consumers.

Other earlier inspected lookalikes (`CCreateRoleSchoolPos` relative UI positions, `CFlyFlagConfig` item/level rows, returnee `CReturnTrip` reward rows) are not promoted to spawn authority. `CMapConfig.xjPos/yjPos/playerPosX/Y` consumer semantics were not established by this batch; they remain unverified and are not used as alternative coordinates.

## Original instruction longitudinal test

The prior [Scene landing research](WORLD_SCENE_LANDING_RESEARCH.md) already ran the real Scene/Main/actor landing setters and found no maze correction. This batch does not repeat that setter experiment or the already proven blocked-start grid kernel. It initializes the same exact logical point and projected actor value in a controlled object graph, then runs original held-input `0x1214bd0` → gate `0x1211db0` → mouse `0x81ae00` → screen/world conversion `0x11c5b40` → consumer `0x12143b0`. Original source queries are captured at `0x11c5c00`, with return `0x121464c` for the current point and `0x12146bc` for the original source-neighbor loop.

Original bytes `0x1214654..0x12146f4` test eight direction offsets at logical pixel radii 1 through 8. The loop can assign an adjusted **local** start at `0x12146d8/0x12146dc`; it does not move the actor there. If all 64 samples remain blocked, the original consumer reaches `0x1214701..0x1214712` and returns before path entry. The seven rejected cases each record 66 queries: clear clicked goal, blocked current, 64 blocked candidate source samples. Their actor/getter stays unchanged and no original MOVE/CHECK/STOP is built. No generic path-kernel success is substituted for this higher-level consumer rejection.

For 1301→1100, controlled click 608,1200 yields adjusted local start 623,1200, while actual actor remains projected 936,1200 and original current remains 624,1200 before update. The actual original sender-built MOVE at return `0x1214aa9` still starts **624,1200**, ending 608,1200, scene q64 1100. After one original actor budget unit, getter becomes 623,1200. Original timed update builds CHECK at return `0x12172b1`, with history [624,1200] and current 623,1200; bounded actor updates later build STOP at return `0x1217fce`, current 608,1200.

For 1305→1104, controlled click 1824,416 yields adjusted local start 1839,431 while actor remains projected 2760,432 and getter 1840,432 before update. Actual MOVE starts **1840,432**, ending 1824,416, scene q64 1104. First original actor update produces getter 1839,431; CHECK history contains 1840,432; final original STOP reports 1824,416. The live native objects are marshalled by original MOVE `0xe50840`, CHECK `0xe9cd00`, STOP `0xe9d6d0` before native collection destruction. Full bodies and source/goal queries are in the structured result.

The two successes do not authorize relaxing server source validation. They show that a blanket “client sends repaired source” premise is false. Root must judge the exact committed-source/current-mask and segment-validation contract separately; seven other cases still fail in the original higher-level input consumer.

## Adapter and validity bounds

Host fixtures supply original map bytes, unchanged landing, scene q64 context, object graph, mouse coordinates, camera origin and held-input latch. Controlled goals are clear grid-cell corners chosen deterministically inside a bounded test area; this is an input generator, **not** a server landing selection algorithm. Clock/budget inputs and original speed setter `0x6529b0` multiplier 1.0 make the experiment deterministic, with no real-time/server-speed claim. Allocator/STL, device, renderer and send-sink seams are inherited from the named native harnesses; no sockets or GPU run. Region containers are fixture empty, not captured original server region state. The path, actor updates, reports, and packet marshalling execute original mapped instructions.

The initial experiment reused the small-map harness address `0x5031000` for maze storage. Map 1007 has 252416 cells and overlapped mouse/session fixtures at `0x5040000`, causing a false early gate result for three guild cases. That intermediate result is explicitly preserved as [invalid fixture overlap](world-blocked-exit-click-native-invalid-fixture-overlap.json), **not accepted evidence**. The independent subclass relocates unchanged maze bytes to `0x5080000` and asserts size <0x80000, below stack `0x5100000`. All nine final cases read the mouse once; the corrected guild cases now reach the real source-neighbor rejection. Original maze bytes, landing coordinates and mask stay unchanged.

## Reproduction, hashes, and remaining questions

Run from project root, using the bundled Python with `-B`:

```
python -B revival/research_world_portal_exit_sources.py
python -B revival/verify_world_blocked_exit_click_native.py
```

Both commands completed successfully. Final native assertions require the exact two success cases, unchanged pre-update actor/getter in every case, original source prefix equality, actual later actor change and MOVE→CHECK→STOP in two cases, and 66 original queries/no movement in seven. This is a regression-capable research loop for these consumer behaviors; it does not certify the original user's GUI symptom or any production fix.

Original mapped image SHA-256: `2b49e95d27cbbec0d83a049b5495da4365b205d9a913582b1e6688df67468791`.

Key original entry SHA-256:

- CMapConfig: `374d400f933a74e83d402c8da948fef47823e7f92344ccb660414edfb87a1814`.
- paths.xml: `5784fd5b9f3ccc65cb0974fee6cceb0185b4525286275363c2d639e55aaa9d10`.
- CShimenXunlu: `4cdc64d757f0c43498e55fb4b08c46b41a243facebe46b5e3f7899a49b54dca7`.
- SchoolInfo: `3ed66a6f40f615b6d89372a1775246a33c644b9d612df7794532edb656332a2d`.
- CMainMissionInfo: `ed4bad3a037498115e3d9cac308daddd39c3d60b70c1372ad22044085f06c706`.
- CNpcConfig: `b4fc5d440380fb535a36b8e5315c5a1bf10a99f550f5bfde55bd156fca864f85`.

Every read entry and native dependency has its own hash in the structured outputs. Original-server ScenePos packets, indirect NPC service return flows, full App/GPU integration, real instance/region ownership and actual server speed remain unverified. No official web guide was used as a numeric protocol source.

Questions for root/planner: what authority defines the seven unrecoverable exact server return points; whether a narrowly scoped blocked-start recovery contract is desired for the two original-consumer successes; and whether the original dynamic guild interiors use server-return locations absent from client goto markers. Those decisions require further original-server evidence or explicitly documented design. They cannot be inferred from source paths centers, closest clear cells, mask switching or a fictional instance.
