# XHS 运行规则（引用自技能主文）

## 0.1 低 token 与快照约束

- 优先 `evaluate`，减少无意义 dump 与重复抓取。
- 只在关键节点做快照：登录确认、到发布页、填写完成、发布完成。
- 避免 `fullPage`（除用户要求整页归档）；重复调用优先复用同一 `targetId`。
- 每个动作最多重试 1 次；第二次失败改稳健路径并汇报。
- 记录关键证据：账号名、页面状态、按钮可见、字数等，返回可执行信号。

## 0.2 浏览器规则（最高优先）

**所有浏览器操作统一使用 `scripts/browser.py`（Camoufox 反指纹浏览器）。**

**⛔ 严禁使用以下替代方案访问小红书**：
- IDE 内置浏览器（如 Cursor Simple Browser）
- MCP 浏览器工具（如 `cursor-ide-browser`、`browser-use`）
- `WebFetch` / `WebSearch` 直接抓取小红书页面
- 任何非 Camoufox 的浏览器或 HTTP 请求

原因：只有 Camoufox 在 C++ 层面修改指纹，其他方式均会暴露自动化痕迹，导致账号风控。

### Camoufox 核心特性
- C++ 级指纹修改（非 JS 注入），覆盖 navigator、WebGL、Canvas、AudioContext 等
- `humanize=True`：贝塞尔曲线鼠标移动，模拟人类操作轨迹
- `locale="zh-CN"`：通过 C++ 引擎设置语言环境，无注入痕迹
- `persistent_context`：持久化 profile，cookie/localStorage 跨会话复用

### 启动流程（Profile-First）

**编程调用必须用 `launch_with_auth()`**，一行完成 profile-first 认证：
```python
bm.launch_with_auth(fallback_cookie=env_vars.get("XHS_COOKIE", ""))
```

内部流程：
1. `launch()` 启动 Camoufox（加载 profile 目录中的 cookies.sqlite）
2. `check_login()` 检测 profile 持久化的登录态
3. Profile 有效 → **跳过 Cookie import**，直接返回 page
4. Profile 失效 → import `fallback_cookie`（来自 `.env`），再次检测
5. 两者均失效 → 抛出 `RuntimeError`，提示运行 `login` 命令

**⚠️ 严禁在 `check_login()` 之前调用 `import_cookies()`** — stale cookie 会覆盖 profile 中还有效的登录态，这是"每次都要登录"的根因。

### 登录失效处理流程
当 profile 和 `.env` Cookie 均无法恢复登录态时：

1. 调用 `screenshot_qrcode()` 截图二维码，保存到 `/tmp/xhs-qrcode.png`
2. **将二维码截图路径返回给用户**，提示用户用小红书 App 扫码
3. 调用 `wait_for_login(timeout=120)` 轮询等待用户扫码完成
4. 登录成功后 **profile 自动持久化登录态**（下次启动无需重复登录）
5. 可选：调用 `export_cookies()` 导出并回写 `.env` 作为备份
6. 继续执行原任务

**CLI 快捷方式**：
```bash
python scripts/browser.py check                                    # 检查登录状态
python scripts/browser.py login                                    # 扫码登录（session 自动持久化到 profile）
python scripts/browser.py scrape "URL" --download-cover pic/c.png  # 抓取笔记内容
python scripts/browser.py evaluate "URL" --js "document.title"     # 执行 JS
python scripts/browser.py publish --cover pic/cover.png --title "标题" --body "正文\\n#话题"  # 发布图文
python scripts/browser.py publish --cover pic/cover.png --title "标题" --body "正文" --dry-run  # 预览不发布
python scripts/browser.py reset --confirm                          # 清除 profile（重置登录态）
```

### 登录方式（按推荐优先级）

