#!/usr/bin/env python3
"""技术核对核心（v3.0，2026-09-30）。

只做三类**可复现的技术核对**，不做创作判断：

  1. 输入完整性：正文是否存在、可解码、非空。
  2. 算术与字数主张：显式算式、引文汉字数等**字面自相矛盾**的错误。
  3. 描述性指标：字数、行数、数字密度、估时（都带口径名，不是实测）。

创作规则（无烟、禁词、开头、对白、账目档位、体量、结构评分等）不在这里判，
它们已整体写进 `skills/fuben-write/` 的提示词与 references——由写作者与审读者按
提示词逐条自检。本模块的 BLOCK 只用于「确定的输入/算术错误」；其余一律
REVIEW/NOTE，交给人的判断。

  python3 scripts/fuben_run.py 作品/NN_主题/ --json          # 技术核对（默认）
  python3 scripts/fuben_run.py 作品/NN_主题/ --style --json   # 附加 AI 腔句式候选（可选）

PASS 只说明没有检出确定的机械错误，不代表稿子好看、账目已核或可以发布。
"""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from fuben_numbers import numeric, number, NUM_PATTERN

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path(__file__).with_name('fuben_policy.json')
AI_CHECKER = (ROOT / 'skills/story-review/scripts/check-ai-patterns.js'
              if (ROOT / 'skills/story-review').is_dir()
              else ROOT / 'scripts/_fuben_vendor/check-ai-patterns.js')
SEVERITIES = ('ERROR', 'BLOCK', 'REVIEW', 'NOTE')


