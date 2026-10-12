#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new拆文库索引器（技术工具，不判创作）。

用途：把 `new拆文库/*/` 已有的拆解产物（`_meta.json` / `拆文报告.md` / `情节节点.md` /
`写作手法.md`）抽成**机器可读索引 + 人读卡片库**，供 `fuben-write` 阶段 1（选题）与
阶段 2（人生时间轴/剧情）查表用。

产物（只写这三个文件，不动任何原文）：
  new拆文库/_index.json   机器可读记录
  new拆文库/_索引.md      总表（编号 NL-###、题材、字数、反转类型、情绪极值、峰值位置、可用层级）
  new拆文库/_卡库.md      每篇一张卡（一句话/结构/开头钩子/结尾/避坑），写前直接抄 3 抄 1

纪律：本脚本**不打分、不判好坏、不排名**；它只做抽取与计数。
      `new拆文库/*/原文/*` 与 `拆文库/*/原文/*` 不得改写（受 tests/protected_sources.json 保护）。

用法：
  python3 scripts/newlib_index.py            # 生成/刷新三个产物
  python3 scripts/newlib_index.py --check     # 只检查索引是否是最新的（CI/体检用）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "new拆文库")
OUT_JSON = os.path.join(LIB, "_index.json")
OUT_MD = os.path.join(LIB, "_索引.md")
OUT_CARDS = os.path.join(LIB, "_卡库.md")

# ---------------------------------------------------------------- 题材分层
# A=可直接现实化（现代/现实向，只换人物不换赛道）
# B=需转译（古言/宫斗/重生/穿书/玄幻 → 转成现代权力结构：家族企业/婆媳/拆迁/职场）
# C=只取关系机制（甜宠恋爱日常/纯设定流，题材不用，只用推拉/称呼/误会锯齿等机制）
KW_C = ["甜宠", "仙侠", "玄幻", "科幻", "脑洞", "奇幻", "养成", "游戏", "青春恋爱"]
KW_B = ["古言", "宫斗", "宅斗", "古穿", "穿越", "穿书", "重生", "复仇", "豪门", "真假千金",
        "文娱", "娱乐圈", "民国", "双生", "沙雕", "系统", "权谋", "女帝", "宫廷"]
KW_A = ["世情", "都市", "现代", "小三", "婚恋", "追妻", "火葬场", "死人文学", "悬疑", "民俗",
        "校园", "霸凌", "拐卖", "卧底", "缅北", "救赎", "现实", "破镜重圆", "职场", "县城"]

# 古代/非现实标记（故意用强标记，避免「影帝」「朝暮」这类词误伤现代题材）
ANCIENT = ["古言", "宫廷", "宫斗", "宅斗", "嫡", "庶", "贵妃", "皇后", "皇帝", "太孙", "太子",
           "王爷", "侯门", "婢", "朝堂", "科举", "将军", "后宫", "妃嫔", "王朝", "皇太孙",
           "修仙", "仙门", "宗门", "仙侠", "玄幻", "异界", "妖族", "神明", "灵根"]


def tier_of(genre: str, sample: str = "") -> str:
    """A 近 / B 需转译 / C 只取机制。

    判定顺序：非现实标记 → 甜宠/幻想类 → 古代/权谋类 → 现代现实类 → 默认 A。
    这只是「离抖音现实向口播的距离」的近似值，**不是评分**；拿不准时以卡库正文人工判断。
    """
    g, s = genre or "", sample or ""
    if any(k in g for k in KW_C):
        return "C"
    if any(k in s for k in ANCIENT) or any(k in g for k in KW_B):
        return "B"
    if any(k in g for k in KW_A):
        return "A"
    return "A" if g else "B"


# ---------------------------------------------------------------- 抽取工具
def read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    for enc in ("utf-8", "gbk", "utf-8-sig"):
        try:
            with open(path, encoding=enc) as fh:
                return fh.read()
        except UnicodeDecodeError:
            continue
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def section(text: str, *names: str) -> str:
    """取某个二级/三级小节的正文（到下一个同级标题为止）。"""
    lines = text.splitlines()
    out: list[str] = []
    want = False
    level = 0
    for ln in lines:
        m = re.match(r"^(#{2,4})\s+(.*)$", ln)
        if m:
            hlen, title = len(m.group(1)), m.group(2).strip()
            if want and hlen <= level:
                break
            if any(n in title for n in names):
                want, level = True, hlen
                continue
        if want:
            out.append(ln)
    return "\n".join(out).strip()


