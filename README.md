<!--
  xhs-skill README
-->

# xhs-skill

小红书自动运营 Skill，搭配 Openclaw 可以独立运营小红书账号，帮你分析、选题、创作、复盘、复刻。

基于 Camoufox 反指纹浏览器（CDP），首次扫码登录后 profile 持久化，后续无需重复验证。

## 核心能力

- ✅ **图文生成**：输入选题，本地渲染封面+正文卡片（8 种主题），组装完整素材包
- ✅ **一键发布**：CLI 命令直接发布图文笔记（`browser.py publish`）
- ✅ **首页推荐流分析**：分析推荐内容的传播钩子和内容结构
- ✅ **账号分析**：分析账号定位，不同笔记之间的差异，为什么某些笔记赞更多
- ✅ **选题灵感**：结合知识库、账号定位，提供选题灵感
- ✅ **知识库沉淀**：分析结果和动作自动保存为 Markdown，便于复盘复用
- ✅ **爆款笔记复刻**：输入爆款笔记 URL，分析爆款因素，生成类似素材
- ✅ **自动回复评论**：检查新评论并按人设语气回复
- ✅ **人设管理**：`persona.md` 控制账号定位和回复语气

## 安装

```bash
# 方法1: Openclaw / Codex 安装
帮我安装这个skill，`https://github.com/louiseliu/xhs-skill`

# 方法2: Clawhub 安装
clawhub install xhs-skill
```

安装后首次运行需扫码登录：

```bash
python scripts/browser.py login
```

## 常用命令

```bash
# 检查登录状态
python scripts/browser.py check

# 渲染图文卡片（Markdown → 封面+正文卡片 PNG）
python scripts/render_xhs.py content.md -t sketch -m auto-split --output-dir pic/

# 发布图文笔记
python scripts/browser.py publish --cover pic/cover.png --title "标题" --body "正文\n#话题"

# 抓取笔记内容
python scripts/browser.py scrape "URL" --download-cover pic/cover.png

# 打开 URL 并截图
python scripts/browser.py open "URL" --screenshot pic/screenshot.png
```

## 仓库结构

```
xhs-skill/
├── SKILL.md                    # 技能主逻辑与执行规则
├── persona.md                  # 人设/语气/回复风格
├── scripts/
│   ├── browser.py              # Camoufox 反指纹浏览器（登录/发布/抓取）
│   ├── render_xhs.py           # 本地图文渲染（8 主题 + 4 分页模式）
│   └── render_xhs_v2.py        # 渲染 V2（渐变色彩风格备用）
├── assets/
│   ├── cover.html              # 封面 HTML 模板
│   ├── card.html               # 正文卡片 HTML 模板
│   ├── styles.css              # 公共样式
│   └── themes/                 # 8 种主题 CSS
├── references/
│   ├── xhs-image-text-gen.md   # 图文生成链路（选题→素材包）
│   ├── xhs-publish-flows.md    # 发布流程拆解
│   ├── xhs-viral-copy-flow.md  # 爆款复刻流程
│   ├── xhs-runtime-rules.md    # 运行时规则（认证/浏览器）
│   ├── xhs-render-params.md    # 渲染参数完整文档
│   ├── xhs-card-styles.md      # 主题样式预览
│   └── ...                     # 其他 SOP 文档
├── knowledge-base/             # 知识库（分析结果/动作记录）
└── examples/                   # 垂直场景案例
```

## 图文渲染主题

| 主题 | 风格 | 适用场景 |
|------|------|----------|
| `sketch` | 手绘素描 | 默认推荐，大字报/观点类 |
| `playful-geometric` | 活泼几何 | 轻松/趣味话题 |
| `neo-brutalism` | 粗野主义 | 冲击力强/态度鲜明 |
| `botanical` | 植物清新 | 生活/自然/养生 |
| `professional` | 专业商务 | 职场/知识/教程 |
| `retro` | 复古怀旧 | 回忆/文化/情怀 |
| `terminal` | 极客终端 | 科技/编程/数码 |
| `default` | 简约灰 | 通用 |

## 认证机制

采用 Profile-First 策略，登录态持久化到 `~/.xhs-skill/profiles/xhs-default/`：

1. 首次使用：`python scripts/browser.py login` 扫码登录
2. 后续使用：profile 自动复用，无需重复登录
3. Session 过期：自动降级尝试 `.env` 中的 `XHS_COOKIE`（如有）
4. 都失效：提示重新扫码

## 依赖

```bash
pip install camoufox[geoip] markdown pyyaml playwright
playwright install chromium
```
