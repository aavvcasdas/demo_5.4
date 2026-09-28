#!/usr/bin/env python3
"""技能库体检：体积、常驻描述预算、重复文件、触发词冲突、损坏引用。

用法：
    python3 scripts/skills_audit.py                 # 人读报告
    python3 scripts/skills_audit.py --json          # 机器可读
    python3 scripts/skills_audit.py --strict        # 有问题时退出码 1（供门禁/CI 用）
    python3 scripts/skills_audit.py --context 128000 --desc-limit 150

判据来源见 docs/技能库体检-2026-09-28.md：
- 常驻 listing 有预算：Claude Code 默认取上下文窗口的 1%，单条 description 另有上限；
  超预算会按调用频次整条丢描述，被丢的 skill 只剩名字、不再触发；
- description 建议 ≤150 字符且触发词前置；
- 同一能力不要在多个 skill 里抢同一批触发词（相似 skill 会互相干扰）。

只读，不修改任何文件。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOTS = ("skills", ".agents/skills")
# 本仓主链路的触发词；出现在多个 skill 的 description 里就是抢入口
TRIGGERS = (
    "人生副本", "剧本人生", "口播", "短剧", "短篇", "长篇", "拆文", "扫榜",
    "去AI味", "封面", "导入", "审查", "审核", "正文", "剧本", "分镜", "视频",
)
DESC_WARN = 150          # 单条 description 建议上限（字符）
DEFAULT_CONTEXT = 200000  # 上下文窗口 token 数，用于估算 1% listing 预算
CHARS_PER_TOKEN = 0.8     # 中文为主的粗估：1 token ≈ 0.8 字符
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
# 这些脚本必须逐字节一致（每个 skill 独立可分发的代价，由 tests/test_fuben.py 断言）；
# 同名但不同内容只有它们算“漂移”，其它 references 同名不同内容属于长短篇差异，正常。
MUST_MATCH = {"check-ai-patterns.js", "story-profile.js", "story_hook_core.js", "style-whitelist.js"}


def read_description(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'^description:\s*"?(.*?)"?\s*$', text, re.M | re.S)
    return " ".join(match.group(1).split()) if match else ""


def collect(root: Path) -> dict[str, dict]:
    """返回 {skill 名: {path, files: {相对路径: (md5, 字节数)}, description}}。"""
    skills: dict[str, dict] = {}
    for base in SKILL_ROOTS:
        base_path = root / base
        if not base_path.is_dir():
            continue
        candidates = []
        for name in sorted(os.listdir(base_path)):
            path = base_path / name
            if not path.is_dir() or path.is_symlink():
                continue
            if name == "_archive":            # 归档区：下一层每个目录仍是一个 skill
                candidates.extend(sorted(p for p in path.iterdir() if p.is_dir()))
            else:
                candidates.append(path)
        for path in candidates:
            name = path.name
            skill_md = path / "SKILL.md"
            files: dict[str, tuple[str, int]] = {}
            for dirpath, dirnames, filenames in os.walk(path):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for filename in filenames:
                    full = Path(dirpath) / filename
                    rel = full.relative_to(path).as_posix()
                    data = full.read_bytes()
                    files[rel] = (hashlib.md5(data).hexdigest(), len(data))
            is_archived = name != "_archive" and "_archive" in path.parts
            key = f"{base}/{name}" if not is_archived else f"{base}/_archive/{name}"
            skills[key] = {
                "path": path.as_posix(),
                "archived": is_archived,
                "skill_md": skill_md.is_file(),
                "description": read_description(skill_md) if skill_md.is_file() else "",
                "files": files,
            }
    return skills


def broken_links(path: Path) -> list[str]:
    bad: list[str] = []
    for md in sorted(path.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"\]\(([^)#)]+\.(?:json|ya?ml|mjs|md|py|sh|js))", text):
            target = match.group(1)
            if target.startswith(("http://", "https://")):
                continue
            if not (md.parent / target).resolve().exists():
                bad.append(f"{md.relative_to(ROOT).as_posix()} -> {target}")
    return bad


def inspect(root: Path, context_tokens: int, desc_limit: int) -> dict:
    skills = collect(root)
    active = {k: v for k, v in skills.items() if not v["archived"]}
    archived = {k: v for k, v in skills.items() if v["archived"]}

    report: dict = {
        "skill_root": root.as_posix(),
        "counts": {"total": len(skills), "active": len(active), "archived": len(archived)},
        "totals": {},
        "skills": [],
        "duplicates": [],
        "trigger_conflicts": [],
        "broken_links": [],
        "warnings": [],
    }

    total_files = total_bytes = 0
    desc_chars = 0
    # 同相对路径 + 同内容 = 分发拷贝（本仓由测试强制一致，属分布成本，只报告不告警）
    by_rel: dict[str, list[str]] = {}
    for name, info in sorted(skills.items()):
        files = info["files"]
        size = sum(v[1] for v in files.values())
        total_files += len(files)
        total_bytes += size
        desc = info["description"]
        if not info["archived"]:      # 归档 skill 不占常驻 listing
            desc_chars += len(desc)
        row = {
            "skill": name,
            "archived": info["archived"],
            "files": len(files),
            "kb": round(size / 1024, 1),
            "desc_chars": len(desc),
            "desc_over_limit": len(desc) > desc_limit,
        }
        report["skills"].append(row)
        for rel, (digest, nbytes) in files.items():
            if rel == "SKILL.md":
                continue
            by_rel.setdefault(rel, []).append(name)

    report["totals"] = {
        "files": total_files,
        "mb": round(total_bytes / 1024 / 1024, 2),
        "description_chars": desc_chars,
        "listing_budget_chars": int(context_tokens * 0.01 * CHARS_PER_TOKEN),
        "context_tokens": context_tokens,
    }
    budget = report["totals"]["listing_budget_chars"]
    if desc_chars > budget:
        report["warnings"].append(
            f"常驻 description 合计 {desc_chars} 字符 > 1% listing 预算约 {budget} 字符，"
            "超预算时按调用频次整条丢描述，低频 skill 会静默不再触发"
        )

    # 触发词冲突：同一关键词出现在 2 个以上“在用” skill 的 description 里
    for trigger in TRIGGERS:
        owners = [row["skill"] for row in report["skills"]
                  if not row["archived"] and trigger in
                  skills[row["skill"]]["description"]]
        if len(owners) > 1:
            report["trigger_conflicts"].append({"trigger": trigger, "skills": owners})

    # 重复文件（同路径同内容 + 同内容不同路径两种口径）
    for rel, owners in sorted(by_rel.items()):
        if len(owners) < 2:
            continue
        digests = {skills[o]["files"][rel][0] for o in owners}
        if len(digests) == 1:
            report["duplicates"].append({
                "path": rel, "skills": owners, "same_content": True,
                "kb": round(skills[owners[0]]["files"][rel][1] / 1024, 1),
            })
        elif Path(rel).name in MUST_MATCH:
            report["duplicates"].append({
                "path": rel, "skills": owners, "same_content": False, "kb": 0.0,
            })
    for row in report["skills"]:
        if row["desc_over_limit"] and not row["archived"]:
            report["warnings"].append(
                f"{row['skill']} 的 description {row['desc_chars']} 字符 > {desc_limit}，"
                "建议触发词前置并压到上限内"
            )
    if any(d["same_content"] is False for d in report["duplicates"]):
        report["warnings"].append("存在同路径不同内容的分发拷贝：可能已漂移，检查后同步")

    report["broken_links"] = broken_links(root)
    return report


def render(report: dict) -> None:
    totals = report["totals"]
    counts = report["counts"]
    print(f"技能库：{counts['total']} 个（在用 {counts['active']}，归档 {counts['archived']}）"
          f" / {totals['files']} 文件 / {totals['mb']} MB")
    print(f"常驻描述：{totals['description_chars']} 字符"
          f"（1% listing 预算约 {totals['listing_budget_chars']} 字符"
          f" @ {totals['context_tokens']} token 上下文）")
    print()
    print(f"{'skill':34}{'文件':>6}{'KB':>9}{'描述字符':>10}  状态")
    for row in sorted(report["skills"], key=lambda r: -r["desc_chars"]):
        state = "归档" if row["archived"] else ("描述超限" if row["desc_over_limit"] else "")
        print(f"{row['skill']:34}{row['files']:>6}{row['kb']:>9}{row['desc_chars']:>10}  {state}")
    print()
    if report["trigger_conflicts"]:
        print("触发词冲突（同一关键词被多个在用 skill 的 description 占用）：")
        for item in report["trigger_conflicts"]:
            print(f"  {item['trigger']}: {', '.join(item['skills'])}")
    else:
        print("触发词冲突：无")
    print()
    same = [d for d in report["duplicates"] if d["same_content"]]
    diff = [d for d in report["duplicates"] if not d["same_content"]]
    redundant = sum(d["kb"] * (len(d["skills"]) - 1) for d in same)
    print(f"分发拷贝（同路径同内容）：{len(same)} 组 / 单份合计 "
          f"{sum(d['kb'] for d in same):.1f} KB / 冗余体积 {redundant:.1f} KB"
          " —— 本仓由测试强制一致，属分布成本")
    if diff:
        print("同路径不同内容（疑似漂移）：")
        for item in diff:
            print(f"  {item['path']}: {', '.join(item['skills'])}")
    print(f"损坏引用：{len(report['broken_links'])}")
    for item in report["broken_links"]:
        print(f"  {item}")
    if report["warnings"]:
        print("\n提醒：")
        for warning in report["warnings"]:
            print(f"  - {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT,
                        help="上下文窗口 token 数，用于估算 1%% listing 预算")
    parser.add_argument("--desc-limit", type=int, default=DESC_WARN)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="有超限描述/漂移/损坏引用时退出码 1")
    args = parser.parse_args(argv)

    report = inspect(args.root, args.context, args.desc_limit)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        render(report)
    if args.strict and (
        report["warnings"]
        or report["broken_links"]
        or any(not d["same_content"] for d in report["duplicates"])
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