def grab(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text, re.M)
    return m.group(1).strip() if m else default


NUM = r"[0-9]+(?:\.[0-9]+)?"


VALUE_RE = re.compile(r"([+-]?\d+)\s*$")


REVERSAL = ["认知反转", "身份反转", "动机反转", "信息反转", "视角反转", "时间线反转", "无反转"]


def _emotion(emo_label: str, emo_val: str | None) -> tuple[str, int | None]:
    """情绪字段统一成 (标签, 数值)。两种写法：情绪{震惊}{-5} 与 情绪{震惊-5}。"""
    if emo_val not in (None, ""):
        try:
            return emo_label.strip(), int(emo_val)
        except ValueError:
            pass
    m = VALUE_RE.search(emo_label.strip())
    if m:
        return emo_label[:m.start()].strip() or emo_label.strip(), int(m.group(1))
    return emo_label.strip(), None


def parse_nodes(path: str) -> dict:
    """情节节点.md → 节点数 / 情绪序列 / 极值 / 峰值位置% / 翻转次数 / 手法频次。

    兼容三种既有排版：
      A `N1 **标题**：类型{对话} | 情绪{平静+1} | 涉及{…} | 手法{反差钩子}`
      B `N1 **标题**：类型{信息} | 情绪{冷峻}{-3} | 涉及{…}`（无手法列）
      C `- N1【起·钩子】正文…`（清单式，无情绪量表 → 只计节点数）
    """
    text = read(path)
    nodes: list[dict] = []
    pat = re.compile(
        r"^N(\d+)\s+\*\*(.+?)\*\*：类型\{([^}]*)\}\s*\|\s*情绪\{([^}]*)\}(?:\{([+-]?\d+)\})?\s*\|\s*涉及\{([^}]*)\}"
        r"(?:\s*\|\s*手法\{([^}]*)\})?", re.M)
    for m in pat.finditer(text):
        idx, title, ntype, emo_label, emo_val, who, craft = m.groups()
        label, val = _emotion(emo_label, emo_val)
        nodes.append({
            "n": int(idx), "title": title.strip(), "type": ntype.strip(),
            "emotion": label, "value": val,
            "who": [w.strip() for w in re.split(r"[、,，]", who) if w.strip()],
            "craft": [c.strip() for c in re.split(r"[+＋/、]", craft or "") if c.strip()],
        })
    if not nodes:  # 竖线式：**N1** ｜ Hook ｜ -5 ｜ 人物 ｜ 手法
        for m in re.finditer(r"^\s*[-*]?\s*\*\*N(\d+)\*\*\s*[｜|]\s*([^｜|\n]*)[｜|]\s*([+-]?\d+)\s*[｜|]\s*([^｜|\n]*)[｜|]\s*([^\n]*)",
                             text, re.M):
            nodes.append({"n": int(m.group(1)), "title": "", "type": m.group(2).strip(),
                          "emotion": "", "value": int(m.group(3)),
                          "who": [w.strip() for w in re.split(r"[、,，]", m.group(4)) if w.strip()],
                          "craft": [c.strip() for c in re.split(r"[+＋/、]", m.group(5)) if c.strip()]})
    if not nodes:  # 清单式：- **N1** 描述 / N1【标题】
        for m in re.finditer(r"^\s*[-*]?\s*\*{0,2}N(\d+)\*{0,2}\s*【?([^】\n]{0,40})】?", text, re.M):
            nodes.append({"n": int(m.group(1)), "title": m.group(2).strip().rstrip("：: "), "type": "",
                          "emotion": "", "value": None, "who": [], "craft": []})
    vals = [n["value"] for n in nodes if n["value"] is not None]
    extreme = min(vals) if vals else None
    peak_pct = None
    if vals and extreme is not None:
        first = next(i for i, n in enumerate(nodes) if n["value"] == extreme)
        peak_pct = round(first / max(len(nodes) - 1, 1) * 100, 1)
    flips = 0
    for a, b in zip(vals, vals[1:]):
        if (a > 0 > b) or (a < 0 < b) or (a == 0 and b != 0):
            flips += 1
    craft_freq: dict[str, int] = {}
    for n in nodes:
        for c in n["craft"]:
            craft_freq[c] = craft_freq.get(c, 0) + 1
    return {
        "node_count": len(nodes),
        "emotion_min": extreme,
        "emotion_max": max(vals) if vals else None,
        "peak_pct": peak_pct,
        "flips": flips,
        "craft_freq": dict(sorted(craft_freq.items(), key=lambda kv: -kv[1])),
        "first_nodes": [{"title": n["title"], "emotion": n["emotion"], "type": n["type"]}
                        for n in nodes[:3]],
    }


