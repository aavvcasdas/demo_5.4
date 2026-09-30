# AGENTS.md — 本仓库 Skill 路由入口

本仓库是抖音「人生副本/剧本人生」口播**剧本**生成库：`skills/` 为创作与工具 skill，`拆文库/` 为 45 个故事段 ASR 原稿拆解（写作手法与节奏的蒸馏源，39 篇在速拆卡在册），`作品/` 为产出，`scripts/` 为**技术核对**工具（v3.0 起不再对创作设卡）。按用户意图路由：

| 用户意图 | 路由到 | 说明 |
|---|---|---|
| 写人生副本口播剧本（人生副本、剧本人生、XX 的一生、口播稿、第二人称人生体验） | [skills/fuben-write/SKILL.md](skills/fuben-write/SKILL.md) | **主链路（v3.0 提示词版，2026-09-30 换代）**：真实检索（≥8 路真实骨架）＋选题三闸 →人生时间轴（5–8 站：事件/物证/一句人话；压制→谷底→反打→释放）→三秒开场（首行即钩、签名后置）＋每 15–25 秒翻面＋结尾互动钩 →投手预演七问＋平铺扫描＋账目手算 →十项自检＋五维对标（`references/7`）→交付逐字稿＋标题/封面/首评/话题＋数据回传 |
| 审人生副本（副本审稿、口播复核、切条验收） | [skills/fuben-review/SKILL.md](skills/fuben-review/SKILL.md) | 创作审查＋读通专项；报告绑定 `body_path` 与 `body_text_sha256`（技术绑定，防旧结论背书新稿） |
| 写中文短剧/漫剧剧本、改单集剧本、剧本审读 | [.agents/skills/short-drama-write/SKILL.md](.agents/skills/short-drama-write/SKILL.md) | 第三方（zenstory-ai/drama-skills，MIT）：管短剧剧本格式与可拍性，不管资产/分镜/媒体提示词；人生副本口播走 `fuben-write` |
| 造/改 skill、体检技能库 | [.agents/skills/skill-creator/SKILL.md](.agents/skills/skill-creator/SKILL.md) | 第三方（anthropics/skills）。描述瘦身、单一职责、查重与瘦身标准 |
| 写普通短篇/长篇网文、拆书、扫榜、去 AI 味、封面、导入 | [skills/story/SKILL.md](skills/story/SKILL.md) | 网文工具箱路由（小说口径；人生副本不走此线） |
| 部署/同步环境 | [skills/story-setup/SKILL.md](skills/story-setup/SKILL.md) | 模板与 hooks 部署；`scripts/deploy-fuben-tools.py` 分发技术工具 |
| 浏览器采集 | [skills/browser-cdp/SKILL.md](skills/browser-cdp/SKILL.md) | CDP 抓取 |
| 研究/借鉴/改造 Agent | 只交方法与接入改动 | 不自动转成样稿 |
| 查找/安装新能力 | [.agents/skills/find-skills/SKILL.md](.agents/skills/find-skills/SKILL.md) | 技能生态入口：`npx skills find <关键词>` → 核安装量/来源 → `npx skills add`；skills.sh 直连失败时按该文件的 GitHub 兜底通道 |
| 会话交接打包 | [.agents/skills/handoff/SKILL.md](.agents/skills/handoff/SKILL.md) | 把当前会话压成 handoff 文档给下个 agent |

## 人生副本管线（fuben-write v3.0.3）

```text
00 简报 → 01 深读+检索(≥8路并行,四类真实骨架)+选题三闸+方向卡(用户选定)
→ 02 人生时间轴(5–8 站,事件/物证/人话;爽点四段;物证3件;兑现认领)
→ 03 成稿(首行即钩+签名后置+钩子备选 A/B/C 同批写出+分块直写,块级三问)
→ 04 投手预演七问(引原句+行号)+平铺扫描+念稿测试+账目手算表+十项自检/五维对标
→ 04b fuben-review 读通专项 → 05 自检八问 + 技术核对(fuben_run / fuben_products) → 交付
```

**v3.0 契约（2026-09-30 用户裁决：「不要这么多的限制脚本，把规则写进提示词」）**：