def load_policy():
    value = json.loads(POLICY_PATH.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value['schema_version'] != 1:
        raise ValueError('invalid fuben policy')
    if not isinstance(value.get('profiles'), list) or not value['profiles'] or not all(isinstance(p, str) for p in value['profiles']):
        raise ValueError('invalid policy profiles')
    for key in ('estimated_chars_per_second', 'tool_timeout_seconds'):
        n = value.get(key)
        if type(n) not in (int, float) or not math.isfinite(n) or n <= 0:
            raise ValueError('invalid policy numeric value: ' + key)
    return value


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_sha256(path):
    """Hash decoded text after normalizing line endings for cross-platform review binding."""
    text = Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def char_count(text):
    # Existing repository convention, retained for before/after comparability.
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#')]
    return len(re.sub(r'[，。、？！：；「」\"\'\s]', '', ''.join(lines)))


NUMBER_TOKEN = re.compile(NUM_PATTERN)


def metrics(text, cps=6.4):
    """Descriptive only: named units, no literary verdict."""
    lines = [(i, l.strip()) for i, l in enumerate(text.splitlines(), 1)
             if l.strip() and not l.lstrip().startswith('#')]
    body = ''.join(re.sub(r'[，。、？！：；「」\"\'\s]', '', l) for _, l in lines)
    tokens = len(NUMBER_TOKEN.findall(body))
    denominator = len(body) or 1
    total = char_count(text)
    return {'characters_repository_convention': total, 'nonempty_prose_lines': len(lines),
            'longest_line_characters': max((char_count(l) for _, l in lines), default=0),
            'number_tokens': tokens, 'number_density_per_1000': round(tokens / denominator * 1000, 1),
            'density_denominator': denominator, 'assumed_cps': cps,
            'estimated_duration_seconds': round(total / cps, 2),
            'duration_kind': 'estimate_not_audio_measurement'}


def finding(code, severity, category, message, *, file=None, line=None, evidence=None):
    if severity not in SEVERITIES:
        raise ValueError('unknown severity: ' + str(severity))
    out = dict(rule_id=code, severity=severity, category=category, message=message)
    for key, value in (('file', file), ('line', line), ('evidence', evidence)):
        if value is not None:
            out[key] = str(value) if key == 'file' else value
    return out


def finish(report):
    severities = {f['severity'] for f in report['findings']}
    report['status'] = ('ERROR' if 'ERROR' in severities else 'FAIL' if 'BLOCK' in severities
                        else 'PASS_WITH_REVIEW' if 'REVIEW' in severities else 'PASS')
    report['exit_code'] = 2 if 'ERROR' in severities else 1 if 'BLOCK' in severities else 0
    report['mechanical_pass'] = report['exit_code'] == 0
    report['editorially_approved'] = False
    report['release_ready'] = False
    return report


def explicitly_fallible_context(text, start, end, *, quoted_math=False):
    lo = text.rfind('\n', 0, start) + 1
    hi = text.find('\n', end)
    line = text[lo:hi if hi != -1 else len(text)]
    if re.search(r'误算|算错|错算|错写|故意写错|故意说错|谎称|误以为|错误示例', line):
        return True
    if quoted_math:
        return any(m.start() <= start - lo < m.end() for m in re.finditer(r'[“「\"][^”」\"]*[”」\"]', line))
    return False


def literal_checks(text, path, profile):
    result = []
    # Match a small, explicit equation, not amounts scattered across a story.
    pat = re.compile(rf'(?P<lhs>{NUM_PATTERN}(?:\s*[+＋×*÷/−-]\s*{NUM_PATTERN}){{1,12}})\s*[=＝]\s*(?P<c>{NUM_PATTERN})(?P<percent>[%％‰]?)')
    for m in pat.finditer(text):
        # Do not validate a suffix of a longer/unsupported expression.
        before = text[:m.start()].rstrip()
        if before and (before[-1] in '+＋×*÷/−-' or re.fullmatch(r'[0-9零〇一二两三四五六七八九十百千万亿.]', before[-1])):
            continue
        try:
            values = [number(token.strip().rstrip('，,'), colloquial=False) for token in re.split(r'[+＋×*÷/−-]', m['lhs'])]
            ops = re.findall(r'[+＋×*÷/−-]', m['lhs'])
            expected = number(m['c'].rstrip('，,'), colloquial=False)
            divisor = Decimal(1000 if m['percent'] == '‰' else 100 if m['percent'] else 1)
            expected /= divisor
            terms = [values[0]]
            for op, value in zip(ops, values[1:]):
                if op in '×*':
                    terms[-1] *= value
                elif op in '÷/':
                    terms[-1] /= value
                else:
                    terms.append(value if op in '+＋' else -value)
            calculated = sum(terms, Decimal(0))
        except (ValueError, InvalidOperation, ZeroDivisionError):
            result.append(finding('EQUATION_AMBIGUOUS', 'REVIEW', 'facts', '显式算式无法可靠计算，请确认数词或除数', file=path,
                                  line=text.count('\n', 0, m.start()) + 1, evidence=m[0]))
            continue
        tolerance = Decimal(0)
        if m['percent'] or any(op in '÷/' for op in ops):
            places = len(m['c'].split('.')[-1]) if '.' in m['c'] else 0
            tolerance = Decimal('0.5') * (Decimal(10) ** -places) / divisor
        if abs(calculated - expected) > tolerance:
            uncertain = profile == 'reference' or explicitly_fallible_context(text, m.start(), m.end(), quoted_math=True)
            result.append(finding('EXPLICIT_ARITHMETIC', 'REVIEW' if uncertain else 'BLOCK', 'facts',
                                  f'显式算式应为 {calculated}，不是 {expected}；确认语境后修订', file=path,
                                  line=text.count('\n', 0, m.start()) + 1, evidence=m[0]))
    # Only a directly quoted pure-Han string yields an unambiguous character count.
    n = r'[一二两三四五六七八九十百\d]+'
    quoted_group = r'(?P<quoted>(?:[“「\"][^\n”」\"]{1,60}[”」\"][、,， ]*){1,8})'
    # Horizontal spacing is formatting, not a reason to miss an explicit claim.
    count_claim = rf'(?P<n>{n})[ \t]*个?[ \t]*(?:汉)?字'
    patterns = [quoted_group + r'(?:这|共|一共|只有|就|总共)?' + count_claim,
                count_claim + r'[：:,， ]*' + quoted_group]
    seen = set()
    for regex in patterns:
        for m in re.finditer(regex, text):
            if text[:m.start()].rstrip().endswith('第'):
                continue
            if m.span() in seen:
                continue
            seen.add(m.span())
            count = numeric(m['n'], colloquial=False)
            quote = ''.join(re.findall(r'[“「\"]([^\n”」\"]+)[”」\"]', m['quoted']))
            actual = len(re.findall(r'[\u4e00-\u9fff]', quote))
            pure = bool(re.fullmatch(r'[\u4e00-\u9fff]+', quote))
            if count is not None and count != actual:
                certain = pure and profile != 'reference' and not explicitly_fallible_context(text, m.start(), m.end())
                result.append(finding('QUOTED_CHARACTER_COUNT', 'BLOCK' if certain else 'REVIEW', 'facts',
                                      f'引文有 {actual} 个汉字，附近声称 {count} 个字（混合文字需确认计数口径）',
                                      file=path, line=text.count('\n', 0, m.start()) + 1, evidence=m[0]))

    # A narrow unquoted form used by line-broken oral scripts: "人生就四字\n练完再耍".
    lines = text.splitlines()
    scoped = re.compile(rf'^(?P<label>[^，。！？：:,]{{1,24}}?)就(?P<n>{n})[ \t]*个?[ \t]*(?:汉)?字[ \t]*(?:[：:,，][ \t]*(?P<inline>[^\n]{{1,40}}))?[ \t]*$')
    for index, raw_line in enumerate(lines):
        m = scoped.match(raw_line.strip())
        if not m or raw_line.lstrip().startswith('第'):
            continue
        target = (m['inline'] or '').strip()
        target_line = index + 1
        if not target:
            target_line = index + 2
            while target_line <= len(lines) and not lines[target_line - 1].strip():
                target_line += 1
            if target_line > len(lines):
                continue
            target = lines[target_line - 1].strip()
        count = numeric(m['n'], colloquial=False)
        actual = len(re.findall(r'[\u4e00-\u9fff]', target))
        pure = bool(re.fullmatch(r'[\u4e00-\u9fff]+', target))
        if count is None or count == actual:
            continue
        nearby = '\n'.join(lines[max(0, index - 1):index + 1])
        fallible = bool(re.search(r'误算|算错|错算|错写|故意写错|故意说错|谎称|误以为|错误示例', nearby))
        certain = pure and profile != 'reference' and not fallible
        result.append(finding('SCOPED_CHARACTER_COUNT', 'BLOCK' if certain else 'REVIEW', 'facts',
                              f'“{m["label"]}就{m["n"]}字”只计其后短语；该短语有 {actual} 个汉字，不是 {count} 个',
                              file=path, line=index + 1, evidence=raw_line.strip() + ' → ' + target))

    # ASR / unquoted speech is intentionally not a hard verdict.
    for m in re.finditer(rf'(?P<n>{n})个字[：:,， ]*\n(?P<quote>[^\n]{{1,40}})', text):
        quote = m['quote'].strip()
        count = numeric(m['n'], colloquial=False)
        actual = len(re.findall(r'[\u4e00-\u9fff]', quote))
        if count is not None and 1 <= count <= 20 and count != actual:
            result.append(finding('UNQUOTED_COUNT_CANDIDATE', 'REVIEW', 'facts',
                                  f'相邻口播行含 {actual} 汉字，上文称 {count} 个字；须核实引文边界',
                                  file=path, line=text.count('\n', 0, m.start()) + 1, evidence=m[0]))
    return result


def style_diagnostics(path, *, checker=AI_CHECKER, executable='node', timeout=30):
    """可选：AI 腔句式候选（通用去 AI 味检查器，advisory，从不 BLOCK）。"""
    command = [executable, str(checker), '--json', '--fail-on=blocking', '--profile=fuben', str(path)]
    info = {'name': 'ai_style_diagnostics', 'command': command, 'state': 'ERROR'}
    try:
        r = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        info['exit_code'] = r.returncode
        if r.returncode not in (0, 1):
            raise ValueError(f'checker exit {r.returncode}: {r.stderr[-1200:]}')
        data = json.loads(r.stdout)
        if not isinstance(data, dict) or not isinstance(data.get('findings'), list):
            raise ValueError('expected {findings: [...]} JSON protocol')
        for item in data['findings']:
            if not isinstance(item, dict) or item.get('severity') not in ('blocking', 'advisory') or not isinstance(item.get('line'), int):
                raise ValueError('malformed checker finding')
        blocking = any(i['severity'] == 'blocking' for i in data['findings'])
        if (r.returncode == 1) != blocking:
            raise ValueError('checker exit code and JSON findings disagree')
        info['state'] = 'COMPLETED'
        info['finding_count'] = len(data['findings'])
        return [finding('AI_STYLE_' + str(item.get('type', item.get('rule', 'pattern'))), 'REVIEW', 'style',
                        str(item.get('message', item.get('reason', '句式模式候选；依据表达功能判断，禁止机械清零'))),
                        file=path, line=item['line'], evidence=item.get('excerpt', item.get('text', item.get('match'))))
                for item in data['findings']], info
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError) as exc:
        info['error'] = str(exc)
        return [finding('STYLE_TOOL_ERROR', 'ERROR', 'tool', str(exc), file=checker)], info