1. **Profile 持久化复用（首选）**：只要不 reset profile，登录态会通过 `~/.xhs-skill/profiles/` 的 cookies.sqlite 自动复用。启动时优先检测此登录态，有效则跳过 `.env` Cookie import。
2. **QR 扫码登录（推荐）**：`browser.py login`。登录成功后 profile 自动持久化，后续启动无需重复登录。可选 `--save-cookie` 将 Cookie 备份到 `.env`。
3. **手动 F12 获取（降级兜底）**：Chrome 打开 xiaohongshu.com → 登录 → F12 → Network → Cookie → 复制整行粘贴到 `.env` 的 `XHS_COOKIE`。仅在 profile 失效且无法扫码时使用，Cookie 最完整（含 `id_token`），跨 profile 可靠。

### 稳定规则
- 持久化 profile 路径：`~/.xhs-skill/profiles/xhs-publish`
- **Profile-First**：启动后先检测 profile 登录态，有效则直接使用，不读取 `.env` Cookie
- Profile 失效时降级读取 `.env` 中 `XHS_COOKIE` 并 import
- 两者均失效时触发 QR 扫码登录，登录成功后 profile 自动持久化
- 连续 2 次点击/导航失败后改稳健路径（如直达点击改为 evaluate+定位），不做盲重试
- Camoufox 通道支持两种发布模式：直接发布（默认）和停手确认（用户要求时）

### DOM 交互原则（创作后台专用）

**核心原则：创作后台（`creator.xiaohongshu.com`）的元素交互优先使用 `page.evaluate()` JS 方式，不依赖 Playwright 原生 `.click()` / `.fill()`。**

原因：创作后台布局复杂，多个元素处于视口外或被隐藏遮罩覆盖，Playwright 原生方法会触发 30s 超时。

| 操作 | ❌ 会超时 | ✅ 推荐方式 |
|------|----------|-----------|
| Tab 切换 | `page.locator('text="上传图文"').click()` | `page.evaluate()` JS 遍历 span 点击 |
| 标题填写 | `title_input.click()` + `.fill()` | `page.evaluate()` nativeInputValueSetter + dispatchEvent |
| 正文填写 | `body_el.fill()` | `page.evaluate()` focus + `keyboard.type()` 逐行 |
| 发布按钮 | `pub_btn.click()` | `page.evaluate()` 遍历 button 匹配文本点击 |
| 上传文件 | - | `page.locator('input[type="file"]').set_input_files()` **这个可用** |

**唯一例外**：`input[type="file"]` 的 `set_input_files()` 不受视口限制，可直接使用。

**时序等待**：每个 DOM 操作后必须 `time.sleep()`，具体见 `references/xhs-publish-flows.md` 4.4 节。

## 3.5 搜索并浏览（核心约束）

1. 仅从搜索结果页点击进入帖子，禁止直接 `navigate` 到 `/explore/<id>`。
2. 默认跳过本账号作者内容（避免自刷）。
3. 进入后先校验：不是 404、可见评论/互动信息、可识别标题或作者。
4. 进入方式优先点卡片本体，避免点头像/作者名导致跳错。
5. 若评论控件为 `contenteditable` 或 `p.content-input`，需先触发输入事件再发送。
6. 两条点击失败或 404 后返回搜索页换下一条，不对同链接直跳重试。

## 6.0 回放与降级

- 若搜索结构变化先 snapshot 更新 selector 再继续，不盲跑旧路径。
- 关键页（创作页、探索页、用户页）尽量复用已打开 tab，不重复 `open`。
- 先告诉用户“已达异常节点”，避免无意义继续操作导致误发。
- 发布页关键动作（切 tab、上传、点击发布）失败时：
  1) 先 snapshot 刷新 ref
  2) 同动作最多再试 1 次
  3) 仍失败则切稳健路径（同义入口/用户手动最后一击）
- 轮播详情页抓图时，禁止取第一个 `.img-container`；必须优先抓取 `.swiper-slide-active:not(.swiper-slide-duplicate) .img-container img`。
- 抓图后要做一次人工核对：检查 URL 末段 key 是否与用户指定封面一致（例如 `.../1040g3k...`）。不一致则重新抓取 active 图。
- 图生图产物需要做“相似度体感检查”：若用户反馈元素过于雷同，切换到 style-only 提示词并重生，不争辩。
- 涉及 browser.upload 时，默认先检查文件是否位于 `/tmp/openclaw/uploads`，否则先复制再上传。
