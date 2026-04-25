# XHS Publish Flows

本文件拆分并细化「发布链路」的操作步骤，供 `SKILL.md` 按需引用。

## 0. 总览

发布类型：
- 视频
- 图文
- 长文

三要素（发布前必须齐全）：
1. 封面
2. 标题
3. 正文

### 0.1 素材获取（发布前第一步）

发布前先确定素材来源：

1. **草稿文件（优先）**：读取 `knowledge-base/drafts/` 下最新的 `status: draft` 文件，从中提取封面路径、标题、正文、话题
2. **对话上下文**：若无草稿文件，从当前会话中获取刚生成的素材包
3. **用户指定**：用户说"发布 XX 那篇"时，按关键词搜索 `knowledge-base/drafts/` 匹配

发布完成后，更新草稿文件的 `status` 为 `published`。

## 0.2 登录状态检测（发布前必做，Profile-First）

发布流程开始前，按以下优先级检测登录状态：

1. **Profile 优先**：`browser.py` 启动后自动检测 profile 持久化的登录态
2. Profile 有效 → 直接继续发布流程（不读取 `.env` Cookie）
3. Profile 失效 → 降级从 `.env` import `XHS_COOKIE`，再次检测
4. 两者均失效 → 自动触发二维码登录：
   - 调用 `bm.screenshot_qrcode("/tmp/xhs-qrcode.png")` 截图二维码
   - 将截图路径返回给用户，提示扫码
   - 调用 `bm.wait_for_login()` 等待扫码完成
   - 登录成功后 profile 自动持久化，可选 `export_cookies()` 备份到 `.env`
   - 继续发布流程

## 0.3 发布模式（二选一）

根据用户指令判断使用哪种发布模式：

| 模式 | 触发词 | 最后一步行为 |
|------|--------|------------|
| **直接发布**（默认） | 「发布」「帮我发」「直接发」 | 校验三要素后直接点击发布按钮 |
| **停手确认** | 「先看看」「预览一下」「发布前让我确认」「审一下」 | 到达发布按钮处停手，截图给用户确认后再点击 |

以下流程中最后一步统一写为「**执行发布动作**」，具体行为取决于上述模式。

## 1. 图文发布（推荐默认）

### 1.0 CLI 一键发布（首选方式）

**优先使用 CLI 命令发布**，不需要自己写 Python 脚本：

```bash
# 直接发布
python scripts/browser.py publish \
    --cover "pic/cover.png" \
    --title "你的标题" \
    --body "第一行\n第二行\n#话题1 #话题2"

# 预览不发布（填完内容后停手，截图给用户确认）
python scripts/browser.py publish \
    --cover "pic/cover.png" \
    --title "你的标题" \
    --body "正文内容\n#话题" \
    --dry-run
```

CLI `publish` 内部自动处理：Profile-First 认证 → 切换到上传图文 tab → 上传封面 → JS 填标题 → ProseMirror 填正文 → 点击发布。

### 1.1 上传图文（普通）
1. 打开发布页并进入「上传图文」
2. 上传首图/多图
3. 填写标题（建议 <=20 字）
4. 填写正文
5. 追加话题/标签（放正文末尾）
6. 校验三要素后 **执行发布动作**

### 1.2 图文-文字配图（大字报）
1. 进入「上传图文」
2. 点击「文字配图」
3. 输入封面大字报文案
4. 点击「生成图片」
5. 在模板页选择样式并点「下一步」
6. 进入编辑页填写：标题、正文、话题/标签
7. 校验三要素后 **执行发布动作**

### 1.3 图文半程预发（不发布）
满足以下条件即视为“半程预发完成”：
- 已完成封面生成（或上传）
- 已进入编辑页
- 已填写标题与正文
- 仅停在「发布」按钮可见处，未点击发布

### 1.4 图文上传（本地渲染封面 + 正文卡片）
适用于先用 `render_xhs.py` 生成图片卡片，再走图文发布的场景。

前置说明：使用项目内置 `scripts/render_xhs.py` 渲染封面和正文卡片。
渲染命令示例：
```bash
python scripts/render_xhs.py content.md -t sketch -m auto-split --output-dir pic/
```
生成的图片存放在 `pic/` 目录下：`cover.png`（封面）+ `card_1.png`...（正文卡片）。

1. 先确认封面图已生成（推荐 PNG/JPG）
2. 若使用 browser.upload：先将图片复制到 `/tmp/openclaw/uploads`
3. 进入「上传图文」后优先点击「上传图片」
4. 上传封面图并确认进入编辑页（可见图片编辑区 + 标题/正文输入框）
5. 填写标题、正文、标签
6. 发布前强校验：
   - 标题长度建议 `<=20`（出现 `xx/20` 超限需先压缩）
   - 三要素齐全（封面/标题/正文）
7. 校验通过后 **执行发布动作**

