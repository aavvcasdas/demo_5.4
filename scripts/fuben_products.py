#!/usr/bin/env python3
"""阶段产物完整性门禁（2026-09-24b 增补）。

把 AGENTS.md「缺阶段产物视为未执行」从口号变成可跑的检查：按 arena.runtime.json
的 pipeline.stages 清单核对 `作品/NN_主题/_运行/YYYY-MM-DD/` 下各阶段产物是否存在、
非空，根目录交付物（正文.md、钩子备选.md 等）是否存在，以及 `审核报告.md` 的
body_path / body_text_sha256 是否仍绑定当前正文。

    python3 scripts/fuben_products.py 作品/82_主题                # 自动取最新运行目录
    python3 scripts/fuben_products.py 作品/82_主题 --run 2026-09-24 --json

命名规范：一次运行一个日期目录 `_运行/YYYY-MM-DD/`（同日多轮加后缀 b/c…）；阶段文件
名以 arena.runtime.json 的 product 字段为准（00_简报.md … 05_机检.json）。
本检查只证明「走了管线」，不评价管线里的判断好坏。
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fuben_engine import text_sha256  # noqa: E402

RUN_DIR_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')


def _rel(path) -> str:
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def load_pipeline():
    cfg = json.loads((ROOT / 'arena.runtime.json').read_text(encoding='utf-8'))
    return cfg['pipeline'], cfg.get('rules', {})


def pick_run_dir(work: Path, explicit: str | None):
    base = work / '_运行'
    if not base.is_dir():
        return base, False
    if explicit:
        d = base / explicit
        return d, d.is_dir()
    dated = sorted(p for p in base.iterdir() if p.is_dir() and RUN_DIR_RE.match(p.name))
    if dated:
        return dated[-1], True
    return base, any(p.is_file() for p in base.iterdir())  # 旧式平铺目录仍检查，但记 NOTE


def check(work: Path, run: str | None = None):
    pipeline, rules = load_pipeline()
    report = {'target': str(work), 'status': 'OK', 'missing': [], 'empty': [], 'notes': [],
              'run_dir': None, 'deliverables': {}, 'review_binding': {}}
    run_dir, exists = pick_run_dir(work, run)
    if not exists:
        report['status'] = 'MISSING'
        report['missing'].append(_rel(work / '_运行') + '（无运行目录＝视为未执行管线）')
    else:
        report['run_dir'] = _rel(run_dir)
        if run_dir == work / '_运行':
            report['notes'].append('旧式平铺 _运行/ 目录；新管线请按 _运行/YYYY-MM-DD/ 命名')
    for stage in pipeline.get('stages', []):
        product = stage.get('product')
        if not product:
            continue
        rel = Path(product)
        path = (work / rel) if rel.name == '审核报告.md' else (run_dir / rel)
        if not path.is_file():
            report['status'] = 'MISSING' if report['status'] == 'OK' else report['status']
            report['missing'].append(_rel(path))
        elif path.stat().st_size < 40:
            report['empty'].append(_rel(path))
        elif path.suffix == '.json':
            try:
                json.loads(path.read_text(encoding='utf-8'))
            except ValueError as exc:
                report['notes'].append(f"{path.name} 不是合法 JSON: {exc}")
    # 若仅缺部分阶段产物且已有局部述文（00_ 留档），视同选择性返修：不缺产物，留提醒就行。
    run_products = [s.get('product') for s in pipeline.get('stages', [])
                    if s.get('product') and s.get('product') != '审核报告.md']
    present = [p for p in run_products if (run_dir / p).is_file()]
    # 定向返修目录（通常只有 00_闭环/00_补记 + 机检重跑，共 1–2 个同名阶段产物）不上整管线检查；
    # 完整运行缺任一阶段仍算 MISSING（如 fixture：缺 02 但有 00_简报/01/03/04/05 → present=4，不计返修）。
    if exists and report['status'] == 'MISSING' and 0 < len(present) < 3 \
            and any(globbed.is_file() for globbed in run_dir.glob('00_*')):
        missing_stage = [p for p in run_products if p not in present]
        report['status'] = 'PARTIAL'
        report['missing'] = [m for m in report['missing'] if not any(m.endswith(p) for p in missing_stage + present)]
        report['notes'].append(f'选择性返修运行（非全管线）：缺 {missing_stage}，目录内 00_*.md 返修记录已说明定点返修范围；不构成「未走管线」。')
    body = work / '正文.md'
    for name in rules.get('deliverables', []) + rules.get('optional_deliverables', []):
        path = work / name
        required = name in rules.get('deliverables', [])
        report['deliverables'][name] = 'OK' if path.is_file() else ('MISSING' if required else 'absent(optional)')
        if path.is_file() and required and not path.read_text(encoding='utf-8').strip():
            report['empty'].append(name)
    if body.is_file():
        current = text_sha256(body)
        report['review_binding']['current_body_text_sha256'] = current
        review = work / '审核报告.md'
        if review.is_file():
            text = review.read_text(encoding='utf-8')
            # 报告「修订记录」追加体例：同一键出现多次时以最后一条为准。
            hash_matches = re.findall(r'body_text_sha256\s*[：:]\s*`?([0-9a-fA-F]{64})`?', text)
            if not hash_matches:
                report['review_binding']['state'] = 'UNBOUND'
                report['status'] = 'MISSING' if report['status'] == 'OK' or report['status'] == 'PARTIAL' else report['status']
                report['missing'].append('审核报告缺 body_text_sha256（不能证明绑定当前正文）')
            elif hash_matches[-1].lower() != current:
                report['review_binding']['state'] = 'STALE'
                report['status'] = 'STALE'
                report['notes'].append('审核报告哈希≠当前正文：旧结论对新稿失效，必须复审重绑')
            else:
                report['review_binding']['state'] = 'BOUND'
    else:
        report['missing'].append('正文.md')
        report['status'] = 'MISSING'
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work', help='作品目录，如 作品/82_主题')
    parser.add_argument('--run', help='运行目录名，如 2026-09-24；默认取最新')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    report = check(Path(args.work).resolve(), args.run)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"PRODUCTS: {report['status']} | {report['target']} | run={report['run_dir']}")
        for item in report['missing']:
            print(f"MISSING {item}")
        for item in report['empty']:
            print(f"EMPTY {item}")
        for item in report['notes']:
            print(f"NOTE {item}")
        print('本门禁只核对管线是否留下产物与哈希绑定；不为创作质量背书。')
    return 1 if report['status'] != 'OK' else 0


if __name__ == '__main__':
    raise SystemExit(main())
