# AGENTS.md — Arena · 人生副本可拍剧本（skill 项目）

本仓库是**由 skill 驱动的抖音「人生副本／剧本人生」短剧本创作项目**（v3.0，2026-09-29 从「口播逐字稿」换代为「旁白驱动·可拍剧本」）：`skills/` 为创作与治理 skill，`拆文库/` 为 45 篇赛道原稿的拆解（语感与手法蒸馏源，受保护只读），`作品/` 为产出（`剧本.md`＋`旁白.md`），`scripts/` 为**只留能真出错那部分**的机检工具。按用户意图路由：

| 用户意图 | 路由到 | 说明 |
|---|---|---|
| 写人生副本可拍剧本（人生副本、剧本人生、XX 的一生、副本改剧本、第二人称人生体验） | [skills/fuben-write/SKILL.md](skills/fuben-write/SKILL.md) | **主链路（v3.0）**：真实检索（≥8 路）＋选题三闸 → 分场表（5–8 场）→ `剧本.md`（画面/旁白/对白/秒数）＋`旁白.md` → 划走点三扫三问 → 交付剧本＋配音轨＋发布包 |
| 审人生副本剧本（副本审稿、剧本读通、切条前复核） | [skills/fuben-review/SKILL.md](skills/fuben-review/SKILL.md) | 三扫（衔接/密度/念不出来）＋可拍三问，🔴🟡🟢 分级；**不再要求哈希绑定与闭环销账表** |
| 写多集真人短剧/漫剧剧本、分镜、图片视频提示词 | [.agents/skills/short-drama-write/SKILL.md](.agents/skills/short-drama-write/SKILL.md) | 上游 zenstory-ai/drama-skills（MIT，2.4k★）。**单条人生副本不走这条**；它管 EP/SC 格式、资产与制作链。要下游（分镜表/提示词）时转过去，不在本仓复刻 |
| 造/改 skill、体检技能库 | [.agents/skills/skill-creator/SKILL.md](.agents/skills/skill-creator/SKILL.md) | 描述瘦身、单一职责、查重与瘦身标准 |
| 写普通短篇/长篇网文、拆书、扫榜、去 AI 味、封面、导入 | [skills/story/SKILL.md](skills/story/SKILL.md) | 网文工具箱路由（小说口径；人生副本不走此线） |
| 部署/同步环境 | [skills/story-setup/SKILL.md](skills/story-setup/SKILL.md) | 模板与 hooks 部署（`KNOWN_SKILLS` 清单由测试绑定，勿随意增删 `skills/` 目录） |
| 浏览器采集 | [skills/browser-cdp/SKILL.md](skills/browser-cdp/SKILL.md) | CDP 抓取 |
| 研究/借鉴/改造 Agent | 只交方法与接入改动 | 不自动转成样稿 |
| 查找/安装新能力 | [.agents/skills/find-skills/SKILL.md](.agents/skills/find-skills/SKILL.md) | `npx skills find <词>`；沙箱内 curl 直连 skills.sh 会 SSL 失败，走 `https://skills.sh/api/search?q=<词>` 兜底 |
| 会话交接打包 | [.agents/skills/handoff/SKILL.md](.agents/skills/handoff/SKILL.md) | 把当前会话压成 handoff 文档给下个 agent |

## 剧本管线（fuben-write v3.0）

```text
00 简报（题面+时长档）→ 01 检索≥8路+选题三闸+方向卡(用户选定) → 02 分场表（5–8 场：事件/画面主体/旁白字数/对白句数/秒数/钩点）
→ 03 成稿：剧本.md（首行即钩＋每场必有 画面： 行＋旁白驱动）→ 抽 旁白.md
→ 04 划走点三扫（衔接/密度/念不出来）＋可拍三问 → 🔴🟡🟢 处置 → 分层返工
→ 05 机检（fuben_run full + fuben_craft --ledger，可选落 05_机检.json）→ 交付：剧本+旁白+钩子备选+发布包
```

