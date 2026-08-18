# CHANGELOG

## [0.1.52] - 2026-08-17

### 新增
- **兼容无开放 API 的旧系统（退步兼容）**：开放 API 要求 fnOS ≥ 1.2.0401，旧系统（统一网关起，1.1.3100）不注入 `TRIM_API_TOKEN`、无网关 socket。现在应用按**运行时能力探测**（`trimapi.is_openapi_available()`：token 主信号 + socket 确认，现读不缓存）自动区分两模式，同一 fpk 通吃：
  - **严格模式**（开放 API 可用，行为不变）：任务创建前校验目录在授权范围内，trimapi 失败即暴露、不回退 `os.access`
  - **legacy 模式**（拿不到 apitoken）：`_check_auth_scope` 跳过授权范围校验，靠「系统设置 → 应用 → 文件工具箱 → 授权目录」手动授权 + `os.access`（OS 层 ACL 门禁）；`/api/auth/folders` 返回 `{paths:[], legacy:true}`、`/api/path/convert` 返回恒等映射（前端显示原始路径）、DELETE auth folders 引导去系统设置
  - `os_min_version` 从 `1.2.0401` 降回 `1.1.3100`（统一网关最低要求）。`manifest`、`trimapi.py`、`router.py`；前端 `trimSdk.js`（导出 `sdkAvailable`）、`Settings.vue`（legacy 下隐藏授权目录列表、改引导系统设置）、`wizard/install`、`wizard/config`（双模式文案）
  - +单测 `tests/test_openapicap.py`（探测三分支）、`tests/test_validate_dir.py`（legacy 跳过 scope + os.access 通过/拒绝 + 非法路径保留）、`tests/test_router_auth.py`（legacy 三路由降级）；`tests/conftest.py` 增 `openapi_mode`/`legacy_mode` fixture（既有严格模式用例沿用 `openapi_mode`）
  - 设计文档：`BACKWARD_COMPAT_SDD.md`（新增）；`OPENAPI_SDD.md` 头部附录声明覆盖 T2-a（os_min_version 上调决策）


### 改进
- **历史任务结果迁到应用私有数据目录**：compare/duplicate 的历史任务结果从 data-share 共享目录（appshare，用户文件管理器可见）迁到应用私有数据目录 `$TRIM_PKGVAR/results/`（@appdata）——用户不再在共享目录看到结果文件，需要时经「导出/下载」取出。**旧 appshare 结果不迁移**，升级后旧历史不显示（重新扫描即可）。`logstore.py`
- **卸载「保留数据」语义调整**：卸载向导改为「是否保留应用数据（历史任务结果与导出文件）」——选「保留」时保留 @appdata（历史任务结果 + 文件索引）+ @appshare（导出文件），删除其余（@apphome/@appconf/@appmeta/@appcenter）；选「删除所有数据」时全部清理。`cmd/uninstall_callback`、`wizard/uninstall`
- **文件索引搜索结果「复制路径」改为「在文件管理器中打开」**：结果行原来只能复制完整路径到剪贴板，现与单目录查重结果一致——通过 fnOS 前端 SDK `openFileManager` 直接打开系统文件管理器并定位到该文件所在目录（传父目录，打开即可见该文件）；宿主外（SDK 不可用/独立浏览器）静默降级。`FileIndex.vue`（`useTrimSdk` + `openInFileManager`，删 `copyPath`）
- **「系统不支持选目录授权」提示改为可关闭 Toast**：legacy 系统下原在每个「选择目录」输入框下方挂整段说明（Compare 目录A/B 重复两遍、常驻占中间栏）。改为全局右上角 toast——**打开工具弹一次（同会话 sessionStorage 记，不重复）**，点置灰的「选择目录」也再弹（每次），可点 × 关闭、约 6s 自动消失；选择器打开失败（pickError）也走同一 toast。新增 `useToast.js` + `ToastHost.vue`（挂 `App.vue`），`DirPicker.vue` 删内联提示、按钮改「置灰样式 + 点击拦截」（不用原生 `disabled`，否则点不到弹不了）；设置页「授权目录」区域引导文案保留。
- **应用介绍补「文件索引」**：manifest `desc` 与安装向导文案此前漏了 0.1.46 引入的文件索引工具，补上「📇 文件索引 — 为目录建立持久化索引，按文件名、扩展名、大小、修改时间快速搜索」；README 环境要求系统版本下限同步 `os_min_version`（`1.2.0401`→`1.1.3100`）并补旧系统降级说明

### 修复
- **legacy 下 SDK 相关按钮置灰 + 引导**：旧系统（无宿主 bridge）下，「选择目录」按钮此前直接隐藏、查重结果与文件索引的「在文件管理器中打开」按钮点了静默无反应——改为按钮**置灰禁用**并提示原因/替代路径：「选择目录」旁提示「系统不支持应用内选目录授权，请在系统设置 → 应用 → 文件工具箱 → 授权目录 手动添加」；「在文件管理器中打开」悬停提示「系统不支持打开文件管理器」。用 `sdkResolved` 区分「SDK 初始化中」与「确认 legacy」，避免开放 API 系统初始化瞬间闪现提示。`DirPicker.vue`、`DuplicateResult.vue`、`FileIndex.vue`
- **前端能力判定改由后端权威信号驱动**：修复旧系统（如 fnOS 1.2.0203）按钮「亮起但不可点」——此前用 `sdk.isWeb && !sdk.isStandaloneWeb` 判宿主可用，但旧系统在 web 宿主 iframe 里 `isWeb=true` 而开放 API bridge 根本没注入，误判为可用（按钮亮、点击静默失败）。现改为 `detectSdkAvailable()` = **后端 `/api/capability` 信号（token+socket，权威）+ 宿主 bridge 实探（`getPlatformConfig` 成功）**，响应式 `useSdkAvailable()` 供按钮 `:disabled` 绑定；后端新增 `GET /api/capability → {openapi}`。`trimSdk.js`、`router.py`。+单测 `tests/test_router_auth.py`（capability 严格/legacy 两态）
- **卸载向导「删除所有数据」红色加粗警示**：卸载时「删除所有数据」选项文字改为红色加粗（`<b style="color:#ef4444">`），并新增红色加粗 tips 警告「⚠️ 选择「删除所有数据」将永久删除历史任务结果与导出文件，此操作不可恢复！」——helpText 的 HTML 渲染是已验证路径，保证警示必显示（即使 radio label 不支持 HTML 也有 tips 兜底）。`wizard/uninstall`
- **「选择目录」按钮「不置灰但点不动」修复**：0.1.52 改动后按钮仍不置灰、点击却无反应。两个根因叠加：① `DirPicker.vue` 漏导 `sdkReady`（0.1.51 还打包着，0.1.52 变裸全局引用）→ `pickDir` 里 `await sdkReady()` 抛 `ReferenceError` 被静默 catch → 点击永远无反应；② 能力探测 bridge 实探用 `getPlatformConfig()`，但 extension-host 连接下它本地解析即成功（假阳性）而 `pickSharedFile`/`openFileManager` 实际抛 `NotSupportedInExtensionHost` → 探测过、点不动。修复：补 `sdkReady` 导入；探测改为调 `setTitle`（与文件类 SDK 方法同可用性，native-OS 宿主可用、extension-host 抛错）正确区分；`pickDir` 失败不再静默、显示替代路径提示兜底。`trimSdk.js`、`DirPicker.vue`
- **卸载向导 radio 选项 HTML 原文显示修复**：「删除所有数据」radio 选项 label 里的 `<b style="color:#ef4444">` 标签在卸载向导原文显示（radio 选项 label 不支持 HTML）——改为纯文本，红色加粗警示保留在 tips `helpText`（HTML 渲染已验证路径）。`wizard/uninstall`
- **任务完成瞬间丢勾选修复**：查重结果里勾选文件时任务恰好完成（live→history 过渡），`selectedResult` 在历史结果异步载入窗口短暂置空 → DuplicateResult 卸载重挂 → 已勾选清零、移入暂存区按钮禁用——改为历史结果载入窗口桥接 taskMap 终态结果，保持组件挂载、勾选不丢。`App.vue`（`selectedResult`）。+E2E 回归（21 例全绿，含新增的查重三模式/比较完整/终止任务/暂存区永久删除/索引删除重建）

## [0.1.50] - 2026-08-17

### 新增
- **文件索引「读取错误详情」可展开**：索引卡片「N 个读取错误（权限/损坏）」角标改为可点击，展开显示**具体失败目录/文件的完整错误**（含路径与原因，等宽小字、超多可滚动），提示「修复权限后重建索引可收录」——此前只显示数字、无法得知哪些路径被跳过。`FileIndex.vue`（`expandedErr` 状态 + 卡片改两段式布局）。+E2E 1 例（fixture 建含 `chmod 000` 子目录的目录：可读文件照常入库 + 错误角标展开可见 `locked` 路径，`scripts/test-e2e.sh` 加 fixture）

### 改进
- **检查更新失败双落记录**：GitHub 不可达/检查失败不再只显示红字——前端 `checkForUpdates` 把 error 写入**浏览器 localStorage 崩溃日志**（设置页「应用崩溃日志」可见，持久化上限 200 条）；后端 `_handle_update_check` 同时记 app.log。`Settings.vue`、`router.py`。+单测 `tests/test_router_update_log.py`（失败记 ERROR / 成功不记）
- **后端关键失败记 app.log（服务端持久化）**：三类此前静默/仅 UI 可见的失败接入 `TRIM_PKGVAR/app.log`（经 logging → cmd/main stderr 重定向）：
  - **trimapi 开放 API 失败**：`trimapi.call()` 源头包装日志，任何 `TrimApiError`（网关 socket 连不上 / token / scope / 非 JSON）先记 app.log 再照常抛出——覆盖查/删授权目录、路径转换、授权范围校验（建任务必经）全部调用方。`trimapi.py`（拆 `call` 日志包装 + `_call_impl`）
  - **任务运行异常 + 落盘失败**：`runner._finish` 任务崩溃（err 传入）记 app.log；`logstore.save_run` 落盘失败原 `except: pass` 静默吞改记 app.log（磁盘满/权限时「任务结束即消失」可查根因）。`runner.py`
  - **索引构建失败**：daemon 构建异常记 app.log。`indexbuild.py`
  - +单测 `tests/test_trimapi.py`（TrimApiError 记日志且照常抛）、`tests/test_runner_finish.py`（任务失败/落盘失败记日志）

