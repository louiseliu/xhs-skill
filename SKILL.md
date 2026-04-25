---
name: xhs-skill
description: "小红书全链路运营技能，覆盖账号定位、选题研究、内容生产、发布执行与复盘修复。所有浏览器操作统一使用 scripts/browser.py（Camoufox 反指纹浏览器），优先使用 profile 持久化登录态（.env Cookie 作降级兜底），隐藏自动化指纹。"
---

# 小红书运营技能（通用版）

目标：构建可复用的“小红书运营”流程，让任何账号类型都能复用同一套动作框架。

## 适用范围（默认即通用流程）

- 账号定位与内容方向
- 选题产出与争议点挖掘
- 竞品/同类账号对标
- 小红书发布前演练与内容交付
- 发布后快速复盘（互动结构、评论回复、热点追踪）
- Viral Copy 链路（输入 URL，高贴合学习封面/配图、标题、正文并生成可发布近似结构笔记）
- 图文生成（输入选题，通过即梦API生成封面图+标题+正文+话题的完整素材包）

将每类账号的行业细节作为“案例模块（case module）”挂载到通用流程中。

## 常用术语

- `选题`：可发布、可讨论、可转发的内容切入点
- `引流钩子`：标题/开头一句用于触发停留与点击
- `结构化输出`：标题、正文、互动问句、话题、标签五元组
- `快照`：用于验证页面状态的关键证据快照
- `回放`：流程失败后重试或改道执行

## 0) 启动与环境校验（所有任务都遵循）

执行前先按 `references/xhs-runtime-rules.md` 中“运行规则”执行，优先遵循失败可复用顺序。

- **凭据加载**（优先级从高到低）：
  1. **Profile 持久化登录态（首选）**：`~/.xhs-skill/profiles/` 中保存了跨会话复用的 cookie/localStorage，启动后先检测 profile 登录态是否有效——有效则直接使用，不读取 `.env` 中的 Cookie。
  2. **`.env` Cookie（降级兜底）**：仅当 profile 登录态失效时，才读取 `.env` 中的 `XHS_COOKIE` 并 import。
  3. **QR 扫码登录（最终兜底）**：两者均失效时，触发二维码登录，登录成功后 profile 自动持久化。
  - `.env` 中的其他变量仍正常读取：`JIMENG_SESSION_ID`（生图必须）、`JIMENG_API_URL`（默认 `http://localhost:5100`）、`XHS_DOMAIN`（默认 `xiaohongshu.com`）。
  - 若 `.env` 缺少必要变量（如 `JIMENG_SESSION_ID`），执行到需要时再向用户索要，拿到后回填 `.env`。
- **浏览器操作统一使用 `scripts/browser.py`**（Camoufox 反指纹浏览器）：
  - 所有涉及小红书的浏览/搜索/抓取/发布/评论操作，一律通过 `scripts/browser.py` 中的 BrowserManager 执行
  - **严禁使用其他浏览器工具**：禁止使用 IDE 内置浏览器、MCP browser 工具（如 `cursor-ide-browser`）、WebFetch、或任何非 Camoufox 的浏览器方式访问小红书。原因：其他浏览器不具备反指纹能力，会暴露自动化痕迹
  - Camoufox 在 C++ 级修改浏览器指纹（非 JS 注入），`humanize=True` 启用贝塞尔曲线鼠标模拟
  - **认证必须用 `launch_with_auth()`**：`bm.launch_with_auth(fallback_cookie=env_vars.get("XHS_COOKIE", ""))` 一行搞定 profile-first 认证。**严禁在 `check_login()` 之前调用 `import_cookies()`**——stale cookie 会覆盖 profile 中还有效的登录态。
  - 持久化 profile 路径：`~/.xhs-skill/profiles/xhs-default`，登录态跨会话自动复用
  - 常用 CLI 命令：`open`（打开URL+截图）、`scrape`（提取笔记内容）、`evaluate`（执行JS）、`login`（扫码登录）、`check`（检查登录态）、`publish`（发布图文笔记）
  - 详见 `references/xhs-runtime-rules.md` 0.3 节