def parse_report(path: str) -> dict:
    text = read(path)
    one = grab(r"^\*\*一句话(?:评价|核|主线)?\*\*：(.+)$", text)
    core = section(text, "故事核")
    setup = grab(r"^\*\*设定\*\*：(.+)$", section(text, "故事核"))
    theme = grab(r"^\*\*主题\*\*：(.+)$", section(text, "故事核"))
    reversal = grab(r"^\*\*反转类型\*\*：(.+)$", text)
    if not reversal:
        reversal = grab(r"反转类型：([^\n|]+)", text)
    timing = grab(r"^\*\*时机\*\*：(.+)$", text)
    end_type = grab(r"\|\s*结尾类型\s*\|\s*([^|\n]+)\|", text)
    end_power = grab(r"\|\s*结尾情绪强度\s*\|\s*([^|\n]+)\|", text)
    open_type = grab(r"\|\s*钩子类型\s*\|\s*([^|\n]+)\|", text)
    open_power = grab(r"\|\s*开头情绪强度\s*\|\s*([^|\n]+)\|", text)
    spread = grab(r"\|\s*传播欲\s*\|\s*([^|\n]+)\|", text)
    # 可复用结构 / 可借鉴套路 / 可复现模块
    reuse_text = section(text, "可复用结构") or section(text, "可借鉴套路") or section(text, "可复现模块")
    if not reuse_text:  # 粗体行内小节：**可复用结构（≥3）**：
        reuse_text = grab(r"^\*\*可复用(?:结构|手法|套路)[^\n]*\*\*[：:]?\s*$\n((?:[-*\d].*\n?)+)", text) or ""
    reuse = [re.sub(r"\s+", " ", m.group(2)).strip()
             for m in re.finditer(r"^\s*(\d+)[\.、]\s*\*\*(.+?)\*\*", reuse_text, re.M)]
    if not reuse:
        reuse = [re.sub(r"\s+", " ", m.group(1)).strip()
                 for m in re.finditer(r"^\s*(?:\d+[\.、]|[-*])\s*(.{12,})$", reuse_text, re.M)]
    avoid = [re.sub(r"\s+", " ", m.group(1)).strip()
             for m in re.finditer(r"^\s*\d+[\.、]\s*(.{12,})$", section(text, "不建议模仿", "避坑"), re.M)]
    scores = dict(re.findall(r"\|\s*(开头吸引力|情感拉扯力|反转设计|节奏控制|结尾余韵)\s*\|\s*(\d)\s*\|", text))
    dens = dict(re.findall(r"\|\s*(事件密度|对话密度|冲突密度)\s*\|\s*([^|\n]+)\|", text))
    return {
        "one_line": one, "setup": setup, "theme": theme, "reversal": reversal, "timing": timing,
        "end_type": end_type.strip(), "end_power": end_power.strip(),
        "open_hook": open_type.strip(), "open_power": open_power.strip(), "spread": spread.strip(),
        "reuse": reuse[:8], "avoid": avoid[:5], "scores": scores, "density": dens,
    }