## [0.1.49] - 2026-08-17

### 新增
- **建任务「暂存区残留闸门」处理进度**：目录有未清理暂存区时，点「恢复全部并扫描」弹**流式逐文件恢复进度条**（复用 `/api/trash/restore-stream`：先 `rebuild` 兜底补录清单、再全量逐文件恢复、恢复完自动开始扫描）；「永久删除并扫描」是 rmtree 整区一次删（快），弹 spinner。此前这两步是单次阻塞 POST，期间界面无任何进度反馈。`useTaskCreate.js`（`restoreGate`/`purgeGate` 状态 + `resolveTrashGate` 改流式恢复 + 完成后仍带 `trashAction='restore'` 提交，后端 `restore_all` 兜底失败条目并保证任务照常开始）、`App.vue`（两个处理中弹窗）

### 改进
- **移入/恢复进行中禁止删除任务**（防丢文件）：删任务收尾会 `purge_trash` 清掉 `.ft-trash`，若在移入/恢复期间执行，会把正在写入/读取的暂存区整个清掉（已移入文件丢失）。前端 `TaskList` 删除按钮在 `activeOp` 命中该目录（`kind` 为 move/restore 且 `scanDir` 相同）时禁用并灰显 + `handleDelete` 防御 guard；后端 `_handle_delete_log` 加 `_ops_find` 防线（该目录有运行中 op → 409「正在移入/恢复中，请稍后再删除任务」），兜底前端被绕过的场景。`TaskList.vue`、`App.vue`、`router.py`。+单测 `tests/test_router_delete_opguard.py`（2 例：同目录有 op 拒删且 run 记录保留 / op 在别的目录不影响本目录删除）
- **恢复全部进行中禁用单文件恢复**：单文件「恢复」按钮此前只在移入进行中（`moveRunning`）禁用，恢复全部进行中仍可点——会与恢复循环并发写 `trash.db`（撞锁 / 已恢复文件再点报「清单缺失」）。修复：按钮禁用条件 + `doRestore` guard 补 `restoringAll || restoreOp.running`（本会话 + 后台恢复进行中），与 0.1.47 移入处理对齐。`StagingDrawer.vue`

### 修复
- **日志面板「正在移入/正在恢复」进度要切换界面才显示**：根因 = `useOps` 是「发现型」连接，只在 `watch(trashScanDir)` / `watch(stagingDrawer)`（切换任务/视图、开抽屉）时 `getOpsStatus` 轮询一次、发现有运行中的 op 才连上；本会话实时移入/恢复流发起时不会立即填充 `activeOp`，一切换视图才显示。修复：实时流首帧 `start` 事件带 `opId`（`router.py` 早已下发 `{total, opId}`）→ 组件读到后 `signalLiveOp` 写入模块级信号 → App `useOps.connectById` 立即按 opId 连上该 op，进度即时进日志面板（本会话与关窗重开后台 op 共用同一 `activeOp`，两路径归一）。`useOps.js`（重构 `openEs` + 新增 `connectById` + `liveOpSignal`/`signalLiveOp`）、`App.vue`（watch 信号即连）、`DuplicateResult.vue`（移入）/`StagingDrawer.vue`（恢复全部）/`TaskList.vue`（删除前恢复）各自流读到 `start` 即信号

## [0.1.48] - 2026-08-17

### 新增
- **查重建任务「暂存区残留闸门」**：目录有未清理的暂存区（典型：卸载前未走「删除任务→清理暂存区」流程，卸载后 `.ft-trash/` 与 `trash.db` 随用户目录保留）时，walker 扫描会排除 `.ft-trash`，直接建任务会遗漏这些文件 → 结果不完整。现在建任务检测到残留即挂起创建，弹「恢复全部并扫描 / 永久删除并扫描」二选一：恢复 = `rebuild` 兜底补录清单（覆盖 DB 缺失场景）+ `restore_all` 移回原位再扫描；删除 = `purge_trash` 后再扫描。闸门只命中孤儿暂存区——`_dir_has_task` 已保证建新任务前该目录无存活任务记录，而正常删任务又强制先清暂存区，故「有暂存区无任务记录」只可能是卸载残留。`engine/trash.py`（`recoverable_count`：DB 有条目按 DB 数、DB 缺失按 `.ft-trash` 实际文件数）、`router.py`（`_handle_duplicate` 409 `{trashRecoveryRequired, trashCount}`，`trashAction` 仅允许 restore/purge）、`frontend/src/api.js`（`startDuplicate` 支持 `trashAction` + 识别 409）、`useTaskCreate.js`（`trashGate` + `resolveTrashGate`）、`App.vue`（ConfirmDialog 二选一挂载）。+单测 `tests/test_router_gate.py`（6 例：正常创建 / 无 action 挂起 / restore / purge / DB 缺失 restore / 非法 action）、`tests/test_trash.py`（+3 例 `recoverable_count`）、E2E 2 例（`/tmp/ft-test/gate` 孤儿暂存区 → 恢复后扫出重复组 / 删除后无重复）

### 改进
- **打包卫生：源码与本地测试物理分离**（fpk 载荷纯净化，root cause = fnpack 哑打包器无排除机制、凡 `app/` 内一律进包）。诊断发现 0.1.47 的 `app.tgz` 打进了 4 类本地/开发产物：`server/tests/`（19 个 pytest 文件）、`server/logs/`（本地运行残留）、`server/pytest.ini`、`server/www/demo.html`（「下拉方案对比」开发演示页）。
  - `tests/` + `pytest.ini` 移出 `app/` → `file-tools/` 顶层（与 `app/` 平级，天然不入包）；`tests/conftest.py` sys.path 同步定位 `app/server`（dirname 两次后拼 `app/server`）。
  - 3 处本地裸跑写回退重定向到 `file-tools/.localdata/`（`app/` 之外，不入包）：`logstore.py`（logs）、`indexstore.py`（index）、`router.py`（DEBUG_LOCAL 导出 export）。部署走 `TRIM_DATA_SHARE_PATHS`/`TRIM_APPDEST`，行为不变。
  - `server.py` mock 假网关路径修正：`SCRIPT_DIR/tests/mock_gateway.py` → `dirname(dirname(SCRIPT_DIR))/tests/mock_gateway.py`（`--port` 本地 debug 模式 / e2e 必需）。
  - 移除 `frontend/public/demo.html`（无应用引用，构建后 `www/` 不再生成）；删除 `app/server/logs/` 旧残留。
  - `Makefile` build 追加 `rm -rf app/server/logs app/server/index app/server/export` 保险；`.gitignore` 加 `.localdata/`。
  - 验证：pytest 新命令 `cd file-tools && ../.venv/bin/python -m pytest -q` 全绿、`npm run build` 后 `www/` 无 demo.html、`make test-e2e` 13 passed（mock 假网关拉起）、解包确认 `app.tgz` 无 tests/logs/pytest.ini/demo.html/`__pycache__`。

## [0.1.47] - 2026-08-17

### 改进
- **移入/恢复进度条搬进日志面板**：从右侧面板顶部挪到日志面板内容区顶部（「正在处理」上方），进度展示与任务处理统一位置；`activeOp` 透传 `LogPanel`（本会话/关窗重开后台 op 共用）。`App.vue`（删顶部横幅 + 传参）、`LogPanel.vue`（`activeOp` prop + 进度块）
- **移入/恢复进度标签统一进行时文案**：「移入暂存区/恢复全部」→「正在移入/正在恢复」，与「正在处理/正在扫描/正在比对」语感对齐。`LogPanel.vue`
- **BLAKE3 降级输出错误日志**：`blake3` 模块导入失败自动降级 SHA-256 时，向 `app.log`（`${TRIM_PKGVAR}/app.log`，经 `cmd/main` stderr 重定向）打一条 ERROR——含导入失败原因 + 修复提示（检查应用自带 `venv` 是否含 blake3 依赖）。此前降级完全静默，仅任务起始行「SHA-256（兜底）」与 `/api/info` 可查。`engine/hashing.py`

### 修复
- **移入暂存区进行中，暂存区抽屉单文件「恢复」按钮未禁用**：「重建暂存区/恢复全部」在 `moveRunning`（本会话 emit / 关窗重开 `activeOp.kind==='move'` 兜底）时已禁用，但列表内每个文件的「恢复」按钮漏了该判断——移入期间仍可点击单文件恢复，与进行中的写入竞态。修复：按钮 `:disabled` 补齐 `moveRunning` + `doRestore()` 加防御 guard（对齐 `doRestoreAll()` 风格）。`StagingDrawer.vue`

## [0.1.46] - 2026-08-17

