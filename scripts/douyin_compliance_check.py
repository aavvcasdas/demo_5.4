#!/usr/bin/env python3
"""v4.1 剧本门禁自动化核查工具（反教练车公文词/PPT报菜名/哑巴默剧 + 对白配额 + 肯定式结尾 + 接缝连接词）。

用法：
    python3 scripts/douyin_compliance_check.py 作品/96_.../正文.md
    python3 scripts/douyin_compliance_check.py 作品/96_.../ --json
    python3 scripts/douyin_compliance_check.py 作品/96_.../正文.md --strict
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FORBIDDEN_ENDING_PATTERNS = (
    "关掉也不会塌", "不换但也不欠", "没有人找你", "你不知道你只知道",
)
FORBIDDEN_AI_CLICHES = (
    "值得一提的是", "不禁", "不由得", "五味杂陈", "五雷轰顶", "心潮澎湃",
    "感慨万千", "眼眶一热", "似乎在诉说着",
)
FORBIDDEN_BUREAUCRATIC_JARGON = (
    "连带责任", "涤除", "实控人", "经办盾", "复核盾", "承接协议", "备案回执", "移交单", "暨",
)
PPT_ENUMERATION_RE = re.compile(r"第[一二三]样(?:拿出来|摊开|亮出来|掏出来)")
SEAM_FORBIDDEN_STARTERS = (
    "于是，", "于是", "后来，", "从那以后", "就这样，", "然而，", "与此同时", "不仅如此",
)

SPEAKER_TAG_RE = re.compile(
    r"(?:(?:^|[，。！？\s])(?:你|他|她|老板|主管|店长|班长|大勇|王哥|老李|李姐|外甥|你妈|我妈|你爸|同事|客服|护士|警察)"
    r"[^。！？\n]{0,18}?"
    r"(?:说|问|答|追问|反问|喊|回道|开口|吼道|骂道|哭喊道|哭喊|催你|点醒)[：:，,]?)"
)

QUOTE_SENTENCE_RE = re.compile(r"[「“]([^」”]{4,})[」”]")


def resolve_body_path(target: Path) -> Path:
    if target.is_dir():
        candidate = target / "正文.md"
        if candidate.is_file():
            return candidate
    return target


def check_text(text: str, path: Path) -> dict:
    raw_lines = text.splitlines()
    non_empty = [(idx + 1, line.strip()) for idx, line in enumerate(raw_lines) if line.strip()]
    findings: list[dict] = []

    # 1. 禁用网文/AI 套话与 v4.1 禁用公文词/PPT 报菜名扫描
    for lineno, line in non_empty:
        for cliche in FORBIDDEN_AI_CLICHES:
            if cliche in line:
                findings.append({
                    "severity": "BLOCK",
                    "rule_id": "FORBIDDEN_AI_CLICHE",
                    "line": lineno,
                    "evidence": line,
                    "message": f"命中禁用网文/AI套话「{cliche}」。",
                })
        for jargon in FORBIDDEN_BUREAUCRATIC_JARGON:
            if jargon in line:
                findings.append({
                    "severity": "BLOCK",
                    "rule_id": "BUREAUCRATIC_JARGON",
                    "line": lineno,
                    "evidence": line,
                    "message": f"命中 v4.1 禁用普法/公文术语「{jargon}」，必须改成 ≤6 字大白话。",
                })
        if PPT_ENUMERATION_RE.search(line):
            findings.append({
                "severity": "BLOCK",
                "rule_id": "PPT_ENUMERATION_CLIMAX",
                "line": lineno,
                "evidence": line,
                "message": "命中 v4.1 禁用「第一样/第二样/第三样」PPT 报菜名句式，高潮必须用单王牌引爆活人互咬。",
            })

    # 2. v3.8 / v4.1 对白配额与说话人标记核查（2–6 处，禁 0 处哑巴默剧）
    speaker_lines: list[int] = []
    quote_lines: list[int] = []
    for lineno, line in non_empty:
        if SPEAKER_TAG_RE.search(line):
            speaker_lines.append(lineno)
            if len(speaker_lines) >= 2 and speaker_lines[-1] - speaker_lines[-2] == 1:
                findings.append({
                    "severity": "REVIEW",
                    "rule_id": "ADJACENT_SPEAKER_TAGS",
                    "line": lineno,
                    "evidence": line,
                    "message": f"行 {speaker_lines[-2]} 与行 {lineno} 出现相邻说话人标记，违反「任意两处不得相邻」。",
                })
        if QUOTE_SENTENCE_RE.search(line):
            quote_lines.append(lineno)

    if len(speaker_lines) == 0:
        findings.append({
            "severity": "REVIEW",
            "rule_id": "MUTE_MIME_ZERO_SPEAKER",
            "line": 1,
            "evidence": "说话人标记行共 0 处",
            "message": "v4.1 规定全篇说话人标记应保持 2–6 处，0 处易沦为全员哑巴默剧。",
        })
    elif len(speaker_lines) > 6:
        findings.append({
            "severity": "REVIEW",
            "rule_id": "SPEAKER_TAG_QUOTA",
            "line": speaker_lines[0],
            "evidence": f"说话人标记行共 {len(speaker_lines)} 处（行 {speaker_lines}）",
            "message": f"规定说话人标记全篇 ≤6 处，当前检测到 {len(speaker_lines)} 处，建议用「字替话四法」压缩。",
        })

    if len(quote_lines) > 3:
        findings.append({
            "severity": "REVIEW",
            "rule_id": "QUOTED_LINE_QUOTA",
            "line": quote_lines[0],
            "evidence": f"整句引号台词共 {len(quote_lines)} 处（行 {quote_lines}）",
            "message": f"规定整句引号钉子 ≤3 处，当前检测到 {len(quote_lines)} 处。",
        })

    # 3. v3.9.4 结尾肯定式硬门禁（最后 15 行非空行）
    tail_15 = non_empty[-15:] if len(non_empty) >= 15 else non_empty
    neg_hits: list[tuple[int, str]] = []
    neg_re = re.compile(r"(?:不是|不会|没有|不知道|不换|不算|也没|算了吧)")
    for lineno, line in tail_15:
        for pat in FORBIDDEN_ENDING_PATTERNS:
            if pat in line:
                findings.append({
                    "severity": "BLOCK",
                    "rule_id": "FORBIDDEN_NEGATIVE_ENDING",
                    "line": lineno,
                    "evidence": line,
                    "message": f"结尾命中 v3.9.4 禁用丧式否定骨架「{pat}」，必须改为肯定式收尾。",
                })
        if neg_re.search(line):
            neg_hits.append((lineno, line))

    if len(neg_hits) >= 3:
        findings.append({
            "severity": "BLOCK",
            "rule_id": "ENDING_NEGATIVE_DENSITY",
            "line": neg_hits[0][0],
            "evidence": f"最后15行含否定词 {len(neg_hits)} 处：{[x[0] for x in neg_hits]}",
            "message": f"v3.9.4 规定最后 15 行否定词 ≥3 次必须返工（当前 {len(neg_hits)} 处），请改为肯定式得到句。",
        })

    # 4. 段首连接词扫描（v3.4 禁连接词开场）
    for idx, line in enumerate(raw_lines):
        s = line.strip()
        if not s:
            continue
        is_para_start = (idx == 0) or (not raw_lines[idx - 1].strip())
        if is_para_start:
            for starter in SEAM_FORBIDDEN_STARTERS:
                if s.startswith(starter):
                    findings.append({
                        "severity": "REVIEW",
                        "rule_id": "SEAM_CONJUNCTION_START",
                        "line": idx + 1,
                        "evidence": s,
                        "message": f"段首使用禁用连接词「{starter}」起笔，违反 v3.4 接缝十法纪律。",
                    })
                    break

    blocks = [f for f in findings if f["severity"] == "BLOCK"]
    reviews = [f for f in findings if f["severity"] == "REVIEW"]
    status = "FAIL" if blocks else ("PASS_WITH_REVIEW" if reviews else "PASS")

    return {
        "path": str(path),
        "status": status,
        "compliance_pass": len(blocks) == 0,
        "metrics": {
            "total_lines": len(raw_lines),
            "non_empty_lines": len(non_empty),
            "speaker_tag_count": len(speaker_lines),
            "quoted_sentence_count": len(quote_lines),
            "tail_15_negative_count": len(neg_hits),
        },
        "block_count": len(blocks),
        "review_count": len(reviews),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="作品目录或正文.md路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--strict", action="store_true", help="存在 REVIEW 时也返回非 0")
    args = parser.parse_args()

    body_path = resolve_body_path(args.target)
    if not body_path.is_file():
        print(json.dumps({"status": "ERROR", "message": f"找不到文件: {body_path}"}, ensure_ascii=False), file=sys.stderr)
        return 2

    text = body_path.read_text(encoding="utf-8", errors="replace")
    report = check_text(text, body_path)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"=== v4.1 剧本门禁核查: {report['path']} ===")
        print(f"状态: {report['status']} | BLOCK: {report['block_count']} | REVIEW: {report['review_count']}")
        m = report["metrics"]
        print(
            f"指标: 非空行={m['non_empty_lines']} | 说话人标记={m['speaker_tag_count']}(2–6) | "
            f"整句引号={m['quoted_sentence_count']}(≤3) | 结尾15行否定词={m['tail_15_negative_count']}(<3)"
        )
        for f in report["findings"]:
            print(f"  [{f['severity']}] L{f['line']} ({f['rule_id']}): {f['message']} -> 「{f['evidence']}」")

    if report["block_count"] > 0:
        return 1
    if args.strict and report["review_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
