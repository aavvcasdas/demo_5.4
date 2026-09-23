# GitHub 短视频 Agent：借了什么，接到了哪里

历轮只研究并改造 Agent 方法与手艺层，**没有写新样稿、修稿件字数或制作新的机检报告**。目标是让 Agent 真正执行强开头、爽感兑现、伏笔与侧面推进，而不是多写几句“要好看”。

> **2026-09-23 第 4 轮新增**：借鉴对象从「Agent 编排类项目」扩展到「Skill 写法类项目」
> （`0xsline/short-drama`、`blader/humanizer` 51.6k★、`hardikpandya/stop-slop` 17.5k★、
> `anthropics/skills` 官方、`Leonxlnx/taste-skill` 89.5k★），产出
> [fuben-craft 手艺层](../skills/story-short-write/references/fuben-craft/README.md) 8 个文件、
> 重建 `arena.runtime.json` 与根 `AGENTS.md`、新增只读工具 `scripts/fuben_craft_scan.py`，
> 并修复 2 个长期红的测试。完整的病因定位与逐条对照见
> [skill诊断与优化_2026-09-23.md](skill诊断与优化_2026-09-23.md)。下面 §1–§3 是前三轮的记录，保持原样。

## 1. 从设计 Agent 借“候选竞争＋兑现路径”

来源：`dyzsasd/writing-loop`，固定版本 `56364527c8f7302a8d26e1675874a25303a6d28e`。

