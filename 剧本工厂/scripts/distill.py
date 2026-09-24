#!/usr/bin/env python3
"""合集蒸馏：把 拆文库/ 的原文蒸馏成可施工的结构指纹与开场原句库。

用法：
  python3 剧本工厂/scripts/distill.py            # 全量蒸馏
  python3 剧本工厂/scripts/distill.py 17 80      # 只处理编号匹配的条目

产物（都是"待人工校准的机器初判"，不是成品）：
  剧本工厂/资产/指纹/<篇名>.json      每篇的结构指纹
  剧本工厂/资产/开场原句库.md          54 条真实开场原句 + 机器初判钩子类型
  剧本工厂/资产/骨架库存量.json        幕数/幕长/对手/兑现方式的统计
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "拆文库"
OUT = Path(__file__).resolve().parents[1] / "资产"

# 只蒸馏"人生副本"系列（其余长篇拆文库不参与口播剧本蒸馏）
SERIES_PREFIX = re.compile(r"^(\d{2}[a-c]?)_")

SPACE_WORDS = ("店 厅 馆 场 路 街 楼 门 桌 椅 窗 楼道 天台 地铁 车厢 院 校 屋 房 房间 "
               "厨房 客厅 阳台 电梯 楼梯 站台 公园 医院 学校 教室 办公室 工位 车里 后座 "
               "前台 收银 摊 巷 村 田 广场 网吧 网吧厅 大堂 包间 走廊").split()
ROLE_WORDS = ("老板 教练 同事 领导 主管 客户 亲戚 二姨 三叔 大姨 舅舅 奶奶 姥姥 外婆 爷 妈 "
              "爸爸 妈妈 哥 姐 弟 妹 老师 同学 室友 房东 中介 保安 医生 护士 服务员 前台 "
              "经理 阿姨 大叔 大爷 老太太 队长 班长 队长 民警 司机 摊主 老板 组长").split()
TIME_WORDS = ("那天 这天 这天晚上 当晚 第二天 第二天早上 第三天 后来 从此 直到 一年后 两年后 "
              "三年后 五年后 十年后 几个月后 半个月后 一个月后 半年后 上个月 去年 今年 那年 "
              "小时候 初中 高中 大学 毕业 第一年 第1年 第2年 第3年 第4年 第5年 冬天 夏天 秋天 春天 "
              "第1集 第2集 第3集 第4集 第5集 第6集 第7集 第8集").split()
QUOTE_OPEN = ("“", "「", "『", "\"")
DIALOGUE_VERBS = ("说 问 答 喊 叫 回 嘀咕 骂 笑 吼 念叨 说 劝 补 接 讲 呵呵").split()
UPGRADE_CUES = ("又 再 更 越来越 一次比一次 结果 没想到 可是 但是 但 然而 直到 甚至 "
                "第二天 后来 紧跟着 紧接着 最后一 最后一根").split()


def load_body(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def chars_of(lines: list[str]) -> int:
    return len(re.sub(r"\s", "", "".join(lines)))


def split_title(lines: list[str]) -> tuple[str, list[str]]:
    """剥掉栏目签名（今天体验的人生副本是X的一生 / 副本是X / 每天体验一种人生副本今天体验X）。

    ASR 会把签名和正文粘在一行，因此规则是：在前 4 行里找到**最后一个**含
    「人生/一生/副本」的签名行，把它连同之前的内容一起丢掉；题眼从签名行里正则抠出。
    """
    title = ""
    cut = 0
    for i, s in enumerate(lines[:4]):
        if re.search(r"(人生副本|副本是|体验的?是?.*的人生|的一生|人生$)", s):
            cut = i + 1
            m = (re.search(r"副本是(.+)", s) or re.search(r"体验的人生副本是(.+)", s)
                 or re.search(r"体验一种人生副本今天体验(.+)", s))
            if m:
                title = re.sub(r"(第[一二三四五六七八九十\d]+集.*)$", "", m.group(1)).strip()
            else:
                title = re.sub(r"^(今天|每天)?(带你|体验|一种)*", "", s)
    body = lines[cut:] if cut else list(lines)
    return title, body


def find_hook(body: list[str]) -> dict:
    """开场钩子＝前 4 句非签名台词。"""
    hook = body[:4]
    text = "".join(hook)
    kind = []
    if re.search(r"\d", text):
        kind.append("数字锚点")
    if re.search(r"(发现|忽然|突然|异常|不对劲|那天|没想到)", text):
        kind.append("异常悬念")
    if re.search(r"(你是一个|你有一个|你是那种|从小到大你|你生在)", text):
        kind.append("身份圈定")
    if re.search(r"(被|挨了|丢了|没了|死了|欠|塌)", text):
        kind.append("损失先行")
    if re.search(r"(所有人|都以为|再也|从来没人)", text):
        kind.append("认知反差")
    if not kind:
        kind.append("画面切入")
    return {"text": hook, "chars": len(re.sub(r"\s", "", text)), "tags": kind}


def segment(body: list[str]) -> list[dict]:
    """按时间/集数/强转折切幕。切点规则保持保守——宁可少切，人工可再并。"""
    cuts = []
    for i, s in enumerate(body):
        if i < 3:
            continue
        if re.match(r"^第[一二三四五六七八九十\d]+集", s):
            cuts.append((i, "集切"))
            continue
        for w in ("那天", "这天", "当晚", "第二天", "几天后", "几年后", "后来", "直到", "从那以后"):
            if s.startswith(w) and len(s) <= 14:
                cuts.append((i, w))
                break
    if not cuts:
        return [{"i": 0, "n": len(body), "cue": "全篇"}]
    segs, start, cue = [], 0, "开场"
    for idx, c in cuts:
        if idx - start >= 6:
            segs.append({"i": start, "n": idx, "cue": cue})
            start, cue = idx, c
    segs.append({"i": start, "n": len(body), "cue": cue})
    return segs


def seg_features(lines: list[str]) -> dict:
    text = "".join(lines)
    spaces = {w: text.count(w) for w in SPACE_WORDS if text.count(w)}
    roles = {w: text.count(w) for w in ROLE_WORDS if text.count(w)}
    quotes = sum(text.count(q) for q in QUOTE_OPEN)
    questions = text.count("吗") + text.count("呢") + text.count("?") + text.count("？")
    upgrades = sum(text.count(w) for w in UPGRADE_CUES)
    return {
        "chars": len(re.sub(r"\s", "", text)),
        "spaces_top": sorted(spaces.items(), key=lambda x: -x[1])[:4],
        "roles_top": sorted(roles.items(), key=lambda x: -x[1])[:4],
        "quotes": quotes,
        "questions": questions,
        "upgrade_marks": upgrades,
    }


def ending(lines: list[str]) -> list[str]:
    return [s for s in lines[-5:] if len(s) >= 2]


def distill_one(path: Path) -> dict:
    body = load_body(path)
    title, body = split_title(body)
    named = path.parent.parent.name
    segs = segment(body)
    detail = []
    for s in segs:
        chunk = body[s["i"]:s["n"]]
        f = seg_features(chunk)
        f.update({"cue": s["cue"], "start_line": s["i"], "first": chunk[0][:24] if chunk else ""})
        detail.append(f)
    total_chars = chars_of(body)
    return {
        "entry": named,
        "title": title or named,
        "series": "剧本人生",
        "source": str(path.relative_to(ROOT)),
        "chars": total_chars,
        "est_seconds_at_4_2cps": round(total_chars / 4.2),
        "hook": find_hook(body),
        "segments": detail,
        "segment_count": len(detail),
        "ending": ending(body),
        "line_stats": {
            "lines": len(body),
            "median_line_chars": round(statistics.median(len(s) for s in body), 1) if body else 0,
            "max_line_chars": max((len(s) for s in body), default=0),
        },
    }


def main() -> int:
    args = sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "指纹").mkdir(exist_ok=True)
    entries = []
    for d in sorted(CORPUS.iterdir()):
        if not d.is_dir() or not SERIES_PREFIX.match(d.name) or d.name.startswith("00_"):
            continue  # 00_ 是合集本体，已被逐篇拆出，不重复蒸馏
        src = d / "原文" / "原文.txt"
        if not src.exists():
            continue
        if args and not any(a in d.name for a in args):
            continue
        entries.append(distill_one(src))
    if not entries:
        print("没有匹配的条目")
        return 1

    for e in entries:
        (OUT / "指纹" / f"{e['entry']}.json").write_text(
            json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")

    # 开场原句库：真实原句，不做改写
    lines = ["# 开场原句库（机器提取 · 真实原句）", "",
             "> 来源：`拆文库/*/原文/原文.txt` 去签名后的前 4 句。**原句只用于研究钩子的构造方式；",
             "> 写新稿时必须换掉主题与句子，只借注意力机制。**类型标签为机器初判，引用前人工复核。", ""]
    for e in entries:
        tags = "/".join(e["hook"]["tags"])
        quote = "".join(e["hook"]["text"])
        lines.append(f"- **{e['entry']}** ｜{tags}｜{e['hook']['chars']}字")
        lines.append(f"  > {quote}")
    (OUT / "开场原句库.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 存量统计
    seg_counts = [e["segment_count"] for e in entries]
    stats = {
        "entries": len(entries),
        "segment_count_hist": {str(k): seg_counts.count(k) for k in sorted(set(seg_counts))},
        "chars": {
            "min": min(e["chars"] for e in entries),
            "median": statistics.median(e["chars"] for e in entries),
            "max": max(e["chars"] for e in entries),
        },
        "est_seconds_median": statistics.median(e["est_seconds_at_4_2cps"] for e in entries),
        "top_roles": {},
        "top_spaces": {},
    }
    from collections import Counter
    roles, spaces = Counter(), Counter()
    for e in entries:
        for c in e["segments"]:
            roles.update(dict(c["roles_top"]))
            spaces.update(dict(c["spaces_top"]))
    stats["top_roles"] = roles.most_common(15)
    stats["top_spaces"] = spaces.most_common(15)
    (OUT / "骨架库存量.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"蒸馏 {len(entries)} 篇 → 资产/指纹/*.json, 资产/开场原句库.md, 资产/骨架库存量.json")
    print(f"幕数分布 {stats['segment_count_hist']}；中位字数 {stats['chars']['median']:.0f}（≈{stats['est_seconds_median']:.0f} 秒）")
    print("常见对手位:", roles.most_common(8))
    print("常见空间:", spaces.most_common(8))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
