# Arena 运行时说明 —— 本会话怎样读懂并运行本仓库的 Skill / Agent（v3.0）

对应机器可读配置：[arena.runtime.json](../arena.runtime.json)（路由与契约见 [AGENTS.md](../AGENTS.md)）。

## 这是什么

本仓库的 `skills/*/SKILL.md` 与 `skills/story-setup/references/templates/agents/*.md` 原本是写给 codex / Claude Code / opencode 这类外部执行器读的。当前环境没有这些执行器，而 **Arena Agent Mode 主会话本身就是执行器**。`arena.runtime.json` 是绑定配置：它告诉 Arena agent 打开本仓库时怎样把仓库里的角色定义跑起来——不是把 SKILL.md 当参考文章读一遍然后随手写，而是按配置逐阶段实例化角色、落产物、跑机检。

**v3.0 的定位**：这是一个 **Arena skill 剧本项目**——主交付是「旁白驱动·可拍剧本」（`剧本.md`＋`旁白.md`），不是口播逐字稿。运行时同时负责一件事：**别把流程当成产出**。00–04 每份 ≤80 行，正文预算优先。

## 运行方式（人生副本剧本）

| 阶段 | 角色 | 产物 | 这一步真正要交的东西 |
|---|---|---|---|
| 00 简报 | 主控 | `00_简报.md` | 题面原话、时长档、禁用器物；**题面确为单事件段子时在此登记** |
| 01 检索＋选题 | 策划＋并行检索 | `01_深读_检索与方向.md` | ≥8 路真实检索逐路表（≤80 行）＋选题三闸结论＋3–4 张方向卡＋**用户选定（原话引用）** |
| 02 分场表 | 策划 | `02_分场表.md` | 5–8 场：事件／画面主体（物证）／旁白字数／对白句数／秒数／钩点；情绪曲线；伏笔登记 |
| 03 成稿 | 主笔 | `03_初稿.md` → `剧本.md`＋`旁白.md` | 场标题＋`画面：`＋`旁白：`＋`角色（提示）：台词`；首行即钩、签名后置；一次一场 ≤35 行；写完抽配音轨 |
| 04 划走点审读 | 审读＋主笔 | `04_审读.md` | 三扫（衔接断裂／密度掉了／念不出来）＋可拍三问，逐条**引场号或行号**；🔴🟡🟢 处置；`fuben_craft --ledger` 对账；改前→改后 findings 差异 |
| 05 机检（可选） | `scripts/fuben_run.py` | `05_机检.json` | 真实命令输出；PASS ≠ 创作批准，也不等于能拍 |

调用证据是文件，不是话术：缺阶段产物＝这一步没做，不得声称走了管线。**但"文件在场"不再是门禁**——v3.0 已删 `fuben_products.py`（产物齐备核对）与审核报告的 `body_text_sha256` 绑定；也不再要求"机检候选逐条销账表"。理由见 [docs/剧本化改造诊断-2026-09-29.md](剧本化改造诊断-2026-09-29.md)：那套东西只证明文件没被改过，并且是把注意力从正文挪走的直接原因。

## 机检（只剩会咬人的）

```bash
python3 scripts/fuben_run.py 作品/NN_主题/ --profile full --json   # 目录形态优先读 旁白.md，回落 正文.md
python3 scripts/fuben_craft.py 作品/NN_主题/旁白.md --ledger          # 数字判词链 ↔ 同段金额
python3 scripts/skills_audit.py                                   # 技能库体检（治理，不碰单篇）
python3 scripts/test_gates.py                                     # 仓库健康总入口
python3 scripts/fuben_data.py record --input snapshot.json        # 发布后真实数据回填
```

- `NO_SMOKE` 是 BLOCK（用户红线，无豁免）；`VOLUME_UNDER_FLOOR`（终稿旁白 <700 字）、`SCENE_NO_VISUAL`、`SCENE_SPARSE`、`VO_TRACK_OVER`（对白 >25%）、`LEDGER_*` 是必须处置的 REVIEW；`VOLUME_OFF_BAND`（超上限）与 `*_STATS` 是描述，不是任务。
- INFO 行的「每行汉字」是对标指纹（拆文原稿 9.3）：**低于 8＝把一句话拆成三行**，回稿合并。
- 已退役：`fuben_products.py`、`fuben_loop.py`、`fuben_release.py`、`fuben_scene_check.py`、`fuben_viral.py`、`fuben_claims.py`、`fuben_lint.py`、`corpus_gate_audit.py`。**别写回来**：能数关键词打 ✅ 的检查，只会让人少改稿。

## 诚实边界

- 外部执行器（codex / Claude Code / opencode / gemini-cli）若日后在本环境安装并认证，可在 `arena.runtime.json` 把 `executors.active` 切过去，产物协议不变。
- 独立外部审读目前不可用；04 由主会话以审读角色独立执行并在文件里标注这一点，**不冒充多 Agent 会审、不虚构会话 ID**。
- 机检 PASS 只说明无机械阻断；审读意见只说明有人读过并点名了位置。两者都不是流量预测，也不构成发布批准。
- 主题边界：以用户题面为准。题面是人生，题材元素（如健身、游戏）只能做质感与道具，不能抢走主线；04 专门核这一条。