### 新增
- **文件索引工具（v1）**：独立「文件索引」页——选已授权目录建一次持久化索引（只读递归扫描，记录文件名/相对路径/大小/mtime/扩展名），之后搜索纯查本地 SQLite（`$TRIM_PKGVAR/index/index.db`）毫秒级返回：按文件名子串（大小写不敏感、支持中文）、扩展名/大小范围过滤、按名称/大小/修改时间排序、分页；附带目录快照（文件数/总大小/构建时间/读取错误数）；一目录一索引，可重建（原子替换）/删除（含取消进行中构建）；构建独立 daemon 线程，可显示进度、可取消，关应用窗后台续跑、重开可重连进度（EventSource snapshot 先行 + exit 收尾）。**隔离旁路**：索引构建不 import `tasks`/`runner`/`logstore`，不进 `/api/tasks`、`/api/logs`、`_dir_has_task` 互斥，只写自有数据目录、不写被扫目录，compare/duplicate 照旧实时遍历文件系统、**永不读索引**。文件：`engine/index.py`、`indexstore.py`、`indexbuild.py`（新）、`router.py`（+7 handler）、`frontend/src/pages/FileIndex.vue`、`frontend/src/components/IconIndex.vue`（新）、`api.js`（+7 函数）、`App.vue`（导航项 + 整区独立页）。+测试 `test_index.py`、`test_router_index.py`
- **移入暂存区进行中退出弹窗**：移入时关应用窗弹「移入暂存区将在后台继续完成，可随时返回查看进度。确定离开吗？」（对齐「恢复全部」同款 `setExitPageTips`）。`ResultView.vue`（透出 moving 状态 emit）、`App.vue`（moveRunning 并入退出提示三路 watch）
- **后台移入/恢复数量实时刷新（SSE 事件驱动，取代 2s 轮询）**：`useOps` 事件流透出 `moved {path,trashRel,size}` / `restored {trashRel}` / `snapshot`，App 收到事件逐文件增删 `trashEntries` → 结果面板「暂存区 N」+ 行内「已移入」标记关窗重开后**逐文件实时变**（不再 2 秒一跳）；`snapshot` 做基线、`exit` 收权威纠偏，EventSource 自动重连靠 snapshot 重基线补丢事件。`useOps.js`（回调透出）、`App.vue`（事件驱动 + 删轮询 + restore 状态重构）、`StagingDrawer.vue`

### 改进
- **「每组保留一个」→「每组至少保留一个」**：查重选择规则区文案统一（UI 复选框 + 相关注释），语义更准确——保证每组至少保留 1 份，多于 1 份按规则勾选移入。`DuplicateResult.vue`
- **移入暂存区进行中禁用暂存区抽屉「重建暂存区/恢复全部」**：含关窗重开后后台移入（activeOp `kind==='move'` 兜底），避免与进行中的移入竞态；移入结束自动恢复可点。`App.vue`（`moveRunning` 共用 computed）、`StagingDrawer.vue`
- **移除全部 2s 轮询**：后台恢复 `syncRestore` 与后台移入轮询统一改事件驱动（见新增）；抽屉列表后台恢复自动刷新加 300ms 防抖（事件驱动下 done 逐文件变，避免每文件一次全量拉取）。`App.vue`、`StagingDrawer.vue`

### 修复
- **仅剩 1 份可移入文件时选择规则仍会勾选它（整组被清空）**：一组 2 份文件、其中 1 份已移入暂存区或锁定后，点「选择规则」会把剩下那份也勾选上 → 整组清空，违背「每组至少保留一个」。根因 `reapplyRule()` 兜底条件 `movable.length > 1` 在可移入候选只剩 1 个时放行。修复：条件改 `movable.length >= 1`——规则不得选中组内全部可移入文件，仅剩 1 份时该组不做勾选（整组保留），与手动勾选已有保底一致。+回归 e2e「每组至少保留一个：锁定一份后点规则不勾选最后一份」（反证旧逻辑失败）。`DuplicateResult.vue`、`playwright-test/e2e.spec.js`
- **后台移入暂存区数量不更新（与恢复全部不对称）**：恢复全部有 2s 轮询刷数量、移入没有，关窗重开后移入结束前「暂存区 N」不动。根治见新增（事件驱动逐文件实时，顺带恢复全部也去掉轮询）。`useOps.js`、`App.vue`

## [0.1.45] - 2026-08-17

### 新增
- **移入/恢复关窗后继续后台跑 + 重开可见逐文件进度（统一后台操作机制）**：移入暂存区与恢复全部共用一套「后台操作」注册表（`_ops`：kind/scan_dir/status/total/done/failed/current/listeners）。移入也保证客户端断开（关应用窗）后由 daemon 请求线程继续处理到跑完；新增 `GET /api/ops/status?scanDir=`（发现该目录进行中的操作，返回 `{running, opId, kind, total, done, failed, current}`）和 `GET /api/ops/events?opId=`（重连流式：**先发最新快照、再流式后续逐文件事件，不回放历史**，断线自动重连以快照为权威重置计数）。前端新增 `useOps` 监控：选中对应查重任务时发现进行中操作并重连流式，右侧顶部显示「移入/恢复进行中」横幅——百分比条 + 当前文件 + done/total（与运行中任务进度条同款），操作结束自动刷新暂存区。`router.py`、`api.js`、`useOps.js`（新）、`App.vue`。+3 单测（move 注册清理 / ops-status 发现 / ops-events 快照先行流式）
- **恢复全部进行中弹离开提示**：点「恢复全部」确认后立即置恢复进行中（不等 2s 轮询，关窗不遗漏弹窗），关闭应用弹「恢复全部将在后台继续完成，确定离开吗？」（与任务运行中同款 `setExitPageTips`）。`App.vue`、`StagingDrawer.vue`

### 改进
- **查重分布条 UI 微调**：图例（保留/已选中/暂存区）字号 `text-sm`→`text-xs`；「选择规则 / 每组保留一个 / 文件数 / 容量」标签文字色统一为右上角「暂存区」按钮同款；「容量」中间插全角空格与「文件数」等宽对齐。`DuplicateResult.vue`
- **日志面板默认高度 200→96px**（收起后展开记忆值同步）。`LogPanel.vue`

## [0.1.44] - 2026-08-14

### 修复
- **查重结束后任务短暂消失又出现（0.1.43 回归）**：SSE `exit` 到达 → 任务状态变终态，`activeTaskArray` 立即把任务从运行列表剔除，而历史列表要等 `refreshRuns()` 异步拉 `/api/logs` 返回后才出现，中间一段窗口任务两边都不在 → 一闪而过；且后端 `_finish` 先发 `exit` 事件再落盘，前端抢在落盘前拉日志会查不到记录（任务消失后不回来，需手动刷新）。修复：① 后端 `_finish` 先 `save_run` 落盘、再发 `exit`，保证前端收到 exit 时历史记录必已就绪；② 前端任务进入终态时打 `pendingHistory` 桥接标记，`activeTaskArray` 保留这类任务显示——桥接卡片隐藏「终止」按钮与进度条、改显示结果摘要+参数行（与历史卡片一致），`refreshRuns` 完成后清标记 → 任务从运行卡片无缝切到历史卡片，全程可见不闪没。`runner.py`、`useSSE.js`、`App.vue`、`TaskList.vue`。+1 单测（`_finish` 落盘先于 exit 事件）

### 改进
- **查重分布条新增「文件数」指标条**：原只有「容量」分段条（按字节占比填充），小文件多时比例严重失真（几十个小文件占不到几个百分点）。新增「文件数」分段条（按文件个数占比填充），与「容量」条上下并排、共享图例——容量反映「占磁盘多少」、文件数反映「多少个文件」，两个视角可对照。`DuplicateResult.vue`

## [0.1.43] - 2026-08-14

### 修复
- **扫描期 `/api/path/convert` 反复 POST 洪流（网关 502 / 大量瞬时 POST）**：`useSemanticPath.convertPaths` 只缓存「成功返回 semanticPath」的路径；对无语义映射的路径（如 ZFS 池路径 `/vol2/@team/ZFS-02`，后端返回 `result: []`）不缓存 → `TaskList` 的路径转换 watch 每次任务更新都触发（扫描时 taskMap 高频变化：进度/inflight/dupGroup 每帧都变），把未缓存路径**每秒数次重发 POST**，请求洪流拖垮网关 → 其他请求 502。修复：转换结果为空的路径**缓存为原值**（标记「已尝试」），后续 watch 不再重发；网络失败仍不缓存、保留下次重试。`useSemanticPath.js`
- **恢复全部中途关窗重开，前端状态不恢复（结果面板不自动刷新 / 「恢复全部」按钮亮起）**：恢复全部跑在 daemon 请求线程，客户端断开（关窗）不中断、恢复继续跑完，但后端无任何记录表明恢复正在进行——重开后前端没有 live 流可听，`restoringAll` 等局部状态已重置 → 结果面板「暂存区」不随恢复递减、「恢复全部」按钮重新亮起。新增后端内存注册表 `_restore_ops`（scanDir → `{total,done,failed}`）+ `GET /api/trash/restore-status` 查询接口；`restore-stream` 开始注册、逐文件更新、`finally` 注销（恢复完/断连跑完都清）。前端 `App.vue` 持有 `restoreOp` 并轮询状态 + `loadTrash()` → 结果面板「暂存区」随恢复实时递减（自动刷新）、恢复结束停轮询并最后一次刷新；`StagingDrawer.vue` 接 `restoreOp`——后台恢复进行中按钮禁用 + 显示进度（本会话本地流仍走 `restoringAll`）、抽屉列表随恢复推进实时刷新。`router.py`、`api.js`、`App.vue`、`StagingDrawer.vue`。+3 单测（恢复流跑完注销 / 引擎抛错 finally 兜底注销 / restore-status 无恢复与进行中两种返回）
- **E2E 定位器随分布条文案更新**：恢复全部测试断言 `已移入 0` → `暂存区 0`（配合下方分布条文案改动，否则 E2E 恢复全部用例失败）。`playwright-test/e2e.spec.js`

