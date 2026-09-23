# GitHub 短视频 Agent：借了什么，接到了哪里

本轮只研究并改造 Agent 方法，**没有写新样稿、修稿件字数或制作新的机检报告**。目标是让 Agent 真正执行强开头、爽感兑现、伏笔与侧面推进，而不是多写几句“要好看”。

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

## 4. 本轮增补：从有 star 的抖音剧本/口播 prompt 库借“口播原生结构与手艺”

本轮目标：把人生副本分支从小说 skill 里拆出来，建成原生抖音口播 skill（`skills/fuben-write/`），并把流水账问题交给具体手艺而不是流程规则。检索对象为 GitHub 上抖音视频/剧本生成相关的 skill、prompt 与 agent，中文优先。

| 来源 | 借了什么 | 落到哪里 |
|---|---|---|
| [yaojingang/yao-open-prompts](https://github.com/yaojingang/yao-open-prompts)（2.8k★，双语提示词库） | 「口播爆款文案」的分层结构与情绪波浪（每 15–20 秒一个小高潮）、时长-字数对应、「抖音爆款策划师」的黄金 3 秒开头类型与结尾类型、「爆款仿写拆解与重构」的骨肉分离（借骨架不借皮肉）、「智能润色 v3」的反 AI 腔禁词与不完美化 | `fuben-write/references/口播结构与节奏.md`、`搜索与质感.md`（借质感不借剧情）、`代入感手艺.md`（禁词与语感）、`独立提示词.md`（该库的“标题/简介/Prompt”三段式可复制格式） |
| [1-SKILL/jiaoben](https://github.com/1-SKILL/jiaoben)（短视频脚本工坊） | hook 公式库、平台节奏表（语速字数校准 4–5 字/秒）、口播质检清单（单句 ≤15 字、用「你」不用「大家」、念稿测试） | `口播结构与节奏.md`（钩子公式表按叙事体改造）、`审读与改稿.md`（念稿测试） |
| [liuyunlong2021-wq/jc-xiachen-duanshipin-jiaoben](https://github.com/liuyunlong2021-wq/jc-xiachen-duanshipin-jiaoben)（下沉短视频剧本 skill） | 扒片→结构指纹→母版剧本；高保真改编锁定“钩子、人物功能位、冲突与证据顺序、空间推进、阶段奖励、结尾兑现”结构机制而非替换名词 | `搜索与质感.md`（质感借用表＝结构指纹的口播版）、`代入感手艺.md`（场景四件套） |
| [longmao-001/kesheng_skill](https://github.com/longmao-001/kesheng_skill)（多 agent 视频团队） | 判型先行（硬规则 #43）：口播稿＝**文案/信息驱动**（独白讲述）、剧本＝**戏剧动作驱动**（台词交锋）——两套形态不可混写 | `fuben-write/SKILL.md` 的“写的是口播逐字稿不是小说”定位；二轮修订后升级为**旁白驱动铁律**（`代入感手艺.md` 三点五：对白 ≤10%、只做激将/预警/刻度、禁乒乓回合）——首版稿把剧本手法混进口播导致「你说他说」小说腔，已返工 |
| [LiChangZheng10086/doyin_ai_video](https://github.com/LiChangZheng10086/doyin_ai_video)（抖音下载+ASR+洗稿+Skill 蒸馏） | 合集转录→skill 蒸馏的路线印证：本仓 `拆文库/` 即同类蒸馏产物，应直接喂给写作链路 | `代入感手艺.md` 全文（从 `拆文库/_系列总拆书.md` 与各篇 `写作手法.md` 蒸馏成可执行规则） |
| [Mr-funny/hbg-life-simulation](https://github.com/Mr-funny/hbg-life-simulation)、[samjia12/skill-video-script](https://github.com/samjia12/skill-video-script)、[towardsyoung/video-agent-skills](https://github.com/towardsyoung/video-agent-skills) 等 | 下游成片/分镜/改编链路与“黄金 3 秒+技法标注”格式，确认口播稿应交付逐字稿+钩子备选而非小说章节 | `fuben-write/SKILL.md` 交付契约 |

**没有原样搬任何一家的完整提示词**：采用的是重新表述、按人生副本第二人称叙事适配的结构与手艺，未导入外部代码。yao-open-prompts 的五层结构是带货/干货口播口径，本仓把它改写成叙事体的“情绪波浪＝小兑现/新信息/坏消息”；其示例文案与人设背景未采用。不宣称这些方法已证明流量提升；好看与否以用户验收与真实观众为准。

## 现在仓库里怎样执行

```text
当前请求是研究/改造Agent → 借鉴与接入，到此结束，不自行生成作品

当前请求是写人生副本口播稿
  → fuben-write：深读 + 真实检索（≥8 路，四类质感）
  → 分类型剧情方向卡 → 用户选定
  → 场次单（可拍场景 + 判词压缩）
  → 成稿：反流水账八件武器（感官锚定/器物三现/数字判词链/拆穿旁白…）
  → 审读：追看断点 + 念稿测试 + 反流水账复检 → 分层返工
  → 交付正文逐字稿 + 钩子备选 → fuben-review 读通专项

当前请求是写普通网文 → story-short-write / story-long-write（原小说流程不变）
```

已接入的位置：

- [fuben-write](../skills/fuben-write/SKILL.md)（**现行人生副本入口**，原生抖音口播 skill）：[搜索与质感](../skills/fuben-write/references/搜索与质感.md)、[口播结构与节奏](../skills/fuben-write/references/口播结构与节奏.md)、[代入感手艺](../skills/fuben-write/references/代入感手艺.md)、[审读与改稿](../skills/fuben-write/references/审读与改稿.md)、[独立提示词](../skills/fuben-write/references/独立提示词.md)。
- [人生副本 Agent 方法](../skills/story-short-write/references/genre-styles/人生副本_Agent方法.md) 与 [主profile v13](../skills/story-short-write/references/genre-styles/人生副本实录.md)：历史与分工参考，入口已迁 fuben-write。
- [审核入口](../skills/fuben-review/SKILL.md)：按创作问题层级返工，明确独立审读与改稿分开。
- `story-setup/references/{templates,opencode,codex}/agents/` 中现有的 `story-architect`、`narrative-writer`、`character-designer`：已在副本提前分流内写入各自职责，不再只有“绕过小说规则”的说明；没有新增一个空壳 Agent 名称。
- [根路由](../AGENTS.md) 与 [调用方参考选择](../skills/story-setup/references/agent-references/agent-reference-profiles.md)：按任务动作分流，并传递对应方法片段。

采用的是重新表述、按人生副本适配的方法，没有导入外部代码或安装第三方运行平台。已经部署过的项目需通过原有 `story-setup` 同步模板；本轮没有擅自安装或启动宿主。模板接入不等于宿主已部署；本轮没有运行独立模型/观众实验，不宣称这些方法已证明流量提升。
