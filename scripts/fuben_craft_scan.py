#!/usr/bin/env python3
"""Read-only 读感扫描：按 fuben-craft 的十二条 slop 给出带行号的候选，永不 BLOCK。

对应文档：skills/story-short-write/references/fuben-craft/口播腔调与反AI味.md（§B 十二条、§C 保留清单）。

这不是质量门禁，也不打分：
- 正则只能发现「形状像」的句子，不能判断它在语境里是不是问题。
- 每条候选都必须由人回到正文读一遍再决定改不改；§C 保留清单命中的项默认**不改**。
- 本脚本不修改任何文件，不写审核结论，不影响 fuben_run.py 的 BLOCK/REVIEW 判定。
- 创作效果以 fuben-review 的证据化审读与用户验收为准。

用法:
    python3 scripts/fuben_craft_scan.py 作品/NN_主题/正文.md
    python3 scripts/fuben_craft_scan.py 作品/NN_主题/ --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 检测规则
# 每条 = (编号, 名称, 强弱, 正则或函数, 为什么是问题)
# 强弱沿用 humanizer 的分级：strong = 见一次就值得改；weak = 需要同段还有其他毛病。

STRONG_PATTERNS = [
    ('B1', '口号收尾', 'strong',
     re.compile(r'(人生就|人这一生|说白了|归根结底|所以说|记住|愿你|这才是)(.{0,14})$'),
     '结尾用格言/对仗句收束 = 说教税；语料正解是器物或动作收束（28 号的碗、20 号的奶茶、79 号的请帖）。'),
    ('B2', '抽象总结代替戏', 'strong',
     re.compile(r'(大家都|所有人都|全场|众人|一群人)?(服了|震惊了|傻眼了|惊呆|炸了|沸腾|鸦雀无声|气氛(一下子)?(凝固|尴尬|降至冰点))|论证了一(晚上|整天|路)|后来(你|他|我)?(就)?(解决|搞定|赢)了'),
     'telling instead of showing：最好看的一场被旁白替观众看完了。展开成交锋与反应。'),
    ('B3', '假动作主语', 'strong',
     re.compile(r'(沉默|尴尬|紧张|气氛|空气|压力|情绪|时间)(蔓延|扩散|凝固|停滞|停止|涌上|包裹|填满)|(评论区|群里|全场|整个)(炸了|炸开|沸腾了|安静了)'),
     'stop-slop false agency：无生命物做人的动作。指名谁做了什么（17 号静场给的是三种具体躲避动作）。'),
    ('B4', '梗原文搬运', 'strong',
     re.compile(r'(全网|网上|大家|网友们?|互联网)(都)?(在传|在说|管这个叫|称之为|流行|火了)|最近(全网|网上)都在'),
     '旁白介绍热梗 = 把词典放在门口。梗要从人物嘴里出来，并被剧情重新定价。'),
    ('B12', '工程词泄漏', 'strong',
     re.compile(r'(伏笔|钩子|侧面描写|第一幕|第二幕|爽点|情绪值|节奏板|字数约|本段|下一段|setup|payoff)'),
     '设计语言混进口播正文；check-degeneration.js 也在查这一项。'),
]

WEAK_PATTERNS = [
    ('B7', '情绪播报', 'weak',
     re.compile(r'你(突然|忽然|一下子)?(觉得|感到|感觉到)?(很|有点|特别|十分)?(破防|委屈|心酸|难过|羞愧|自卑|无力|崩溃|窒息)'),
     '情绪是结论不是证据。过身体/器物/数字三通道（80 号正例：「揣得很轻 跟做贼一样」）。'),
    ('B8', '万能旁观者', 'weak',
     re.compile(r'(大家|所有人|众人|全场|周围(的)?人)(都)?(投来|露出|给出|报以)'),
     '群体没有脸等于没有群体。给三种不同的具体反应，或只写一个人的一件事。'),
    ('B9', '时间戳分段器', 'weak',
     re.compile(r'^(周[一二三四五六日末]|星期[一二三四五六日]|第[一二三四五六七八九十]+[天周月年]|那[天晚]|当天|第二天|几天后|几周后|几个月后|月底|年初|去年|今年|那天)[，,、]?\s*\S'),
     '时间只能嵌在动作句里，且仅当时间本身是信息（约定时刻、掐表成绩、倒计时）才保留。'),
    ('B10', '旁白讲解员', 'weak',
     re.compile(r'^(你要知道|你得知道|要知道|这就是|所谓的|换句话说|也就是说|简单来说|其实这就是)'),
     'narrator-from-a-distance：第二人称一旦解释概念，代入就断了。'),
    ('B11', '不是X而是Y', 'weak',
     re.compile(r'(这|那|它)?(不是|并非)(.{1,12})[,，、]?\s*(而是|是|就是)(.{1,12})$'),
     'humanizer §1：负面半句若没人主张过，正面半句只是显得更大。例外：负面半句纠正观众真持有的信念，且正文里被演出来。'),
    ('B6', '排比三件套', 'weak',
     re.compile(r'^(\S{1,4})\s+(\S{1,4})\s+(\S{1,4})$'),
     'stop-slop：two items beat three。除非第三拍翻面（17 号「越过她、越过前面的大哥、越过了一排又一排的人」）。'),
]

# 保留清单（humanizer 的 When not to act）：命中即提醒「不要误清」，不是问题。
PRESERVE_PATTERNS = [
    ('C-方言俚语', re.compile(r'(嘛|啥子|咋|咯|呗|哈|咧|嚯|哥们|爷们|老铁|兄弟)'),
     '市井俚语与方言语气词是人味；80 号审读已正确裁决保留「羽化登仙」。'),
    ('C-角色胡诌', re.compile(r'(老话(说|真有道理)|俗话说|人家都说|我跟你讲|你听我说|这叫)'),
     '角色在骗自己（39 号「想来想去还是没钱」、29 号急了学）。语气能听出胡诌就保留。'),
    ('C-答非所问玩笑', re.compile(r'(你说|你回|你只说了?)\s*[:：]?\s*\S{1,12}$'),
     '故意答非所问可以是玩笑本身（80 号「让人吃口鱼」＝蟹柳是鱼糜仿蟹）。有语境支撑就保留。'),
    ('C-具体怪数字', re.compile(r'\d+(\.\d+)?\s*(块|元|毛|分|厘米|米|公斤|斤|秒|分钟|小时|次|条|个)'),
     '具体数字是共情通道 C（68块5 / 48,452.31 / 15块8毛6 / 4,000次）。别为了「去数字」清掉。'),
]


def _lines(text: str):
    return text.split('\n')


def scan_fragmentation(lines):
    """B-碎行：连续 ≤4 字的超短行超过 3 行，或空行夹在两个超短行之间（冒充停顿）。"""
    out = []
    run = []
    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#'):
            run = []
            continue
        if len(line) <= 4:
            run.append((idx, line))
        else:
            if len(run) >= 3:
                out.append((run[0][0], run[-1][0], [x[1] for x in run]))
            run = []
    if len(run) >= 3:
        out.append((run[0][0], run[-1][0], [x[1] for x in run]))
    return out


def scan_unexplained_jargon(lines):
    """B5-术语/新词首现无解释：引号式口号、"XX主义/XX学/XX型人格" 等新造词首次出现时，
    前后 3 行内没有任何解释性上下文（管…叫 / 意思是 / 就是 / 指的是 / 一句人物台词）。
    这是启发式，误报率不低，必须人读。"""
    out = []
    expl = re.compile(r'(管这个叫|管.{0,6}叫|意思是|指的是|就是说|说白了|他们叫|圈内叫|圈内管|这个词'
                      r'|网上是这么解释|这么解释|这么说的|解释的|所谓的|一句话|你后来才知道|叫这个|喊这个)')
    # 新造词：≥4 字整体，后缀只收多字词（去掉裸「学」「税」——会误伤「第一课学什么」「放学」这类正常句子）。
    # COINED_STRONG 一看就是新造的人设词；COINED_WEAK 是日常词，命中只作提醒（误报率高）。
    coined_strong = re.compile(r'[\u4e00-\u9fa5A-Za-z0-9]{2,8}(?:型人格|综合症|综合征|经济学|刺客)')
    coined_weak = re.compile(r'[\u4e00-\u9fa5A-Za-z0-9]{2,8}(?:主义|自由|焦虑|通胀|复利)')
    # 常见词不当新造词处理（否则会误伤「资本主义」这类日常词汇）。
    common = {'资本主义', '社会主义', '消费主义', '个人主义', '集体主义', '乐观主义', '悲观主义',
              '唯物主义', '形式主义', '官僚主义', '自由主义', '身材焦虑', '容貌焦虑', '信息自由',
              '财务自由', '通货膨胀', '复利'}
    # 引号式口号 / 语录母版：整段搬运时通常成对出现。
    slogan = re.compile(r'[「『"“].{4,}[」』"”]')

    # 逐词判定：只要**任意一次**出现附近有解释，就算已解释；全篇都没解释才报第一次出现。
    # 口播常见「先命名后解释」（17 号 L23 出术语、L25「网上是这么解释的」），所以窗口向后放宽。
    term_hits = {}
    for idx, raw in enumerate(lines, start=1):
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        window = '\n'.join(lines[max(0, idx - 5):idx + 12])
        explained = bool(expl.search(window))
        for m in coined_strong.finditer(s):
            term_hits.setdefault(m.group(0), {'strength': 'strong', 'first': idx, 'explained': True})
            rec = term_hits[m.group(0)]
            rec['first'] = min(rec['first'], idx)
            rec['explained'] = rec['explained'] and explained
        for m in coined_weak.finditer(s):
            if m.group(0) in common:
                continue
            rec = term_hits.setdefault(m.group(0), {'strength': 'weak', 'first': idx, 'explained': True})
            rec['first'] = min(rec['first'], idx)
            rec['explained'] = rec['explained'] and explained
        for m in slogan.finditer(s):
            word = m.group(0).strip('「」『』""“”')
            rec = term_hits.setdefault(word, {'strength': 'weak', 'first': idx, 'explained': True})
            rec['first'] = min(rec['first'], idx)
            rec['explained'] = rec['explained'] and explained

    for word, rec in sorted(term_hits.items(), key=lambda kv: kv[1]['first']):
        if not rec['explained']:
            out.append((rec['first'], word, rec['strength']))
    return out


def scan_ending(lines):
    """B1-口号收尾：只看最后 12 行非空行，命中格言句式或连续两个金句。"""
    tail = [(i, l.strip()) for i, l in enumerate(lines, start=1) if l.strip() and not l.strip().startswith('#')]
    if not tail:
        return []
    last = tail[-12:]
    hits = []
    for idx, line in last:
        for code, name, strength, rx, why in STRONG_PATTERNS:
            if code == 'B1' and rx.search(line):
                hits.append((idx, line, name, why))
    return hits


def scan(path: Path):
    text = path.read_text(encoding='utf-8-sig')
    if not text.strip():
        raise ValueError('empty body')
    lines = _lines(text)

    candidates = []
    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        for code, name, strength, rx, why in STRONG_PATTERNS + WEAK_PATTERNS:
            if code == 'B1':
                continue  # 口号收尾只在结尾判，避免误伤中段
            if rx.search(line):
                candidates.append(dict(code=code, name=name, strength=strength, line=idx,
                                       evidence=line, why=why))

    for idx, line, name, why in scan_ending(lines):
        candidates.append(dict(code='B1', name=name, strength='strong', line=idx,
                               evidence=line, why=why + '（位于结尾 12 行内）'))

    for start, end, chunk in scan_fragmentation(lines):
        candidates.append(dict(code='B-碎行', name='碎行堆叠', strength='weak', line=start,
                               evidence=' / '.join(chunk),
                               why=f'第 {start}-{end} 行连续 {len(chunk)} 行 ≤4 字；'
                                   'stop-slop dramatic fragmentation。每行须携带新信息或动作。'))

    for idx, word, strength in scan_unexplained_jargon(lines):
        candidates.append(dict(code='B5', name='术语/新词首现无解释', strength=strength, line=idx,
                               evidence=word,
                               why='口播是线性媒介，观众不能回翻。让剧情自己解释，不用旁白下定义。'
                                   '（启发式，误报率高，必须回读上下文：解释可能落在术语后面几行）'))

    preserved = []
    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        for name, rx, why in PRESERVE_PATTERNS:
            if rx.search(line):
                preserved.append(dict(rule=name, line=idx, evidence=line, note=why))

    # 降级：如果「所有人都傻眼了」这类总结句前后 4 行内已经有具体的身体／器物／数量细节，
    # 它可能只是收束一笔而不是替代整场戏（17 号 N7 就是「所有人都傻眼了」紧跟「老太太下巴差点掉在地上」）。
    # 这种情况降为 weak，交给人读，不强改。
    concrete = re.compile(r'(手|眼|脸|嘴|唇|肩|脖|背|腿|脚|下巴|眉|指|腕|腰|头|碗|杯|筷|勺|锅|瓶|盒|袋|包|桌|椅|门|窗|纸|牌|手机|屏幕|钥匙|钱|账单|短信|\d)')
    for c in candidates:
        if c['strength'] == 'strong' and c['code'] in ('B2', 'B3', 'B8'):
            window = '\n'.join(lines[max(0, c['line'] - 5):c['line'] + 4])
            if len(concrete.findall(window)) >= 3:
                c['strength'] = 'weak'
                c['why'] += '（降级：前后已有具体身体／器物细节，可能只是收束一笔；回读确认是否替代了整场戏。）'

    counts = {}
    for c in candidates:
        counts[c['code']] = counts.get(c['code'], 0) + 1

    return dict(
        path=str(path),
        status='ADVISORY',
        characters=len(re.sub(r'\s', '', text)),
        lines=len([l for l in lines if l.strip()]),
        candidate_count=len(candidates),
        counts_by_code=counts,
        candidates=sorted(candidates, key=lambda x: (0 if x['strength'] == 'strong' else 1, x['line'])),
        preserved_human_voice=preserved[:40],
        preserved_note='保留清单命中项默认不改：一个 tell 的分量与「认真写作者故意这么写的概率」成反比。',
        disclaimer='只读扫描；不打分、不判好看、永不 BLOCK、不写审核结论。'
                   '每条候选必须回正文读一遍再决定；创作结论由 fuben-review 按证据下。'
                   '已知盲区：B5 只覆盖带构词后缀的新造词（X主义/X型人格/X综合症/X经济学）与引号式口号，'
                   '纯俚语黑话（充碳、耍起、练起嘛）工具不猜，靠人读；'
                   '开头追看、笑点引擎、蓄势兑现、共情通道四项**没有任何正则能判**，必须人读。',
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', help='正文文件或作品目录（目录时取 正文.md）')
    parser.add_argument('--json', action='store_true', help='输出 JSON')
    parser.add_argument('--strong-only', action='store_true', help='只列 strong 候选')
    args = parser.parse_args(argv)

    path = Path(args.path)
    path = path / '正文.md' if path.is_dir() else path
    try:
        report = scan(path)
    except (OSError, ValueError) as exc:
        print(f'ERROR: 读不到正文或正文为空：{path}（{exc}）', file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f'读感扫描 · {report["path"]} · {report["status"]}')
    print(f'{report["characters"]} 字 / {report["lines"]} 非空行 / 候选 {report["candidate_count"]} 条')
    print('-' * 72)
    shown = [c for c in report['candidates'] if not args.strong_only or c['strength'] == 'strong']
    if not shown:
        print('无候选。注意：无候选 ≠ 好看；开头追看、笑点引擎、蓄势兑现必须人读。')
    for c in shown:
        print(f'L{c["line"]:<4} [{c["strength"]:^6}] {c["code"]} {c["name"]}')
        print(f'      原句：{c["evidence"]}')
        print(f'      为什么：{c["why"]}')
    if report['preserved_human_voice']:
        print('-' * 72)
        print(f'保留清单命中 {len(report["preserved_human_voice"])} 处（默认不改）：')
        for p in report['preserved_human_voice'][:12]:
            print(f'L{p["line"]:<4} {p["rule"]}: {p["evidence"]}')
        print('  …' if len(report['preserved_human_voice']) > 12 else '')
    print('-' * 72)
    print(report['disclaimer'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
