---
trigger: always_on
---

# oh-story writing project rules

## 人生副本优先分流（本仓扩展）

人生副本 / 剧本人生 / 第二人称体验类口播稿走**独立 Skill `story-koubo-write`**（`/写口播`、`/人生副本`），不再走 `story-short-write` 的分支；审稿走 `fuben-review`（**审核 = 成稿复读 + 联网搜索对标**）。这个分支不执行后文普通小说的细纲、付费点、追踪、去味配额与必读表，也不要求部署独立 Agent 才能写。只有实际可调用时才委派，solo 不冒称独立审核。创作判据与真实示例在 `skills/story-koubo-write/references/fuben-craft/`（**口播稿规格** / **反流水账** / 开场与钩子 / 笑点机制 / 侧面与共情 / 爽点兑现 / 结构与曲线 / 样本索引），按 `story-koubo-write` 的 profile v15 加载表分阶段读。**写稿前第一个动作是精读，不是搜索**：同型样本的 `拆文库/NN_*/原文/原文.txt` **全文**进上下文（不是拆文报告、不是节点表），并复述「它怎么把一个瞬间写大到能住进去」——**考点提纲不能生产质地，课文才能**。口播稿规格按 **6.4 字/秒**对账定字数档，一行一个意群 12–20 字，判词与数字独占一行做气口，空行 ≤6 处，零标点，验收标准是**听一遍就懂**；**审核 = 成稿复读 + 联网搜索对标，不写脚本自动删改正文，口播稿不做去 AI 味清零**；**禁止读 `story-koubo-write/references/_archived/` 的旧配额包**（场景数、每场行数、时间标签数、内联说话行数、字数区间已作废，按它写或审会把稿子逼回流水账）。
新建口播项目若已启用小说 hooks，且尚无可识别的正文/设定，在**作品目录**放 `.fuben.json`：`{"schema_version":1,"profile":"fuben"}`，避免首次写入被当普通小说；不要标到混合书库根。未启用 hooks 的直接创作不要求这个文件。普通小说分支保持原合同。

This workspace uses the oh-story web-fiction skill pack. Discover skills from
`.agents/skills/`; read the selected skill's `SKILL.md` before executing it and
load its references only when that skill instructs you to do so.

## Routing

- Long-form writing or continuation: `story-long-write`
- Short-form writing: `story-short-write`
- Long/short deconstruction: `story-long-analyze` / `story-short-analyze`
- Long/short market scan: `story-long-scan` / `story-short-scan`
- Remove AI-writing patterns: `story-deslop`
- Adversarial review: `story-review`
- Import an existing story: `story-import`
- Cover generation: `story-cover`
- Ambiguous story intent: `story`
- Project deployment/update: `story-setup`
- Reuse an authenticated Chrome session: `browser-cdp`

## Writing guardrails

- Keep every story artifact, temporary drafting segment, tracking transaction,
  and generated project directory inside the current workspace. Never create or
  continue an oh-story book under `~/.gemini/`, Antigravity's `scratch/`, or any
  other directory outside the workspace unless the user explicitly names that
  external destination.
- Before writing novel prose, long-form projects require the matching
  `大纲/细纲_第N章*.md`; short-form projects require `小节大纲.md`.
- Treat `追踪/_tracking-state.json` as the structured source of truth. Do not
  hand-edit its derived Markdown views.
- After prose is written, resolve every deterministic finding injected by the
  oh-story Antigravity hooks before continuing to another chapter.
- Prefer the seven deployed custom agents in `.agents/agents/` for specialist
  work. Call `invoke_subagent` with the agent's `TypeName`; if the runtime cannot
  start them, use the skill's documented solo/direct fallback instead of
  failing the workflow.

## Context recovery

At the start of a new conversation, and whenever context appears compacted or
story state is uncertain, locate the active book and read `追踪/上下文.md` before
continuing. The Antigravity external hook API has no PreCompact/PostCompact
event, so this rule is the mandatory recovery path after compaction.