def parse_craft(path: str) -> dict:
    """写作手法.md → 高可复用度的手法行（只取『可复用度 高』那一列）。"""
    text = read(path)
    high = [re.sub(r"\s+", " ", m.group(1)).strip()
            for m in re.finditer(r"\|\s*([^|\n]{6,40}?)\s*\|\s*[^|\n]*\|\s*[^|\n]*\|\s*(?:高|高｜|\*\*高\*\*)\s*\|", text)]
    if not high:  # 兼容没有「可复用度」列的写法
        high = [re.sub(r"\s+", " ", m.group(1)).strip()
                for m in re.finditer(r"\|\s*([^|\n]{6,40}?)\s*\|\s*[^|\n]*\|\s*高\s*\|", text)]
    pov = grab(r"\|\s*POV 类型\s*\|\s*([^|\n]+)\|", text)
    dialogue = grab(r"\|\s*对话占比\s*\|\s*([^|\n]+)\|", text)
    if not high:  # 兼容「## N. 手法名」分节式写法：取节标题 + 首句
        for m in re.finditer(r"^##\s*(?:\d+[\.、]\s*)?([^#\n]{4,40})$", text, re.M):
            title = m.group(1).strip()
            if title in ("POV 策略", "对话手法", "时间操控", "信息控制", "其他手法", "意象/物件追踪"):
                continue
            body = text[m.end():m.end() + 400]
            first = next((ln.strip(" ->") for ln in body.splitlines()
                          if ln.strip() and not ln.startswith(("#", "|", ">"))), "")
            high.append(f"{title}｜{first[:80]}" if first else title)
    objects = re.findall(r"^\|\s*([^|\n]{1,24}?)\s*\|\s*[^|\n]*\|[^|\n]*\|[^|\n]*\|\s*$", text, re.M)
    return {"pov": pov, "dialogue": dialogue, "high_value": high[:10], "object_rows": len(objects)}


def parse_entry(name: str) -> dict:
    d = os.path.join(LIB, name)
    meta = {}
    mp = os.path.join(d, "_meta.json")
    if os.path.exists(mp):
        try:
            meta = json.loads(read(mp))
        except json.JSONDecodeError:
            meta = {}
    rep = os.path.join(d, "拆文报告.md")
    nodes = parse_nodes(os.path.join(d, "情节节点.md"))
    report = parse_report(rep) if os.path.exists(rep) else {}
    if not report.get("one_line"):  # 长篇式：从「概要」取全书概要首句
        brief = read(os.path.join(d, "概要.md"))
        para = grab(r"^##\s*全书概要[^\n]*\n+((?:[^\n#].*\n?)+)", brief)
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            report["one_line"] = para[:160] + ("…" if len(para) > 160 else "")
    craft = parse_craft(os.path.join(d, "写作手法.md"))
    genre = meta.get("genre_detected") or grab(r"题材\s*[:：]\s*([^|\n]+)", read(rep)[:2000])
    sc = meta.get("structure_counts") or {}
    reversal = sc.get("reversal_type") or ""
    rev_txt = report.get("reversal", "")
    for r in REVERSAL:  # 报告里写成整句，抽回枚举值
        if rev_txt.startswith(r):
            reversal = reversal or r
            break
    sample = f"{report.get('one_line','')} {report.get('setup','')} {report.get('theme','')} {genre}"
    return {
        "name": name,
        "has_meta": bool(meta),
        "has_report": os.path.exists(rep),
        "has_nodes": os.path.exists(os.path.join(d, "情节节点.md")),
        "has_craft": os.path.exists(os.path.join(d, "写作手法.md")),
        "word_count": meta.get("word_count") or 0,
        "created_at": meta.get("created_at", ""),
        "genre": genre,
        "tier": "D" if not meta else tier_of(genre, sample),
        "reversal": reversal or (rev_txt[:20] if rev_txt else ""),
        "timing": report.get("timing", ""),
        "one_line": report.get("one_line", ""),
        "setup": report.get("setup", ""),
        "theme": report.get("theme", ""),
        "end_type": report.get("end_type", ""),
        "end_power": report.get("end_power", ""),
        "open_hook": report.get("open_hook", ""),
        "open_power": report.get("open_power", ""),
        "spread": report.get("spread", ""),
        "reuse": report.get("reuse", []),
        "avoid": report.get("avoid", []),
        "scores": report.get("scores", {}),
        "density": report.get("density", {}),
        "pov": craft.get("pov", ""),
        "dialogue_share": craft.get("dialogue", ""),
        "high_value": craft.get("high_value", []),
        "node_count": nodes["node_count"],
        "emotion_min": nodes["emotion_min"],
        "emotion_max": nodes["emotion_max"],
        "peak_pct": nodes["peak_pct"],
        "flips": nodes["flips"],
        "craft_freq": nodes["craft_freq"],
        "first_nodes": nodes["first_nodes"],
        "structure_counts": sc,
    }


