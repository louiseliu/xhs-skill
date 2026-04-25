# xhs-skill Smoke Test

## 测试环境
- Browser: OpenClaw 内置浏览器 / Camoufox 反指纹浏览器
- Profile: `openclaw`（默认）/ Camoufox persistent profile（反指纹模式）
- 站点: `https://www.xiaohongshu.com`
- 生图: 即梦API（jimeng-4.5，localhost:5100）
- 测试方式: 手工执行最小闭环

---

## 一、分析类功能（2026-03-19）

### 1. ✅ 首页推荐流分析
- 执行：采样首页推荐流，抓取高赞样本及标题钩子
- 产物：`knowledge-base/patterns/2026-03-19-home-feed-openclaw-sample.md`

### 2. ✅ 账号分析
- 执行：打开账号主页并采样账号信息/近帖表现
- 产物：`knowledge-base/accounts/2026-03-19-account-analysis-nannantech.md`

### 3. ✅ 选题灵感
- 执行：结合首页信号 + 账号定位生成 5 条选题
- 产物：`knowledge-base/topics/2026-03-19-topic-ideas-ai-creator.md`

### 4. ✅ 知识库沉淀
- 执行：按类型写入 patterns/accounts/topics/actions
- 产物：`knowledge-base/actions/2026-03-19-smoke-test-4-features.md`

### 过程问题与修复
- 问题：`browser click <ref>` 因页面刷新导致 ref 失效，出现 timeout。
- 修复：改为 `browser navigate <user_profile_url>` 继续流程，测试通过。

---

## 二、图文生成（2026-04-13）

### 5. ✅ 图文生成（选题 → 素材包，不发布）
- 选题输入：「AI 龙虾」
- 执行流程：
  1. 内容策划：生成 3 个备选标题 + 正文（虾薯人设语气）+ 互动问句 + 7 个话题
  2. 封面设计：构建赛博朋克龙虾 prompt，竖版 3:4
  3. 即梦API 生图：调用 jimeng-4.5，`--ratio "3:4" --resolution "2k"`
  4. 素材组装：完整素材包输出
- 产物：
  - `pic/jimeng_20260413_080238_1.png`（封面图 1）
  - `pic/jimeng_20260413_080238_2.png`（封面图 2）
  - `pic/jimeng_20260413_080238_3.png`（封面图 3）
  - `pic/jimeng_20260413_080238_4.png`（封面图 4）
- 文案产物：
  - 标题推荐：「当龙虾学会了赛博朋克」
  - 正文：虾薯人设语气，含互动收尾
  - 话题：#AI绘画 #即梦AI #赛博朋克 #龙虾 #AI生成 #小红书封面 #数字艺术
- 耗时：生图约 57 秒，整体流程约 2 分钟
- 状态：素材生成完毕，**未执行发布**

### 6. ✅ 即梦API 连通性
- API 地址：`http://localhost:5100`
- 模型：jimeng-4.5
- 认证方式：Session ID（Bearer Token）
- 状态：正常返回 4 张图片

---

## 三、Camoufox 反指纹发布（2026-04-13）

### 7. ⬜ Camoufox 反指纹发布（待测试）
- 预期流程：
  1. 使用 `scripts/browser.py` 启动 Camoufox 浏览器
  2. 持久化 profile 自动复用登录态
  3. humanize 贝塞尔曲线鼠标模拟
  4. 上传图文 + 填写标题正文 + 执行发布动作（直接发布 or 停手确认）
- 前置条件：`pip install camoufox playwright && python -m camoufox fetch`
- 待测环境确认后执行

---

## 结论
- 分析类 4 个功能（03-19）已跑通 MVP
- 图文生成流程（04-13）已跑通：选题→即梦API生图→素材包产出→不发布
- Camoufox 反指纹发布待实际环境测试
- Nano Banana 已全量替换为即梦API（jimeng-api）
