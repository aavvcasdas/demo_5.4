# AGENTS.md — 本仓库 Skill 路由入口

本仓库是抖音「人生副本/剧本人生」口播稿生成库：`skills/` 为创作与工具 skill，`拆文库/` 为 39 个故事段（另收 28b、46、48a–c 补充原文与 00 合集本体，共 45 个目录）ASR 原稿拆解（写作手法蒸馏源），`作品/` 为产出，`scripts/` 为机检工具。按用户意图路由：

| 用户意图 | 路由到 | 说明 |
|---|---|---|
| 写人生副本口播稿（人生副本、剧本人生、XX 的一生、口播稿、第二人称人生体验） | [skills/fuben-write/SKILL.md](skills/fuben-write/SKILL.md) | **主链路**（v1.3.4，含共鸣元素+大额校验+口播读感四教律+数据回传台账）。深读+真实检索（≥8 路）→方向卡→场次单→反流水账成稿→审读返工（账目+对话+红线）→机检候选闭环→交付逐字稿 |
| 审人生副本（副本审稿、口播复核、切条验收） | [skills/fuben-review/SKILL.md](skills/fuben-review/SKILL.md) | 创作审查＋读通专项，报告绑定 `body_path` 与 `body_text_sha256` |
| 写中文短剧/漫剧剧本、改单集剧本、剧本审读 | [.agents/skills/short-drama-write/SKILL.md](.agents/skills/short-drama-write/SKILL.md) | 2026-09-28 新装（zenstory-ai/drama-skills，MIT）。管短剧剧本格式与可拍性，不管资产/分镜/媒体提示词；人生副本口播仍走 `fuben-write` |
| 造/改 skill、体检技能库 | [.agents/skills/skill-creator/SKILL.md](.agents/skills/skill-creator/SKILL.md) | 2026-09-28 安装（anthropics/skills，39.2 万安装）。描述瘦身、单一职责、查重与瘦身标准 |
| 写普通短篇/长篇网文、拆书、扫榜、去 AI 味、封面、导入 | [skills/story/SKILL.md](skills/story/SKILL.md) | 网文工具箱路由（小说口径；人生副本不走此线） |
| 部署/同步环境 | [skills/story-setup/SKILL.md](skills/story-setup/SKILL.md) | 模板与 hooks 部署 |
| 浏览器采集 | [skills/browser-cdp/SKILL.md](skills/browser-cdp/SKILL.md) | CDP 抓取 |
| 研究/借鉴/改造 Agent | 只交方法与接入改动 | 不自动转成样稿 |
| 查找/安装新能力 | [.agents/skills/find-skills/SKILL.md](.agents/skills/find-skills/SKILL.md) | 技能生态入口：`npx skills find <关键词>` → 核安装量/来源 → `npx skills add` |
| 会话交接打包 | [.agents/skills/handoff/SKILL.md](.agents/skills/handoff/SKILL.md) | 把当前会话压成 handoff 文档给下个 agent；最新一份在 `/home/user/handoff-2026-09-25d-fuben-85.md` |

## 人生副本管线（fuben-write）

```text
00 简报 → 01 深读+检索(≥8路并行)+剧情方向卡(含开场方向,用户选定) → 02 场次单
→ 03 首稿(钩子备选 A/B/C 同批写出+正文分段直写,反流水账八件武器)
→ 04 审读(追看断点/念稿测试/账目对账)+分层返工(修正常项,非默认步)
→ 04b fuben-review 读通专项 → 05 机检+工艺门禁(PASS≠好看,候选须闭环) → 交付
```

**首稿质量优先**：目标是一次写对、审读只做减法；不许把审读当默认兜底。`03_初稿.md` 同批产出钩子备选（最终定稿落根目录 `钩子备选.md`），不是跑完机检后再补写。成稿纪律：一次生成 ≤35 行就停手回读，逐段推进；长中文一次性生成易漂移。`5–12 字一行` 是口播体裁指纹（语感指引），**没有任何机检对行长设卡**；写作纪律自定行宽可以，但不要误当技能规则。

阶段产物落 `作品/NN_主题/_运行/YYYY-MM-DD/`（同名阶段产物按 [arena.runtime.json](arena.runtime.json) 的 `product` 字段，用 `python3 scripts/fuben_products.py 作品/NN_主题` 验收）；不调用真实搜索即任务失败（用户裁决）；未获用户选定方向不得开写正文。`fuben_run` 默认含 craft 门禁（无烟红线/禁词/开头铁律/对白限额/账目档位/体量带；`fuben_craft --ledger` 出账目全表）；`facts`/`policy` 类候选在审读阶必须逐条销账。运行说明见 [docs/Arena运行时.md](docs/Arena运行时.md)。