def sort_key(r: dict):
    return (r["tier"], -(r["word_count"] or 0))


def build() -> list[dict]:
    names = sorted(n for n in os.listdir(LIB)
                   if os.path.isdir(os.path.join(LIB, n)) and not n.startswith(("_", ".")))
    recs = [parse_entry(n) for n in names]
    recs.sort(key=sort_key)
    for i, r in enumerate(recs, 1):
        r["id"] = f"NL-{i:03d}"
    return recs


# ---------------------------------------------------------------- 渲染
TIER_DOC = {
    "A": "可直接现实化（现代/现实向）",
    "B": "需转译（古言/重生/穿书 → 现代权力结构）",
    "C": "只取关系机制（题材不直接用）",
    "D": "整书式（用剧情/情绪模块.md 的模块库，不做单篇卡）",
}


def md_index(recs: list[dict]) -> str:
    L = ["# new拆文库索引（技术索引，非评分表）", "",
         f"> 由 `scripts/newlib_index.py` 生成 · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
         f"共 {len(recs)} 篇。**本表不排名、不打分**；`可用层级`只表示「离抖音现实向口播的距离」，"
         "A 近、B 要转译、C 只借机制。", "",
         "字段：`极值`＝情节节点情绪量表最小值（-9~+9）；`峰值`＝该极值在全文的落点百分比；"
         "`翻转`＝情绪正负反转次数；`钩`＝`结构计数 hooks`（有 meta 时）。", ""]
    for tier in ("A", "B", "C", "D"):
        rows = [r for r in recs if r["tier"] == tier]
        L += [f"## {tier} 类 · {TIER_DOC[tier]}（{len(rows)} 篇）", "",
              "| 编号 | 书名 | 题材 | 字数 | 反转 | 极值 | 峰值 | 翻转 | 节点 | 钩 | 一句话（截断） |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            one = (r["one_line"] or "").replace("|", "／")[:46]
            L.append("| {id} | {name} | {genre} | {wc} | {rev} | {mn} | {pk} | {fl} | {nc} | {hk} | {one} |".format(
                id=r["id"], name=r["name"][:22], genre=(r["genre"] or "—")[:18], wc=r["word_count"] or "—",
                rev=(r["reversal"] or "—")[:8], mn=r["emotion_min"] if r["emotion_min"] is not None else "—",
                pk=f"{r['peak_pct']}%" if r["peak_pct"] is not None else "—", fl=r["flips"] or "—",
                nc=r["node_count"] or "—", hk=(r["structure_counts"] or {}).get("hooks", "—"), one=one or "—"))
        L.append("")
    L += ["## 汇总", ""]
    for tier in ("A", "B", "C", "D"):
        rows = [r for r in recs if r["tier"] == tier]
        L.append(f"- {tier} 类 {len(rows)} 篇：" + "、".join(r["id"] for r in rows[:40]) + ("…" if len(rows) > 40 else ""))
    L += ["", "## 用法（写前 3 分钟）", "",
          "1. 阶段 1 选题：在 A 类里找 **同身份/同处境** 的 1–2 篇，读它们卡片的 `一句话` 与 `处境`，只取切口，不取剧情。",
          "2. 阶段 2 剧情：读该篇卡片的 `可复用结构` 与 `情绪曲线`（极值/峰值/翻转），抄 **3 条结构 + 1 条避坑**，带 `NL-编号`。",
          "3. 阶段 4 复核：把自己稿子的谷底位置、翻转次数与参照篇并排写一行（**不打分**）。", ""]
    return "\n".join(L)


def md_cards(recs: list[dict]) -> str:
    L = ["# new拆文库卡片库（写前抄 3 抄 1 用）", "",
         f"> 由 `scripts/newlib_index.py` 生成 · {len(recs)} 张卡。**只借结构不借文本**；"
         "原文在 `new拆文库/*/原文/`，受哈希保护，不得改写或搬运。", ""]
    for r in recs:
        L += [f"## {r['id']} · {r['name']}", "",
              f"- 题材：{r['genre'] or '—'} ｜ 字数：{r['word_count'] or '—'} ｜ 层级：{r['tier']} ｜ "
              f"反转：{r['reversal'] or '—'} ｜ 揭底时机：{r['timing'] or '—'}",
              f"- POV：{r['pov'] or '—'} ｜ 对话占比：{r['dialogue_share'] or '—'} ｜ "
              f"节点 {r['node_count'] or '—'} 个 ｜ 情绪极值 {r['emotion_min'] if r['emotion_min'] is not None else '—'} ／ "
              f"峰值 {str(r['peak_pct']) + '%' if r['peak_pct'] is not None else '—'} ／ 翻转 {r['flips'] or '—'} 次",
              f"- 一句话：{r['one_line'] or '—'}"]
        if r["setup"]:
            L.append(f"- 故事核·设定：{r['setup'][:160]}")
        if r["theme"]:
            L.append(f"- 主题：{r['theme'][:160]}")
        if r["first_nodes"]:
            heads = [f"{n['title']}（{n['emotion']}）" if n.get("emotion") else n["title"]
                     for n in r["first_nodes"] if n.get("title")]
            if heads:
                L.append("- 开头三节点：" + " → ".join(heads)[:200])
        if r["open_hook"]:
            L.append(f"- 开头钩：{r['open_hook'][:120]}（强度 {r['open_power'] or '—'}）")
        if r["end_type"]:
            L.append(f"- 结尾：{r['end_type'][:80]}（强度 {r['end_power'] or '—'}｜传播欲 {r['spread'] or '—'}）")
        if r["reuse"]:
            L.append("- 可复用结构：")
            L += [f"  {i}. {s[:150]}" for i, s in enumerate(r["reuse"], 1)]
        if r["high_value"]:
            L.append("- 高可复用手法：" + "；".join(r["high_value"][:5]))
        if r["density"]:
            L.append("- 节奏速报：" + "｜".join(f"{k} {v}" for k, v in r["density"].items()))
        if r["avoid"]:
            L.append("- 避坑：" + "；".join(a[:110] for a in r["avoid"][:2]))
        elif not r["reuse"]:
            L.append("- 避坑：本卡未抽到，需人工读同目录 `拆文报告.md` 的节奏速报/短板判语。")
        L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验索引是否为最新")
    args = ap.parse_args()
    recs = build()
    payload = {
        "generator": "scripts/newlib_index.py",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "discipline": "索引只做抽取与计数，不打分不排名；原文受 tests/protected_sources.json 保护",
        "count": len(recs),
        "by_tier": {t: sum(1 for r in recs if r["tier"] == t) for t in ("A", "B", "C", "D")},
        "entries": recs,
    }
    if args.check and os.path.exists(OUT_JSON):
        # 比对时忽略时间戳，只比内容是否随库变化
        try:
            payload["generated_at"] = json.loads(read(OUT_JSON)).get("generated_at", payload["generated_at"])
        except json.JSONDecodeError:
            pass
    body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not os.path.exists(OUT_JSON) or read(OUT_JSON) != body:
            print("STALE: new拆文库/_index.json 需要重新生成（python3 scripts/newlib_index.py）")
            return 1
        print(f"OK: 索引最新（{len(recs)} 篇）")
        return 0
    for path, text in ((OUT_JSON, body), (OUT_MD, md_index(recs) + "\n"), (OUT_CARDS, md_cards(recs) + "\n")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"written {os.path.relpath(path, ROOT)}  ({len(text)} chars)")
    print("by_tier:", payload["by_tier"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
