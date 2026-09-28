#!/usr/bin/env python3
"""人生副本口播稿工艺门禁（craft gate，2026-09-24b 增补）。

把 SKILL 里原本只靠人自觉的硬约束变成机检候选：
  红线      NO_SMOKE（用户裁决 2026-09-23：正文/钩子/短版不得出现烟）
  语感      BANWORD（书面腔/AI 腔清单，见代入感手艺·四）
  开头      OPENING（禁定义前置、系统提示≤2 行、首行超载；见口播结构与节奏·开头铁律）
  对白      DIALOGUE（引语帧/钉子句/乒乓回合计数，粗口径候选，04 逐项闭环）
  账目      LEDGER（位数主张与档位主张须与同段金额对账；数字判词链的机检下限）
  体量      VOLUME（字数参考带按 profile；不达标只报不判，但 04 必须写明处置）

协议与 fuben_engine 一致：BLOCK=可复现的明确违例（只保留红线级）；REVIEW=上下文
候选，由审读阶段逐项闭环（修复或给出保留理由）；NOTE=描述信息。门禁不判好坏、
不判文笔，PASS_WITH_REVIEW 不代表开头留得住或账目已核——闭环义务在 04。
profile=reference（原文校准）不受本账号红线约束，整个 craft 检查豁免。
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
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


def opening_findings(text, cfg):
    """开头铁律的可机检子集（硬规见口播结构与节奏·开头铁律）。

    场景行号口径（机械可分辨的下限，非最终裁决，人审复核标记线索能亲手「采」的物件/动作/人名/具体地点）：
      签名＝开头非空首行自带「副本/今天要体验的人生副本/最近…都在传/大家管这叫」的提示基调；
      系统提示＝接下来的「系统提示」行头及其下一行（仅认 <=2 行笑话形态）；
      首个场景行＝此后第一个同时含动作动词词典与具体名词词典的非空行；
      名词词典＝本系列家常物件/身体机构/场所/金额小字/年龄谱/学称级标/C 段标记。
    """
    out = {}
    lines = [l for l in text.splitlines() if l.strip()]
    head = re.sub(r'\s+', '', text)[:DEFINITION_WINDOW]
    out['definer'] = next((w for w in cfg['definition_upfront'] if w in head), None)
    out['sig'] = bool(re.search(r'今天.{0,4}体验.{0,6}人生副本', head[:120])) if lines else False
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
                                 f'书面腔/AI 腔禁词「{w}」命中 {len(hits)} 处（代入感手艺·四清单）；逐处改写或说明保留理由',
                                 file=path, line=hits[0], evidence='; '.join(text.splitlines()[i - 1].strip() for i in hits[:4])[:160]))

    op = opening_findings(text, cfg)
    if op['definer']:
        result.append(finding('DEFINITION_UPFRONT', 'REVIEW', 'style',
                              f"开头 {DEFINITION_WINDOW} 字内出现讲解腔标记「{op['definer']}」——黄金 3 秒禁定义前置，名词解释后置到剧情第一次用到的地方（口播结构与节奏·开头铁律）",
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
                             '未见「今天你要体验的人生副本是…」签名开场；系列资产默认必用，刻意不用请在 00_简报记录理由',
                             file=path, line=1))

    cues, quoted, pct = dialogue_stats(text)
    # 对白限额只对整稿成立：短文/切片样本（<800 汉字）上百分比会失真，只留结构扫描。
    if _han_count(text) < 800:
        cues, quoted, pct = 0, 0, 0.0
    if cues or pct:
        msg = f'引语帧候选 {cues} 行（「讲，/说，」+括号引号同帧口径，跨行引语会低估）；估引语占比 {pct}%'
        if cues > cfg['nail_over'] or pct > cfg['quote_pct_over']:
            result.append(finding('DIALOGUE_OVER_BUDGET', 'REVIEW', 'style',
                                  msg + f'；超限额（钉子候选≤{cfg["nail_over"]}、引语≤{cfg["quote_pct_over"]}%）。04 审读必须给逐项排除表：哪些是转述/微刻度不计句数，剩余的必须收拢（代入感手艺·三点五）',
                                  file=path, line=1, evidence=f'cues={cues} pct={pct}'))
        else:
            result.append(finding('DIALOGUE_STATS', 'NOTE', 'style',
                                  msg + '；限额内也请在 04 审读记录同口径数字，禁止无工具的手工自报',
                                  file=path, evidence=f'cues={cues} pct={pct}'))
    for start, end in pingpong_hits(text):
        result.append(finding('PINGPONG', 'REVIEW', 'style',
                              f'L{start}-L{end} 连续 3 行以上「你说/他说」交替——口播禁乒乓回合，交锋改旁白转述（代入感手艺·三点五）',
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

    bands = None
    if isinstance(policy, dict) and isinstance(policy.get('volume_bands'), dict) and isinstance(policy.get('profile_volume_band'), dict):
        band_key = policy['profile_volume_band'].get(profile)
        bands = (band_key, policy['volume_bands'].get(band_key)) if band_key else None
    if bands and bands[1] and len(bands[1]) == 2:
        from fuben_engine import char_count
        n = char_count(text)
        lo, hi = bands[1]
        if not lo <= n <= hi:
            result.append(finding('VOLUME_OFF_BAND', 'NOTE', 'style',
                                  f"体量 {n} 字不在 {bands[0]} 参考带 [{lo},{hi}]（policy 唯一口径）；00 简报覆盖区间须引用用户同意原话，否则 04 补足或在报告写明接受理由",
                                  file=path, evidence=f'band={bands[0]}'))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', help='作品目录或任意正文文件')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--ledger', action='store_true', help='只打印账目对账全表（含 CONSISTENT）供 04 闭环')
    args = parser.parse_args(argv)
    source = Path(args.path).resolve()
    body = source / '正文.md' if source.is_dir() else source
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