**scripts/ 分工**（创作期只调左列三个；右列是库级治理，不碰单篇）：

| 创作日常 | 库级治理（不碰单篇） |
|---|---|
| `fuben_run.py <作品> --profile full` 主检查（facts/style/account/policy/craft） | `fuben_health.py` 全库体检（`test_gates.py --works --corpus` 调用） |
| `fuben_craft.py <作品> --ledger` 工艺门禁 + 账目主张全表 | `fuben_corpus.py` 受保护语料只读校准（工具行为标定） |
| `fuben_products.py <作品>` 产物齐备/哈希绑定门禁 | `corpus_gate_audit.py` 语料反审（R20 专用，自报不兼容现行协议） |
| `fuben_loop.py report|review <作品>` 报告生成/回读绑定 | `test_gates.py` 仓库健康总入口（unittest + works + corpus 证据） |
| `fuben_release.py check <作品>` 发布前证据（PROVISIONAL 不代发） | `fuben_lint.py` engine 的旧别名（facts+style+account 子集，供旧调用方） |
| — | `skills_audit.py [--strict|--json]` 技能库体检：体积/描述预算/重复/触发冲突/坏链 |

描述性工具（读稿参考，不设卡）：`fuben_density.py`（数字密度）、`fuben_hype.py`（节奏统计）。`check_fuben_texture.py` 已退役删除：启发式质地判据失准（对白占比、ASCII 价格正则等会误报），其有用项已并入 craft/style 门禁。

## 技能库卫生（2026-09-28 起）

- 现状（2026-09-28 体检后）：在用 14 个 skill + 归档 5 个（`skills/_archive/`）、462 文件、5.16 MB；**在用 description 合计 2,325 字符**。**常驻 listing 已超预算**——Claude Code 默认按上下文 1% 做预算（200k 窗口≈1,600 字符）、单条上限 1536 字符，超预算时按调用频次**整条丢描述**，被丢描述的 skill 只剩名字、不再触发。所以长描述不是"更清楚"，是在挤掉别的 skill。
- 规则：新增 skill 前先查重（功能重叠优先并入现有 skill，不新开）；description **≤150 字符、触发词前置**（截断时活下来的是开头）；一个 skill 只接一件事，触发词不抢别的产线（人生副本口播只归 `fuben-write`）；主体超 500 行就下沉 references。
- 已归档（低频、与主线无关，文件保留、不路由、不占 listing）：`story-long-write`、`story-long-analyze`、`story-long-scan`、`story-import`、`story-cover`；恢复方式与同步要求见 [skills/_archive/README.md](skills/_archive/README.md)。
- 待办：在用 skill 仍有 5 条 description 超 150 字符（`browser-cdp` 389、`story-short-analyze` 308、`story-setup` 216、`story-review` 152、`skill-creator` 319 为上游原文）。
- 体检工具：`python3 scripts/skills_audit.py`（体积 / 描述预算 / 重复 / 触发冲突 / 坏链；`--strict` 有问题时非零退出，`--json` 供脚本消费）。完整数据与候选对比：[docs/技能库体检-2026-09-28.md](docs/技能库体检-2026-09-28.md)。
- 本沙箱注意：`curl https://skills.sh` 直连失败（SSL），但 `npx skills add` 的下载通道可用；检索走 `https://skills.sh/api/search?q=<关键词>&limit=20`。
- 安装位置：第三方 skill 只落 `.agents/skills/`。**不要在 `skills/` 里留软链**——`skills/*/SKILL.md` 是 `story-setup` 的部署清单，`test_gates.py::test_deployment_inventory_includes_fuben_review` 会断言它等于 `deploy-antigravity-skills.py` 的 `KNOWN_SKILLS`；`npx skills add` 顺手建的软链会污染清单并让门禁变红（本轮已处理）。
- 多份拷贝是**故意的**：`test_distributed_sources_are_identical` 强制 `check-ai-patterns.js`、`story-profile.js`、`story_hook_core.js` 在各 skill 里逐字节一致（每个 skill 要能独立部署）。改一处必须同步全部，不能只改单份。

## 手艺与事实边界

- 创作标准以 [skills/fuben-write/references/代入感手艺.md](skills/fuben-write/references/代入感手艺.md) 为核心（反流水账八件武器）；对标语感读 `拆文库/` 原稿与 `写作手法.md`。
- 保留用户给定事实；检索来源注明；不编造数据与授权；不报“必爆”；机检 PASS 只说明无机械阻断。
- 独立可复制提示词（不装 skill）：[skills/fuben-write/references/独立提示词.md](skills/fuben-write/references/独立提示词.md)。