- 以 `evaluate` 为先，关键节点少量 `snapshot`，单步动作最多重试一次。
- 失败后保留已获结果，切稳健路径并汇报。

## 1) 技能默认行为（所有任务都遵循）

- **先读本技能目录下的 `persona.md`**（小红书平台专用人设/语气/发布与回复风格）。所有对外文案（发帖/评论回复/私信话术）都必须遵循。
- 开始新任务前，先读 `knowledge-base/README.md` 这个总览入口，再按 `references/xhs-knowledge-base.md` 的规则检索最近的同类记录；能复用的 pattern 不重复摸索。
- 优先输出可执行的 SOP 而非一次性内容稿
- 语言优先“能对话”而不是“写报告”：短句、口语、站位明确、可引导评论
- 所有输出默认保留“可追问点”，用于评论区继续延展

## 2) 账号定位（可复用）

每个账号先确认 4 个变量：

- 目标用户：年龄/场景/痛点（如「下班后碎片时间」「追星讨论人群」）
- 内容价值主张：每篇给用户什么（观点、情绪价值、实操建议）
- 差异化角度：同类账号不做什么、你做什么
- 风格规范：语气、长度、冲突边界（避免过激）

输出：

- 人设关键词（3-5）
- 内容支柱（3 个）
- 口头禅/固定句式（2-3 个）
- 不能碰底线（红线）清单（剧透、人身攻击、虚假承诺）

## 2.5) 账号分析（新增）

按 `references/xhs-account-analysis.md` 执行。

- 默认采样最近 9-15 篇内容做轻量体检
- 从定位、内容结构、互动转化、辨识度、可持续性 5 个维度判断
- 输出必须包含“最大优势、最大短板、下一步动作”

## 3) 通用选题与对标流程

### A. 平台侧抓取信号（可并行）

1. 先在小红书抓同题材高互动内容（点赞/收藏/评论高于近期平均值）
2. 记录可复用字段：`title`, `hook`, `angle`, `结构标签`, `评论信号`, `互动CTA`, `标签组`
3. 汇总前 10-20 条到候选池

### A.1 首页推荐流分析（新增）

按 `references/xhs-home-feed-analysis.md` 执行。

- 先看首页推荐流里“为什么推给你”
- 再提炼可复用的传播钩子、内容结构和选题方向
- 结果优先服务账号定位、选题灵感和后续内容判断

### B. 需求侧补充信号（行业/场景）

1. 按主题去主流平台/社媒抓“评论区观点分歧”
2. 抽取支持/反对/中性观点各一组
3. 输出可发文争论点（争议但可控）

### C. 形成选题清单（每轮至少 3 条）

每条选题包含：

- 选题标题（20 字内可选）
- 观点标签（支持/反对/中性）
- 预计互动钩子
- 证据来源（哪组高互动数据）
- 风险提示（是否容易踩线）

## 3.2) 选题灵感（新增）

按 `references/xhs-topic-ideation.md` 执行。

- 将平台信号、需求信号、账号定位合并成可发布选题
- 默认输出 3-5 条，每条都要带互动钩子和三段式结构
- 产物可直接作为内容生成或 Viral Copy 的前置输入

## 3.5) 搜索并浏览（新增操作类型）

按 `references/xhs-runtime-rules.md` 的搜索与评论入口章节执行。

- 只允许从搜索结果页进入帖子；
- 优先通知/回复场景前先对位校验。
- 连续失败回退策略见引用文件。

## 3.6) Viral Copy（URL → 新笔记）

按 `references/xhs-viral-copy-flow.md` 执行。

- 输入：目标爆款笔记 URL（可多条）。
- 输出：1 套可发布素材（封面/配图方案 + 标题 + 正文 + 话题）。
- 复刻原则：高贴合主题与结构（标题句式、封面信息层级、正文节奏、互动机制），同时避免逐字照抄与素材侵权。

## 4) 通用内容模板（小红书）

每次产出至少 2 个备选：

- 标题（争议/立场/反问，≤20字优先）
- 开头钩子（1-2 句）
- 正文（3 段：观点→证据→反方）
- 互动提问（1 句）
- 话题（5-8 个）
- 风险标注（是否剧透 / 引战边界 / 版权风险）