### 改进
- **打包剔除开发缓存目录**：`fnpack` 无排除项，`make build` 打包前自动清理 `__pycache__` / `.pytest_cache` / `.DS_Store`（跳过 node_modules）——包体积从 97 条目降到 55，不再携带测试缓存与 macOS 垃圾文件。`Makefile`
- **查重结果大结果分批渲染（卡爆）**：原一次性 v-for 渲染全部重复组（数千组 × 每组多文件）→ 默认只渲染前 100 组（`visibleGroups = groups.slice(0, renderCount)`），滚动区底部新增「已显示 X / N 组」+「加载更多 +100」+「加载全部结果（共 N 组）」按钮；「加载全部」用 rAF 每帧追加 500 组 + 进度 %，点完不卡死（已渲染组不重建）；**逻辑数据（分布条/勾选/移入）仍基于完整结果**，只限制 DOM 展示层。`DuplicateResult.vue`
- **流式推送不重置渲染上限**：渲染上限由 `watch(result)` 改 `watch(result.scanDir)`——只在换任务（scanDir 变化）时重置，流式 `dupGroup` 每帧 flush 不再把用户「加载更多/全部」的选择打回 100。配套 `useSSE.connect` 支持透传任务 `args`、App 流式合成 result 带 `scanDir`（创建/重连两处透传）。`useSSE.js`、`useTaskCreate.js`、`App.vue`、`DuplicateResult.vue`
- **查重分布条文案**：进度指标条「已移入」改「暂存区」、「待移入」改「已选中」（仅移入暂存区进行中显示「待移入」）。`DuplicateResult.vue`
- **交互 demo**：新增 `frontend-demo/dup-load-demo.html`——查重结果「加载更多/全部」交互 + 结果规模调节（100~20,000 组）+ 勾选文件 + **模拟流式推送**（演示任务进行中页脚计数实时涨、加载选择不被流式 flush 打回）+ 深色模式

## [0.1.42] - 2026-08-14

### 新增
- **移入暂存区改流式逐文件**：原「200 一批」批量请求 → 单次 POST 流式（SSE 逐文件推 `moved`/`skipped`/`exit`）。新增 `POST /api/duplicate/move`（`_handle_move_stream`，复用 `_delete_one`，客户端断开即停、已落盘的留暂存区）。前端「已移入」**逐文件 +1 实时涨**、进度条逐文件走、复核跳过项即时进失败列表（不再只在结尾汇总）。`router.py`、`api.js`（`moveDuplicatesStream`+`readSSE`）、`DuplicateResult.vue`（`liveMoved` 乐观叠加 + `trashPaths` 联合）
- **恢复暂存区改流式逐文件**：抽屉「恢复全部」与删任务「恢复全部」原 200 一批 → 单次 POST 流式。新增 `POST /api/trash/restore-stream`（`_handle_restore_stream`，复用 `trash.restore`）。`router.py`、`api.js`（`restoreTrashStream`）、`TaskList.vue`、`StagingDrawer.vue`

### 改进
- **运行中重复组结果节流渲染**：dupGroup 事件改非 reactive 缓冲 + 400ms 批量 flush 到 `partialGroups`，避免高并发哈希完成时每秒上百事件触发全列表重渲染打崩页面。`useSSE.js`（`DUP_FLUSH_MS`/`_flushDup`/`dupBuffers`）；`DuplicateResult.vue` group/file `:key` 改稳定 `g.key`/`f.path`，Vue 复用 DOM 只 patch 新增行
- **任务状态轮询兜底**：任务后端已完成但 SSE 的 `exit` 被网关缓冲/连接陈旧漏送时，前端会一直停在「运行中」、计时无限走。新增 10s 周期轮询 `/api/task-status`（普通 GET 不受 SSE 缓冲影响）取权威终态，漏 exit 时翻牌 + 关陈旧连接 + 触发回调，后续 refreshRuns/history 由 App watch 接管。`useSSE.js`（`STATUS_POLL_MS`/`_pollAll`）
- **首尾局部哈希块大小选项**：64KB/256KB/1MB → **64KB/1MB/16MB**（放大系数）；默认值 64KB → **1MB**。`useTaskCreate.js`（`BLOCK_SIZES` + 表单默认）、`router.py`（5 处兜底默认）、`DuplicateResult.vue`（结果兜底）
- **「每组保留一个」切换即时重算**：原勾选/取消该开关不触发重算（结果停留在旧选择）。抽出 `reapplyRule()` + `watch(keepOnePerGroup)` 切换时按当前规则重算——开多留一个、关补回留的那份。`DuplicateResult.vue`
- **「选择规则」标签样式统一**：`选择规则` span 颜色 `slate-400→slate-500`，与右侧「每组保留一个」label 同色。`DuplicateResult.vue`
- **删除模式选择下方黄色提示条**：查重/比较选中模式后的 `modeHint` 琥珀色说明条移除（连 `modeHint` computed 及 `MODES` 的 `.hint` 字段一并清掉，无残留死数据）。`pages/Duplicate.vue`、`pages/Compare.vue`、`useTaskCreate.js`
- **恢复全部不再只恢复 200 条**：抽屉「恢复全部」原用 `pageSize:1000000` 拉全量，被后端 pageSize 上限 200 截断 → 每次只恢复 200。改走不分页 `listTrash`（no-page 返回全量），一次恢复全部。`StagingDrawer.vue`
- **恢复全部「已移入」逐文件实时递减**：抽屉恢复全部流式逐文件恢复时，每个 `restored` 事件按 `trashRel` 定位原 `rel` 并 `emit('restored-one')`，App 实时从 `trashEntries` 移除已恢复条目——结果面板「已移入」随恢复进度逐文件减少（不再等全部完成才一次性归零）。`StagingDrawer.vue`、`App.vue`
- **选择规则区两行布局**：`选择规则` 标签 + `每组保留一个` 复选框独占一行，规则按钮（`修改·最新` 等）换到下一行，避免一行内挤爆。`DuplicateResult.vue`

### 修复
- **`liveMoved.value` 致 DuplicateResult 渲染崩**：`liveMoved` 从 `ref(new Set())` 改 `reactive(new Set())` 后，`trashPaths` 里漏改的 `liveMoved.value`（undefined）迭代抛 `TypeError`，`trashPaths` computed 崩 → 整个查重结果组件渲染失败（工具栏在、组列表空）。改为 `liveMoved`
- **移入/恢复暂存区流式响应卡死（进度卡 100%）**：`_handle_move_stream`/`_handle_restore_stream` 误设 `Connection: keep-alive`——http.server 的 `send_header` 遇 keep-alive 会把 `close_connection` 置 False，一次性短流发完 `exit` 后连接不关闭，前端 `readSSE` 永远等不到 EOF（done），`moving` 卡 true、进度停在 100%。移除两处 keep-alive 头（长连接任务流 `_handle_sse` 保留）。+2 单测（`tests/test_router_stream.py`：断言流式短流响应头无 keep-alive、`close_connection` 保持 True）
- **刷新按钮后「已移入」陈旧为 0（暂存区有数据）**：`onRunsRefresh`（刷新按钮）只 `refreshRuns()` 不同步 `loadTrash()`，移入后 `emit('deleted')` 漏跑时 `trashEntries` 保持空 → 结果面板「已移入」显示 0。刷新按钮/删任务后补 `loadTrash()` 兜底，让「刷新」真正拉最新状态。`App.vue`
- **恢复全部完成后「已移入」不归 0（需手动刷新暂存区）**：restore-stream 卡住（同上）→ 恢复全部完成后的 `emit('restored')` 不执行 → App `loadTrash` 不刷新，已移入停在恢复前。修复流式连接后完成即自动归零；恢复过程中另逐文件同步（见改进）。`router.py`、`StagingDrawer.vue`

## [0.1.41] - 2026-08-14

### 改进
- **任务开始日志恢复哈希算法名**：0.1.37 把开始行的 `BLAKE3/SHA-256` 改成抽象「哈希」（误伤），复盘日志无法判断当时算法。`runner.py` 恢复显示 `hashing.HASH_ALGO`（SHA-256 带「（兜底）」后缀，与「关于」页一致）。例：`[开始] 查重：/xxx（推荐 · 块64KB · 不过滤 · BLAKE3）`
- **推荐/完整模式隐藏「大小」选择规则**：推荐/完整同组大小一致，按大小选无意义 → 隐藏「大小·最大/最小」；极速（同组可不同大小）保留。`DuplicateResult.vue` `visibleRules` 按 mode 过滤 + `watch(mode)` 清残留 size 规则
- **删除任务确认文案**：「删除后无法恢复，确定删除吗？」→「删除后可重新扫描，确定删除吗？」（删的是任务记录，文件不动，可重扫）。`TaskList.vue`

### 修复
- **查重选择规则语义反转**：原「规则定保留项、勾选其余」→ 改为「规则勾选匹配项、移入/锁定是后续独立动作」（点「路径最长」→ 路径最长的文件被勾选，而非保留）。`pickKeep`→`pickRuleMatches`（极值并列全返）、`toggleRule` 改勾选匹配项、去掉「保留：」标签；「每组保留一个」作兜底（规则若选中组内全部可移入文件则留一个）。本地 DOM 实测两方向正确
- **极速模式说明与实现不符**：`manifest desc`（`极速（文件名+大小）`）与 `README`（「仅比对文件名 + 大小」）写的还是旧定义，但代码 0.1.37 已重定义极速为「仅按文件名分组（不读内容、不要求同大小）」。三处文案改对：manifest desc→「极速（仅文件名）」、README→「仅按文件名分组（不读内容）」、CLAUDE.md 同步

## [0.1.40] - 2026-08-14

### 新增
- **设置「应用反馈&建议」加「飞牛论坛主页」链接**：飞牛文件收集、GitHub 旁加第三条 `https://club.fnnas.com/home.php?mod=space&uid=64436`。`Settings.vue`

