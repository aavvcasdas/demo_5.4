# AGENTS.md — Arena Skill 路由入口

本仓库的**当前主项目是 Arena 中文单集剧本项目**：`skills/arena-screenplay/` 是主 Skill，`剧集/` 是新产出，`审核/` 是绑定当前正文的审读记录，`拆文库/` 是合法素材的研究语料。旧 `作品/`、`skills/fuben-*` 和 `scripts/fuben_*` 保留作人生副本口播稿历史样本与回归工具，不能反过来审新剧本。

## 路由表

| 用户意图 | 路由到 | 说明 |
|---|---|---|
| 写/改 Arena 中文单集剧本、把口播稿剧本化 | [skills/arena-screenplay/SKILL.md](skills/arena-screenplay/SKILL.md) | 主链路：项目契约 → 按需读原文/查事实 → 目标-阻力-行动-结果 → `剧集/EP<NNN>/剧本.md` → 独立审读 → 机械绑定；不生成文章式 `正文.md` |
| 写人生副本口播稿（人生副本、剧本人生、XX 的一生） | [skills/fuben-write/SKILL.md](skills/fuben-write/SKILL.md) | **legacy 明确分流**：仅用户明确要第二人称口播稿时使用；不把口播稿当剧本 |
| 审人生副本口播稿 | [skills/fuben-review/SKILL.md](skills/fuben-review/SKILL.md) | 只服务历史 `作品/` 口播稿 |
| 查找/安装能力 | [.agents/skills/find-skills/SKILL.md](.agents/skills/find-skills/SKILL.md) | 已安装；`npx skills find <关键词>` → 核来源 → `npx skills add` |
| 造/改 skill、体检技能库 | [.agents/skills/skill-creator/SKILL.md](.agents/skills/skill-creator/SKILL.md) | 先查重、压描述、做触发回归 |
| 研究中文短剧手艺 | [.agents/skills/short-drama-write/SKILL.md](.agents/skills/short-drama-write/SKILL.md) | 已安装的上游参考；Arena 主项目由 `arena-screenplay` 接入和约束 |
| 普通网文/拆书/扫榜/去 AI 味 | [skills/story/SKILL.md](skills/story/SKILL.md) | 与 Arena 剧本产线隔离 |
| 部署/同步环境 | [skills/story-setup/SKILL.md](skills/story-setup/SKILL.md) | 不以部署成功代替创作审读 |
| 浏览器采集 | [skills/browser-cdp/SKILL.md](skills/browser-cdp/SKILL.md) | CDP 抓取 |
| 会话交接 | [.agents/skills/handoff/SKILL.md](.agents/skills/handoff/SKILL.md) | handoff |

## Arena 主链路

```text
00 项目简报 → 01 按需读原文/查事实 → 02 目标-阻力-行动-结果
→ 03 剧集/EP<NNN>/剧本.md → 04 逐场审读（原句+行号）
→ 05 arena_screenplay_check（机械 PASS ≠ 编辑通过）→ 作者/制片确认
```

**主项目边界**：不以搜索路数、物件数、笑点数、关键词认领或机器 PASS 代替好看；不强制固定字数、场数、反转或 CTA。剧本必须让动作、对白、空间和声音承担信息，不能把口播文案换行后冒充剧本。详细诊断见 [docs/剧本项目改造诊断-2026-09-29.md](docs/剧本项目改造诊断-2026-09-29.md)。

## 旧人生副本管线（legacy，仅明确要求口播稿时）

```text
00 简报 → 01 深读+检索(按旧 fuben 契约) → 02 人生时间轴 → 03 口播稿
→ 04 读通+返工 → 05 旧工具回归 → 交付逐字稿
```

`fuben_*` 工具和 `作品/` 报告服务历史口播稿；`fuben_viral.py` 只查旧阶段文件的结构关键词，不能判剧情水不水。旧报告里的 `PASS` 不能当新 Arena 剧本通过。

## find-skills 安装状态

项目级 Skill 已存在于 `.agents/skills/find-skills/`，`npx skills list --json` 可见。本轮运行 `npx skills find "screenplay script writing"` 返回注册表无结果，已使用项目中已安装的 `short-drama-write` 作为外部参考，并新建本地 `arena-screenplay`，避免重复装同类包。

## 运行与验证

```bash
python3 skills/arena-screenplay/scripts/arena_screenplay_check.py \
  剧集/EP001/剧本.md --json
python3 skills/arena-screenplay/scripts/arena_screenplay_review.py \
  剧集/EP001/剧本.md --output 审核/EP001.md
python3 scripts/skills_audit.py --json
python3 -m unittest discover -s tests -v
```

`arena_screenplay_check.py` 只检查 UTF-8、场景标题、对白格式、空场、明显审核元话语与 SHA-256；`mechanical_status=PASS` 不代表编辑层通过。没有独立审读、成片试听或发布数据时，报告必须明确缺失，不得声称好看或必爆。

## 技能库卫生

- 第三方 Skill 只落 `.agents/skills/`；仓库自己的部署 Skill 放 `skills/`。
- description 触发词前置且尽量不超过 150 字符；同一产线不叠加多个入口。
- `python3 scripts/skills_audit.py` 是只读体检，不是创作质量审核。
- `skills/arena-screenplay/SKILL.md` 的主体保持短，细则下沉到 `references/`；修改机械校验时同步测试。
- 旧分发测试仍要求 `check-ai-patterns.js`、`story-profile.js`、`story_hook_core.js` 等拷贝逐字节一致；不要只改其中一份。