## 4.5) 图文生成（选题 → 素材包，不发布）

按 `references/xhs-image-text-gen.md` 执行。

- 输入：选题描述
- 输出：完整的小红书图文素材包（封面图 + 正文卡片 + 标题 × 3 + 正文 + 互动问句 + 话题）
- **图片生成使用本地渲染**（`scripts/render_xhs.py`），不依赖外部 API：
  1. 撰写 Markdown 文档（含 frontmatter 封面信息 + 正文内容）
  2. 调用 `python scripts/render_xhs.py content.md -t sketch -m auto-split --output-dir pic/`
  3. 自动生成：`cover.png`（封面）+ `card_1.png`、`card_2.png`...（正文卡片）
- **8 种主题**：`sketch`（手绘，默认推荐）、`playful-geometric`、`neo-brutalism`、`botanical`、`professional`、`retro`、`terminal`、`default`
- **4 种分页模式**：`separator`（手动 `---` 分页）、`auto-split`（自动拆分，推荐）、`auto-fit`（固定尺寸缩放）、`dynamic`（动态高度）
- 默认竖版 1080×1440px（3:4 比例）
- 主题样式参考：`references/xhs-card-styles.md`，完整参数：`references/xhs-render-params.md`
- **草稿持久化**：生成素材后自动保存到 `knowledge-base/drafts/`，文件含封面路径、标题、正文、话题的完整对应关系
- **本流程仅生成素材，不执行发布**；用户确认后可衔接第 5 节发布流程
- 触发语句：「帮我生成一篇小红书图文」「出一套关于 XX 的素材」「生成封面图和文案」

## 5) 通用发布链路

详细发布执行路径请直接按 `references/xhs-publish-flows.md` 执行，避免重复维护。

发布前必须满足的核心点：

- **素材来源**：优先从 `knowledge-base/drafts/` 读取最新的 `status: draft` 草稿文件，获取封面路径、标题、正文、话题的完整对应关系；若无草稿则从当前对话上下文获取。
- **草稿确认**：从草稿读取素材后，需向用户展示标题/封面/正文摘要，**用户确认后才执行发布**。
- 通过 `scripts/browser.py` 启动 Camoufox 浏览器，优先使用 profile 持久化登录态，profile 失效时降级导入 `.env` Cookie。
- 明确发布类型（视频 / 图文 / 长文），三要素：封面、标题、正文。
- 封面生成默认使用即梦API（`scripts/generate_image.py`），支持文生图和图生图两种模式，详见 `references/xhs-publish-flows.md` 1.4 节。
- **登录检测**：发布前调用 `check_login()` 检测登录态，失效时自动触发二维码登录流程。
- **发布模式**（两种，根据用户指令判断）：
  - **直接发布**（默认）：用户说「发布」「帮我发」「直接发」→ 校验三要素后直接点击发布按钮完成发布
  - **停手确认**：用户说「先看看」「预览一下」「发布前让我确认」→ 到达发布按钮处停手，截图给用户确认后再点击发布
- 发布全程通过 Camoufox 反指纹浏览器执行，详见 `references/xhs-publish-flows.md` 1.5 节。
- **发布后更新草稿状态**：发布成功后将草稿文件的 `status` 从 `draft` 更新为 `published`。

## 6) 评论与回复（轻量）

评论检查与回复统一遵循 `references/xhs-comment-ops.md`，并结合 `examples/reply-examples.md` 作文案风格。

- 默认优先走通知页，先对位后输入后发送。
- 默认 one-send-per-turn（如无明确要求不连发）。
- 长度、隐性承诺、风控停损点等风险控制项请以引用文件为准。

## 6.5) 知识库沉淀（新增）

按 `references/xhs-knowledge-base.md` 执行。

- 总览入口固定为 `knowledge-base/README.md`
- 细分记录按类型写入 `knowledge-base/accounts/`、`knowledge-base/topics/`、`knowledge-base/patterns/`、`knowledge-base/actions/`、`knowledge-base/reviews/`
- 分析优先沉淀 `pattern` / `topic` / `review`
- 执行动作优先沉淀 `action`
- 任务结束时至少留下可检索的结论、证据、风险和下一步

