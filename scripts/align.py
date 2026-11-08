"""把 episode.json 里的时间戳对准到字幕中最匹配的那一句。

用法: python3 align.py episode.json subtitles.srt
原理: 对每个要点，用它的标题和内容在原时间附近（前后约 90 秒）的字幕里找
      用词重合度最高的位置（罕见的词权重更高），把时间戳改成那句字幕开始的时间。
      金句在更大范围内逐句匹配。正文里引用的 {{H:MM:SS}} 跟着一起更新。
"""
import json, re, sys, math, collections

ep_path, srt_path = sys.argv[1:3]
ep = json.load(open(ep_path, encoding="utf-8"))

def secs(t):
    p = [int(x) for x in t.split(":")]
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]

def fmt(s):
    s = max(0, int(s))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"

# ---- subtitles ----
cues = []
for block in open(srt_path, encoding="utf-8").read().strip().split("\n\n"):
    lines = block.strip().split("\n")
    if len(lines) < 3 or "-->" not in lines[1]:
        continue
    h, m, s = lines[1][:8].split(":")
    cues.append((int(h) * 3600 + int(m) * 60 + int(s), " ".join(lines[2:])))

def grams(text):
    text = re.sub(r"<[^>]+>|\{\{[^}]*\}\}", "", text)
    han = re.findall(r"[\u4e00-\u9fff]+", text)
    out = set()
    for run in han:
        out.update(run[i:i + 2] for i in range(len(run) - 1))
    out.update(w.lower() for w in re.findall(r"[A-Za-z]{3,}", text))
    return out

cue_grams = [grams(c[1]) for c in cues]
df = collections.Counter(g for gs in cue_grams for g in gs)
N = len(cues)
idf = lambda g: math.log((N + 1) / (df.get(g, 0) + 1))

def best(keys, lo, hi, span=4):
    """返回 [lo, hi] 内匹配得分最高的字幕起点（秒）及得分。"""
    keys = {g for g in keys if g in df}
    if not keys:
        return None, 0
    scored = []
    for i, (t, _) in enumerate(cues):
        if t < lo or t > hi:
            continue
        window = set().union(*cue_grams[i:i + span])
        scored.append((t, sum(idf(g) for g in keys & window)))
    if not scored:
        return None, 0
    peak_t, top = max(scored, key=lambda x: x[1])
    # 话题开始的地方：最密集处之前 60 秒内，第一个得分达到峰值 55% 的句子
    for t, sc in scored:
        if peak_t - 50 <= t <= peak_t and sc >= 0.5 * top:
            return t, top
    return peak_t, top

mapping, report = {}, []
for ch in ep["chapters"]:
    prev = None
    for b in ch["beats"]:
        old = secs(b["t"])
        anchor = b.get("anchor")
        t, sc = None, 0
        if b.get("t_exact"):
            t, sc = secs(b["t_exact"]) + 1, 999  # 人工核对过的时间（下面会统一减 1 秒）
        elif anchor:
            # 锚点句：写总结时从字幕里抄下的话题开头原句，直接精确查找
            a = re.sub(r"\s", "", anchor)
            for ct, text in cues:
                if abs(ct - old) <= 600 and a[:12] in re.sub(r"\s", "", text + "".join(x[1] for x in cues if 0 < x[0] - ct <= 6)):
                    t, sc = ct, 999
                    break
        if t is None:
            keys = grams(b["title"] + " " + " ".join(b["points"]))
            t, sc = best(keys, old - 25, old + 60)
        if (old < 30 and sc != 999) or t is None or sc < 6:
            t = old  # 片头和匹配不到的保持原样
        t = max(0, t - 1)  # 留 1 秒余量，跳过去刚好听到开头
        if prev is not None and t <= prev and sc != 999:
            t = max(old, prev + 5)
        mapping[b["t"]] = fmt(t)
        report.append((b["t"], fmt(t), round(sc, 1), b["title"]))
        b["t"] = fmt(t)
        prev = t
    ch["start"] = ch["beats"][0]["t"]
for i, ch in enumerate(ep["chapters"]):
    if i + 1 < len(ep["chapters"]):
        ch["end"] = ep["chapters"][i + 1]["start"]

# 金句：按原句在更大范围里找
for q in ep.get("quotes", []):
    old = secs(q["t"])
    t, sc = best(grams(q["q"]), old - 240, old + 240, span=2)
    if t is not None and sc >= 6:
        mapping.setdefault(q["t"], fmt(t - 1))
        q["t"] = fmt(t - 1)

def remap(t):
    if t in mapping:
        return mapping[t]
    # 不在映射里的时间（比如章节或片段起点），用最近的要点映射平移
    s = secs(t)
    near = min(mapping, key=lambda k: abs(secs(k) - s))
    if abs(secs(near) - s) <= 5:
        return mapping[near]
    return t

def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "t" and isinstance(v, str) and re.fullmatch(r"\d+:\d\d:\d\d", v):
                o[k] = remap(v)
            elif k in ("start", "end") and isinstance(v, str) and re.fullmatch(r"\d+:\d\d:\d\d", v) and "beats" not in o:
                o[k] = remap(v)
            elif k == "times":
                o[k] = [remap(x) for x in v]
            else:
                o[k] = walk(v)
        return o
    if isinstance(o, list):
        return [walk(x) for x in o]
    if isinstance(o, str):
        return re.sub(r"\{\{(\d+:\d\d:\d\d)\}\}", lambda m: "{{" + remap(m.group(1)) + "}}", o)
    return o

ep = walk(ep)
ep["aligned"] = True
json.dump(ep, open(ep_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

moved = [r for r in report if r[0] != r[1]]
print(f"要点 {len(report)} 个，调整 {len(moved)} 个；平均偏移 {sum(abs(secs(a)-secs(b)) for a,b,*_ in report)/len(report):.0f} 秒")
for a, b, sc, title in report[:: max(1, len(report) // 15)]:
    print(f"  {a} → {b}  得分{sc:>5}  {title}")
