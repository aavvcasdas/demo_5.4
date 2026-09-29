# skills/_archive/ — 归档区（2026-09-28 起）

这里放**本仓当前主线用不到的 skill**：目录、内容、脚本全部保留，只是**不参与路由、不参与部署清单**，因此不占常驻 listing 预算、也不会再和主链路抢触发词。

## 为什么归档这几个

- 本仓主线是抖音「人生副本/剧本人生」口播稿（`fuben-write` → `fuben-review`），长篇网文线只在写小说时才会用到。
- 常驻 skill 的 description 是**每次会话都要付的预算**（Claude Code 默认按上下文 1% 给 listing 预算，超预算会按调用频次整条丢描述），低频 skill 常驻会挤掉高频 skill 的可发现性。
- 判定依据与体检数据见 [`docs/技能库体检-2026-09-28.md`](../../docs/技能库体检-2026-09-28.md)。

| 归档 skill | 原职责 |
|---|---|
| `story-long-write` | 长篇网文写作（大纲/世界观/日更） |
| `story-long-analyze` | 长篇拆文（黄金三章、逐章摘要） |
| `story-long-scan` | 长篇扫榜与选题 |
| `story-import` | 逆向导入已有小说 |
| `story-cover` | 网文封面生成（依赖 `GPT_IMAGE_API_KEY`） |

## 恢复方式

```bash
git mv skills/_archive/<name> skills/<name>
```

并同步两处，否则 `python3 scripts/test_gates.py` 会红：

1. `skills/story-setup/scripts/deploy-antigravity-skills.py` 的 `KNOWN_SKILLS`（部署清单必须等于 `skills/*/SKILL.md` 的实际集合）；
2. `skills/story/SKILL.md` 路由表里对应行的状态标注。

## 纪律

- 归档 ≠ 删除：文件仍在仓库、仍受 `test_distributed_sources_are_identical` 的逐字节一致性约束。
- 不要只为「少几个文件」而归档高频 skill；归档的判据是**低频 + 与主线无关 + 常驻成本 > 收益**。
