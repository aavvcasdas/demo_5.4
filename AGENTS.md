# AGENTS.md · 仓库路由与契约

本仓是**网文写作工具集（oh-story-claudecode 系）+ 人生副本工具包扩展**。
主会话在 Arena Agent Mode 里**本身就是执行器**：按 [arena.runtime.json](arena.runtime.json) 逐阶段实例化角色、
加载 profile 与手艺切片、落阶段产物、过机检。运行方式见 [docs/Arena运行时.md](docs/Arena运行时.md)。

**配置文件缺失时的行为**：`arena.runtime.json` 或本文件读不到 →
报告 `BLOCKED: runtime config missing` 并给出缺失路径，**不要用主会话直接代写正文兜底**。
这两个文件曾在沙箱回滚中丢失过（`作品/80_练薄肌的人活在成都/审核报告.md` 的「环境事故披露」）。

---

## 一、按任务动作分流（先判动作，再判题材）

| 用户动作 | 关键词示例 | 走哪条 | 明确不做 |
|---|---|---|---|
| **研究 / 借鉴 / 改造 Agent** | 「看看别人的项目」「借鉴一下」「优化这个 skill」 | 只交来源、采纳的方法、接入位置与改动；落 `docs/` | **不自写样稿替代借鉴**，不擅自转成创作任务 |
| **写人生副本 / 剧本人生口播** | 「人生副本」「剧本人生」「体验某种人生」「来一篇 X 的剧本」 | `pipelines.fuben-write`：[人生副本实录.md](skills/story-short-write/references/genre-styles/人生副本实录.md)（v14）+ [fuben-craft/](skills/story-short-write/references/fuben-craft/README.md) | 不叠加普通小说 Reference Gate、付费点、十二列表格、默认篇幅、角色配额、去味清零表 |
| **审人生副本** | 「副本审稿」「口播复核」「切条验收」「看看这篇好不好看」 | [fuben-review](skills/fuben-review/SKILL.md)（按证据的定点审核/修订） | 不路由到网文配额审核；**不按 `_archived/` 旧配额验收** |
| **写短篇网文** | 「短篇」「盐言」「一万字」 | [story-short-write](skills/story-short-write/SKILL.md) Phase 1-4 | — |
| **写长篇网文** | 「开书」「写大纲」「日更」「续写」 | [story-long-write](skills/story-long-write/SKILL.md) | — |
| **拆文** | 「拆这本书」「分析黄金三章」「拆这篇短文」 | story-long-analyze / story-short-analyze → 产物落 `拆文库/{书名}/` | — |
| **扫榜** | 「长篇什么火」「短篇什么火」 | story-long-scan / story-short-scan | — |
| **导入已有小说** | 「把我的书导进来」「反向解析」 | story-import | — |
| **去 AI 味（普通网文）** | 「这篇太 AI 了」 | story-deslop | 人生副本走 fuben-craft 的 §口播腔调，不走普通小说的句式清零 |
| **封面 / 制作 / 发布** | 「做个封面」「出成片」「发布」 | story-cover；媒体与发布证据阶段仅在用户要求后进入 | 不代发；工具通过不等于账号主授权或平台通过 |

**分流优先级**：人生副本 / 剧本人生 / 第二人称体验类口播，或项目根有
`.fuben.json` = `{"schema_version":1,"profile":"fuben"}` → 立即进副本分支，该分支到此结束。
`story-deslop` 与 `story-review` 的 SKILL.md 开头都有「人生副本早期分流」段，指向 `fuben-review`。

---

## 二、人生副本的执行契约（最常走错的一条）

1. **真实调用**：所有正文、续写、重写、试写及候选片段必须由角色文件对应的实际执行产出。
   读过 SKILL.md、存在 Agent 模板、复制部署文件、运行检查脚本，**都不等于调用了创作 Agent**。
2. **阶段产物即证据**：`作品/NN_主题/_运行/00~05`。缺阶段产物 = 调用未发生，不得声称走了管线。
3. **阶段 01 的硬门**：必须含 ①同型样本清单 + 借用的机制名（`拆文库/NN` + 手法名）
   ②一次并行多路真实搜索（≥8 路，单批并发，留批号、检索词、来源、取用的质感）
   ③3–4 个分类型剧情方向 ④**用户选定结果**。用户裁决：不调用搜索即任务失败；未经选定方向不得动笔
   （用户授权「你定」时由主控代选并记录理由）。
