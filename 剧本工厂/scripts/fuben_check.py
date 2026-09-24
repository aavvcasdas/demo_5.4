#!/usr/bin/env python3
"""念稿体检：只测可以测的东西，测不到的一律明说不给通过。

用法：
  python3 剧本工厂/scripts/fuben_check.py 剧本工厂/样片/001_年夜饭桌/剧本.md

契约（剧本.md 格式，见 templates/剧本.md）：
  --- YAML 头：目标时长 / 语速 ---
  ## B1 ｜0-6s｜钩子            ← beat 头：编号｜起止秒｜功能
  旁白：……                      ← 口播行，计入字数
  二姨：……                      ← 台词行，计入字数与台词占比
  镜头：…… / 音效：……          ← 制作提示，不计入口播字数

输出：
  同目录 体检.json（机器）+ 体检.md（人读）；退出码 0=PASS/WARN，2=BLOCK。
"""
from __future__ import annotations

import json
import hashlib
import re
import statistics
import sys
from pathlib import Path

CRAFT_PREFIX = ("镜头：", "镜头:", "音效：", "音效:", "画面：", "画面:", "场：", "场:", "字幕：", "字幕:")
BEAT_RE = re.compile(r"^##\s*(B\d+)\s*[｜|]\s*(\d+(?:\.\d+)?)\s*[-–~]\s*(\d+(?:\.\d+)?)\s*s?\s*[｜|]?\s*(.*)$")

AI_HARD = ["首先", "其次", "最后我们", "总而言之", "综上所述", "值得注意的是", "值得一提的是",
           "不禁", "仿佛", "宛如", "油然而生", "五味杂陈", "难以言喻", "心潮澎湃", "赋能",
           "抓手", "闭环", "在这个", "时代的浪潮", "值得注意的是", "让我们", "纵观"]
AI_SOFT = ["其实", "或许", "也许", "某种程度上", "某种意义上", "事实上", "不得不说", "可以说"]
TIME_WORD = ("那天", "这天", "当晚", "第二天", "后来", "从此", "直到", "几年后", "一年后", "两年后",
             "三年后", "五年后", "十年后", "几个月后", "半个月后", "一个月后", "上个月", "去年")
SPACE_WORD = "店 厅 馆 场 路 街 楼 门 桌 椅 窗 楼道 天台 地铁 车厢 院 校 厨房 客厅 阳台 电梯 站台 车 房 屋 摊 巷".split()
# 施压代理词（追问/对比/否定三类，只是代理指标；逐句人工复核仍是必要的）
CONFLICT_WORD = "凭什么 你敢 你怎么 还不 别人 人家 你看看 就你 丢人 出息 怎么不敢 轮不到 多少 还没 怎么 敢 都".split()
ACTION_VERB = "走 坐 站 放 拿 递 推 拉 端 夹 夹起 转 抬 低 收 塞 拎 掏 倒 挪 开 关 按 放 摸 抬 起 停 扶 站起 放下".split()


def load(path: Path):
    text = path.read_text(encoding="utf-8")
    head, *rest = text.split("---", 2)
    front = rest[0] if rest else ""
    body = rest[1] if len(rest) > 1 else head
    meta = {}
    for line in front.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text, body


def parse_beats(body: str):
    beats, cur = [], None
    for raw in body.splitlines():
        s = raw.rstrip()
        m = BEAT_RE.match(s.strip())
        if m:
            cur = {"id": m.group(1), "start": float(m.group(2)), "end": float(m.group(3)),
                   "func": m.group(4).strip(), "lines": []}
            beats.append(cur)
            continue
        if not s.strip() or cur is None:
            continue
        cur["lines"].append(s.strip())
    return beats


def is_craft(line: str) -> bool:
    return line.startswith(CRAFT_PREFIX) or line.startswith("【")


def speak_chars(line: str) -> int:
    s = re.sub(r"^(旁白|[^：:]{1,6})[：:]", "", line)  # 去掉说话人前缀
    return len(re.sub(r"[\s，。！？、；：…—""''（）()《》【】]", "", s))