### 1.5 Camoufox 反指纹自动发布（隐藏自动化痕迹）

适用于需要隐藏浏览器自动化指纹的发布场景，使用 `scripts/browser.py` 中的 Camoufox 方案。

**核心优势**：
- Camoufox 在 C++ 层面修改浏览器指纹，不是简单的 JS 注入，平台更难检测
- `humanize=True` 启用贝塞尔曲线鼠标移动，模拟真人操作轨迹
- 支持持久化 profile，登录态可跨会话复用
- locale 通过 C++ 引擎设置（navigator.language, Accept-Language, Intl API），无注入痕迹

#### 1.5.1 创作后台页面结构与关键选择器（实测验证）

**⚠️ 以下是经过实测验证的技术细节，务必严格遵循，否则发布会失败。**

**页面 URL**：`https://creator.xiaohongshu.com/publish/publish?source=official`

**Tab 切换**：
- 创作后台默认打开「上传视频」tab，**不是**「上传图文」
- 必须先切换到「上传图文」tab 才能发布图文笔记
- tab 元素 `<span class="title">上传图文</span>` 可能处于视口外（outside viewport），**Playwright 的 `.click()` 会超时**
- **解决方案**：使用 JS 点击绕过视口限制：
  ```python
  page.evaluate("""() => {
      const tabs = document.querySelectorAll('span');
      for (const t of tabs) {
          if (t.textContent.trim() === '上传图文') { t.click(); return; }
      }
  }""")
  time.sleep(3)
  ```

**上传封面**：
- 使用隐藏的 `input[type="file"]` 元素
- 切换到「上传图文」tab 后再上传，否则文件会上传到视频区
- 上传后需等待 **至少 8-10 秒**让服务器处理完成
  ```python
  page.locator('input[type="file"]').first.set_input_files(cover_path)
  time.sleep(10)
  ```

**填写标题**：
- 选择器：`input[placeholder*="标题"]`（placeholder 为「填写标题会有更多赞哦」）
- **⚠️ Playwright `.click()` 可能超时**（performing click action 后卡住，疑似被 overlay 遮挡）
- **解决方案**：使用 JS 原生方法设值 + 触发事件：
  ```python
  page.evaluate("""() => {
      const input = document.querySelector('input[placeholder*="标题"]');
      if (input) {
          const setter = Object.getOwnPropertyDescriptor(
              window.HTMLInputElement.prototype, 'value'
          ).set;
          setter.call(input, '你的标题');
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
      }
  }""")
  ```

**填写正文**：
- 正文编辑器是 **ProseMirror (TipTap)**：`<div class="tiptap ProseMirror" contenteditable="true">`
- **⚠️ `.fill()` 对 ProseMirror 无效**，内容不会被框架识别
- **解决方案**：先用 JS focus + click 聚焦，再用 `keyboard.type()` 逐行输入：
  ```python
  page.evaluate("""() => {
      const editor = document.querySelector('.ProseMirror[contenteditable="true"]');
      if (editor) { editor.focus(); editor.click(); }
  }""")
  time.sleep(0.5)
  for i, line in enumerate(body_lines):
      if i > 0:
          page.keyboard.press("Enter")
      if line:
          page.keyboard.type(line, delay=8)
  ```

**点击发布按钮**：
- 按钮文本可能是「发布」或「发布笔记」
- **同样可能有视口/遮挡问题**，优先使用 JS 点击：
  ```python
  clicked = page.evaluate("""() => {
      const btns = document.querySelectorAll('button');
      for (const b of btns) {
          const text = b.textContent.trim();
          if (text === '发布笔记' || text === '发布') {
              b.click();
              return text;
          }
      }
      return null;
  }""")
  ```
- 发布成功后 URL 会变为 `...?published=true`

**窗口尺寸**：
- 建议设置 `window=(1280, 900)` 避免元素超出视口
- 尺寸太小会导致更多元素 outside viewport

#### 1.5.2 完整发布代码模板

