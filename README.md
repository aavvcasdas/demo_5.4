# Arena 中文剧本项目

本仓库现在以 `arena-screenplay` 为主入口：把题面、采访和合法持有的素材，写成可拍摄的中文单集剧本。旧的「人生副本」口播稿、`作品/` 及 `scripts/fuben_*` 保留作历史样本与回归工具，不再作为本项目的新稿入口。

## 当前入口

- Skill：[`skills/arena-screenplay/SKILL.md`](skills/arena-screenplay/SKILL.md)
- Arena 管线：[`arena.runtime.json`](arena.runtime.json)
- 已安装的上游短剧 Skill： [`.agents/skills/short-drama-write/SKILL.md`](.agents/skills/short-drama-write/SKILL.md)
- 查找 Skill： [`.agents/skills/find-skills/SKILL.md`](.agents/skills/find-skills/SKILL.md)

## 项目交付

```text
项目简报.md
剧集/EP001/剧本.md
审核/EP001.md
```

检查当前剧本：

```bash
python3 skills/arena-screenplay/scripts/arena_screenplay_check.py \
  剧集/EP001/剧本.md --json
python3 skills/arena-screenplay/scripts/arena_screenplay_review.py \
  剧集/EP001/剧本.md --output 审核/EP001.md
```

机械检查只会告诉你格式和绑定是否成立，不会判定好看，更不会预测抖音流量。旧 `fuben_*` 工具不能审 `剧集/` 剧本。

## 这次改造的核心

最新的 `作品/87_年卡洗澡空调饮用水/正文.md` 是口播段子草稿：错位设定成立，但主要靠物件清单、笑点串联、算账和旁白总结推进；它没有持续的目标—阻力—行动—结果，因此不把它伪装成剧本。`拆文库/` 的原始 ASR 剧本则显示，能留人的不是“检查项数量”，而是具体行为造成的代价、关系变化和可回收的词/物件。

诊断与抖音搜索记录见 [`docs/剧本项目改造诊断-2026-09-29.md`](docs/剧本项目改造诊断-2026-09-29.md)。