def inspect_path(path, *, profile='draft', run_style=False, checker=AI_CHECKER, executable='node'):
    report = {'schema_version': 3, 'profile': profile, 'target': str(path), 'findings': [], 'tools': [],
              'checked': [], 'unverified': ['editorial quality', 'narrative continuity and referent resolution',
                                            'theme/event alignment and dialogue response', 'external factual truth',
                                            'TTS listening', 'actual media consistency', 'platform publication'],
              'inputs': {}}
    try:
        policy = load_policy()
        report['policy_version'] = policy['version']
        if profile not in policy['profiles']:
            raise ValueError('unknown profile: ' + profile)
        source = Path(path).resolve()
        body_path = source / '正文.md' if source.is_dir() else source
        if not body_path.is_file():
            raise OSError('正文文件不存在: ' + str(body_path))
        body = body_path.read_text(encoding='utf-8-sig')
        report['body_path'] = str(body_path)
        report['inputs']['body_sha256'] = sha256(body_path)
        report['inputs']['body_text_sha256'] = text_sha256(body_path)
        if not body.strip() or char_count(body) == 0:
            report['findings'].append(finding('EMPTY_BODY', 'BLOCK', 'input', '正文为空或只有标题', file=body_path))
            return finish(report)
        if '\x00' in body:
            report['findings'].append(finding('BINARY_INPUT', 'ERROR', 'input', '正文包含 NUL，拒绝按文本审核', file=body_path))
            return finish(report)
        report['metrics'] = metrics(body, policy['estimated_chars_per_second'])
        report['checked'].append('readable_nonempty_body_and_descriptive_metrics')
        if '\ufffd' in body:
            report['findings'].append(finding('REPLACEMENT_CHARACTER', 'REVIEW', 'input', '存在替换字符，可能是转写/编码损坏', file=body_path))
        report['findings'].extend(literal_checks(body, body_path, profile))
        report['checked'].append('explicit_equations_and_literal_character_counts')
        profile_path = body_path.parent / '.fuben.json'
        if profile != 'reference' and profile_path.exists():
            config = json.loads(profile_path.read_text(encoding='utf-8'))
            if not isinstance(config, dict) or type(config.get('schema_version')) is not int or config.get('schema_version') != 1 or config.get('profile') != 'fuben':
                raise ValueError('invalid .fuben.json: expected schema_version=1, profile=fuben')
            report['inputs']['profile_sha256'] = sha256(profile_path)
        if run_style:
            findings, info = style_diagnostics(body_path, checker=checker, executable=executable,
                                               timeout=policy['tool_timeout_seconds'])
            report['findings'].extend(findings)
            report['tools'].append(info)
            if info['state'] == 'COMPLETED':
                report['checked'].append('style_pattern_candidates_not_literary_judgment')
        else:
            report['unverified'].append('optional AI-style pattern scan not requested (--style)')
    except (OSError, ValueError, TypeError, ImportError, KeyError, ZeroDivisionError) as exc:
        report['findings'].append(finding('INPUT_OR_ENGINE_ERROR', 'ERROR', 'tool', str(exc), file=path))
    return finish(report)


