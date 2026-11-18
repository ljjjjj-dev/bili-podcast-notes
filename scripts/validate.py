"""构建前校验 episode.json 的结构、时间单调性、锚点句与覆盖密度。

用法: python3 validate.py <剧集文件夹>
"""
import sys, os, re, json

if len(sys.argv) < 2:
    sys.exit("用法: python3 validate.py <剧集文件夹>")

ep_dir = sys.argv[1]
ep_path = os.path.join(ep_dir, "episode.json")
if not os.path.isfile(ep_path):
    sys.exit(f"找不到 {ep_path}")

ep = json.load(open(ep_path, encoding="utf-8"))
errors, warns = [], []

def secs(t):
    p = [int(x) for x in t.split(":")]
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]

for k in ("bv", "url", "title", "short_title", "duration", "published", "source", "chapters", "core"):
    if not ep.get(k):
        errors.append(f"缺少必填字段: {k}")

total = secs(ep["duration"]) if ep.get("duration") else 0
beat_times = []
no_anchor = 0
for ci, ch in enumerate(ep.get("chapters", []), 1):
    if not ch.get("title") or not ch.get("beats"):
        errors.append(f"第 {ci} 章缺少 title 或 beats")
        continue
    for bi, b in enumerate(ch["beats"], 1):
        t = b.get("t", "")
        if not re.fullmatch(r"\d+:\d\d:\d\d", t):
            errors.append(f"第 {ci} 章第 {bi} 段时间戳格式错误: {t!r}")
        else:
            s = secs(t)
            if total and s > total:
                errors.append(f"第 {ci} 章第 {bi} 段超出视频总时长: {t}")
            if beat_times and s < beat_times[-1][0]:
                warns.append(f"第 {ci} 章第 {bi} 段时间倒退: {t} < {beat_times[-1][1]}")
            beat_times.append((s, t))
        anc = (b.get("anchor") or "").strip()
        if not anc and not b.get("t_exact"):
            no_anchor += 1
        elif anc and len(anc) < 10:
            warns.append(f"第 {ci} 章第 {bi} 段 ({t}) anchor 过短（{len(anc)} 字）")

max_gap = 0
if total and beat_times:
    pts = [0] + [s for s, _ in beat_times] + [total]
    gaps = [pts[i + 1] - pts[i] for i in range(len(pts) - 1)]
    max_gap = max(gaps)
    if max_gap > 900:
        warns.append(f"存在超过 15 分钟的空窗期（最大间隔 {max_gap // 60} 分钟），检查是否漏读段落")

def scan_refs(obj):
    if isinstance(obj, str):
        for m in re.finditer(r"\{\{([^}]+)\}\}", obj):
            if not re.fullmatch(r"\d+:\d\d:\d\d", m.group(1)):
                errors.append(f"非法时间引用 {{{{{m.group(1)}}}}}")
            elif total and secs(m.group(1)) > total:
                errors.append(f"时间引用超出视频时长 {{{{{m.group(1)}}}}}")
    elif isinstance(obj, list):
        for x in obj:
            scan_refs(x)
    elif isinstance(obj, dict):
        for v in obj.values():
            scan_refs(v)

scan_refs(ep)

for w in warns:
    print("警告:", w)
for err in errors:
    print("错误:", err)

if errors:
    sys.exit(1)

print(f"校验通过：{len(ep.get('chapters', []))} 章 {len(beat_times)} 段 · 最大间隔 {max_gap // 60} 分 {max_gap % 60} 秒" +
      (f" · {no_anchor} 段无 anchor" if no_anchor else "") +
      (f" · {len(warns)} 条警告" if warns else ""))