4. **手艺切片按需下发**：见 [人生副本_Agent方法.md §2「带什么给主笔」](skills/story-short-write/references/genre-styles/人生副本_Agent方法.md)。
   不把整个 fuben-craft 转发给每个角色。
5. **返工分层**：结构→重构 / 场面→展开 / 表达→局部修。顺序不可换，
   **不许把结构问题降格成换词或清句式**。
6. **版本绑定**：`审核报告.md` 必须写 `body_path` 与 `body_text_sha256`；正文一改，旧结论只能是
   `STALE/PROVISIONAL`。`scripts/fuben_loop.py review` 会把未绑定或过期的报告显式报出来。
7. **主题边界**：以用户题面为准。题面是人生，题材元素（游戏、健身、方言梗）只能做质感与道具，不能抢主线。
8. **机检不是批准**：`scripts/fuben_run.py` 的 PASS 只说明无机械阻断。
   `scripts/fuben_craft_scan.py` 是只读的读感扫描，输出带行号的候选，**永不 BLOCK，不计入创作结论**。

---

## 三、目录地图

```
skills/                     14 个 Skill（story 路由 + 13 个专项）
  story-short-write/references/
    genre-styles/人生副本实录.md            ← 副本 profile v14（入口）
    genre-styles/人生副本_Agent方法.md       ← 角色分工与手艺切片下发
    genre-styles/人生副本_通用骨架.md        ← 卡住时的排障问答
    genre-styles/_archived/                 ← 旧配额包，史料，不加载
    fuben-craft/                            ← 手艺层（v14 新增）
      README.md                             加载表 + 用法纪律
      开场与钩子.md                          六种开场模板 + 段内钩子五型
      笑点机制.md                            九种笑点引擎 + 剂量安全线
      侧面与共情.md                          共情翻译器三通道 + 侧面四型
      爽点兑现.md                            四拍结构 + 绝杀台词产品化
      结构与曲线.md                          十大志 + 曲线 + 六段公式
      口播腔调与反AI味.md                    行节奏 + 12 条 slop + 保留清单 + 5 维评分
      样本索引.md                            写什么题读哪几篇
  fuben-review/                             副本审核（创作判据 + 读通专项 + 事实底线）
scripts/                    fuben_* 机检与数据工具；fuben_craft_scan.py 只读读感扫描
拆文库/                     语料库：45 篇写作手法 + 情节节点 + 54 篇原文（手艺层的数据源）
作品/                       成稿与 _运行/ 阶段产物、_regression/ 红绿样
tests/                      test_fuben.py（60 项）、test_fuben_trial.py、protected_sources.json
evaluations/                对照实验设计与冻结规则（史料，不加载执行）
docs/                       Arena运行时.md、短视频Agent借鉴.md、skill诊断与优化_2026-09-23.md
```

---

## 四、诚实边界（所有 Skill 共用）

- 独立外部审读目前不可用；审读由主会话以审读角色在独立步骤执行，产物注明 `solo`，
  **不冒充多 Agent 会审、不虚构会话 ID**。
- 没有真实观众偏好或平台反馈时，不许报「必爆」「恢复原作水平」或虚构胜率。
- 字数估时（6.4 字/秒）是工具默认估值，不是配音实测；没有音视频不声称听感或画面已验证。
- 工具缺失或失败记 `ERROR`，如实说明，**不退回估算后说通过**。
- 发布任务才填 `.发布证据.json`；模板中的 `UNVERIFIED` 不能未经实际复核改成 `APPROVED`。最终确认属于账号主。

---

## 五、部署到别的项目

人生副本工具包尚未发布到上游，上游重装命令不能替代或覆盖当前修复版。
经用户授权部署到另一个项目时，从**本仓根**显式运行：

```bash
python3 skills/story-setup/scripts/deploy-fuben-tools.py --dest /path/to/project
```

分发 skills 时包含 `fuben-review` 这个第 14 个 Skill；旧 13 个宿主 command 文件不等于 14 个 Skill。
不要声称只复制 SKILL.md 就安装了脚本。已经部署过的项目需通过原有 `story-setup` 同步模板。