```python
import time
from pathlib import Path
from scripts.browser import BrowserManager, DEFAULT_PROFILES_DIR, load_env

env_vars = load_env()

bm = BrowserManager(
    profile_dir=DEFAULT_PROFILES_DIR / "xhs-default",
    headless=False,
    humanize=True,
    xhs_domain="xiaohongshu.com",
    window=(1280, 900),
)

try:
    # Step 0: Profile-First 认证（一行搞定）
    # launch_with_auth() 自动：检查 profile → 失效则 try fallback cookie → 都失败则报错
    bm.launch_with_auth(fallback_cookie=env_vars.get("XHS_COOKIE", ""))
    page = bm.page

    # Step 1: 打开创作后台
    bm.navigate(
        "https://creator.xiaohongshu.com/publish/publish?source=official",
        wait_until="networkidle",
    )
    time.sleep(5)

    # Step 2: 切换到「上传图文」tab（JS 点击绕过视口问题）
    page.evaluate("""() => {
        for (const t of document.querySelectorAll('span')) {
            if (t.textContent.trim() === '上传图文') { t.click(); return; }
        }
    }""")
    time.sleep(3)

    # Step 3: 上传封面（切 tab 之后再上传）
    page.locator('input[type="file"]').first.set_input_files("pic/cover.png")
    time.sleep(10)

    # Step 4: 填写标题（JS 原生设值，绕过 click 超时）
    page.evaluate("""(title) => {
        const input = document.querySelector('input[placeholder*="标题"]');
        if (input) {
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(input, title);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }""", "你的标题")
    time.sleep(1)

    # Step 5: 填写正文（ProseMirror 必须 keyboard.type）
    page.evaluate("""() => {
        const editor = document.querySelector('.ProseMirror[contenteditable="true"]');
        if (editor) { editor.focus(); editor.click(); }
    }""")
    time.sleep(0.5)
    body_lines = ["第一行", "第二行", "#话题1 #话题2"]
    for i, line in enumerate(body_lines):
        if i > 0:
            page.keyboard.press("Enter")
        if line:
            page.keyboard.type(line, delay=8)
    time.sleep(2)

    # Step 6: 发布（JS 点击绕过视口问题）
    page.evaluate("""() => {
        for (const b of document.querySelectorAll('button')) {
            const t = b.textContent.trim();
            if (t === '发布笔记' || t === '发布') { b.click(); return; }
        }
    }""")
    time.sleep(10)
    print(f"Final URL: {page.url}")

finally:
    bm.close()
```

**首次使用**：
1. 安装依赖：`pip install camoufox playwright`，然后 `python -m camoufox fetch`
2. 首次运行：`python scripts/browser.py login` 扫码登录，登录态自动持久化到 profile 目录
3. 后续启动无需重复登录，profile 会自动复用。`.env` 中的 `XHS_COOKIE` 仅作降级兜底

## 2. 视频发布

1. 进入「上传视频」
2. 上传视频文件
3. 补齐封面/标题/正文
4. 校验可见范围与设置
5. 校验通过后 **执行发布动作**

## 3. 长文发布

1. 进入「写长文」
2. 新建创作或导入链接
3. 填写长文标题与正文结构
4. 若用户目标是图文，避免误走长文链路

## 4. 常见问题与处理

### 4.1 页面结构问题
- **误入长文**：返回发布笔记，明确切回「上传图文」
- **草稿箱默认视频**：创作后台默认停在「上传视频」tab，必须先切到「上传图文」tab
- **标题超限**：出现 `xx/20` 时立刻压缩
- **只做了封面没填文案**：必须补齐标题与正文
- **封面上传到视频区**：如果没有先切换到「上传图文」tab 就上传文件，图片会被传到视频上传区域

### 4.2 Playwright 交互问题（实测踩坑）
- **元素 outside viewport（超时 30s）**：创作后台布局导致部分元素超出视口。**解决**：改用 `page.evaluate()` JS 点击，不依赖 Playwright `.click()`
- **标题 input `.click()` 卡死**：Playwright 的 `.click()` 在 performing click action 阶段永远等待。**解决**：用 JS `nativeInputValueSetter` + `dispatchEvent` 设值
- **ProseMirror 正文编辑器 `.fill()` 无效**：`.fill()` 写入的内容不被 TipTap/ProseMirror 框架识别，发布时正文为空。**解决**：用 `keyboard.type()` 逐字输入，每行之间 `keyboard.press("Enter")`
- **发布按钮点击无反应**：可能有遮罩层。**解决**：用 JS `document.querySelectorAll('button')` 遍历查找并 `.click()`
- **最后点击发布时报元素失效**：先 snapshot 刷新引用；仍失败则提示用户手动点击「发布」

### 4.3 网络与登录问题
- **创作后台需要独立登录**：`creator.xiaohongshu.com` 可能需要再次扫码，与主站 cookie 不完全通用
- **网页端详情扫码限制**：评论优先在通知页处理，必要时改 App 端
- **Cookie 不含 id_token**：QR 扫码登录导出的 cookie 可能缺少 `id_token`，但同 profile 内登录态有效（Profile-First 机制下这是首选方式）；跨 profile 需要时建议用 F12 手动获取并填入 `.env`

### 4.4 操作时序关键点
- **Tab 切换后等 3 秒**：JS 切换 tab 后页面 DOM 重新渲染需要时间
- **封面上传后等 8-10 秒**：服务端需要处理图片（压缩、生成缩略图）
- **正文输入后等 2 秒**：ProseMirror 内部 state 同步需要时间
- **发布按钮点击后等 8-10 秒**：等待服务端确认发布成功
- **窗口建议 1280x900**：太小导致元素 outside viewport 概率大增
