# CHANGELOG

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
