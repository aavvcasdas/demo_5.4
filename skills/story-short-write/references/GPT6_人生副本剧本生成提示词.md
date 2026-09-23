# 人生副本提示词 · 旧路径兼容入口

旧版「联网→设定→大纲→全文」、固定情绪与场面配额已撤销，不再作为另一套现行规则。文件名仅为兼容旧链接，不是模型效果背书。

## 现行入口（v14）

| 用途 | 文件 |
|---|---|
| 创作 profile（入口，含加载表） | [genre-styles/人生副本实录.md](genre-styles/人生副本实录.md) |
| 角色分工与手艺切片下发 | [genre-styles/人生副本_Agent方法.md](genre-styles/人生副本_Agent方法.md) |
| 手艺层（示例驱动的机制库） | [fuben-craft/README.md](fuben-craft/README.md) |
| 审核判据 | [fuben-review/SKILL.md](../../fuben-review/SKILL.md) |
| 运行时配置与路由 | [arena.runtime.json](../../../arena.runtime.json) · [AGENTS.md](../../../AGENTS.md) |

## 可复制的独立提示词

原来这里指向 `作品/_提示词_人生副本_v2.md`，**该文件不在仓库里**（从未提交，或随沙箱回滚丢失）。
需要一段可粘到外部模型的独立提示词时，按下面顺序拼，不要凭记忆重写：

1. `genre-styles/人生副本实录.md` 的「一句话定位」+「把追看和兑现写进正文」六条；
2. 本题方向对应的那一个 `fuben-craft/*.md`（搞笑向取 `笑点机制.md`，扎心向取 `侧面与共情.md`，爽向取 `爽点兑现.md`）；
3. `fuben-craft/口播腔调与反AI味.md` 的 §A 行节奏 + §B 前 5 条 + §C 保留清单；
4. `拆文库/{同型 1-2 篇}/情节节点.md` 的节点表（给形状，不给整篇拆文报告）。

拼完的提示词落盘到 `作品/_提示词_人生副本_{日期}.md` 再使用，别只在对话里存在。

## 旧版

仅供研究，可从 Git 基线 `c064a61` 查看，或读 [genre-styles/_archived/人生副本实录_v1_归档.md](genre-styles/_archived/人生副本实录_v1_归档.md)
（该文件是史料，**不加载、不叠加执行**，不得和新版同时使用）。
