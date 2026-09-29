#!/usr/bin/env python3
"""Create a bound editorial-review scaffold without pretending to approve a script."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from arena_screenplay_check import check  # noqa: E402

QUESTIONS = [
    "第一拍是否已经发生了可理解的事情，而不是标题/说明？",
    "每场主角的目标、阻力、具体动作和结果是什么？",
    "哪个对手或环境策略使主角改变了下一步？",
    "最早出现连续说明、平行罗列或无变化对白的位置在哪里？",
    "关键情绪是否由表演、动作、声音或关系变化承担，而非旁白宣布？",
    "结尾兑现的是前面哪个选择，代价和退出状态是否可见？",
    "哪些事实需要来源、授权或成片试听才能确认？",
]


def render(report: dict, body_path: Path) -> str:
    findings = report.get("findings", [])
    lines = [
        "# Arena 剧本审读记录（未盖章）",
        "",
        f"- body_path: `{body_path}`",
        f"- body_text_sha256: `{report.get('body_text_sha256', 'MISSING')}`",
        f"- generated_at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- mechanical_status: `{report.get('mechanical_status', 'ERROR')}`",
        "- editorial_status: `REQUIRED`",
        "- release_status: `NOT_READY`",
        "- reviewer: `未提供独立审读者`",
        "",
        "> 这份文件只绑定当前正文并列出审读问题。机械检查通过不等于剧本好看；没有逐场人读、成片试听和作者确认，不得改写成 APPROVED、READY 或“必爆”。",
        "",
        "## 机械检查摘要",
        "",
        f"- 场景数：{report.get('scene_count', 0)}",
        f"- 行数：{report.get('metrics', {}).get('lines', 0)}；对白行：{report.get('metrics', {}).get('dialogue_lines', 0)}；动作行：{report.get('metrics', {}).get('action_lines', 0)}",
    ]
    if findings:
        lines += ["", "## 机械发现（不能替代人读）", ""]
        for item in findings:
            at = f"（L{item['line']}）" if "line" in item else ""
            lines.append(f"- `{item['severity']}` `{item['code']}`{at}：{item['message']}")
    else:
        lines += ["", "## 机械发现", "", "- 未发现格式级阻断；这不是编辑层通过。"]
    lines += ["", "## 必须由审读者填写的逐场问题", ""]
    for i, question in enumerate(QUESTIONS, 1):
        lines.append(f"{i}. {question}\n   - 场景/行号：\n   - 原句短引：\n   - 结论与改法：")
    lines += [
        "",
        "## 未验证项",
        "",
        *[f"- {item}" for item in report.get("unverified", [])],
        "",
        "## 状态迁移",
        "",
        "- 只有补完逐场证据、重新读取当前正文并由作者/制片确认，才可把 `PROVISIONAL` 推进到 `READY_FOR_OWNER_CONFIRMATION`。",
        "- 正文、素材或本集契约任何一项变化后，重新运行本脚本；旧哈希对应的记录标记为 `STALE`。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an honest Arena screenplay review scaffold")
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = check(args.path)
    if args.json:
        print(json.dumps({
            "review_status": "PROVISIONAL",
            "editorial_status": "REQUIRED",
            "release_status": "NOT_READY",
            "mechanical": report,
            "questions": QUESTIONS,
        }, ensure_ascii=False, indent=2))
    else:
        output = args.output or args.path.with_name("审核记录.md")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(report, args.path), encoding="utf-8")
        print(f"WROTE {output}")
        print("editorial_status: REQUIRED")
        print("release_status: NOT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