### 改进
- **检查更新：版本号去 v**：当前版本、发现新版本显示去掉字面 `v` 前缀（`0.1.39` 非 `v0.1.39`）；GitHub Release tag 同步不带 v。`Settings.vue` + 发布流程
- **检查更新：「前往下载」指向 Release 页面**：`updatecheck.fetch_latest_release` 的 `downloadUrl` 一律取 `html_url`（`.../releases/tag/<version>`），不取 fpk 资产直链——由用户在 release 页下载。`updatecheck.py`
- **检查更新：无 Release/Tag 不再当错误**：仓库未发 Release 且无 Tag 时显示「暂无更新信息」（灰字），不再红字报「检查更新失败」。`fetch_latest_release` 返回 `None`（不抛）、`check_update` 无 error、前端加 `latest` 空分支。单测同步
- **检查更新：1 小时结果缓存**：进程内 TTL 缓存，重复点击不重复请求 GitHub，避免撞 60 次/小时/IP 的未认证配额。只缓存成功结果、错误不缓存（可立即重试）、`force` 跳过、升级后 current 变化自动 miss、`clear_cache()`；仅对默认真实 fetcher 缓存（测试自定义 fetcher 跳过）。+6 单测
- **设置「关于」删「作者」行**：`Settings.vue`
- **manifest 开发者/发布者改 Haorran**：`maintainer`/`distributor` 及两者 URL 改为 `https://github.com/Haorran/file-tools/releases`
- **空状态 amber 说明条上移**：`ResultView.vue` 空状态容器 `py-12`→`pt-4`，离「创建任务」按钮近 32px（实测 64px→32px）

### 修复
- **检查更新：后端读不到当前版本（回退 0.0.0）**：`updatecheck._manifest_path` 少一层 dirname——从 `app/server/` 到包根（manifest 所在）应上三层，只上了两层落到 `app/`。改为三层（与 `server.py` 同口径），强化单测（断言 ≠0.0.0 + 路径存在）。单测同步
- **窗口标题随菜单切换变化**：`App.vue` 切菜单时 `watch(activeTool)` 调 `sdk.setTitle(当前菜单项名)`，标题变成「单目录查重」「设置」等。改为一次性 `sdk.setTitle('文件工具箱')`，标题恒定

## [0.1.39] - 2026-08-14

### 新增
- **设置页「检查更新」按钮**：设置 → 关于「当前版本」行最右侧加「检查更新」按钮。后端新增 `updatecheck.py`（纯 stdlib，无第三方依赖）+ `GET /api/update/check` 路由，由后端代理 GitHub Releases/Tags API 取最新版本，与 manifest 当前版本 semver 比对，返回 `{current, latest, hasUpdate, releaseUrl, downloadUrl, releaseNotes, error?}`；无 Release 时回退取首个 Tag，网络失败不抛、返回 error 降级。前端 `api.js` 加 `checkUpdate()`，`Settings.vue` 点击后内联展示「已是最新 / 发现新版本 vX.Y.Z + 前往下载 / 错误信息」。+12 单测（版本比较、tag 解析、有新版/已是最新/无 release 走 tags/无 release 无 tag/网络错误降级/资产优先选 .fpk）

### 改进
- **空状态 amber 说明条对齐**：`ResultView.vue` 空状态（查重 + 比较）的 amber 说明条原 `w-full` 在窄结果栏下顶到两边、且居中与「创建任务」按钮（左对齐）对不齐。外层容器加 `px-5`（与按钮栏一致），说明条加 `self-start` 左对齐——左边缘与「创建任务」按钮对齐；`max-w-[640px]` 保留一定尺寸，不再顶到右边缘。本地 DOM 坐标实测：amber 左缘 == 按钮左缘，右侧留 28px 间隙

### 修复
- **推荐模式查重 key 未含文件大小（误报根因）**：`group_key` mode 1 原仅用 `partial_hash`（首尾哈希），未拼 size——理论上首尾块相同但总大小不同的文件会被误归一组。改为 `f"{size}_{partial_hash}"`，大小不同不归组。极速(0) 不变（纯文件名，允许同名不同大小）；完整(2) 不变（全哈希相等已隐含同大小）。删除复核 `_delete_one` 用同一 `group_key` 重算、扫描与复核格式一致。docstring 同步修正（原写「大小 + 首尾局部哈希」但实现没带 size 的历史不符）。+2 单测（首尾相同大小不同→不归组、同大小同首尾→仍归组）

## [0.1.38] - 2026-08-14

### 新增
- **大小范围过滤（下限 + 上限）**：原仅「过滤阈值」单下限（≥X），扩展为「大小范围」双输入框（≥ 下限 ≤ 上限，含等号，共用 KB/MB 切换），可圈定文件大小区间。查重页「过滤阈值」改「大小范围」双框；比较页**新增**大小范围控件（原比较无过滤）。后端 `duplicate.py`/`compare.py` 加 `filter_max_kb`（比较补 `filter_kb`），建 map/候选前过滤；`router`/`runner` 解析透传 `filterMaxKB`，下限>上限校验；`api.js`/`useTaskCreate`/`Duplicate.vue`/`Compare.vue` 同步。任务开始摘要支持 `≥X·≤Y` 区间显示。+6 单测（查重上限/区间 3 项、比较下限/上限/区间 3 项）
- **极速模式「忽略文件名大小写」开关**：极速分组 key 可选大小写归一化（`Photo.jpg`/`photo.jpg` 视为同名）。与「忽略扩展名」并排同一行（标题「极速选项」，扩展名 3 选 1 + 竖分隔线 + 大小写 区分/忽略 2 选 1），默认区分大小写。`_name_key`/`group_key`/`scan_duplicates` 加 `ignore_case`；**删除复核 `_delete_one` 同步透传 `ignore_case`**（否则大小写归一化后复核 key 对不上会误跳过）；`router`/`runner`/`api.js`/`useTaskCreate`/`DuplicateResult`（删除调用带 ignoreCase）同步。+2 单测（忽略大小写同组、与忽略扩展名组合）。顺带修正 `_name_key` docstring「忽略大小」与实现不符的历史不一致
- **右侧空状态 amber 说明条**：无任务/未选中时，右侧结果区空状态（SVG+标题+说明）上方加 amber 说明条，随当前选中工具切换两套文案——作用 + **场景↔模式对应表**（模式 | 适合场景 | 那种情况扫不出来）+「不确定就选推荐」兜底。查重 3 行、比较 2 行。`ResultView.vue` 用 `activeTool` 切换，仅空状态显示

### 改进
- **中间栏 modeHint 改极简版**：右侧空状态说明条已全览各模式区别，中间栏随选中模式切换的说明条信息重复 → 改为只显示**该模式「会漏什么」**一句（与右侧表第三列口径一致），详情靠右侧空状态表。`useTaskCreate.js` DUP_MODES/CMP_MODES 的 `hint` 全部精简
- **中间栏字号体系统一**：区块标题 14px / 模式卡片副描述 10px 不动，其余（模式卡片主标题、子选项按钮、过滤输入框、KB/MB 按钮、错误提示）统一 12px。`Duplicate.vue`/`Compare.vue`
- **全部按钮横向内边距统一 px-3**：创建任务行（创建任务/锁定/移入暂存区/暂存区）、选择目录、确认弹窗（取消/备选/确认）、删任务弹窗（取消/恢复全部/永久删除/删除）横向内边距统一 12px。`ResultView`/`DirPicker`/`ConfirmDialog`/`TaskList`

### 修复
- **比较模式 has_diff 误报（加大小过滤后）**：`compare_dirs` 的 `has_diff` 原用全量容量比较，加了大小过滤后被过滤掉的文件造成的容量差会误报「有差异」。改为用过滤后容量判断 `has_diff`，全量容量仍展示（用户看目录总大小）。未过滤时行为不变

## [0.1.37] - 2026-08-14

> 本版为 0.1.36 打包（08-13 19:42）之后的源码改动单独立版。0.1.36 那个 fpk 未含以下改动，本版首次打入包并待 NAS 验证。

### 改进
- **查重极速模式重定义**：原极速 = 文件名+大小，结果与推荐趋同、价值低 → 改为**仅按文件名分组**（忽略大小、不读内容），并新增**忽略扩展名**选项（none/last/all，仅极速模式出现）。`duplicate.py` `group_key`/`_name_key`/`scan_duplicates` 支持 `ignore_ext`；`runner.start_duplicate` 透传；`router._handle_duplicate`/`_delete`/`_batch_delete`/`_delete_one`（复核按 run 的 ignoreExt 重算 group_key）；前端 `useTaskCreate`（`dupForm.ignoreExt` + `DUP_MODES[0]` desc「仅按文件名」）、`Duplicate.vue`（3 选 1 控件）、`api.js`、`DuplicateResult`（带 ignoreExt 删）。新增 6 项 mode0 单测
- **多目录比较砍极速模式**：比较原极速（仅比大小，速度优势小且漏静默损坏）价值低，**只留 推荐/完整 两档**。`CMP_MODES` 删极速、`router._handle_compare` mode 校验限 (1,2)、`compare.py` 文件头注释、`Compare.vue` 栅格 `grid-cols-2`
- **模式说明条**：模式选择卡片下方加 amber 提示条，**随选中模式动态切换**，文案=场景+结果预期。查重 3 条（极速/推荐/完整）、比较 2 条（推荐/完整文案分写，结果预期不同：查重=重复组、比较=A/B 差异）。字号 `text-xs`，`Duplicate.vue`/`Compare.vue` 各 `modeHint` computed
- **应用介绍对齐 README**：manifest `desc` 按方案 A 重写——四工具齐全（EXIF 文件信息/快照对比标「开发中」），EXIF 行分列照片（时间·相机·光圈·快门·ISO·焦距）与视频（分辨率·色彩空间·颜色格式·比特率）元信息；精简任务模型/功能特性为单行。`wizard/install` helpText 同步补 EXIF/快照对比（开发中）
- **用户可见处不再提哈希算法名**：BLAKE3/SHA-256 是实现细节，用户可见文案统一说「哈希」。改 CMP 完整 desc/hint、manifest desc、`runner` 任务开始日志行（`hashing.HASH_ALGO`→「哈希」），清掉 `runner` 无用 `hashing` import。内部代码/docstring 保留算法名
- **logstore 旧版 `.log` 兼容代码清理**：删除 `.log` 单文件旧格式读取逻辑（`_base_of`/`_load_run`/`list_runs`/`delete_run`/`get_run_by_id` 中的 .log 分支）。`save_run` 只写 `.meta.json`/`.result.json`，从不写 `.log`（pre-release 不写旧版兼容，见 `no-backward-compat`）

