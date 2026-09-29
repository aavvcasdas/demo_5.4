# Arena 运行时说明

对应机器可读配置：[arena.runtime.json](../arena.runtime.json)。本仓库当前主项目是 `arena-screenplay`；人生副本 `fuben-*` 管线只保留给历史口播稿。

## 当前剧本管线

1. **路由**：打开 [AGENTS.md](../AGENTS.md)，写/改中文单集剧本进入 [arena-screenplay](../skills/arena-screenplay/SKILL.md)。明确说“人生副本口播稿”才进入 legacy `fuben-write`。
2. **契约**：先确定本集观看承诺、主角目标、阻力策略、不可替代动作、兑现/代价/退出状态和拍摄限制。
3. **读源**：先读合法持有的 `拆文库/*/原文/`，再看同篇拆文；需要现实细节时按需检索并记录来源，不以八路/十八路搜索作为创作门槛。
4. **写正文**：唯一当前正文是 `剧集/EP<NNN>/剧本.md`。场景标题、动作、对白、VO、SFX 写在同一份制作文本中；不要把口播稿换行或把 `正文.md` 改名为剧本。
5. **审读**：`审核/EP<NNN>.md` 绑定 `body_path` 与 `body_text_sha256`，逐场写原句、行号、问题和改法。无独立审读者时只能记为 `PROVISIONAL` / `editorial_status: REQUIRED`。
6. **机械检查**：

   ```bash
   python3 skills/arena-screenplay/scripts/arena_screenplay_check.py 剧集/EP001/剧本.md --json
   python3 skills/arena-screenplay/scripts/arena_screenplay_review.py 剧集/EP001/剧本.md --output 审核/EP001.md
   ```

   检查器只查格式、绑定和明显元话语；不会判断“剧情水不水”、不会数关键词冒充笑点、不会把检索路数/物证数/机器 PASS 变成好看证明。

## 为什么要换管线

最近的 `作品/87_年卡洗澡空调饮用水/正文.md` 是口播段子草稿，不是剧本：第一句的“健身年卡用成三个家电”是有效错位，但正文随后以缺热水、洗澡、吹空调、接水、教练问答、通知、算账、榜单平行排列，主角没有持续的目标—阻力—行动—结果链。审核报告里的 18 路检索、8 个“笑点”、7 站和 `fuben_viral` 9/9，只说明阶段表和关键词存在，不能证明这些内容在画面里成为戏。

拆文库原稿的有效处恰恰不同：

- 《无辣不欢》用“被激将→吃完→被喊辣王→排骨汤失味→腹泻→反复加码→白粥回甘→微辣”推进，每次加码改变身体和身份；
- 《外卖员》用 8 个权力位置变化推进：被取消、抢单、派单、封禁、算法收紧、被清算、新人循环；数字和回旋镖台词服务于行动，而不是组成资料表；
- 新项目应学习这些因果机制，不能把原句或 `拆文报告.md` 的打分表复制到新稿。

## 结果命名

- `mechanical_status=PASS`：格式层没有阻断；
- `editorial_status=REQUIRED`：尚未完成人读；
- `PROVISIONAL`：人读记录存在但仍有未验证项；
- `READY_FOR_OWNER_CONFIRMATION`：证据齐全，仍需作者/制片确认；
- `STALE`：正文或素材改变，旧哈希失效；
- `NOT_READY`：尚未取得发布资格。

不要再输出笼统的“审核通过”。平台播放、点赞、评论、完播只能在真实发布后回填，不从报告里预言。

## legacy 说明

`作品/`、`scripts/fuben_run.py`、`fuben_craft.py`、`fuben_claims.py`、`fuben_viral.py` 等仍供历史人生副本口播稿回归测试。它们与新 `剧集/` 目录隔离；旧工具的机械 PASS 不得用于剧本项目。