**v3.1 增补（2026-09-29，作品 88 初稿被用户判"数词太多、远不如 87"）**：可念轨数字串 ≤70/千字、量词数串 ≤20/千字（只数带记账单位的量词：年/次/块/元/斤/千卡/节/顿…；「一个·一样·一下」这类虚指不计）、同一数复现 ≤3 次、装饰性时间词 ≤2 次；审读从三扫改**四扫**（新增"数词与比喻"）；规则是"能算的账只留一处、其余数字写进画面单据"与"一篇只养一个比喻"，来源里的上限不得当等号用。

**v3.0 契约（用户裁决原话：「审核脚本删到会咬人就行」）**：①主交付是**能拍的剧本**——`## 场N（地点·日夜·25—45 秒）` ＋ `画面：` ＋ `旁白：` ＋ `角色（提示）：台词`，标签集封闭（不自造）；②**体量下限恢复为门禁**：终稿旁白轨 <700 字＝`VOLUME_UNDER_FLOOR`（REVIEW），上限仍自由（policy `volume_authorization`）；③**旁白驱动可机检**：剧本形态按标签行数占比，对白 >25% 报 `VO_TRACK_OVER`，并取消旧版「<800 字对白统计归零」的豁免（v2.0 把稿子压到 600 字级正好落进免检区）；④可拍性检查 `SCENE_NO_VISUAL`/`SCENE_SPARSE`/`SCENE_OVER`；⑤**退役审核剧场**：删除产物齐备门禁、审核报告哈希绑定、发布前证据、数关键词的结构自评、兑现认领对表（见 `arena.runtime.json` 的 `project.retired_in_v3`）。换代诊断与赛道证据见 [docs/剧本化改造诊断-2026-09-29.md](docs/剧本化改造诊断-2026-09-29.md)。

**保留不动的红线**：真实检索（≥8 路、逐路表、不调用即任务失败）、选题三闸一票否决、未获用户选定方向不写正文、全程无烟、账目可反算、不报「必爆」、不编造来源与授权、发布带「剧情为虚构演绎」声明、发布后数据回填台账。

**过程文件是脚手架**：`_运行/YYYY-MM-DD/00–04` 每份 ≤80 行，正文（剧本.md）的预算优先于自证；**不许用文档长度证明工作质量**（v2.0 的 87 篇：审读文档 4000+ 字，正文 617 字）。一次只写一场（≤35 行）再回读；`5–12 字一行` 是情绪钉子的语感，**不是把一句话拆成三行的许可**（对标每行≈9.3 汉字，机检 INFO 报「每行汉字」）。

阶段产物与交付文件名以 [arena.runtime.json](arena.runtime.json) 为准（旧作品仍叫 `02_场次单.md`/`04_审读与返工.md`/`正文.md`，机检按 `旁白.md → 正文.md` 回落，不必回填改名）。运行说明见 [docs/Arena运行时.md](docs/Arena运行时.md)。

## scripts/ 分工（v3.0 瘦身后）