### 修复
- **「首位局部哈希」错别字**：推荐模式哈希读首+尾两块，文案「首位局部哈希块大小」「大小+首位局部哈希」应为「首尾」。改 `Duplicate.vue`/`Compare.vue` 标签 + `useTaskCreate.js` 模式描述共 4 处

## [0.1.36] - 2026-08-13

### 新增
- **导航「快照对比」规划中项**：左侧导航加「快照对比」（disabled 规划中，与 EXIF 同样灰显不可点），对应 `DESIGN_SNAPSHOT_DIFF.md`（存储池内两份 Btrfs/ZFS 快照对比文件差异）。图标用内联 render-function 层叠图标（`App.vue` 内定义，不新建组件文件）

### 改进
- **完整模式按字节算进度**：原完整模式（全文件 BLAKE3）进度按文件数算，文件大小差异大时进度条不准（大文件哈希久但计数只 +1）。改为按字节：`duplicate.py` mode2 `total_bytes=Σ候选size` + `done_bytes` 累加已完成文件 size，`report` 带 `doneBytes/totalBytes`（极速/推荐不带，仍走文件数）；`runner._emit_progress` 透传；前端 `TaskList.vue` 完整模式（`totalBytes` 存在）→ 条宽=`(doneBytes+Σ在途bytes)/totalBytes`、显示「已处理 0.13/5.20 GB · 计算中 N」、`<1%` 显「<1%」。极速/推荐维持文件数，扫描阶段不变
- **按钮高度/颜色统一**：「选择目录」按钮（`py-2.5`/`bg-blue-500`）与「创建任务」按钮（`py-1.5`/`bg-blue-600`）高度色阶不一致。表单区（扫描目录/过滤输入框 + KB/MB + 选择目录按钮）统一到 `py-1.5` 跟操作栏等高；「选择目录」按钮颜色对齐创建任务（`bg-blue-600` + `font-semibold` + `hover:bg-blue-700`）。模式选择卡片（`py-2.5` 卡片类）不动，Compare 页 dirA/dirB 经 DirPicker 自动覆盖
- **空状态去 emoji**：三处空状态（ResultView 通用、DuplicateResult 查重、CompareResult 比较中）原用 emoji 📂（Windows 下字形缺失/方框），改内联 SVG 线性文件夹图标（`stroke-width 2`/`currentColor`/`width 32`，跨平台一致）。字号仅 `text-sm`+`text-xs`，色阶沿用 slate-300/400/500/600 + blue，无新增

### 修复
- **关应用重开任务「重新遍历」**：重开应用订阅 SSE 时后端 `add_listener` 全量回放 `t["events"]` 逐条 progress 历史（含扫描阶段低数字），前端 `t.progress=d` 每条触发重渲染 → 视觉上像任务从头遍历；`t["events"]` 还随文件数无限膨胀。改为 `progress`/`inflight` 只留最新快照不入 events，`add_listener` 先发快照再回放 durable 事件（stdout/dupGroup/result/exit）。重连瞬间显示真实进度，无历史回放。新增 4 项单测
- **删任务弹窗成功后硬停 1.2s**：删任务（直接删/恢复/永久删除）成功后 `phase=done`+`setTimeout 1200ms` 才关弹窗，但任务已从列表消失（反馈已给），1.2s 纯人为停留且对长操作太短/短操作多余。改为操作 await 完成后立即关弹窗（恢复有进度条、永久删除有 spinner，完成即关）。错误路径保留 2.5s 展示

## [0.1.35] - 2026-08-13

### 修复
- **终止按钮即时反馈不生效（极速等所有模式）**：0.1.34 的终止即时反馈实际没生效——`handleStop` 改的是 `props.running` 里 `activeTaskArray` 展开的**副本**（非 reactive 源），不触发重渲染，badge 仍显示「运行中」直到后端 exit 事件。改为 `inject('task').taskMap[taskId].status` 直接改 taskMap 源，响应式触发：点终止即变「停止中」+ 禁用按钮。实测极速模式 10 万文件扫描中点终止，badge/按钮同步变「停止中」

### 改进
- **安装向导文案**：`wizard/install` 描述「目录比较与目录内查重」（老叫法）改为「单目录查重与多目录比较」（查重在前、比较在后，对应导航工具名）

## [0.1.34] - 2026-08-13

### 新增
- **运行中任务实时耗时**：运行中徽标旁显示「· 1分23秒」每秒跳动。后端 `list_active`/创建任务响应下发 `startedAt`（任务起始 epoch 秒），前端每秒计时；重连（关窗重开）从真实起始时间算，不从重开算

### 改进
- **多目录比较「容量汇总」改双条对比 + Δ**：容量/文件数各两条按比例长度的横条（A 蓝 / B 紫），下方 Δ 直接写「A 比 B 多 3.00 MB」「多 1 个」（一致时「✓ 一致」），替代原朴素表格——一眼看出谁大谁小、差多少。顺手修两个布局问题：容量汇总原 `mx-5 mt-5` 白卡与「创建任务」栏间留空位（已删标题的占位），改 flush 贴顶的 `bg-slate-50` 条（间距 0px）；差异节原紧贴汇总（首项无上间距），滚动区加 `pt-4`（间距 16px）
- **后台任务重开显示**：扫描阶段 `total` 未知时原显示「0% + 正在遍历目录树获取文件总数」不显示已扫描数，重开看着像「从头开始」。改为「扫描中」+ 脉动条 +「正在遍历目录树 · 已扫描 N 个文件」；离开提示文案改「任务将在后台继续运行，可随时返回查看进度」（原「离开页面可能中断」与实测不符，误导用户）
- **终止按钮即时反馈**：点终止即标「停止中」并禁用按钮、徽标变琥珀色「停止中」，不再等后端 exit 事件才变化。NAS 实测后端停止仅 55ms（扫描每文件、哈希每 1MB 检查 cancel），原「点了没反应、半天才停」纯为前端无反馈
- **锁定/移入暂存区按钮去冗余数字**：按钮后「（N）」去掉（下方分布条已显示文件数与大小），更清爽

### 修复
- **删任务记录卡顿**（即使暂存区为空）：`_handle_delete_log` 判空原用 `list_trash`，而 `list_trash`→`_connect` 会在扫描目录凭空建 `.ft-trash/trash.db` + WAL，末尾 `purge_trash` 又建一遍再 rmtree 删——团队共享慢盘上明显卡。新增 `has_trash`（只读 `mode=ro` URI、不建文件）判空；`purge_trash` 无 `.ft-trash` 直接 early-return。无暂存区任务删记录扫描目录零 IO，只删 data share 的 meta/result

## [0.1.33] - 2026-08-13

### 修复
- **openFileManager 传文件路径而非目录**：查重结果文件项「在文件管理器中打开」原传文件完整路径（如 `.../C6273.MP4`），fnOS `openFileManager` 文档示例为目录路径（`openFileManager('/vol1/1000')`），传文件导致定位不准。改为传文件所在目录（`slice(0, lastIndexOf('/'))`）

### 总结：开放 API 能力底座接入（0.1.29 → 0.1.33）

本次从 0.1.29 起接入 fnOS 开放 API 能力底座，依据 `OPENAPI_SDD.md` 三 Phase 规划，全部完成并 NAS 验证通过（12 项验证全过）。

**Phase 1 地基（0.1.29）**：manifest 加 `micro_app=true` + `os_min_version` 上调 `1.2.0401`；config/resource 声明 3 项 api-scope（`trim.file.sharedAccess`/`trim.file.path`/`trim.system.getPlatformConfig`）；app/ui/config 改 `allUsers=false` 管理员限定；后端 `trimapi.py` 客户端（Unix Socket + token 现读不缓存 + 硬依赖失败不回退）+ `mock_gateway.py` 本地假网关（DEBUG_LOCAL 走真实分支不跳过校验）；前端 `trimSdk.js` + `useTheme` 切 SDK；`/api/platform-config` 路由（改读 `TRIM_SYS_*` 环境变量，因 `trim.system.getPlatformConfig` 后端 scope 返回 200003，文件类 scope 正常）。

**Phase 2 授权+权限（0.1.30）**：`/api/auth/folders` GET/DELETE 路由（`getSharedAccessibleFolders`/`delSharedAccessibleFolder`）；`_validate_dir` 三段式改造（路径合法性 → 授权范围校验 `_under` 方向约束只允许授权目录及子目录 → `os.access` 补充）；`DirPicker.vue` 组件（宿主 `pickSharedFile` 原生选择器 + 独立浏览器手输 fallback）；Compare/Duplicate 接 DirPicker；Settings 授权目录管理卡片。

**Phase 3 体验增强（0.1.31-0.1.33）**：`/api/path/convert` 路由 + `useSemanticPath` 语义路径展示（任务目录摘要，language 从 SDK 取后端不硬编码）；`setTitle`/`setExitPageTips`/`openFileManager` 页面交互能力接入；主题移除自研 `fnos-theme-mode` 探测纯走 SDK（保留 `prefers-color-scheme` 兜底）；wizard 文案改「应用内选目录授权」。