它的 `story-designer-agent` 在设计阶段比较不同反转、危机和尾钩方案，并保留弃案原因；`craft-rules.md` 要求用于揭示的线索先进入正文，不能只藏在人物设定里。[3](https://github.com/dyzsasd/writing-loop)

**本仓采用：**新题先内部比较不同驱动力的短开场，每个都要接得上正文中的兑现；没有后续可演的噱头淘汰。先想清兑现，再倒推可见线索。不是给用户扔多个完整稿，也不复制长剧的伏笔数量和跨集配额。

源码定位：
- [3](https://github.com/dyzsasd/writing-loop/blob/56364527c8f7302a8d26e1675874a25303a6d28e/skills/story-designer-agent/SKILL.md#L119-L127)：设计阶段的候选竞争。
- [3](https://github.com/dyzsasd/writing-loop/blob/56364527c8f7302a8d26e1675874a25303a6d28e/references/craft-rules.md#L30-L44)：伏笔先埋入正文与回收。

## 2. 从真实调用链借“不同问题退回不同阶段”

来源：`YingaoZhang/short_drama_agent`，固定版本 `c7688f3cacf84106a6909ff8de8106811fbcabdb`。本轮沿 `workflow.py → routing.py → lead_writer / quality_reviewer / revision_editor → llm_helpers` 读取相关调用与提示片段。

其流程将严重的主线问题退回世界构建，节奏/关键剧情问题退回主笔，轻微问题交给局部改稿；改稿后回审，不是所有问题都换词处理。[9](https://github.com/YingaoZhang/short_drama_agent)

**本仓采用：**切口与主线失效回策划；兑现被跳过、伏笔未落地、侧面成捧哏回主笔重写关键场；只有表达问题才局部润色。审读必须给具体原句和修订目标，主笔实际收到这些反馈。

源码定位：
- [9](https://github.com/YingaoZhang/short_drama_agent/blob/c7688f3cacf84106a6909ff8de8106811fbcabdb/backend/app/graph/workflow.py#L14-L45)：节点与回审边。
- [9](https://github.com/YingaoZhang/short_drama_agent/blob/c7688f3cacf84106a6909ff8de8106811fbcabdb/backend/app/graph/routing.py#L4-L22)：分层退回。
- [9](https://github.com/YingaoZhang/short_drama_agent/blob/c7688f3cacf84106a6909ff8de8106811fbcabdb/backend/app/graph/nodes/revision_editor.py#L33-L58)：局部改稿接收实际审查意见。

**没有原样搬这个 Demo。**它的审核节点存在工具快速分支及台词数量判断，模型辅助函数也有固定结果兜底；这些不能证明内容好看，本仓没有引入。借的是返工分工，不是其 PASS 或预置剧情。[9](https://github.com/YingaoZhang/short_drama_agent/blob/c7688f3cacf84106a6909ff8de8106811fbcabdb/backend/app/graph/nodes/quality_reviewer.py#L61-L130) [9](https://github.com/YingaoZhang/short_drama_agent/blob/c7688f3cacf84106a6909ff8de8106811fbcabdb/backend/app/graph/nodes/llm_helpers.py#L25-L65)

## 3. 从编剧手艺借“策略改变＋有后果的侧面反应”

来源：`zenstory-ai/drama-skills`，固定版本 `0e8929881bb59248618c4f402707c64723adc017`。重点读场景策略、主角主动性、反应后果、台词权力变化及去模板修订段，不声称完整审计了该项目。

这些段落要求阻力能迫使人物改变策略，转向改变下一动作；角色反应要影响选择和关系。旁人或道具不能恰好替主角完成最难的一步；去模板也不是替换几个常用词。[1](https://github.com/zenstory-ai/drama-skills)

**本仓采用：**把爽点写成连续交锋和局面转变；审读追问“他先前能做什么，现在为什么不能再做”。侧面反应放大主角行动的结果，不用全员震惊代替兑现，也不让配角包办主角的反击。

源码定位：
- [1](https://github.com/zenstory-ai/drama-skills/blob/0e8929881bb59248618c4f402707c64723adc017/skills/short-drama-write/references/script-craft.md#L104-L180)：有效阻力、换策与主角主动性。
- [1](https://github.com/zenstory-ai/drama-skills/blob/0e8929881bb59248618c4f402707c64723adc017/skills/short-drama-write/references/script-craft.md#L254-L264)：反应承载后果。
- [1](https://github.com/zenstory-ai/drama-skills/blob/0e8929881bb59248618c4f402707c64723adc017/skills/short-drama-write/references/dialogue-craft.md#L245-L263)：话语权的可见变化。
- [1](https://github.com/zenstory-ai/drama-skills/blob/0e8929881bb59248618c4f402707c64723adc017/skills/short-drama-review/references/anti-template-repair.md#L13-L62)：从因果、策略而非同义词处理模板感。

## 4. 从成熟 Skill 项目借「每条规则都配一段可抄的形状」（2026-09-23）

来源（均本地 clone 后逐文件读，未用网页摘要代替源码）：
`0xsline/short-drama`（SKILL.md 520 行 + references 8 篇）、`blader/humanizer`（SKILL.md 单文件 25 patterns）、
`hardikpandya/stop-slop`（SKILL.md + phrases/structures/examples）、`anthropics/skills`（skill-creator 与 spec）、
`Leonxlnx/taste-skill`（方法论参考）。

**为什么必须借这一层**：前三轮把「候选竞争」「分层返工」「策略改变＋有后果的侧面反应」接进了流程，
但现行 profile 全文只有 1 处例句，而仓里 53 万字 `写作手法.md` + 107 万字 `情节节点.md` 一条都没被引用。
`作品/80` 的实证后果：搞笑题手上没有任何笑点机制，只能把检索到的热梗原句搬进正文
（`_运行/07_诊断_流水账.md`：「我把『梗的出处清单』当成了剧本」）；
审读则按 `_archived` 里已作废的 §17 配额判「达线」，用户仍然裁定「看不懂、是流水账」。

**本仓采用：**

| 来源 | 借的是什么 | 接到哪里 |
|---|---|---|
| `short-drama` references/hook-design.md | 5 种钩子 × 子模式 × **每型一段可直接抄的剧本** × 设计要点 × 致命问题清单 × 自检表 | `fuben-craft/开场与钩子.md` §段内钩子五型（改成单条口播：每 200–400 字挂一个段尾钩子，主兑现置 75–88%） |
| `short-drama` references/opening-rules.md | 6 种开场模板 + 「前 5 秒定生死」+ 绝对禁止的开场 | 同文件 §六种开场模板（分类法保留，示例换成 02/13/15/17/28/38 的真实口播原文） |
| `short-drama` references/satisfaction-matrix.md | 爽点＝压抑→释放、强度分级、爽点自检、致命爽点问题 | `fuben-craft/爽点兑现.md` 四拍结构（并指明「加码」是最常被跳过的一拍）+ 五种兑现型（含本赛道独有的**钝刀断线**） |
| `short-drama` references/villain-design.md | 反派三原则：可恨／可信／递进 | 同文件 §对手设计（可恨的手段换成语料里的话术工具箱） |
| `short-drama` references/rhythm-curve.md | 加速／减速手段表 + 「喘息段是否也在推进剧情」 | `fuben-craft/结构与曲线.md` §节奏调控 |
| `short-drama` SKILL.md `/review` | 五维打分表 + 分数区间处置 | `fuben-craft/口播腔调与反AI味.md` §D + `fuben-review/SKILL.md` 五维（追看/笑点/共情/兑现/腔调），加三条防 Goodhart 纪律 |
| `humanizer` | **Watch for → Problem → Before → After** 四段式；按强弱排序（strong 见一次就改 / weak alone 需同段有其他 tell） | 同文件 §B 十二条中文口播 slop |
| `humanizer` | **When not to act** + 「Keep the details that carry the writer's voice」 | 同文件 §C 保留清单（方言俚语、答非所问的玩笑、角色胡诌、具体怪数字、矛盾情绪、年代梗），并引 80 号审读里两个本来就正确的裁决当范例 |
| `humanizer` | 「一个 tell 的分量与『认真写作者故意这么写的概率』成反比」 | §C 总纪律 + `fuben_craft_scan.py` 的 strong/weak 分级与「前后已有具体细节则降级」逻辑 |
| `humanizer` §1/§2/§17 | not X but Y、one-line closers 与 dramatic fragments、inflated verbs | §B11（保留 humanizer 的例外条款）/ §A 行节奏 + §B6 / §B2 抽象总结代替戏 |
| `stop-slop` structures.md | **false agency**（无生命物做人的动作）、narrator-from-a-distance、telling instead of showing、Cut quotables、two items beat three | §B3 假动作主语 / §B10 旁白讲解员 + `侧面与共情.md` §第二人称三用法 / §B2+§B7 / **§B1 口号收尾（最强一条）** / §B6 |
| `stop-slop` SKILL.md | 5 维评分 <35 revise | §D 五维评分 |
| `anthropics/skills` skill-creator | Progressive disclosure 三层 + 「reference files clearly from SKILL.md **with guidance on when to read them**」+ 大文件带目录 + organize by variant | 新建 `fuben-craft/` 作为第三层（8 文件，每个 <300 行带目录）；profile v14、`AGENTS.md`、`arena.runtime.json`、Agent 方法 §2 全部给出「何时读哪个」的加载表与**按角色下发切片**的表 |
| `anthropics/skills` skill-creator | 「Prefer a short, clear instruction over another exception」/「explain **why** in lieu of heavy-handed musty MUSTs」 | profile v14 压缩到路由 + 加载表 + 七条创作要求；把 54KB 归档配额包移出 `genre-styles/` 发现路径 |
| `taste-skill`（方法论） | 「LLM 有严重的统计偏好，永远选第一个默认值」→ 强制在产出前显式选型并核验（`<design_plan>`） | `arena.runtime.json` 阶段 01 的 `must_contain`：必须写明用哪种开场模板、哪种笑点引擎、哪条曲线、借了哪几篇的**机制名**（写不出机制名＝没读）；`结构与曲线.md` §双联法（选 A/B 面双联找分岔点，避免重复已写过的形状） |

**没有搬的**：`paywall-design.md` 付费卡点与 50–100 集分集目录（口播单条不吊跨集胃口）、出海模式；
`stop-slop` 的「Kill all adverbs / No em dashes / 句子不许以 Wh- 开头」（英文散文规则，中文口播的语气词是人味，照搬会误伤——已在 §C 反向写明）；
`taste-skill` 的 GSAP/Tailwind 全部内容（领域无关，只借方法论）。

---

## 现在仓库里怎样执行

```text
当前请求是研究/改造Agent → 借鉴与接入，到此结束，不自行生成作品

当前请求是写稿
  → 主控：选择能接到兑现的开场
  → narrative-writer：展开关键戏，落伏笔与侧面后果
  → story-architect：创作审读，定位追看断点
  → 按问题退回策划 / 关键场重写 / 局部润色

人物反应薄弱时才让 character-designer 专项补强
```

已接入的位置：

- [人生副本 Agent 方法](../skills/story-short-write/references/genre-styles/人生副本_Agent方法.md)：实际分工、输入、返工目标，以及**按角色下发手艺切片**的表。
- [主profile v14](../skills/story-short-write/references/genre-styles/人生副本实录.md) 与 [写作入口](../skills/story-short-write/SKILL.md)：指向并执行该流程，不是另放一篇无人读取的资料。
- [fuben-craft 手艺层](../skills/story-short-write/references/fuben-craft/README.md)：开场与钩子 / 笑点机制 / 侧面与共情 / 爽点兑现 / 结构与曲线 / 口播腔调与反AI味 / 样本索引，含加载表。
- [审核入口](../skills/fuben-review/SKILL.md) v5.3.0：按创作问题层级返工，明确独立审读与改稿分开，五维评分每分挂原句，**禁止按 `_archived` 旧配额验收**。
- [arena.runtime.json](../arena.runtime.json) 与 [AGENTS.md](../AGENTS.md)：执行通道与根路由（此前缺失，导致 profile 里「两者都不可用就停止」的条款无处落地）。
- [scripts/fuben_craft_scan.py](../scripts/fuben_craft_scan.py)：只读读感扫描，输出带行号候选与「不要误清」提醒，永不 BLOCK。
- [skill诊断与优化_2026-09-23.md](skill诊断与优化_2026-09-23.md)：本轮病因定位、逐条对照与改动清单。
- `story-setup/references/{templates,opencode,codex}/agents/` 中现有的 `story-architect`、`narrative-writer`、`character-designer`：已在副本提前分流内写入各自职责，不再只有“绕过小说规则”的说明；没有新增一个空壳 Agent 名称。
- [根路由](../AGENTS.md) 与 [调用方参考选择](../skills/story-setup/references/agent-references/agent-reference-profiles.md)：按任务动作分流，并传递对应方法片段。

采用的是重新表述、按人生副本适配的方法，没有导入外部代码或安装第三方运行平台。已经部署过的项目需通过原有 `story-setup` 同步模板；本轮没有擅自安装或启动宿主。模板接入不等于宿主已部署；本轮没有运行独立模型/观众实验，不宣称这些方法已证明流量提升。
