# AGENTS.md — 本仓库 Skill 路由入口

本仓库是抖音「人生副本/剧本人生」口播稿生成库：`skills/` 为创作与工具 skill，`拆文库/` 为 39 个故事段（另收 28b、46、48a–c 补充原文与 00 合集本体，共 45 个目录）ASR 原稿拆解（写作手法蒸馏源），`作品/` 为产出，`scripts/` 为机检工具。按用户意图路由：

| 用户意图 | 路由到 | 说明 |
|---|---|---|
| 写人生副本口播稿（人生副本、剧本人生、XX 的一生、口播稿、第二人称人生体验） | [skills/fuben-write/SKILL.md](skills/fuben-write/SKILL.md) | **主链路**（v1.1）。深读+真实检索（≥8 路）→方向卡→场次单→反流水账成稿→审读返工（账目+对话+红线）→机检候选闭环→交付逐字稿 |
| 审人生副本（副本审稿、口播复核、切条验收） | [skills/fuben-review/SKILL.md](skills/fuben-review/SKILL.md) | 创作审查＋读通专项，报告绑定 `body_path` 与 `body_text_sha256` |
| 写普通短篇/长篇网文、拆书、扫榜、去 AI 味、封面、导入 | [skills/story/SKILL.md](skills/story/SKILL.md) | 网文工具箱路由（小说口径；人生副本不走此线） |
| 部署/同步环境 | [skills/story-setup/SKILL.md](skills/story-setup/SKILL.md) | 模板与 hooks 部署 |
| 浏览器采集 | [skills/browser-cdp/SKILL.md](skills/browser-cdp/SKILL.md) | CDP 抓取 |
| 研究/借鉴/改造 Agent | 只交方法与接入改动 | 不自动转成样稿 |

## 人生副本管线（fuben-write）

```text
00 简报 → 01 深读+检索(≥8路并行)+剧情方向卡(用户选定) → 02 场次单
→ 03 成稿(反流水账八件武器) → 04 审读(追看断点/念稿测试/账目对账)+分层返工
→ 04b fuben-review 读通专项 → 05 机检+工艺门禁(PASS≠好看，候选须闭环) → 交付
```

阶段产物落 `作品/NN_主题/_运行/YYYY-MM-DD/`（同名阶段产物按 [arena.runtime.json](arena.runtime.json) 的 `product` 字段，用 `python3 scripts/fuben_products.py 作品/NN_主题` 验收）；不调用真实搜索即任务失败（用户裁决）；未获用户选定方向不得开写正文。`fuben_run` 默认含 craft 门禁（无烟红线/禁词/开头铁律/对白限额/账目档位/体量带；`fuben_craft --ledger` 出账目全表，`fuben-products.py` 查产物）；`facts`/`policy` 类候选在审读阶必须逐条销账。运行说明见 [docs/Arena运行时.md](docs/Arena运行时.md)。

## 手艺与事实边界

- 创作标准以 [skills/fuben-write/references/代入感手艺.md](skills/fuben-write/references/代入感手艺.md) 为核心（反流水账八件武器）；对标语感读 `拆文库/` 原稿与 `写作手法.md`。
- 保留用户给定事实；检索来源注明；不编造数据与授权；不报“必爆”；机检 PASS 只说明无机械阻断。
- 独立可复制提示词（不装 skill）：[skills/fuben-write/references/独立提示词.md](skills/fuben-write/references/独立提示词.md)。