**关键决策与发现**：
- 管理员限定 + 应用共享授权模型，不做多用户隔离/checkUserACL/授权回调页（SDD T1-c/T3-c）
- trimapi 硬依赖：后端文件类调用失败不回退 `os.access`（权限安全不降级）
- `trim.system.getPlatformConfig` 后端 scope 不可用（200003），文件类 scope 全正常——后端读系统语言/版本改用 `TRIM_SYS_*` 环境变量
- trimSdk 独立浏览器判断用 `window.self === window.top`（UA 不可靠，NAS 宿主 iframe UA 与普通浏览器相同）
- 授权拒绝状态码统一 `_err_status` helper（权限/授权范围→403，路径合法性→400）
- convertPath 对部分路径无语义映射时回退原始路径（设计行为，非代码问题）

## [0.1.32] - 2026-08-13

### 修复
- **DirPicker「选择目录」按钮在 NAS 宿主不显示**：trimSdk 的独立浏览器判断用 UA（`/FNApp|FNOS/i`）不可靠——NAS 宿主 iframe 的 UA 与普通浏览器相同（不含 FNApp/FNOS），被误判为独立浏览器走 stub，导致 isHost 恒 false、DirPicker 按钮不渲染、主题不走 SDK、setTitle 等全失效。改用 `window.self === window.top` 判断（NAS 宿主是 iframe，self !== top；独立浏览器 self === top），UA 判断移除

## [0.1.31] - 2026-08-13

### 新增
- **语义路径展示（Phase 3）**：任务卡片目录摘要（dirA/dirB/scanDir）展示为 fnOS 语义路径（如「存储空间1/admin 的文件/...」）——后端新增 `POST /api/path/convert` 调 `trim.file.convertPath` 批量转换；前端 `useSemanticPath` composable 缓存 + 响应式版本号触发重渲染；`language` 由前端从 SDK `getPlatformConfig().language` 取并随请求传入，后端不硬编码
- **页面交互能力（Phase 3）**：宿主内接入 `sdk.setTitle`（随当前视图更新窗口标题）、`sdk.setExitPageTips`（有运行中任务时设离开提示，结束/卸载清除）、`sdk.openFileManager`（查重结果文件项加「在文件管理器中打开」按钮）。全环境失败静默

### 改进
- **主题纯走官方 SDK**：`useTheme.js` 移除自研 `fnos-theme-mode` 探测（URL/localStorage 逆向猜），宿主内用 `sdk.getPlatformConfig` + `$on('os/theme')`，独立浏览器/SDK 失败时回退浏览器原生 `prefers-color-scheme`（非自研探测）
- **wizard 文案**：install/config 向导改引导「应用内点选择目录授权」，不再引导去系统设置手动勾授权目录
- **trimSdk 独立浏览器隔离**：用 UA 预判（`/FNApp|FNOS/i`），独立浏览器直接 stub 不构造真 SDK，避免 `@trimjs/web-app` 抛「Host bridge is not available」全局 JS Error；宿主内才 `new TrimApp` + 读 language

### 修复
- **授权拒绝状态码**：`_validate_dir` 授权范围拒绝原返回 400（文案含「授权范围」不含「权限」未触发 403 判断）——抽 `_err_status(err)` helper 统一判定（含「权限」「授权范围」「授权目录」→403，路径合法性→400），5 处调用点统一调用

## [0.1.30] - 2026-08-13

### 新增
- **授权目录管理（Phase 2）**：Settings 页新增「授权目录」管理卡片，列出应用共享授权目录并支持逐个删除——后端 `GET /api/auth/folders` 调 `trim.file.getSharedAccessibleFolders` 查询、`DELETE /api/auth/folders` 调 `trim.file.delSharedAccessibleFolder` 删除（trimapi 硬依赖，失败即暴露错误码，不回退）
- **DirPicker 目录选择组件**：新增 `frontend/src/components/DirPicker.vue`，宿主内调 `sdk.pickSharedFile` 弹 fnOS 原生共享目录选择器，选择失败/独立浏览器时降级为手输输入框（`isStandalone` fallback），Compare/Duplicate 表单均接入
- **授权范围校验**：`_validate_dir` 改造为三段式——路径合法性（规范化/绝对路径）→ 授权范围校验（`_under` 方向约束：路径必须在某授权目录之下，只允许授权目录及其子目录，trimapi 硬依赖不回退）→ `os.access` 应用用户读权限补充校验（防授权目录下子项手动 chmod 撤权）

### 改进
- **Compare/Duplicate 接入 DirPicker**：dirA/dirB/scanDir 输入框统一换为 DirPicker，宿主内走原生选择器选目录，非宿主环境保留手输
- **Settings 授权管理卡片**：进入 Settings 拉取授权目录列表展示，删除按钮逐个移除（调用后端 DELETE 接口），与新建任务的授权校验同源

## [0.1.29] - 2026-08-13

### 新增
- **开放 API 地基层（Phase 1）**：接入 fnOS 开放 API 底座，为后续应用内选目录授权、语义路径展示、主题官方化铺路（依据 OPENAPI_SDD.md，本次仅地基，授权与权限校验在 Phase 2）
- **后端 trimapi 客户端**：新增 `app/server/trimapi.py`，封装对 fnOS 后端开放 API 的调用（Unix Socket + `TRIM_API_TOKEN` 现读不缓存 + 错误码 200003/200004/200005/200006），硬依赖失败即暴露不回退 `os.access`
- **本地 mock 假网关**：新增 `app/server/tests/mock_gateway.py`，DEBUG_LOCAL 下仿 `/var/run/trim_open_gateway_apiscope.socket`，让本地单测/E2E 走真实授权范围校验分支（不跳过、不降级），纯测试设施不打包进 fpk
- **`/api/platform-config` 路由**：后端读系统语言/版本，直接读 fnOS 注入的环境变量 `TRIM_SYS_LANGUAGE`/`TRIM_SYS_VERSION`（NAS 实测 `trim.system.getPlatformConfig` 的 scope 未绑进后端 token 返回 200003，文件类 scope 正常；环境变量已由系统注入，更简更稳）
- **前端宿主 SDK 封装**：新增 `frontend/src/composables/trimSdk.js`，单例 `@trimjs/web-app` + `isHost`/`isStandalone` 环境判断；构造失败回退 stub 保证独立浏览器不崩

### 改进
- **管理员限定**：`app/ui/config` 改 `allUsers=false` + `control.accessPerm=readonly`，桌面仅管理员可见（fnOS 文档建议管理员限定应用两者同用）
- **微应用模式**：manifest 加 `micro_app=true`，启用宿主 SDK 注入（不改变 socket 网关/路由现有行为）
- **系统版本下限上调**：`os_min_version` 从 `1.1.3100` 上调到 `1.2.0401`（开放 API 全部能力的版本下限，已公测；低版本装不上，代码只维护开放 API 一条路）
- **api-scope 声明**：`config/resource` 加 `trim.file.sharedAccess` / `trim.file.path` / `trim.system.getPlatformConfig` 三项（不含 userAccess/userAcl）
- **主题切官方 SDK**：`useTheme.js` 宿主内改用 `sdk.getPlatformConfig()` 读主题 + `$on('os/theme')` 实时跟随，保留 `fnos-theme-mode` 探测作 fallback（SDK 失败/独立浏览器时降级，Phase 3 确认稳定后移除）
- **DEBUG_LOCAL 机制统一**：从硬编码改为环境变量 `FILE_TOOLS_DEBUG_LOCAL` 驱动，router/server/trimapi 三处同源；`make test-e2e`（TCP 模式）自动拉起 mock 假网关

## [0.1.28] - 2026-08-12

### 修复
- **暂存区恢复全部按钮样式**：「恢复全部」按钮改用原生按钮样式，修复此前样式异常问题

## [0.1.27] - 2026-08-12

### 新增
- **查重锁定保留**：结果区常驻「锁定」按钮（移入暂存区左侧，绿色边框），勾选文件后批量锁定为保留项；锁定文件 checkbox 禁用 + 行绿底 + 「已锁定保留（规则/移入跳过）」副文案，选择规则与移入均跳过锁定文件
- **选择规则 + 每组保留一个**：「保留规则」改「选择规则」8 按钮换行，后接「每组保留一个」勾选框（默认开）——勾选规则时非锁定文件按规则勾选移入，每组自动留 1
- **暂存区恢复全部**：暂存区抽屉「重建暂存区」右侧加「恢复全部」按钮，分批 200/批恢复全部文件回原路径 + 进度条，与删除任务时的恢复全部逻辑一致

### 修复
- **网关鉴权失效报错**：登录态过期时 fnOS 网关返回纯文本 `invalid token`，前端 `res.json()` 抛 SyntaxError 上报 Vue runtime；新增 `parseJson` 统一兜底，非 JSON 响应转友好提示「登录可能已过期，请刷新页面重试」

### 改进
- **设置页文案**：「应用日志」改「应用崩溃日志」；空状态「暂无日志记录」去斜体
- **空状态文案**：去掉「点上方「＋ 创建任务」」中的「＋」
- **比较空状态文案**：「正在比较，结果会实时出现…」改「正在比较，完成后显示结果…」（比较结果跑完一次性出现，非流式）

## [0.1.26] - 2026-08-12

### 改进
- **三块固定 flex 布局**：常驻操作区（创建任务/移入按钮）+ 保留规则 + 冗余分布条（查重）/ 容量汇总（比较）改为 flex `shrink-0` 固定不滚动，重复组/差异分节 `flex-1 overflow-y-auto` 独立滚动区——修复 sticky 门帘子（三块盖重复组）问题
- **移入进度复用分布条**：去掉 ResultView 常驻区红色进度条，doMove 每批后清空本批已移入勾选 + 刷新暂存区，分布条「待移入/已移入」数字实时更新
- **多目录比较容量汇总固定**：创建任务按钮 + 容量汇总（带 有差异/一致 徽标）固定顶部，差异分节独立滚动，与查重布局一致

## [0.1.25] - 2026-08-12