def emit(report, *, json_output=False, label='FUBEN'):
    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{label}: {report['status']} | profile={report['profile']} | {report['target']}")
        if report.get('metrics'):
            m = report['metrics']
            print(f"INFO 字数 {m['characters_repository_convention']}；{m['nonempty_prose_lines']}行；"
                  f"数字密度 {m['number_density_per_1000']}/千字；估时 {m['estimated_duration_seconds']}s（非实测）")
        ordered = sorted(report['findings'], key=lambda f: SEVERITIES.index(f['severity']))
        hard = [f for f in ordered if f['severity'] in ('ERROR', 'BLOCK')]
        soft = [f for f in ordered if f['severity'] not in ('ERROR', 'BLOCK')]
        for item in hard + soft:
            loc = f" L{item['line']}" if item.get('line') else ''
            print(f"{item['severity']} {item['rule_id']}{loc}: {item['message']}")
        print('技术核对只覆盖输入与算术；创作规则按 fuben-write 提示词自检，PASS 不是发布批准。')
    return report['exit_code']


def cli(argv=None, *, label='FUBEN'):
    parser = argparse.ArgumentParser(description='人生副本剧本技术核对（输入/算术/指标）')
    parser.add_argument('path', help='作品目录，或任意正文文件')
    parser.add_argument('--profile', choices=load_policy()['profiles'], default='draft')
    parser.add_argument('--style', action='store_true', help='附加 AI 腔句式候选（advisory，需要 node）')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--apply', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--human', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    report = inspect_path(args.path, profile=args.profile, run_style=args.style)
    return emit(report, json_output=args.json, label=label)


if __name__ == '__main__':
    raise SystemExit(cli())
