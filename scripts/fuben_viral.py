#!/usr/bin/env python3
"""v2.0 结构自评（advisory，不判水、不判好坏）。

背景：用户 2026-09-28 判定 v1.3.x 路线作废（86 篇 1k 播放、点赞 <10），
重构为 v2.0：首行即钩 / 签名后置 / 爽点四段 / 结尾互动钩 / 检索找真实骨架。
本脚本只做**结构项的存在性自检**，给 04 的「投手预演」提供可核对的行号证据：

  1 首行：是不是签名句占用（v2.0 要求首行给钩）
  2 签名句行号（要求 ≤3 行内）
  3 结尾互动钩（末 6 个非空行内是否出现提问/征集/立场句式）
  4 02 站数 与 「物证」登记数（目标：≥3 件物证）
  5 01 检索路数（目标：≥8 路）
  6 字数与两口径估时（语感 4.5–5 字/秒；机检 6.4 字/秒）
  7 发布声明（「剧情…虚构」字样，混合源强制）

本仓退役过启发式质地检查器（判据失准、误报高）：**本脚本不判断"水"**，
任何一项红/黄都只是待人工确认的线索；创作结论一律由 04 投手预演与用户验收给出。

    python3 scripts/fuben_viral.py 作品/NN_主题
    python3 scripts/fuben_viral.py 作品/NN_主题 --json
    python3 scripts/fuben_viral.py 作品/NN_主题 --strict   # 有缺口时退出码 1（默认 exit 0）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIG_RE = re.compile(r'今天.{0,4}体验.{0,6}人生副本')
HOOK_PATTERNS = [r'[？?]', r'评论区', r'留言', r'说说', r'你会', r'要是你', r'你身边', r'你选', r'你敢']
CLAIM_DECL = re.compile(r'虚构|演绎|仅供娱乐')


def nonempty(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines() if l.strip()]


def han_count(text: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', text))


def latest_run(work: Path) -> Path | None:
    base = work / '_运行'
    if not base.is_dir():
        return None
    runs = sorted((p for p in base.iterdir() if p.is_dir()), reverse=True)
    return runs[0] if runs else None


def count_stations(plan: str) -> int:
    return len(re.findall(r'^#{2,4}\s*(?:站|场)\b', plan, flags=re.M))


def count_claim_rows(doc: str) -> int:
    """只数「兑现认领」小节的表格行（advisory）。"""
    rows, inside = 0, False
    for line in doc.splitlines():
        s = line.strip()
        if s.startswith('#'):
            inside = bool(re.search(r'兑现认领|认领', s))
            continue
        if not inside or not s.startswith('|'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) < 2 or set(''.join(cells)) <= set('-: '):
            continue
        if cells[0] in ('兑现点', '承诺', '项目'):
            continue
        rows += 1
    return rows


def count_table_rows(doc: str) -> int:
    rows = 0
    for line in doc.splitlines():
        s = line.strip()
        if not s.startswith('|'):
            continue
        cells = [c.strip() for c in s.strip('|').split('|')]
        if len(cells) < 2 or set(''.join(cells)) <= set('-: '):
            continue
        rows += 1
    return rows


def check(work: Path) -> dict:
    body_path = work / '正文.md'
    hooks_path = work / '钩子备选.md'
    run = latest_run(work)
    report = {'target': str(work), 'run': run.name if run else None, 'disposition': 'advisory_not_a_gate',
              'checks': [], 'notes': []}
    if not body_path.is_file():
        report['notes'].append(f'找不到正文：{body_path}')
        return report
    body = body_path.read_text(encoding='utf-8-sig')
    lines = nonempty(body)
    n = han_count(body)

    def add(item, ok, detail):
        report['checks'].append({'item': item, 'status': 'OK' if ok else 'CHECK', 'detail': detail})

    first = lines[0] if lines else ''
    sig_line = next((i for i, l in enumerate(lines[:5], 1) if SIG_RE.search(l)), None)
    add('首行即钩', not SIG_RE.search(first),
        f'首行＝「{first[:24]}」' + ('（是签名句：v2.0 要求首行给钩、签名后置第 2–3 行）' if SIG_RE.search(first) else ''))
    add('签名句位置', bool(sig_line) and sig_line <= 3,
        f'签名句在第 {sig_line} 行' if sig_line else '未找到签名句（刻意不用请在 00 简报记录理由）')

    tail = '\n'.join(lines[-6:])
    hit = next((p for p in HOOK_PATTERNS if re.search(p, tail)), None)
    add('结尾互动钩', bool(hit), f'末 6 行命中「{hit}」' if hit else '末 6 行未见提问/征集/立场句式——结尾要给观众一个动作')

    plan = None
    stations = props = claims = None
    if run:
        pf = run / '02_场次单.md'
        if pf.is_file():
            plan = pf.read_text(encoding='utf-8-sig')
            stations = count_stations(plan)
            props = plan.count('物证')
            claims = count_claim_rows(plan)
    add('站点数', bool(stations) and 5 <= stations <= 8, f'02 里数到 {stations} 站（v2.0 目标 5–8）')
    add('物证登记', bool(props) and props >= 3, f'02 里「物证」出现 {props} 次（目标 ≥3 件，且每件要干活）')
    add('兑现认领', bool(claims), f'02 兑现认领表 {claims} 行（3–5 行为宜）')

    routes = None
    if run:
        rf = run / '01_深读_检索与方向.md'
        if rf.is_file():
            routes = count_table_rows(rf.read_text(encoding='utf-8-sig'))
    add('检索路数', bool(routes) and routes >= 8, f'01 逐路表 {routes} 行（≥8 路；不调用搜索即失败）')

    decl_src = ''
    for p in (hooks_path, work / '审核报告.md'):
        if p.is_file():
            decl_src += p.read_text(encoding='utf-8-sig')
    add('虚构声明', bool(CLAIM_DECL.search(decl_src)), '发布建议/审核报告里' + ('有' if CLAIM_DECL.search(decl_src) else '缺') + '「剧情虚构演绎」声明（混合源强制）')

    add('体量估时', True,
        f'汉字 {n} 字；语感 4.5–5 字/秒 ≈ {round(n / 5)}–{round(n / 4.5)} 秒；机检 6.4 字/秒 ≈ {round(n / 6.4)} 秒')

    report['words'] = n
    report['checks_detail'] = {'station_count': stations, 'prop_mentions': props, 'claim_rows': claims,
                               'search_rows': routes, 'signature_line': sig_line}
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('work', type=Path)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--strict', action='store_true', help='有 CHECK 项时退出码 1（默认 0，advisory）')
    args = ap.parse_args(argv)
    work = args.work if args.work.is_absolute() else (Path.cwd() / args.work)
    if not work.is_dir():
        raise SystemExit(f'作品目录不存在：{work}')
    rep = check(work)
    bad = [c for c in rep['checks'] if c['status'] != 'OK']
    if args.json:
        print(json.dumps({**rep, 'check_count': len(bad)}, ensure_ascii=False, indent=2))
        return 1 if (args.strict and bad) else 0
    print(f"v2.0 结构自评（advisory，不判水）· {rep['target']}（运行目录 {rep['run']}）")
    for c in rep['checks']:
        mark = '✅' if c['status'] == 'OK' else '⚠️'
        print(f"  {mark} {c['item']}：{c['detail']}")
    print('提醒：结构项只说明「有没有这么做」，好不好看仍由 04 投手预演、念稿与真实观众数据判定。')
    return 1 if (args.strict and bad) else 0


if __name__ == '__main__':
    sys.exit(main())