1. **创作规则全部在提示词里**：无烟红线、禁词表、开头铁律、对白限额、账目纪律、体量口径、结构评分 → [skills/fuben-write/SKILL.md](skills/fuben-write/SKILL.md) 与 `references/1–8`（新增 `7_自检与评分.md`、`8_拆文库与对标.md`）。
2. **脚本只剩技术核对**：`fuben_run.py`（输入/算术/指标，`--style` 可选）、`fuben_products.py`（产物齐备＋审核报告哈希绑定）、`fuben_loop.py`（报告生成/绑定）、`fuben_release.py`（发布证据）、`fuben_data.py`（数据台账）。**PASS 不是创作批准。**
3. **已删除 16 个创作类脚本**（craft/claims/viral/consistency/scene_check/setting_years/density/hype/shotmap/trial_blind/corpus/health/lint/corpus_*/audit_analyze_lib）——它们原来对禁词、开头、对白、账目档位、体量、结构、一致性下判罚；规则已并入提示词。
4. **保留的硬承诺**：真实检索（≥8 路，不调用即任务失败）、未获用户选定方向不得开写、全程无烟、账目可反算、不报「必爆」不编造来源、混合源加「剧情为虚构演绎」声明、发布后数据回填台账。
5. **阶段 05 改名**：产物为 `05_自检.md`（旧作品仍是 `05_机检.json`，`fuben_products` 用 `product_aliases` 兼容）。
6. **v3.0.1 加一步**：方向定板后必须再跑一批**定向补检索**（批号 `B<日期>-NN`、≥4 路、只进「人／事件／物证／一句人话」，未跑则该篇不得标可交付）。
7. **v3.0.3 回写一条 89 缺口**：**物证回收**——02 的物证表升级为三栏（第一次出现｜换义点｜**最后一次出现＝一句可拍动作**），阶段 3 新增「物证回收点名」三问并写进 03，阶段 5 在 05 留回收结论；04 保留复核关卡。
8. **v3.0.2 回写两条 88 教训**：①**见证链**——释放必须有人在现场看见并接住，02 加「谁在场」一行、04 加「在场的人扫描」；②**正文零算式**——数字只准用于对比/事实/背叛/动作，加减乘除与换算全部进 04 后台手算表，谷底由人的反应造成。

产物落 `作品/NN_主题/_运行/YYYY-MM-DD/`（产品清单见 [arena.runtime.json](arena.runtime.json)；`python3 scripts/fuben_products.py 作品/NN_主题` 核对产物与哈希绑定）。运行说明见 [docs/Arena运行时.md](docs/Arena运行时.md)；v3.0 改造前后对照见 [docs/改造说明-v3.0-2026-09-30.md](docs/改造说明-v3.0-2026-09-30.md)。

**scripts/ 现状（12 个文件，全部技术性）**：

| 用途 | 脚本 |
|---|---|
| 技术核对（创作期可用） | `fuben_run.py`（输入/算术/指标）、`fuben_products.py`（产物＋哈希绑定）、`fuben_loop.py report\|review`（报告生成/绑定） |
| 发布与数据 | `fuben_release.py check <作品>`（PROVISIONAL 不代发）、`fuben_data.py`（台账快照，schema 校验） |
| 共享底层 | `fuben_engine.py`（协议/严重度）、`fuben_numbers.py`（中文数字解析）、`fuben_policy.json`（口径与规则位置） |
| 拆文库维护 | `split_episodes.py`（合集切分）、`pos.py`（短语定位） |
| 仓库体检 | `test_gates.py`（软件测试＋受保护语料哈希）、`skills_audit.py`（技能库体积/描述/重复/坏链） |

**纪律**：不用任何脚本判文笔、判剧情水不水、判能不能爆——水与不好看由 04 审读人工点名并引行号；分数按 `references/7_自检与评分.md` 由写作者与审读者自评。

## 拆文库用法（v3.0 起写进创作流程）

- 写前：按 [skills/fuben-write/references/8_拆文库与对标.md](skills/fuben-write/references/8_拆文库与对标.md) 三步查——定文体标签 → 挑 2–3 篇同型样本只读 `情节节点.md` 与 `写作手法.md`「可复用点」→ 记三个数（字数、峰值位置、句均长度）。
- 写后：打五维分（开/拉/反/节/尾）与速拆卡同尺度对标，把差距写成一句话。
- 纪律：**借事实与结构，不借文本**；`拆文库/*/原文/*` 受 `tests/protected_sources.json` 哈希保护，不改写不删除。

## 技能库卫生

- 现状：在用 14 个 skill ＋归档 5 个（`skills/_archive/`）。**常驻 description 合计约 2,286 字符 > 1% listing 预算**——超预算时按调用频次整条丢描述。规则：description **≤150 字符、触发词前置**（`fuben-write` 91、`fuben-review` 55，已达标）；一个 skill 只接一件事；主体超 500 行下沉 references。
- 已归档（低频）：`story-long-write/analyze/scan`、`story-import`、`story-cover`。
- 第三方 skill 只落 `.agents/skills/`；不要 `skills/` 里留软链（会污染 `deploy-antigravity-skills.py` 的 `KNOWN_SKILLS` 断言）。
- 多份拷贝是故意的：`check-ai-patterns.js`、`story-profile.js`、`story_hook_core.js` 由测试强制逐字节一致。
- 体检：`python3 scripts/skills_audit.py [--strict|--json]`。

## 手艺与事实边界

- 创作标准以 [2_选题与结构.md](skills/fuben-write/references/2_选题与结构.md)（选题三闸＋爽点四段）、[3_口播与节奏.md](skills/fuben-write/references/3_口播与节奏.md)（三秒/翻面/互动钩）、[7_自检与评分.md](skills/fuben-write/references/7_自检与评分.md)（十项清单＋五维对标）为核心；[5_代入感与禁忌.md](skills/fuben-write/references/5_代入感与禁忌.md) 保留不水纪律与红线。
- 保留用户给定事实；检索来源注明；不编造数据与授权；不报「必爆」；技术核对 PASS 只说明无机械阻断。
- 独立可复制提示词（不装 skill）：[6_独立提示词.md](skills/fuben-write/references/6_独立提示词.md)。
