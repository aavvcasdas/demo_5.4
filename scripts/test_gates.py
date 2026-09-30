#!/usr/bin/env python3
"""仓库体检总入口（v3.0：只做软件回归与受保护语料校验）。

v3.0（2026-09-30）起删除了对稿件下创作判罚的采集式扫描（works/corpus 门禁曾依赖已删除的
fuben_craft/fuben_health/fuben_corpus）。本入口现在只回答两个技术问题：
  1. 软件测试是否全绿（unittest，见 tests/）；
  2. 受保护语料（拆文库/*/原文/*）是否与 tests/protected_sources.json 逐字节一致。
稿件好不好、水不水、能不能发，一律由 fuben-write 的提示词自检与人工审读判断。

    python3 scripts/test_gates.py [--output report.json]
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from fuben_engine import sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    summary = {'schema_version': 3, 'software_tests': result.testsRun, 'software_pass': result.wasSuccessful(),
               'test_failures': len(result.failures), 'test_errors': len(result.errors)}
    failure = not result.wasSuccessful()
    manifest = json.loads((ROOT / 'tests/protected_sources.json').read_text(encoding='utf-8'))['sha256']
    actual_paths = {str(p.relative_to(ROOT)) for p in (ROOT / '拆文库').glob('*/原文/*') if p.is_file()}
    recorded_paths = {p for p in manifest if p.startswith('拆文库/')}
    mismatches = [p for p, expected in manifest.items() if not (ROOT / p).is_file() or sha256(ROOT / p) != expected]
    if actual_paths != recorded_paths:
        mismatches += sorted(actual_paths ^ recorded_paths)
    summary['protected_input_changes'] = mismatches
    failure |= bool(mismatches)
    summary['software_and_sources_pass'] = not failure
    summary['not_a_release_verdict'] = True
    summary['scope'] = 'software tests + protected sources only; no manuscript quality gate exists in v3.0'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('SOFTWARE-AND-SOURCES:', 'FAIL' if failure else 'PASS')
    return 1 if failure else 0


if __name__ == '__main__':
    raise SystemExit(main())
