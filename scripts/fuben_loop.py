#!/usr/bin/env python3
"""Compatibility entry point for the lightweight fuben workflow.

  design <brief-file>        check supplied brief readability, not quota tables
  draft|facts <body-or-dir>  shared mechanical checks
  review <body-or-dir>       review candidates; never automatic editorial approval
  record <new-data-args>     schema-validated snapshots (see fuben_data.py)
  report                    read validated snapshots; show quarantined legacy data

No generate→quota→rewrite-until-green loop. An editorial iteration fixes the most
important evidenced problems; subjective disagreement goes back to the author.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from fuben_engine import char_count as HAN, inspect_path, emit, finding, finish, sha256, text_sha256


def design(path):
    target = Path(path)
    report = {'schema_version': 2, 'profile': 'draft', 'target': str(path), 'findings': [],
              'tools': [], 'inputs': {}, 'checked': [], 'unverified': ['brief interpretation', 'all story/release checks']}
    try:
        text = target.read_text(encoding='utf-8-sig')
        if not text.strip():
            report['findings'].append(finding('EMPTY_BRIEF', 'BLOCK', 'input', '指定的 brief 文件为空', file=path))
        else:
            report['inputs']['brief_sha256'] = sha256(target)
            report['checked'].append('supplied_brief_is_readable_nonempty')
            report['findings'].append(finding('NO_CREATIVE_QUOTAS', 'NOTE', 'style',
                                             '不要求八拍、爽点表、呼应数或感官配额；理解用户请求后即可起稿。'))
    except (OSError, UnicodeError) as exc:
        report['findings'].append(finding('BRIEF_READ_ERROR', 'ERROR', 'input', str(exc), file=path))
    return finish(report)


def features(directory):
    report = inspect_path(directory, run_style=False, components={'metrics'})
    if not report['mechanical_pass']:
        raise ValueError('cannot extract features from invalid text')
    return {'metric_schema_version': 2, **report['metrics']}


def _normalize_report_body_path(claim: str, *, report_dir: Path) -> Path:
    path = Path(claim.strip().strip('`').replace('\\', '/'))
    if not path.is_absolute():
        path = report_dir / path
    return path.resolve()



def _review_binding_evidence(body_path):
    """Read body_path/body_text_sha256 claims from 审核报告.md without treating prose as approval."""
    review_path = Path(body_path).parent / '审核报告.md'
    if not review_path.is_file():
        return review_path, None, None
    text = review_path.read_text(encoding='utf-8-sig')
    body_match = re.search(r'body_path\s*[：:]\s*`?([^`\n]+)`?', text)
    hash_match = re.search(r'body_text_sha256\s*[：:]\s*`?([0-9a-fA-F]{64})`?', text)
    bound_body_path = (_normalize_report_body_path(body_match.group(1), report_dir=review_path.parent)
                       if body_match else None)
    return review_path, bound_body_path, hash_match.group(1).lower() if hash_match else None


def review(path):
    report = inspect_path(path)
    body_path = Path(report.get('body_path', Path(path) / '正文.md' if Path(path).is_dir() else path)).resolve()
    review_path, bound_body_path, bound_hash = _review_binding_evidence(body_path)
    current_hash = report.get('inputs', {}).get('body_text_sha256')
    if not review_path.is_file():
        report['findings'].append(finding('MISSING_REVIEW_REPORT', 'NOTE', 'evidence',
                                         '缺少审核报告；完整审核须按 fuben-review 读取当前完整稿。', file=review_path))
    else:
        if bound_body_path is None:
            report['findings'].append(finding('MISSING_REVIEW_BODY_PATH', 'REVIEW', 'evidence',
                                             '审核报告未记录 body_path，不能证明结论针对当前正文文件。', file=review_path))
        elif bound_body_path != body_path:
            report['findings'].append(finding('STALE_REVIEW_BODY_PATH', 'REVIEW', 'evidence',
                                             '审核报告记录的 body_path 与当前正文文件不一致；请确认是否复用了旧报告。',
                                             file=review_path, evidence=f'report={bound_body_path} current={body_path}'))
        else:
            report['checked'].append('review_report_body_path_binding')
        if bound_hash is None:
            report['findings'].append(finding('UNBOUND_REVIEW_REPORT', 'REVIEW', 'evidence',
                                             '审核报告未记录 body_text_sha256，不能证明对应当前正文。', file=review_path))
        elif current_hash and bound_hash != current_hash:
            report['findings'].append(finding('STALE_REVIEW_REPORT', 'BLOCK', 'evidence',
                                             '审核报告绑定的正文哈希与当前正文不一致；修改后必须重新审读。',
                                             file=review_path, evidence=f'report={bound_hash} current={current_hash}'))
        else:
            report['checked'].append('review_report_body_text_hash_binding')
    # Hash/path binding prevents stale approval but cannot attest that a real semantic review occurred.
    report['review_status'] = 'PROVISIONAL'
    report['findings'].append(finding('EDITORIAL_NOT_ATTESTED', 'NOTE', 'evidence',
                                     '只生成审核候选并核对版本绑定，没有确认语义精读或独立会审；完整审核按 fuben-review。'))
    return finish(report)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ('record', 'report'):
        from fuben_data import main as data_main
        if argv[0] == 'record' and len(argv) > 1 and not argv[1].startswith('-'):
            print('ERROR: 旧 record NN 点赞 [播放] 缺版本/时间/来源，已禁用以防继续写坏 CSV。\n'
                  '使用 python3 scripts/fuben_data.py record --input snapshot.json；先运行 template 查看结构。', file=sys.stderr)
            return 2
        return data_main(argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['design', 'draft', 'facts', 'consistency', 'review'])
    parser.add_argument('path')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'design':
        report = design(args.path)
    elif args.command == 'review':
        report = review(args.path)
    else:
        report = inspect_path(args.path, components={'facts', 'setting'} if args.command in ('facts', 'consistency') else None)
    return emit(report, json_output=args.json, label='MECHANICAL-' + args.command.upper())


if __name__ == '__main__':
    raise SystemExit(main())
