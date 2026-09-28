#!/usr/bin/env python3
"""兑现与场次卡对表（确定性检查，advisory 不设卡）。

解决两个可机检的「剧情水」成因（2026-09-28 反水调研，来源见 docs/短视频Agent借鉴.md）：

1. **场次卡字段缺口**：02 场次单里每场是否写齐六字段
   （入场 / 欲望 / 阻力 / 落子 / 出场 / 递进）。缺哪一项，正文就有很大概率写不出推进——
   旧格式（只写「冲突/转折」）会整片标缺，属正常差异；v1.3.5 起新写的 02 必须齐。
2. **兑现丢失**：02 末尾的「兑现认领」表承诺的兑现点，是否在正文里真的落到了字面
   （对应 shuohao-skills 的「爽点认领」门：大纲说这集有爆点，剧本必须有戏认领它）。
   只查关键词是否出现，不判写得好看不好看。

兑现认领表格式（02 场次单末尾，3–5 行即可，不新增文件、不新增阶段）：

    ## 兑现认领
    | 兑现点 | 认领关键词 |
    |---|---|
    | 球鞋出厂价埋线 | 一百二十九 |
    | 押金被人交掉 | 住院押金已交 |

用法：
    python3 scripts/fuben_claims.py 作品/NN_主题          # 自动取最新运行目录
    python3 scripts/fuben_claims.py 作品/NN_主题 --json
    python3 scripts/fuben_claims.py 作品/NN_主题 --strict  # 有缺口/丢失时退出码 1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCENE_FIELDS = {
    "入场": r"入场|开场状态|初始状态|开局|此时",
    "欲望": r"欲望|要什么|想|打算|目标|图什么",
    "阻力": r"阻力|冲突|对手|挡|不肯|不给|不批|拒绝|规则",
    "落子": r"落子|主动|当场|他做|你做",
    "出场": r"出场|局面|变化|转折|判词|推进",
    "递进": r"递进|因为|所以|但是|接着|然后|上一场",
}
CLAIM_HEADER = re.compile(r"兑现认领|兑现点|认领")


def latest_run(work: Path) -> Path | None:
    runs = sorted((p for p in (work / "_运行").iterdir() if p.is_dir()), reverse=True)
    return runs[0] if runs else None


def scenes_of(text: str) -> list[dict]:
    blocks, current = [], None
    for line in text.splitlines():
        if re.match(r"^#{2,4}\s*场", line.strip()) or re.match(r"^[-*]\s*\*\*场", line.strip()):
            if current:
                blocks.append(current)
            current = {"title": line.strip()[:40], "text": ""}
        elif current is not None:
            current["text"] += line + "\n"
    if current:
        blocks.append(current)
    return [{"scene": b["title"],
             "missing": [k for k, pat in SCENE_FIELDS.items() if not re.search(pat, b["text"])]}
            for b in blocks]


def claims_of(text: str) -> list[dict]:
    rows, in_claim = [], False
    for line in text.splitlines():
        if CLAIM_HEADER.search(line) and line.strip().startswith("#"):
            in_claim = True
            continue
        if in_claim and line.strip().startswith("#"):
            break
        if not in_claim or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-：: "):
            continue
        if cells[0] in ("兑现点", "承诺", "项目"):
            continue
        rows.append({"claim": cells[0], "keyword": cells[1]})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("work", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="有缺口/未落地兑现时退出码 1")
    args = parser.parse_args(argv)

    work = args.work if args.work.is_absolute() else (Path.cwd() / args.work)
    if not work.is_dir():
        raise SystemExit(f"作品目录不存在：{work}")
    run = latest_run(work)
    body = work / "正文.md"
    scene_file = (run / "02_场次单.md") if run else None
    if not body.is_file():
        raise SystemExit(f"找不到正文：{body}")

    body_text = body.read_text(encoding="utf-8-sig")
    report = {
        "work": str(args.work), "disposition": "advisory_not_a_gate",
        "run": run.name if run else None,
        "scene_status": "NO_SCENE_FILE", "scenes": [],
        "claim_status": "NO_CLAIM_TABLE", "claims": [],
    }
    problems = []
    if scene_file and scene_file.is_file():
        report["scene_status"] = "CHECKED"
        report["scenes"] = scenes_of(scene_file.read_text(encoding="utf-8-sig"))
        for row in report["scenes"]:
            if row["missing"]:
                problems.append(f"{row['scene']} 缺字段：{'/'.join(row['missing'])}")
    if scene_file and scene_file.is_file():
        claims = claims_of(scene_file.read_text(encoding="utf-8-sig"))
        if claims:
            report["claim_status"] = "CHECKED"
            for row in claims:
                found = row["keyword"] in body_text
                report["claims"].append({**row, "found": found})
                if not found:
                    problems.append(f"兑现「{row['claim']}」的关键词「{row['keyword']}」在正文里找不到")

    if args.json:
        print(json.dumps({**report, "problems": problems}, ensure_ascii=False, indent=2))
        return 1 if (args.strict and problems) else 0

    print(f"兑现与场次卡对表（advisory）· {report['work']}（运行目录 {report['run']}）")
    if report["scene_status"] == "NO_SCENE_FILE":
        print("场次卡：未找到 02_场次单.md，跳过。")
    else:
        ok = [r for r in report["scenes"] if not r["missing"]]
        print(f"场次卡：{len(report['scenes'])} 场，六字段齐 {len(ok)} 场"
              f"（旧格式整片标缺属正常；v1.3.5 起新写的 02 必须齐，见 SKILL 阶段 2）")
        for row in report["scenes"]:
            if row["missing"]:
                print(f"  {row['scene']} → 缺 {'/'.join(row['missing'])}")
    if report["claim_status"] == "NO_CLAIM_TABLE":
        print("兑现认领：02 里没有「兑现认领」表（v1.3.5 起要求，3–5 行即可）。")
    else:
        for row in report["claims"]:
            print(f"兑现认领：{row['claim']} → 「{row['keyword']}」{'✅ 正文有' if row['found'] else '❌ 正文没有'}")
    print("提醒：本工具只查字段与关键词，不判好看；兑现写法的好坏仍由 04 人读判定。")
    return 1 if (args.strict and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