### 修复
- **移入进度条不响应**：`ResultView` 读 expose ref 加 `.value`，但 Vue 3 父访问 expose ref 自动 unwrap，`.value` 取到 undefined → isMoving 恒 false、进度条不出；改 `unwrap()` 兼容 boolean/ref，进度条/按钮文案/移入中禁用全部恢复

### 改进
- **移入复核弹窗加宽**：ConfirmDialog 320→480px + 按钮 `whitespace-nowrap shrink-0`，三按钮一行不换行
- **移入中锁定交互**：保留规则按钮禁用（不变灰，仅鼠标禁止）；重复组区域 `opacity-60` 变淡 + checkbox 禁用
- **三块 sticky 固定**：常驻操作区（创建任务/移入按钮/进度条）+ 保留规则 + 冗余分布条滚动时固定顶部；JS 测常驻区高度设 CSS 变量供下方 sticky top 偏移
- **多目录比较结果区 UI**：去掉「📁 多目录比较结果」标题；有差异/一致徽标移到容量汇总表格右上角；深色模式文件列表文字改浅灰（不再黑色）

## [0.1.24] - 2026-08-12

### 新增
- **移入前复核方式选择**：点「移入暂存区」弹窗选复核方式——「指纹复核（推荐）」校验修改时间+大小（秒级，适合大文件）；「全文件哈希复核」重读全文算哈希比对（原设计保留，最严格）。复核不一致的文件跳过（保留原位），不阻断整批
- **删除任务暂存区处理进度**：删除任务·恢复全部改前端分批 200 + 进度条「正在恢复 X% · N/M 个文件」；永久删除走 rmtree + spinner「正在永久删除…」；完成「✅ 任务已删除」反馈。不再无反馈卡住

### 改进
- **rebuild 重建清单可恢复原路径**：孤儿文件原路径不再标「未知」——用文件在 `.ft-trash` 的相对路径作为原路径推断（移入时保留原相对结构），重建后条目可恢复；清旧「未知」条目按实际文件重新补录

### 修复
- **大批量移入卡死**：完整模式 `_delete_one` 移入前每文件重算全文件哈希复核（防 TOCTOU），860GB 大文件重读全量卡死——改默认指纹复核（不重算哈希），全哈希复核作为可选入口
- **创建任务按钮偏移**：加载单目录查重任务后右侧块出现，实心按钮无 border（h=32）vs 暂存区按钮有 border（h=34），`items-center` 居中致创建任务下移 1px——给实心按钮加 `border-transparent` 统一高度

## [0.1.23] - 2026-08-11

### 新增
- **EXIF 信息工具占位**：左侧导航新增「EXIF 文件信息」入口（ⓘ 图标，灰色不可点击），为规划中的图片/视频元信息查看工具预留入口

### 改进
- **多目录比较结果区布局**：删除冗余的「模式/目录A路径/目录B路径」信息块；容量汇总从底部上移至标题徽标行下方（最上）；「有差异」徽标保持右上角
- **暂存区抽屉优化**：结果面板「移入暂存区」与「暂存区」按钮交换位置（移入在前）；抽屉标题去掉垃圾桶图标，新增重建说明文字；重建 🔄 图标改为文字按钮「重建暂存区」
- **清理暂存区迁移死代码**：0.1.21 未发布、无 jsonl 用户，删除 `_migrate_jsonl` + `.migrated` 迁移逻辑，rebuild 不再误收 `.migrated` 标记文件

### 修复
- **删除任务后结果残留**：选中任务删除后结果区仍显示旧结果且可操作——现删除当前选中任务时清空选中态，结果区随之清空、不可再操作
- **删除任务后 trash.db 残留**：原仅在「永久删除」分支清理 `.ft-trash`，恢复/空暂存区分支残留 `trash.db`——现删除任务后统一清理 `.ft-trash`

## [0.1.22] - 2026-08-10

### 改进
- **暂存区清单改 SQLite**：`.manifest.jsonl` 全量重写改为 `.ft-trash/trash.db`（sqlite3）——事务保证「文件移动 + 清单更新」原子性，杜绝「清单与文件不一致」（此前大量文件恢复时多次全量重写易截断损坏，导致暂存区显示空但文件残留）；天然支持分页/搜索（配合暂存区抽屉）；自动迁移旧 jsonl
- **暂存区清单重建**：新增 `POST /api/trash/rebuild`——扫描 `.ft-trash` 实际文件补录清单缺失条目（原路径未知标记，可删除不可自动恢复）；抽屉新增「🔄 重建清单」按钮

---

## [0.1.21] - 2026-08-10

### 新增
- **查重结果页重构**：右侧结果区顶部常驻操作区——「创建任务」常驻（挪自中间栏，随当前工具切换）、批量「移入暂存区」、保留规则（修改/创建/大小/路径 × 最新/最旧/最大/最小/最长/最短，可再次点击取消）、冗余分布堆叠条（保留/待移入/已移入 + 图例，运行中随 dupGroup 实时更新）
- **批量移入暂存区**：新增 `POST /api/duplicate/batch-delete` 接口，一次移入多组勾选文件（替代逐组移入）
- **中间栏配置区精简**：去掉「单目录查重 / 多目录比较」标题与「创建任务」按钮，只留配置表单；创建统一由右侧结果区常驻按钮触发
- **暂存区抽屉**：暂存区从日志面板 tab 改为右侧滑出全屏抽屉——支持**搜索**（按文件名，防抖）与**分页**（每页 50 条，后端分页），单条恢复；后端 `listTrash` 支持 `page/pageSize/q` 参数（不传仍返回全部供「已删态」派生）

### 修复
- **创建时间取真实 btime**：新增跨平台 `engine/btime.py`，通过 `libc.statx` / `syscall` 读取文件出生时间。此前 fnOS 的 python312 运行时无 `os.statx`，创建时间被回退成 ctime（inode 状态变更时间）近似，实际不是真正创建时间；现在取不到真实 btime 时显示「-」，不再用 ctime 冒充
- **耗时显示**：任务不足 1 秒时显示「`<1秒`」，不再为空（前端 `formatDuration` 与日志 `_fmt_duration` 同步）
- **分布条默认全部保留**：无勾选时分布条「保留」显示全部重复文件（默认未决定移入即保留），不再全为 0
- **大批量移入卡死**：移入暂存区改为前端分批请求（每批 200）+ 实时进度（按钮显示「正在移入 X%」+ 进度条），5000+ 文件不再无反馈

### 改进
- **运行中卡片文件数进度常驻**：遍历目录树阶段（总数未知）显示「正在遍历目录树获取文件总数」，总数计算好后切换为「已处理 X / Y 个文件」
- **查重结果文件时间精确到秒**：重复文件的「修改/创建」时间从 `YYYY-MM-DD` 精确到 `YYYY-MM-DD HH:mm:ss`
- **切换运行记录加载动画**：历史任务结构化结果较大时，切换瞬间显示「正在加载结果… / 正在加载日志…」动画占位，不再出现空白或旧内容残留
- **加载动画换圆环 spinner**：结果/日志加载态从 `⏳` 沙漏改为圆环 spinner（结果居中 40px、日志行内 16px）
- **结果页文字大小统一**：主操作/保留规则/分布条图例 14px、文件路径 13px、次要信息 12px
- **移入按钮布局**：「创建任务」「移入暂存区」并排于结果区顶部（创建左、移入右），去掉图标只留文字；分布条「待移入」改红色与移入按钮一致

---

## [0.1.18] - 2026-08-09

### 新增
- **暂存区**：查重结果可勾选重复文件「移入暂存区」（`.ft-trash/`），支持整组移入；恢复或永久删除由用户决定
- **删除任务前置校验**：查重任务有暂存区文件时，必须先处理（恢复全部 / 永久删除）才能删除任务，防止误删
- **任务模型**：单任务约束——同一目录（查重）或目录对（比较）同时只能有一个任务，运行中不可删除
- **inflight 实时进度**：查重哈希阶段每秒上报在途文件列表（文件名 + 已读字节），前端可精确展示正在处理的文件
- **流式重复组**：查重发现重复组时立即推送（`dupGroup` SSE 事件），无需等全部扫描完成
- **结果导出**：比较/查重结果可导出为文本文件，写入 `TRIM_DATA_SHARE_PATHS` 共享目录
### 重构
- **后端引擎**：从 shell 脚本（`dir_compare_check.sh` / `dir_duplicate_check.sh`）完全迁移到 Python 纯函数引擎（`engine/walker.py` / `hashing.py` / `compare.py` / `duplicate.py` / `trash.py`）
- **后端架构分层**：`server.py`（传输层）/ `router.py`（路由与业务）/ `tasks.py`（任务生命周期）/ `runner.py`（后台线程 + SSE）/ `logstore.py`（持久化）
- **前端组件重组**：拆分为 `TaskConfig` / `TaskList` / `CompareResult` / `DuplicateResult` / `StagingPanel` / `LogPanel` / `ConfirmDialog` 等独立组件
- **哈希算法升级**：优先使用 BLAKE3（设备未安装时自动回退 SHA-256）
- **SSE 事件结构化**：`progress` / `inflight` / `dupGroup` / `result` / `exit` / `error` 分类推送

### 修复
- SSE 快速任务丢日志/结果问题：任务完成后连接的客户端可从日志回放完整事件序列
- 删除文件 TOCTOU 防护：移入暂存区前复核文件内容仍与原分组一致，防止内容变化后误删

---

## [0.0.57] - 2026-07-26

首个公开发布版本。

### 功能
- 目录比较：比对两个目录文件清单差异与内容一致性
- 目录查重：扫描单目录，按文件名或内容哈希找出重复文件
- 三种校验模式：极速（文件名+大小）/ 推荐（+首尾局部哈希）/ 完整（+全文件哈希）
- SSE 实时进度推送
- 明暗主题切换
- 运行日志历史记录
