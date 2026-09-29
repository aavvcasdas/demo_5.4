---
name: find-skills
description: "Find and install agent skills (\"find a skill for X\", \"is there a skill for...\"). Use when the user needs a capability that might exist as a skill."
---

# Find Skills

This skill helps you discover and install skills from the open agent skills ecosystem.

## When to Use This Skill

Use this skill when the user:

- Asks "how do I do X" where X might be a common task with an existing skill
- Says "find a skill for X" or "is there a skill for X"
- Asks "can you do X" where X is a specialized capability
- Expresses interest in extending agent capabilities
- Wants to search for tools, templates, or workflows
- Mentions they wish they had help with a specific domain (design, testing, deployment, etc.)

## What is the Skills CLI?

The Skills CLI (`npx skills`) is the package manager for the open agent skills ecosystem. Skills are modular packages that extend agent capabilities with specialized knowledge, workflows, and tools.

**Key commands:**

- `npx skills find [query] [--owner <owner>]` - Search for skills interactively or by keyword, optionally scoped to a GitHub owner
- `npx skills add <package>` - Install a skill from GitHub or other sources
- `npx skills update` - Update all installed skills

**Browse skills at:** https://skills.sh/

## 本地分叉说明（2026-09-28）

本文件已被本仓修改（上游：`vercel-labs/skills`，描述瘦身 + 增加检索兜底），**与 `skills-lock.json` 记录的哈希不再一致**；`npx skills update` 会从上游覆盖这两处改动。需要重装上游版本时先备份本文件。

### 检索通道兜底（skills.sh 不可达时）

`npx skills find` 依赖 CLI 直连 `https://skills.sh`；在部分沙箱/内网里这条通道会失败（表现为「No skills found」或 SSL 错误），但**安装通道通常仍可用**。按下面顺序兜底：

1. **注册表检索 API**（优先）：
   ```bash
   curl -sS "https://skills.sh/api/search?q=<urlencoded-关键词>&limit=20"
   ```
   返回 JSON：`skills[].id / source / skillId / name / installs`；加 `&owner=<owner>` 可按来源收窄。若 `curl` 不通，用宿主自带的网页抓取工具取同一 URL。
2. **GitHub 兜底**（前两条都不可用，或需要看源码质量）：
   ```bash
   gh api search/repositories -X GET -f q='<关键词> SKILL.md'      # 找候选仓库（部分环境不支持 code search）
   gh api repos/<owner>/<repo>/contents --jq '.[].name'            # 列目录
   gh api repos/<owner>/<repo>/contents/<path>/SKILL.md --jq .content | base64 -d   # 读内容（raw.githubusercontent 常被墙）
   ```
3. **安装**：仓库来源确认后照常安装，别因为检索失败就放弃：
   ```bash
   npx -y skills add <owner>/<repo> --skill <name> -y
   ```
   已验证：即使 `curl https://skills.sh` 失败，安装仍可完成。

### 安装后的两条纪律

- **别让 skill 变多到互相抢触发**：一次只装真正缺的那 1–2 个；功能重叠时优先并进已有 skill。常驻 description 有预算（Claude Code 默认按上下文 1%，超预算会整条丢最少使用的描述），装得多会让原本能触发的 skill 静默失效。
- **安装位置**：第三方 skill 落 `.agents/skills/`（或宿主对应目录）。若宿主仓库用自己的 `skills/` 目录做部署清单/测试断言，安装器顺带建的 `skills/<name>` 软链和 `agent/skills/<name>` 拷贝要清掉，否则清单与门禁会被污染（见 2026-09-28 本仓体检记录）。

## How to Help Users Find Skills

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Check the Leaderboard First

Before running a CLI search, check the [skills.sh leaderboard](https://skills.sh/) to see if a well-known skill already exists for the domain. The leaderboard ranks skills by total installs, surfacing the most popular and battle-tested options.

For example, top skills for web development include:
- `vercel-labs/agent-skills` — React, Next.js, web design (100K+ installs each)
- `anthropics/skills` — Frontend design, document processing (100K+ installs)

### Step 3: Search for Skills

If the leaderboard doesn't cover the user's need, run the find command:

```bash
npx skills find [query] [--owner <owner>]
```

For example:

- User asks "how do I make my React app faster?" → `npx skills find react performance`
- User asks "can you help me with PR reviews?" → `npx skills find pr review`
- User asks "I need to create a changelog" → `npx skills find changelog`

### Step 4: Verify Quality Before Recommending

**Do not recommend a skill based solely on search results.** Always verify:

1. **Install count** — Prefer skills with 1K+ installs. Be cautious with anything under 100.
2. **Source reputation** — Official sources (`vercel-labs`, `anthropics`, `microsoft`) are more trustworthy than unknown authors.
3. **GitHub stars** — Check the source repository. A skill from a repo with <100 stars should be treated with skepticism.

### Step 5: Present Options to the User

When you find relevant skills, present them to the user with:

1. The skill name and what it does
2. The install count and source
3. The install command they can run
4. A link to learn more at skills.sh

Example response:

```
I found a skill that might help! The "react-best-practices" skill provides
React and Next.js performance optimization guidelines from Vercel Engineering.
(185K installs)

To install it:
npx skills add vercel-labs/agent-skills@react-best-practices

Learn more: https://skills.sh/vercel-labs/agent-skills/react-best-practices
```

### Step 6: Offer to Install

If the user wants to proceed, you can install the skill for them:

```bash
npx skills add <owner/repo@skill> -g -y
```

The `-g` flag installs globally (user-level) and `-y` skips confirmation prompts.

## Common Skill Categories

When searching, consider these common categories:

| Category        | Example Queries                          |
| --------------- | ---------------------------------------- |
| Web Development | react, nextjs, typescript, css, tailwind |
| Testing         | testing, jest, playwright, e2e           |
| DevOps          | deploy, docker, kubernetes, ci-cd        |
| Documentation   | docs, readme, changelog, api-docs        |
| Code Quality    | review, lint, refactor, best-practices   |
| Design          | ui, ux, design-system, accessibility     |
| Productivity    | workflow, automation, git                |

## Tips for Effective Searches

1. **Use specific keywords**: "react testing" is better than just "testing"
2. **Try alternative terms**: If "deploy" doesn't work, try "deployment" or "ci-cd"
3. **Check popular sources**: Many skills come from `vercel-labs/agent-skills` or `ComposioHQ/awesome-claude-skills`

## When No Skills Are Found

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities
3. Suggest the user could create their own skill with `npx skills init`

Example:

```
I searched for skills related to "xyz" but didn't find any matches.
I can still help you with this task directly! Would you like me to proceed?

If this is something you do often, you could create your own skill:
npx skills init my-xyz-skill
```
