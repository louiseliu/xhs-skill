# XHS Viral Copy 链路（URL 输入）

目标：输入一条爆款 URL，输出“高贴合主题”的可发布新笔记（封面/配图、标题、正文、话题）。

## 标准四步流程（默认）

1. 输入爆款笔记 URL
2. 使用 `scripts/browser.py scrape` 抓取源笔记内容（标题/正文/封面/互动数据）
3. 分析爆款因素，拆解模板
4. 撰写 Markdown + 用 `scripts/render_xhs.py` 本地渲染新封面和正文卡片
5. 发布（上传图文、填写标题正文，执行发布动作）

## 1) 输入

- `source_url`：爆款笔记链接
- `copy_mode`：`style-only`（默认）| `tight`（高一致性）| `medium`（中贴合）

默认使用 `style-only`：保留原主题与互动机制，但封面只参考风格/色调/信息层级，不复用具体元素。
仅在用户明确要求“高一致性复刻”时才切换 `tight`。

## 2) 源笔记拆解（必须）

**第一步：使用 scrape 获取源笔记内容**

```bash
python scripts/browser.py scrape "SOURCE_URL" \
    --screenshot pic/source_note.png \
    --download-cover pic/source_cover.png
```

输出 JSON 包含 title、content、cover_url、images、tags、likes、collects、comments、author 等字段。

**第二步：基于抓取结果拆解**

提取并记录：
- 标题模板：年份/动作词/情绪词/句式（如“请按下确认键”）
- 封面模板：主文案、信息层级、是否多字大字报、配色
- 正文模板：开场金句、观点段数、结尾 CTA
- 互动模板：评论区动作词（如“确认”）、参与门槛
- 标签模板：核心话题与长尾话题

封面抓取规则（scrape 内部已实现，兜底时使用 evaluate）：
- scrape 命令已内置正确的轮播页封面抓取逻辑（优先 `swiper-slide-active` 排除 `duplicate`）
- `--download-cover` 可直接下载封面到本地，用于后续图生图
- 若 scrape 未能正确抓到封面，使用 evaluate 命令手动执行 JS：

```bash
python scripts/browser.py evaluate "SOURCE_URL" \
    --js "document.querySelector('.swiper-slide-active:not(.swiper-slide-duplicate) .img-container img')?.currentSrc"
```

本次实战记录（699e7680000000002801fd62）：
- 直接取第一个 `.img-container` 会抓到错误封面（常见是上一张或 duplicate）。
- 正确做法是以 `swiper-slide-active` 为准，再排除 `.swiper-slide-duplicate`。
- 已验证有效封面 key：`1040g3k031t0du6pc5s005qbtv55n7e4t2h6fqk8`（active 图）。

输出 `Source Template`（简短结构化）。

## 2.5) 本地渲染新封面和正文卡片（核心步骤）

基于源笔记拆解结果，撰写 Markdown 并用 `render_xhs.py` 本地渲染。

### Step 1：撰写渲染用 Markdown

```markdown
---
emoji: "🔥"
title: "新封面大标题（≤15字）"
subtitle: "新封面副标题（≤15字）"
---

# 第一张正文卡片内容

要点一...

要点二...

---

# 第二张正文卡片内容

...
```

### Step 2：渲染图片

```bash
python scripts/render_xhs.py content.md -t sketch -m auto-split --output-dir pic/
```

生成：`pic/cover.png`（封面）+ `pic/card_1.png`、`pic/card_2.png`...（正文卡片）

### 主题选择

根据源笔记风格选择匹配的主题：
- 简约/大字报 → `sketch`（默认推荐）或 `default`
- 活泼/几何 → `playful-geometric`
- 粗野/冲击力 → `neo-brutalism`
- 清新/自然 → `botanical`
- 专业/商务 → `professional`
- 复古/怀旧 → `retro`
- 极客/技术 → `terminal`

## 3) Viral Copy 改写规则（tight）

目标：像同一题材下的“第二篇爆款”，而不是跨主题 remix。

- 保留：
  - 同主题（不改主议题）
  - 同互动机制（如“评论区打确认”）
  - 同内容结构（标题风格、正文节奏、封面层级）
- 替换：
  - 具体措辞、案例细节、表达顺序
  - 账号人设口吻（轻量注入，不改主题）
- 禁止：
  - 逐句照抄
  - 原图二次使用
  - 原作者专属信息/隐私迁移

封面一致性控制（关键经验）：
- 当图生图结果“元素一致性过高”时，立即改为“style-only”提示词：
  - 仅参考风格、色调、信息分层与竖版构图
  - 明确禁止复用：人物姿势、图标组合、文本框形状与位置
- 使用“保留主题 + 重设计元素”策略，不要求元素一模一样。

## 4) 输出格式（一次给全）

1. 标题：3 个（其中 1 个 <=20 字）
2. 正文：1 版可直接发布
3. 封面：
   - 主文案 + 副文案
   - 1 条生图 prompt（高文字可读）
4. 配图：3-6 张图解文案 + 对应 prompt
5. 话题：5-8 个

## 5) 发布衔接

调用发布流程：`references/xhs-publish-flows.md`

- 图文上传
- 填标题正文
- 校验三要素后 **执行发布动作**（直接发布 or 停手确认，取决于用户指令）

## 6) 风险与合规

- 不承诺“必爆/保证涨粉”
- 不输出违规医疗、夸大承诺、引战内容
- 使用“结构级复刻”，避免“文本级抄袭”