#!/usr/bin/env python3
"""人生副本「可拍剧本」工艺门禁（craft gate，v3.0）。

只留能真出错的确定性检查（用户 2026-09-29 裁决：审核「删到会咬人就行」）：
  红线      NO_SMOKE（用户裁决 2026-09-23：剧本/旁白/钩子/短版不得出现烟）
  语感      BANWORD（书面腔/AI 腔清单，见 5_代入感与禁忌·四）
  开头      OPENING（禁定义前置、系统提示≤2 行、首行超载；见 3_口播与节奏·一）
  对白      DIALOGUE（引语帧/钉子句/乒乓回合计数；v3.0 取消「短文豁免」）
  账目      LEDGER（位数主张与档位主张须与同段金额对账；数字判词链的机检下限）
  体量      VOLUME（旁白轨字数：低于下限＝REVIEW，高于参考带＝NOTE）
  可拍性    SCENE（剧本稿的场数与「每场有没有画面行」）

**v3.0 修掉的两个自废门禁**：
① 旧版对 <800 汉字的稿件把对白占比归零（"短文样本失真"）——v2.0 恰好把稿子压到
   600 字级，于是「旁白驱动、引语 ≤10%」这条铁律在最需要它的长度上自动失效；
   现在任何长度都算。
② 旧版体量出带只报 NOTE，且 policy 里写了「引用用户授权原话即可闭环」——等于永不红灯。
   现在低于 `volume_floor` 是 REVIEW，必须处置（补场或把题面明确登记为单事件段子）。

协议与 fuben_engine 一致：BLOCK=可复现的明确违例（只保留红线级）；REVIEW=上下文
候选，由 04 审读处置（修复或写明保留理由）；NOTE=描述信息。门禁不判好坏、不判文笔，
PASS_WITH_REVIEW 不代表开头留得住、账目已核或片子能拍——那些是人的判断。
profile=reference（原文校准）不受本账号红线约束，整个 craft 检查豁免。
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from collections import Counter
import sys

from fuben_numbers import number, numeric, NUM_PATTERN

# 词表默认值；可被 fuben_policy.json 的 "craft" 段覆盖（口径改这里，不改代码）。
DEFAULTS = {
    'smoke_terms': r'香烟|电子烟|烟草|抽烟|吸烟|点烟|烟头|烟灰|烟味|一支烟|一根烟|半包烟|叼着烟|吞云吐雾|二手烟',
    'ban_words': ['首先', '其次', '然而', '随着', '不禁', '值得一提的是', '眼眶一热', '五味杂陈',
                  '五雷轰顶', '不由得', '感慨万千', '心潮澎湃', '不知不觉', '似乎在诉说着'],
    'definition_upfront': ['先校准', '先说说', '先讲讲', '今天我们来聊', '今天聊聊', '大家好',
                           '先来科普', '科普一下', '名词解释', '口径如下', '设定如下', '规则如下',
                           '先对齐', '先统一口径', '解释一下', '世界观设定'],
    'sys_prompt_max_lines': 2,
    'head_max_chars': 50,
    'nail_over': 12,
    'quote_pct_over': 10.0,
}
DEFINITION_WINDOW = 160  # 定义前置只看开头前 160 字符（含标题签名段）

# 剧本形态识别：场标题行与「画面/旁白」标签行（格式契约见 references/0_剧本格式与分场表.md）
SCENE_HEADER = re.compile(r'^#{2,4}\s*场\s*\d+|^场\s*\d+[（(]', re.M)
SCENE_VISUAL = re.compile(r'^\s*(画面|镜头|视觉)\s*[：:]', re.M)
VO_LINE = re.compile(r'^\s*(旁白|你（旁白）|旁白（[^）]*）|VO)\s*[：:]')

# 引语帧：本系列 ASR 体不打引号，用「动词+逗号」引导；「」引号兼容。
CUE_RE = re.compile(r'(讲|说|问|喊|回|答|补|念叨|嘟囔|吼)[，：]')
QUOTE_BRACKETS = re.compile(r'[「“]([^」”\n]{1,60})[」”]')
PP_SUBJECT = re.compile(r'^[你我她他][^，。\n]{0,12}(?:讲|说|问|喊)[，：]')

# Markdown 表格/链接行不属于口播正文（文稿/表格里会出现 A8 式 ID、URL 数字串等假信号）
IGNORE_LINE = re.compile(r'^(?:[#|]|https?://)|\|\|.*\|\|')
DIGIT_CLAIM = re.compile(r'(?P<n>[零〇一二两三四五六七八九十百\d]{1,4})\s*个?\s*位数')
UNIT_CLAIM = re.compile(r'(?P<kind>[ABC])(?P<digits>\d)(?:\.(?P<dec>\d))?(?![0-9])')
# 说法/对比/否认语境不构成资产档位断言；定义句（A 是资产）同样排除。
UNIT_SKIP = re.compile(r'离|还差|差[一二两三四五六七八九十\d]|以为|不是|而是|那个|这个|比|像|晒|管那叫|组合|号称|呢$|吗$|？|\?|是资产|是负债|代表|即|口径|意思')
MONEY_CONTEXT = re.compile(r'钱|账|存款|押金|价|费|工资|分红|身家|资产|借|还钱|还账|把账|付|赔|时薪|日结|月薪|流水|欠款|贷款|本金|余额|零头|转账|赎|买')
AMOUNT_TAIL = re.compile(rf'(?P<num>{NUM_PATTERN})\s*(?P<unit>[块元毛])?\s*(?P<tail>[一二两三四五六七八九])?')

ACT_HINT = re.compile(r'(拿|掏|扛|摆|拍|递|扔|端|推|拉|掀|按|敲|拧|掰|勒|抬|拎|扯|扒|挪|垫|夹|塞|揣|举|走|跑|爬|跳|站|坐|蹲|躺|睡|翻|搂|抱|背|拖|数|打|吃|喝|看|听|笑)')
HAN_RE = re.compile(r'[\u4e00-\u9fff]')


def _cfg(policy):
    cfg = dict(DEFAULTS)
    if isinstance(policy, dict) and isinstance(policy.get('craft'), dict):
        cfg.update(policy['craft'])
    return cfg


def is_screenplay(text):
    """有场标题（`## 场N` 或 `场N（…）`）→ 按可拍剧本口径检查。"""
    return bool(SCENE_HEADER.search(text))


def split_tracks(text):
    """把剧本切成旁白轨与对白轨：旁白＝配音要念的叙述行，对白＝角色显式台词行。

    非剧本稿（纯逐字稿）没有标签行：旁白轨＝全文，对白轨＝空。
    """
    vo, dl, label_skip = [], [], re.compile(r'^\s*(画面|镜头|视觉|音效|声音|字幕|转场|时长|秒数|生产|备注)\s*[：:]')
    speaker = re.compile(r'^\s*(?!\s*(?:画面|镜头|视觉|旁白|VO|音效|声音|字幕|转场|时长|秒数|生产|备注)\s*[：:])[\u4e00-\u9fffA-Za-z（）()·]{1,8}（[^）]{0,24}）?\s*[：:]')
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or IGNORE_LINE.match(line):
            continue
        if VO_LINE.match(line):
            vo.append(re.sub(r'^\s*(?:旁白|VO|你（旁白）[^）]*）?)\s*[：:]', '', line))
        elif label_skip.match(line) or line.startswith('|') or line.startswith('-'):
            continue
        elif speaker.match(line):
            dl.append(re.sub(r'^[^：:]{1,16}[：:]', '', line))
        else:
            vo.append(line)  # 无标签行按旁白处理（逐字稿形态）
    return '\n'.join(vo), '\n'.join(dl)


def scene_rows(text):
    """按场标题切场，返回 [(场标题, 该场文本)]；非剧本稿返回空表。"""
    lines = text.splitlines()
    idx = [i for i, l in enumerate(lines) if SCENE_HEADER.match(l.strip())]
    if len(idx) < 2:
        return []
    out = []
    for n, start in enumerate(idx):
        end = idx[n + 1] if n + 1 < len(idx) else len(lines)
        out.append((lines[start].strip().lstrip('#').strip(), '\n'.join(lines[start:end])))
    return out


def _stanza_of(lines, index):
    start = index
    while start > 0 and lines[start - 1].strip():
        start -= 1
    end = index
    while end + 1 < len(lines) and lines[end + 1].strip():
        end += 1
    return lines[start:end + 1]


def _han_count(text):
    return len(HAN_RE.findall(text))


def _amounts_in(stanza_lines):
    """同段金额候选：带 块/元/毛 单位的口语数额，或有金钱语境段里的 ≥3 位数值。"""
    values = []
    has_context = any(MONEY_CONTEXT.search(l) for l in stanza_lines)
    for line in stanza_lines:
        for m in AMOUNT_TAIL.finditer(line):
            unit = m['unit']
            if not unit and not has_context:
                continue
            value = numeric(m['num'], colloquial=True)
            if value is None:
                continue
            if unit == '毛':
                continue  # 一毛/两块三毛级别不参与档位对账
            if unit and m['tail']:
                extra = numeric(m['tail'], colloquial=True)
                if extra is not None:
                    value = value + extra / 10  # 十八块四 → 18.4
            if unit is None and abs(value) < 300:
                continue  # 三口/三回/二十七 这类非钱数字不入场
            values.append(value)
    return values


def _digit_count(value):
    try:
        integer = abs(int(number(str(value), colloquial=True))) if not isinstance(value, (int, float)) else abs(int(value))
    except Exception:
        integer = abs(int(value))
    return len(str(integer)) if integer else 1


def ledger_rows(text):
    """位数主张与 A/B/C 档位主张 ↔ 同段金额的对账表（描述性，供 04 闭环）。"""
    lines = text.splitlines()
    rows = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or line.startswith('#') or IGNORE_LINE.match(line):
            continue
        stanza = [l for l in _stanza_of(lines, i) if not IGNORE_LINE.match(l.strip())]
        amounts = _amounts_in(stanza)
        for m in DIGIT_CLAIM.finditer(line):
            claim = numeric(m['n'], colloquial=False)
            if claim is None or not (1 <= claim <= 12):
                continue
            if amounts:
                matched = any(_digit_count(v) == claim for v in amounts)
                status = 'consistent' if matched else 'mismatch'
            else:
                status = 'absent'
            rows.append({'kind': 'digit', 'line': i + 1, 'claim': line, 'digits': claim,
                         'amounts': amounts, 'status': status})
        for m in UNIT_CLAIM.finditer(line):
            if UNIT_SKIP.search(line) or UNIT_SKIP.search(stanza[0] if stanza else ''):
                continue
            digits = int(m['digits'])
            dec = m['dec']
            lo = 10 ** (digits - 1)
            hi = 10 ** digits
            if dec:
                lo, hi = int(dec) * 10 ** (digits - 1), (int(dec) + 1) * 10 ** (digits - 1)
            if amounts:
                matched = any(lo <= abs(v) < hi for v in amounts)
                status = 'consistent' if matched else 'mismatch'
            else:
                status = 'absent'
            rows.append({'kind': 'scale', 'line': i + 1, 'claim': line, 'unit': m['kind'] + m['digits'] + ('.' + dec if dec else ''),
                         'range': [lo, hi], 'amounts': amounts, 'status': status})
    return rows


def dialogue_stats(text):
    cues, quoted = 0, 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or IGNORE_LINE.match(line):
            continue
        for m in QUOTE_BRACKETS.finditer(line):
            quoted += _han_count(m.group(1))
        m2 = CUE_RE.search(line)
        if m2:
            cues += 1
            quoted += _han_count(line[m2.end():])
    total = _han_count(text) or 1
    return cues, quoted, round(quoted / total * 100, 1)


def pingpong_hits(text):
    hits = []
    run = []
    for i, raw in enumerate(text.splitlines(), 1):
        if PP_SUBJECT.match(raw.strip()):
            first = raw.strip()[0]
            group = 0 if first in '你我' else 1
            if run and run[-1][1] == group:
                run = [(i, group)]
            else:
                run.append((i, group))
                if len(run) >= 3:
                    hits.append((run[0][0], i))
        elif raw.strip():
            run = []
    return hits


NON_SPOKEN_LINE = re.compile(r'^\s*(画面|镜头|视觉|字幕|音效|转场|BGM)\s*[：:]')
SPOKEN_TAG = re.compile(r'^([\u4e00-\u9fffA-Za-z0-9（）()·]{1,12})\s*[：:]\s*(.*)$')


def spoken_head(text):
    """开头铁律与签名句只看"要念出来的那一条轨"。

    v3.0 的剧本稿以 `#` 标题＋`>` 说明开头，紧跟 `## 场1` 与 `画面：` 行——若按文件行号量开头，
    首行永远数到标题、签名句永远"太晚"。这里跳过版式行；剧本形态再去掉画面/字幕/音效/转场行，
    并把「旁白：」「前台（提示）：」的标签头去掉。逐字稿形态（79–87）不受影响：它们不以标题行开头。
    """
    screenplay = is_screenplay(text)
    kept = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            kept.append('')  # 空行是分段依据（系统提示按自然段数行），不能丢
            continue
        if line.startswith(('#', '>', '---', '```', '|')):
            continue
        if screenplay:
            if NON_SPOKEN_LINE.match(line):
                continue
            m = SPOKEN_TAG.match(line)
            if m:
                line = m.group(2).strip() or line
        if line:
            kept.append(line)
    return '\n'.join(kept)



CN_NUM = re.compile(r'[一二三四五六七八九十百千万亿两零〇0-9]+')
QUANT_UNITS = r'年|次|块|元|毛|角|斤|公斤|克|顿|节|千卡|大卡|卡|岁|天|个月|周|排|行|笔|列|串|口|趟|回|张|台'
# 「一个/一样/一下/一半」是中文高频虚指，不算数词堆；只有带记账单位的量词才计入预算。
CN_QUANT = re.compile(r'(?:[一二三四五六七八九十百千万亿两零〇0-9][一二三四五六七八九十百千万亿两零〇0-9]*)\s*(?:'
                      + QUANT_UNITS + r')|(?:一\s*(?:年|次|块|元|斤|公斤|千卡|大卡|顿|节|天|岁))')


def number_budget(text, cfg, finding, path=None):
    """v3.1.0 数字预算：只量可念轨（旁白＋台词），画面/字幕里的数字不计。

    成因：v3.0 的 6 份 reference 一路把「具体数字」当美德（抽象要落到数字、判词要能反算、
    十件真事压成一句带数字的话），却没有一条上限；`fuben_density` 自述是描述性读数、
    不是门禁。结果首篇样稿 88 数字串 79.8/千字、量词数串 43.6/千字，比被批评的 87 还密，
    「三百」复现 4 次、「三年」当装饰词 4 次——读起来像对账，不像戏。
    """
    out = []
    spoken = spoken_head(text)
    han = _han_count(spoken)
    if han < 120:                      # 短样本上比例无意义（同对白口径）
        return out
    caps = {
        '数字串': (len(CN_NUM.findall(spoken)) / han * 1000, float(cfg.get('number_string_per_1k_max', 70.0))),
        '量词数串': (len(CN_QUANT.findall(spoken)) / han * 1000, float(cfg.get('quantifier_per_1k_max', 20.0))),
    }
    for name, (value, cap) in caps.items():
        if value > cap:
            out.append(finding('NUMBER_STUFFING', 'REVIEW', 'style',
                              f'{name}密度 {value:.1f}/千字，超上限 {cap:.0f}（全库最高基线：数字串 86＝59.9、量词数串 86＝15.6、87＝61.6/14.6）——数词堆不等于实在：留 1—2 处能反算的账，其余换成物件或动作',
                              file=path, evidence=f'{name}={value:.1f}/千 cap={cap:.1f} 汉字={han}'))
    rep_max = int(cfg.get('number_repeat_max', 3))
    rep = [(k, v) for k, v in Counter(CN_NUM.findall(spoken)).items() if len(k) >= 2 and v > rep_max]
    for k, v in sorted(rep, key=lambda x: -x[1]):
        out.append(finding('NUMBER_REPEAT', 'REVIEW', 'style',
                          f'同一个数「{k}」在可念轨出现 {v} 次（>{rep_max}）：数字复现只能当一次笑点，'
                          f'第二次起必须换承载物（一张单据、一件器物、一个动作），否则是把同一句话说了三遍',
                          file=path, evidence=f'token={k} count={v}'))
    spans = [(w, spoken.count(w)) for w in cfg.get('decoy_span_words', []) if spoken.count(w) > int(cfg.get('decoy_span_max', 2))]
    for w, n in spans:
        out.append(finding('DECOY_SPAN', 'NOTE', 'style',
                          f'「{w}」出现 {n} 次：时间跨度交代一次就够，反复挂"三年/五年"是装饰不是重量（87 通篇 0 次）',
                          file=path, evidence=f'word={w} count={n}'))
    return out


def opening_findings(text, cfg):
    """开头铁律的可机检子集（硬规见 3_口播与节奏·一）。

    场景行号口径（机械可分辨的下限，非最终裁决，人审复核标记线索能亲手「采」的物件/动作/人名/具体地点）：
      签名＝开头非空首行自带「副本/今天要体验的人生副本/最近…都在传/大家管这叫」的提示基调；
      系统提示＝接下来的「系统提示」行头及其下一行（仅认 <=2 行笑话形态）；
      首个场景行＝此后第一个同时含动作动词词典与具体名词词典的非空行；
      名词词典＝本系列家常物件/身体机构/场所/金额小字/年龄谱/学称级标/C 段标记。
    """
    text = spoken_head(text)
    out = {}
    lines = [l for l in text.splitlines() if l.strip()]
    head = re.sub(r'\s+', '', text)[:DEFINITION_WINDOW]
    out['definer'] = next((w for w in cfg['definition_upfront'] if w in head), None)
    out['sig'] = bool(re.search(r'今天.{0,4}体验.{0,6}人生副本', head[:120])) if lines else False
    # v2.0：签名句位置（1-based 非空行号）——要求出现在第 2–3 行，首行留给钩
    out['sig_line'] = next((i for i, l in enumerate(lines[:5], 1)
                            if re.search(r'今天.{0,4}体验.{0,6}人生副本', l)), None)
    first = lines[0] if lines else ''
    out['head_len'] = len(re.sub(r'\s', '', first))
    stanzas = [s for s in re.split(r'\n\s*\n', text) if s.strip()]
    sys_lines = None
    for s in stanzas[:3]:
        sl = [l.strip() for l in s.splitlines() if l.strip()]
        if sl and sl[0] in ('系统提示', '【系统提示】'):
            sys_lines = len(sl) - 1
            break
    if sys_lines is None and stanzas:
        single = [l.strip() for l in text.splitlines() if l.strip()]
        for idx, l in enumerate(single[:6]):
            if l in ('系统提示', '【系统提示】'):
                sys_lines = 1
                break
    out['sys_lines'] = sys_lines
    return out


def craft_checks(text, path, profile, policy, finding):
    """返回 craft findings；finding 为 fuben_engine.finding。"""
    cfg = _cfg(policy)
    result = []
    if profile == 'reference':
        return result  # 原文校准不施加本账号红线（烟意象、禁词、档位口径属成品约束）

    for no, line in enumerate(text.splitlines(), 1):
        if re.search(cfg['smoke_terms'], line):
            result.append(finding('NO_SMOKE', 'BLOCK', 'policy',
                                  '用户红线（2026-09-23）：正文/钩子/短版不得出现吸烟·电子烟·烟草；改用等价感官比喻',
                                  file=path, line=no, evidence=line[:120]))
    for w in cfg['ban_words']:
        hits = [i for i, line in enumerate(text.splitlines(), 1) if w in line]
        if hits:
            result.append(finding('BANWORD', 'REVIEW', 'style',
                                 f'书面腔/AI 腔禁词「{w}」命中 {len(hits)} 处（5_代入感与禁忌·四清单）；逐处改写或说明保留理由',
                                 file=path, line=hits[0], evidence='; '.join(text.splitlines()[i - 1].strip() for i in hits[:4])[:160]))

    op = opening_findings(text, cfg)
    if op['definer']:
        result.append(finding('DEFINITION_UPFRONT', 'REVIEW', 'style',
                              f"开头 {DEFINITION_WINDOW} 字内出现讲解腔标记「{op['definer']}」——黄金 3 秒禁定义前置，名词解释后置到剧情第一次用到的地方（3_口播与节奏·一）",
                              file=path, line=1, evidence=''.join(l for l in text.splitlines() if l.strip())[:80]))
    if op['sys_lines'] is not None and op['sys_lines'] > cfg['sys_prompt_max_lines']:
        result.append(finding('SYS_PROMPT_OVER', 'REVIEW', 'style',
                              f"系统提示 {op['sys_lines']} 行，超上限 {cfg['sys_prompt_max_lines']} 行；须压成 ≤2 行笑话，不是说明书",
                              file=path, evidence='系统提示'))
    if op['head_len'] > cfg['head_max_chars']:
        result.append(finding('HEAD_OVERLOAD', 'REVIEW', 'style',
                              f"首行 {op['head_len']} 字，超开头一口气预算 {cfg['head_max_chars']} 字；拆行或砍修饰",
                              file=path, line=1))
    if text.strip() and not op['sig']:
        result.append(finding('SIGNATURE_ABSENT', 'NOTE', 'style',
                             '未见「今天你要体验的人生副本是…」签名句（v2.0 要求放在第 2–3 行，首行留给钩）；刻意不用请在 00_简报记录理由',
                             file=path, line=1))
    elif op['sig_line'] == 1:
        result.append(finding('SIGNATURE_FIRST_LINE', 'NOTE', 'style',
                             '签名句占用了首行——v2.0 要求第 1 行给钩（结果/冲突/反常/悬念四型），签名句后置到第 2–3 行；仪式感开场会拉高跳出（踩坑记录见 docs/技能重构诊断-2026-09-28.md）',
                             file=path, line=1, evidence=op.get('sig_line')))
    elif op['sig_line'] and op['sig_line'] > 3:
        result.append(finding('SIGNATURE_TOO_LATE', 'NOTE', 'style',
                             f"签名句在第 {op['sig_line']} 行，v2.0 要求 ≤3 行内（首行钩、第 2–3 行签名）",
                             file=path, line=op['sig_line']))

    cues, quoted, pct = dialogue_stats(text)
    # v3.0：旧的「<800 字一律归零」豁免已删——它正好把 600–900 字的整稿变成免检区。
    # 只保留必要的统计下限：样本 <200 汉字时百分比没有意义（一句 6 字引语就顶到 3%），降为 NOTE 不降为隐形。
    small_sample = _han_count(text) < 200
    if small_sample:
        if cues or pct:
            result.append(finding('DIALOGUE_STATS', 'NOTE', 'style',
                                  f'样本不足 200 汉字（引语帧 {cues} 行、估占比 {pct}%）：比例不判定，请对整稿跑 剧本.md/旁白.md',
                                  file=path, evidence=f'cues={cues} pct={pct}'))
    elif cues or pct:
        msg = f'引语帧候选 {cues} 行（「讲，/说，」+括号引号同帧口径，跨行引语会低估）；估引语占比 {pct}%'
        if cues > cfg['nail_over'] or pct > cfg['quote_pct_over']:
            result.append(finding('DIALOGUE_OVER_BUDGET', 'REVIEW', 'style',
                                  msg + f'；超限额（钉子候选≤{cfg["nail_over"]}、引语≤{cfg["quote_pct_over"]}%）。04 点名哪些收拢、哪些是刻度句保留（5_代入感与禁忌·三）',
                                  file=path, line=1, evidence=f'cues={cues} pct={pct}'))
        else:
            result.append(finding('DIALOGUE_STATS', 'NOTE', 'style',
                                  msg + '；限额内', file=path, evidence=f'cues={cues} pct={pct}'))

    if is_screenplay(text):
        # 剧本形态：对白是显式标签行，可以直接数占比——旁白驱动的硬口径在这里生效，
        # 不再依赖「动词+逗号」的 ASR 猜句（v2.0 的 87 篇正是靠短文豁免绕过了对白检查）。
        vo_track, dl_track = split_tracks(text)
        vo_n, dl_n = _han_count(vo_track), _han_count(dl_track)
        share = round(dl_n / max(vo_n + dl_n, 1) * 100, 1)
        over = float(cfg.get('label_dialogue_pct_over', 25.0))
        if share > over:
            result.append(finding('VO_TRACK_OVER', 'REVIEW', 'style',
                                  f'剧本口径：对白 {dl_n} 字 vs 旁白 {vo_n} 字，对白占 {share}%（>本系列旁白驱动上限 {over}%）——把交锋改写进旁白转述，或确认本题面确属对白剧（0_剧本格式与分场表·五）',
                                  file=path, evidence=f'dl={dl_n} vo={vo_n}'))
        else:
            result.append(finding('VO_TRACK_STATS', 'NOTE', 'style',
                                  f'旁白轨 {vo_n} 字／对白轨 {dl_n} 字（对白 {share}%，上限 {over}%）', file=path))
        rows = scene_rows(text)
        if rows:
            if not (cfg.get('scene_min') and cfg.get('scene_max')):
                pass
            elif not cfg['scene_min'] <= len(rows) <= cfg['scene_max']:
                result.append(finding('SCENE_SPARSE', 'REVIEW', 'structure',
                                      f'共 {len(rows)} 场，超出 {cfg["scene_min"]}–{cfg["scene_max"]} 场目标带：少了撑不起一生弧（写成段子），多了每场不到 25 秒（拍成流水切换）',
                                      file=path))
            for title, body in rows:
                if not SCENE_VISUAL.search(body):
                    result.append(finding('SCENE_NO_VISUAL', 'REVIEW', 'structure',
                                          f'「{title}」没有「画面：」行——这一场拍不出来；AI 画面与真人拍摄都缺锚点（0_剧本格式与分场表·二）',
                                          file=path))
                if _han_count('\n'.join(l for l in body.splitlines() if VO_LINE.match(l.strip()))) > cfg.get('scene_chars_max', 400):
                    result.append(finding('SCENE_OVER', 'REVIEW', 'structure',
                                          f"「{title}」旁白超 {cfg.get('scene_chars_max', 400)} 字：一场一口气念不完，拆场或把交代压成判词",
                                          file=path))
    result.extend(number_budget(text, cfg, finding, path))
    for start, end in pingpong_hits(text):
        result.append(finding('PINGPONG', 'REVIEW', 'style',
                              f'L{start}-L{end} 连续 3 行以上「你说/他说」交替——口播禁乒乓回合，交锋改旁白转述（5_代入感与禁忌·三）',
                              file=path, line=start))

    for row in ledger_rows(text):
        if row['status'] != 'mismatch':
            continue
        if row['kind'] == 'digit':
            result.append(finding('LEDGER_DIGIT_MISMATCH', 'REVIEW', 'facts',
                                  f"「{row['claim']}」主张 {row['digits']} 位数，同段金额 {row['amounts']} 无一为 {row['digits']} 位数；改数、改主张或让角色点破差异（数字判词链要能反算）",
                                  file=path, line=row['line'], evidence=str(row['amounts'])))
        else:
            result.append(finding('LEDGER_SCALE_MISMATCH', 'REVIEW', 'facts',
                                  f"档位主张「{row['claim']}」标 {row['unit']}，本段金额 {row['amounts']} 无一落在区间 [{row['range'][0]},{row['range'][1]})；档位与金额必须按文内口径对账（如 A5=五位数）",
                                  file=path, line=row['line'], evidence=f'range={row["range"]} amounts={row["amounts"]}'))

    from fuben_engine import char_count
    # 体量只数「要念出来的那一条轨」：剧本稿数旁白轨，逐字稿数全文。
    measured = text
    if is_screenplay(text):
        measured = split_tracks(text)[0]
    bands = None
    if isinstance(policy, dict) and isinstance(policy.get('volume_bands'), dict) and isinstance(policy.get('profile_volume_band'), dict):
        band_key = policy['profile_volume_band'].get(profile)
        bands = (band_key, policy['volume_bands'].get(band_key)) if band_key else None
    if profile not in ('full', 'short', 'clip'):
        return result  # draft=初稿允许短，reference=原文校准不设卡
    if bands and bands[1] and len(bands[1]) == 2:
        n = char_count(measured)
        lo, hi = bands[1]
        floor = policy.get('volume_floor') or lo if profile == 'full' else lo
        if profile == 'full' and n < min(lo, floor):
            result.append(finding('VOLUME_UNDER_FLOOR', 'REVIEW', 'structure',
                                  f'旁白轨 {n} 字低于体量下限 {min(lo, floor)} 字：这个体量撑不起「一生／多年跨度」，只会写成段子（87 篇塌陷到 617 字的直接教训）。'
                                  '处置二选一：①按 02 分场表把缺的场次补上；②题面确为单事件段子，在 00 简报登记「本篇是段子，不走一生弧」后由人工放行。',
                                  file=path, evidence=f'chars={n} floor={min(lo, floor)} band={bands[0]}'))
        elif profile == 'full' and n < lo:
            result.append(finding('VOLUME_UNDER_BAND', 'NOTE', 'style',
                                  f'旁白轨 {n} 字低于 {bands[0]} 参考带下沿 {lo} 字：够播（>体量下限），但按"一生／多年跨度"的形态偏薄——'
                                  '段子体在 00 简报登记即可；本条只提醒不拦（87 篇的教训是下限失守，不是长度本身有罪）',
                                  file=path, evidence=f'chars={n} band={bands[0]}'))
        elif n > hi:
            result.append(finding('VOLUME_OFF_BAND', 'NOTE', 'style',
                                  f'旁白轨 {n} 字高于 {bands[0]} 参考上限 {hi} 字（v3.0 上限自由：按 policy `volume_authorization`「时长不限」口径，在 04 写一句为什么长即可，不需再找用户确认）',
                                  file=path, evidence=f'band={bands[0]}'))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', help='作品目录或任意正文文件')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--ledger', action='store_true', help='只打印账目对账全表（含 CONSISTENT）供 04 闭环')
    args = parser.parse_args(argv)
    source = Path(args.path).resolve()
    from fuben_engine import resolve_body
    body = resolve_body(source) if source.is_dir() else source
    text = body.read_text(encoding='utf-8-sig')
    if args.ledger:
        rows = ledger_rows(text)
        bad = [r for r in rows if r['status'] == 'mismatch']
        if args.json:
            print(json.dumps({'rows': rows, 'mismatch': len(bad)}, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                print(f"{r['status'].upper():10} L{r['line']:4} [{r['kind']}] {r['claim']}  amounts={r.get('amounts')}")
            print(f"共 {len(rows)} 条主张，mismatch {len(bad)}；mismatch 必须在 04 逐条闭环。")
        return 1 if bad else 0
    # 完整 craft gate（含红线 BLOCK），走引擎协议
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fuben_engine import finding, load_policy
    policy = load_policy()
    findings = craft_checks(text, body, 'full', policy, finding)
    counts = {'BLOCK': 0, 'REVIEW': 0, 'NOTE': 0}
    for f in findings:
        counts[f['severity']] = counts.get(f['severity'], 0) + 1
        print(f"{f['severity']} {f['rule_id']} L{f.get('line', '-')}: {f['message']}")
    print(f"RESULT: {len(findings)} 条（BLOCK {counts.get('BLOCK', 0)} / REVIEW {counts.get('REVIEW', 0)} / NOTE {counts.get('NOTE', 0)}）；BLOCK>0 必须清零，REVIEW 须逐项闭环。")
    return 1 if counts.get('BLOCK') else 0


if __name__ == '__main__':
    raise SystemExit(main())