## 7) 失败与修复（必须遵循）

- 自动化失败先重试一次（同策略）
- 仍失败则改道：换到“更稳妥同义路径”
- 不做无效重复动作；保留当前进度可复用，报告一次用户需手动的单一动作
- 若知识库暂时不可写，先返回结构化摘要，任务结束后补记，不阻塞主流程

## 8) 通用提取示例（Evaluate）

通用字段提取脚本示例见 `references/xhs-eval-patterns.md`。

## 9) 具体案例：陪你看剧（保留为特例）
### 使用方式

本技能主文件保留通用框架；垂直行业经验放在 `examples/` 目录，按内容类型选用：

- 先按《通用流程》跑一遍
- 再加载对应案例文件补齐行业特殊动作

当前已可用案例：

- `examples/drama-watch/case.md`（陪你看剧账号）

每个内容类型按目录组织，文件命名可为：

- `examples/<vertical>/<vertical>.md`（推荐）
- 或 `examples/<vertical>/README.md`


- `examples/lifestyle/`（待补充）
- `examples/cosmetics/`（待补充）
- `examples/fitness/`（待补充）

---

## 实操经验（持续有效）

- **统一规则：所有浏览器操作一律使用 `scripts/browser.py`（Camoufox 反指纹浏览器）**，登录态优先从 profile 持久化读取，`.env` Cookie 仅作降级兜底。
- 文字配图是稳定写入口，typed text 直接成为封面文案
- 发布话题优先用 UI 选题，不建议纯文本粘贴大量 `#话题`
- `evaluate` 批量改写富文本时，尽量少改版式，避免丢失 topic entity
- 关键步骤前保留一次快照，可用于复盘与问题定位
- 发布支持两种模式：直接发布（默认）和停手确认（用户要求时），草稿素材发布前均需用户确认
- 若出现新类型评论节奏问题，优先减少每小时回复密度而非提高频率

### 认证代码模板（编程调用必须遵循）

```python
from scripts.browser import BrowserManager, DEFAULT_PROFILES_DIR, load_env
env_vars = load_env()
bm = BrowserManager(
    profile_dir=DEFAULT_PROFILES_DIR / "xhs-default",
    humanize=True, xhs_domain="xiaohongshu.com", window=(1280, 900),
)
bm.launch_with_auth(fallback_cookie=env_vars.get("XHS_COOKIE", ""))
page = bm.page
```

**⚠️ 严禁在 `check_login()` 之前调用 `import_cookies()`** — stale cookie 会覆盖 profile 里还有效的登录态，导致每次都要重新登录。

### 创作后台发布关键技术点（实测验证 2026-04）

- **创作后台默认 tab 是「上传视频」**，必须先切换到「上传图文」才能发布图文笔记
- **创作后台 DOM 交互必须用 `page.evaluate()` JS 方式**：Playwright 原生 `.click()` / `.fill()` 在创作后台会因视口外/遮罩问题超时。唯一例外是 `input[type="file"]` 的 `set_input_files()` 可直接使用
- **正文编辑器是 ProseMirror (TipTap)**：`.fill()` 无效，必须用 `keyboard.type()` 逐字输入 + `keyboard.press("Enter")` 换行
- **标题输入框必须用 JS nativeInputValueSetter + dispatchEvent**：`.fill()` / `.click()` 均可能超时
- **发布按钮用 JS 遍历 button 匹配文本点击**：按钮文本为「发布」或「发布笔记」
- **窗口建议 1280×900**：太小会导致更多元素 outside viewport
- **操作间必须 sleep**：tab切换(3s)、封面上传(10s)、正文输入(2s)、发布按钮(10s)
- **发布成功标志**：URL 变为 `?published=true`
- 详细选择器和代码模板见 `references/xhs-publish-flows.md` 1.5 节

## 运营成熟路径（可选）

- 标题池：按“站队/反问/冲突”各保留 10 条可复用模板
- 话题池：按账号调性建立常用关键词与同义替换列表
- 复用机制：每次复盘后把可复用表达同步进案例文件
