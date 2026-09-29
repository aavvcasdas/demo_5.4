#!/usr/bin/env python3
"""Deterministic checks for the Arena screenplay contract.

This checker deliberately does not score story quality.  A mechanical pass is
reported separately from editorial review and release readiness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCENE_RE = re.compile(r"^##\s+(EP\d+-SC\d+)\s+(.+?)\s*$")
DIALOGUE_RE = re.compile(r"^(?:\[[^\]]+\]\s*)?[\u4e00-\u9fffA-Za-z][^：:]{0,30}(?:（[^）]*）)?[：:]\s*.+$")
PRODUCTION_RE = re.compile(r"^\[(?:VO|OS|SFX|画面文字|连续性|转场)\]")
AUDIT_RE = re.compile(r"审核报告|机检|fuben_(?:run|craft|viral|claims)|PASS_WITH_REVIEW|必爆|评论区报数")


def normalized_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def finding(code: str, severity: str, message: str, line: int | None = None) -> dict:
    item = {"code": code, "severity": severity, "message": message}
    if line is not None:
        item["line"] = line
    return item


def check(path: Path) -> dict:
    path = path.resolve()
    findings: list[dict] = []
    if not path.is_file():
        return {
            "path": str(path),
            "mechanical_status": "ERROR",
            "editorial_status": "REQUIRED",
            "release_status": "NOT_READY",
            "findings": [finding("MISSING_BODY", "BLOCK", "剧本文件不存在")],
        }
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "path": str(path),
            "mechanical_status": "ERROR",
            "editorial_status": "REQUIRED",
            "release_status": "NOT_READY",
            "findings": [finding("NOT_UTF8", "BLOCK", "剧本必须是 UTF-8 文本")],
        }

    lines = text.splitlines()
    scenes: list[dict] = []
    for index, raw in enumerate(lines, start=1):
        line = raw.strip()
        match = SCENE_RE.match(raw)
        if match:
            scenes.append({"id": match.group(1), "title": match.group(2), "line": index, "content": []})
            continue
        if scenes:
            scenes[-1]["content"].append((index, line))
        if "\x00" in raw:
            findings.append(finding("NUL_BYTE", "BLOCK", "正文含 NUL 字节", index))
        if AUDIT_RE.search(raw):
            findings.append(finding("AUDIT_META_IN_BODY", "REVIEW", "剧本正文混入审核/旧口播管线元话语；确认这不是角色台词", index))

    if not text.strip():
        findings.append(finding("EMPTY_BODY", "BLOCK", "剧本为空"))
    if not scenes:
        findings.append(finding("NO_SCENES", "BLOCK", "未找到 ## EP001-SC001 地点格式的场景标题"))
    seen_ids: set[str] = set()
    for scene in scenes:
        if scene["id"] in seen_ids:
            findings.append(finding("DUPLICATE_SCENE_ID", "BLOCK", f"场景编号重复：{scene['id']}", scene["line"]))
        seen_ids.add(scene["id"])
        content = [(n, s) for n, s in scene["content"] if s]
        if not content:
            findings.append(finding("EMPTY_SCENE", "BLOCK", f"{scene['id']} 没有正文", scene["line"]))
            continue
        dialogue_lines = [(n, s) for n, s in content if DIALOGUE_RE.match(s)]
        production_lines = [(n, s) for n, s in content if PRODUCTION_RE.match(s)]
        action_lines = [(n, s) for n, s in content if not DIALOGUE_RE.match(s) and not PRODUCTION_RE.match(s)]
        scene.update({"nonempty_lines": len(content), "dialogue_lines": len(dialogue_lines), "action_lines": len(action_lines)})
        if not action_lines:
            findings.append(finding("NO_ACTION_LINE", "REVIEW", f"{scene['id']} 只有对白/制作标签，没有可表演动作；需人工确认", scene["line"]))
        if not dialogue_lines and not production_lines:
            findings.append(finding("NO_PERFORMED_OR_SOUND_BEAT", "REVIEW", f"{scene['id']} 没有对白、旁白或声音事实；需人工确认是否可拍", scene["line"]))
        malformed_dialogue = [(n, s) for n, s in content if ("：" in s or ":" in s) and not DIALOGUE_RE.match(s) and not PRODUCTION_RE.match(s)]
        for number, _ in malformed_dialogue:
            findings.append(finding("AMBIGUOUS_COLON_LINE", "REVIEW", f"{scene['id']} 有含冒号但不像角色对白的行，确认是否误写为对白", number))

    # This is a format check, not a semantic verdict.
    block_count = sum(f["severity"] == "BLOCK" for f in findings)
    mechanical = "BLOCKED" if block_count else "PASS"
    return {
        "path": str(path),
        "body_text_sha256": normalized_sha256(path),
        "mechanical_status": mechanical,
        "editorial_status": "REQUIRED",
        "release_status": "NOT_READY",
        "scene_count": len(scenes),
        "scenes": [{k: v for k, v in scene.items() if k not in {"content"}} for scene in scenes],
        "metrics": {
            "lines": len(lines),
            "nonempty_lines": sum(bool(line.strip()) for line in lines),
            "dialogue_lines": sum(scene.get("dialogue_lines", 0) for scene in scenes),
            "action_lines": sum(scene.get("action_lines", 0) for scene in scenes),
        },
        "findings": findings,
        "unverified": [
            "故事目标、阻力和状态变化",
            "人物表演与对白潜台词",
            "实际画面/声音可拍性",
            "念稿/成片听感",
            "平台发布与观众数据",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Arena screenplay deterministic contract checker")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    report = check(args.path)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"mechanical_status: {report['mechanical_status']}")
        print(f"editorial_status: {report['editorial_status']}")
        print(f"release_status: {report['release_status']}")
        for item in report["findings"]:
            at = f" L{item['line']}" if "line" in item else ""
            print(f"{item['severity']} {item['code']}{at}: {item['message']}")
    return 0 if report["mechanical_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