| 创作日常（只这两个） | 库级治理（不碰单篇） |
|---|---|
| `fuben_run.py <作品> --profile full` 红线/禁词/开头/对白占比/账目/体量/可拍性/**数字预算**（数词密度·同数复现·装饰时间词） | `fuben_health.py` 全库体检（`test_gates.py --works --corpus` 调用） |
| `fuben_craft.py <剧本或旁白> --ledger` 数字判词链对账全表 | `fuben_corpus.py` 受保护语料只读校准（工具行为标定） |
| `fuben_data.py record|report` 发布后真实数据回填（严格 schema） | `skills_audit.py [--strict|--json]` 技能库体检：体积/描述预算/重复/触发冲突/坏链 |
| `fuben_shotmap.py`／`fuben_density.py`／`fuben_hype.py` 描述性读数（不设卡、不判好坏） | `test_gates.py` 仓库健康总入口（unittest + works + corpus 证据） |

- 描述性工具不判「水」、不判剧情质量：**同一条纪律适用于「水」和一切启发式打分**（本仓已退役过两个：`check_fuben_texture.py` 与平铺扫描器——在 48 篇原稿上标定发现原稿自身「零推进跨度」中位 38.5%，判据无区分度）。水由 04 人工点名＋场号，脚本只查在场性之外真正会出错的东西。
- 已删除（2026-09-29）：`fuben_viral.py`、`fuben_products.py`、`fuben_loop.py`、`fuben_release.py`、`fuben_scene_check.py`、`fuben_claims.py`、`fuben_lint.py`、`corpus_gate_audit.py`。别再写回来：能数关键词的「✅」只会让人少改稿。

## 技能库卫生

- **先查重再新建 skill**（功能重叠优先并入现有 skill）；description **≤150 字符、触发词前置**；一个 skill 只接一件事；主体超 500 行就下沉 references。常驻 listing 有预算（Claude Code 默认按上下文 1%≈1,600 字符），超预算按调用频次**整条丢描述**——被丢描述的 skill 只剩名字、不再触发。
- 触发词分工：「人生副本／剧本人生／XX 的一生」→ `fuben-write`；「短剧／漫剧／EP」多集与制作链 → `short-drama-write`；「审副本／剧本读通」→ `fuben-review`。跑 `python3 scripts/skills_audit.py` 看当前重叠与坏链。
- 现状（2026-09-29 体检）：19 个 skill（在用 14＋归档 5）、464 文件、5.14 MB；**常驻描述合计约 2270 字符 > 预算 ≈1600**。本轮两条主链描述已压到 81／58 字符；仍超 150 的是 `browser-cdp` 389、`skill-creator` 319（上游原文）、`story-short-analyze` 308、`story-setup` 216、`story-review` 152——待办是逐条瘦身，不是再装新 skill。已知触发冲突：「剧本」`short-drama-write`↔`fuben-write`（分工见上表，边界已写死）；完整数据：`python3 scripts/skills_audit.py`。
- 第三方 skill 只落 `.agents/skills/`，**不要在 `skills/` 里留软链**（`skills/*/SKILL.md` 是 `story-setup` 的部署清单，`test_gates` 断言它等于 `deploy-antigravity-skills.py` 的 `KNOWN_SKILLS`）。
- 多份拷贝是**故意的**：`test_distributed_sources_are_identical` 强制 `check-ai-patterns.js`、`story-profile.js`、`story_hook_core.js` 各拷贝逐字节一致（每个 skill 要能独立部署）；改一处必须同步全部。
- 归档区：`skills/_archive/`（低频、不路由、文件保留），恢复方式见 [skills/_archive/README.md](skills/_archive/README.md)。

## 手艺与事实边界

- 创作标准以 [references/0_剧本格式与分场表.md](skills/fuben-write/references/0_剧本格式与分场表.md)（体裁契约）＋[2_选题与结构.md](skills/fuben-write/references/2_选题与结构.md)（三闸＋爽点四段＋分场）＋[3_口播与节奏.md](skills/fuben-write/references/3_口播与节奏.md)（三秒／翻面／行宽／体量）＋[5_代入感与禁忌.md](skills/fuben-write/references/5_代入感与禁忌.md)（旁白驱动与红线）为核心；对标语感读 `拆文库/*/写作手法.md` 与 `原文/原文.txt`。
- 保留用户给定事实；检索来源注明；不编造数据与授权；不报「必爆」；机检 PASS 只说明无机械阻断，审读意见只说明有人读过并点了位置——**两者都不是流量预测**。
- 独立可复制提示词（不装 skill）：[skills/fuben-write/references/6_独立提示词.md](skills/fuben-write/references/6_独立提示词.md)。