def num(s: str) -> float:
    return float(re.sub(r"[^\d.]", "", s) or 0)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = Path(sys.argv[1])
    meta, raw_text, body = load(path)
    target = num(meta.get("目标时长", "0"))
    cps = num(meta.get("语速", "4.2")) or 4.2
    beats = parse_beats(body)
    if not beats:
        print("BLOCK：没有解析到 beat 头（## B1 ｜0-6s｜钩子）")
        return 2

    findings, warn, block = [], 0, 0

    def add(level, code, msg):
        nonlocal warn, block
        findings.append({"level": level, "code": code, "msg": msg})
        if level == "BLOCK":
            block += 1
        elif level == "WARN":
            warn += 1

    spoken_lines = [l for b in beats for l in b["lines"] if not is_craft(l)]
    dialogue_lines = [l for l in spoken_lines if re.match(r"^(?!旁白)[^：:]{1,6}[：:]", l)]
    total_chars = sum(speak_chars(l) for l in spoken_lines)
    est = total_chars / cps
    declared = sum(b["end"] - b["start"] for b in beats)
    all_chars = [len(re.sub(r"[\s，。！？、；：…—""''（）()]", "", l)) for l in spoken_lines]
    dialogue_chars = sum(speak_chars(l) for l in dialogue_lines)

    # 1 时长
    if target:
        off = abs(est - target) / target
        if off > 0.20:
            add("BLOCK", "DURATION", f"口播 {total_chars} 字 ÷ {cps} 字/秒 ≈ {est:.0f}s，与目标 {target:.0f}s 差 {off*100:.0f}%（>20%）")
        elif off > 0.10:
            add("WARN", "DURATION", f"估算 {est:.0f}s vs 目标 {target:.0f}s，差 {off*100:.0f}%")
        else:
            add("PASS", "DURATION", f"口播 {total_chars} 字 ≈ {est:.0f}s（目标 {target:.0f}s，{off*100:.0f}% 内）")
        if abs(declared - target) / target > 0.15:
            add("WARN", "BEAT_SUM", f"beat 窗口合计 {declared:.0f}s 与目标 {target:.0f}s 不一致")
    else:
        add("WARN", "DURATION", "未声明目标时长：时长契约缺失")

    # 2 首钩子窗口
    b1 = beats[0]
    if b1["end"] - b1["start"] > 6:
        add("BLOCK", "HOOK_WINDOW", f"{b1['id']} 钩子窗口 {b1['end']-b1['start']:.0f}s > 6s")
    else:
        add("PASS", "HOOK_WINDOW", f"{b1['id']} 钩子 {b1['end']-b1['start']:.0f}s 内开口")
    hook_text = "".join(b1["lines"])
    if not re.search(r"\d|问|说|走|放|拿|停|站|坐|递|掏|夹", hook_text):
        add("WARN", "HOOK_CONCRETE", "首钩子里没有具体的人/动作/数字，只有概念")

    # 3 每个 beat 不超过 22s（15s 一钩的宽松上限）
    for b in beats:
        span = b["end"] - b["start"]
        if span > 22:
            add("WARN", "BEAT_LEN", f"{b['id']} 窗口 {span:.0f}s > 22s，中间没有新钩子")

    # 4 台词占比
    if total_chars:
        ratio = dialogue_chars / total_chars
        if ratio < 0.25:
            add("BLOCK", "DIALOGUE", f"台词占口播 {ratio*100:.0f}%（<25%）：没有对话就没有戏")
        elif ratio < 0.35:
            add("WARN", "DIALOGUE", f"台词占口播 {ratio*100:.0f}%（<35%）")
        else:
            add("PASS", "DIALOGUE", f"台词占口播 {ratio*100:.0f}%")

    # 5 行长（念得动）
    if all_chars:
        med = statistics.median(all_chars)
        p90 = sorted(all_chars)[min(len(all_chars) - 1, int(len(all_chars) * 0.9))]
        long_lines = [l for l, c in zip(spoken_lines, all_chars) if c > 22]
        if med > 14:
            add("WARN", "LINE_LEN", f"行长中位数 {med:.0f} 字 > 14：断句没有按换气切")
        else:
            add("PASS", "LINE_LEN", f"行长中位 {med:.0f} 字 / P90 {p90} 字")
        if len(long_lines) > len(spoken_lines) * 0.12:
            add("WARN", "LONG_LINES", f"{len(long_lines)} 行 > 22 字（念稿会赶拍）")

    # 6 空间与场景
    full = "".join(spoken_lines)
    spaces = {w for w in SPACE_WORD if w in full}
    if len(spaces) < 2:
        add("WARN", "SPACE", f"空间词只有 {len(spaces)} 个：口播剧至少要有一个空间变化")

    # 7 时间标签裸句
    bare_time = [l for l in spoken_lines
                 if any(w in l for w in TIME_WORD) and len(l) < 14
                 and not any(v in l for v in ACTION_VERB)]
    if bare_time:
        add("WARN", "BARE_TIME", f"{len(bare_time)} 行是「时间+一句话」的日历句，例：{bare_time[0][:16]}")

    # 8 AI 腔
    hard = [w for w in AI_HARD if w in full]
    soft = [w for w in AI_SOFT if w in full]
    if hard:
        add("BLOCK", "AI_TONE", f"硬禁词命中：{'、'.join(sorted(set(hard))[:6])}")
    elif len(soft) > 2:
        add("WARN", "AI_TONE", f"软化词偏多：{'、'.join(sorted(set(soft)))}")
    else:
        add("PASS", "AI_TONE", "无硬禁词、软化词 ≤2")

    # 9 问答与施压（加价）
    questions = len(re.findall(r"[？?]|吗|呢", "".join(dialogue_lines)))
    pressures = sum(1 for l in dialogue_lines
                    if any(w in l for w in CONFLICT_WORD) or re.search(r"[？?]|呢$|呢[\s，。]?", l))
    if pressures < 2:
        add("WARN", "PRESSURE", f"对手施压句只有 {pressures} 处：加价不够，反击就没有重量")
    else:
        add("PASS", "PRESSURE", f"施压句 {pressures} 处 / 疑问 {questions} 处")

    # 10 数字裸句
    bare_num = [l for l in spoken_lines
                if re.search(r"\d", l) and not any(v in l for v in ACTION_VERB)
                and not re.match(r"^[^：:]{1,6}[：:]", l) and len(l) < 20]
    if len(bare_num) > 1:
        add("WARN", "BARE_NUMBER", f"{len(bare_num)} 行数字没有绑定动作，例：{bare_num[0][:16]}")

    # 能量曲线（每 beat 强度，供导演板用）
    curve = []
    for b in beats:
        txt = "".join(b["lines"])
        dlg = sum(1 for l in b["lines"] if l in dialogue_lines)
        strength = dlg * 2 + len(re.findall(r"[？?]", txt)) + sum(txt.count(w) for w in CONFLICT_WORD)
        curve.append({"beat": b["id"], "score": strength})

    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    status = "BLOCK" if block else ("WARN" if warn else "PASS")
    result = {
        "status": status,
        "script_path": str(path),
        "script_sha256": digest,
        "metrics": {
            "spoken_chars": total_chars,
            "dialogue_ratio": round(dialogue_chars / total_chars, 3) if total_chars else 0,
            "est_seconds": round(est, 1),
            "target_seconds": target or None,
            "beats": len(beats),
            "median_line_chars": statistics.median(all_chars) if all_chars else 0,
            "spaces": sorted(spaces),
            "pressure_marks": pressures,
        },
        "energy_curve": curve,
        "findings": findings,
        "unmeasured": [
            "好看度（只有用户/观众能判）",
            "事实真实性与合规",
            "表演、镜头与后期可行性",
            "实际配音时长（需念一遍或用 TTS 实测）",
            "术语是否被观众听懂（无法机器判定）",
        ],
        "note": "体检不等于批准：BLOCK 必须修；PASS 只说明可测项没问题是，不代表稿子好看。",
    }
    out_json = path.with_name("体检.json")
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# 念稿体检 · {meta.get('标题', path.stem)}", "",
             f"**结论：{status}** ｜口播 {total_chars} 字 ≈ {est:.0f}s ｜台词占比 {result['metrics']['dialogue_ratio']*100:.0f}% ｜{len(beats)} beats",
             f"｜正文 sha256 `{digest[:12]}…`", "", "| 等级 | 项目 | 结论 |", "|---|---|---|"]
    for f in findings:
        lines.append(f"| {f['level']} | {f['code']} | {f['msg']} |")
    lines += ["", "## 能量曲线（每 beat 施压强度，供导演板参考）", ""]
    mx = max((c["score"] for c in curve), default=1) or 1
    for c in curve:
        lines.append(f"- {c['beat']} {'█' * max(1, round(c['score'] / mx * 20))} {c['score']}")
    lines += ["", "## 不测的项（不因缺测而算通过）", ""] + [f"- {u}" for u in result["unmeasured"]]
    lines += ["", "> BLOCK 必须修；WARN 逐条判断；PASS 只代表可测项没问题。"]
    path.with_name("体检.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"{status}: {path} ｜口播 {total_chars} 字 ≈ {est:.0f}s ｜台词 {result['metrics']['dialogue_ratio']*100:.0f}% ｜BLOCK {block} / WARN {warn}")
    for f in findings:
        if f["level"] in ("BLOCK", "WARN"):
            print(f"  {f['level']:5s} {f['code']:12s} {f['msg']}")
    return 2 if block else 0


if __name__ == "__main__":
    raise SystemExit(main())
