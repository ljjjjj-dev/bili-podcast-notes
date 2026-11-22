"""从 local/channels.json 订阅的 B站 UP 主拉取最新长视频候选清单（排除已做/已推的 BV 号）。

用法: python3 discover.py [--per-channel 5] [--min-mins 20]
"""
import sys, os, re, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
PY = os.path.join(TOOLS, "python", "bin", "python")
ENV = {**os.environ, "PATH": os.path.join(TOOLS, "bin") + os.pathsep + os.environ.get("PATH", "")}

cfg = json.load(open(os.path.join(ROOT, "local", "settings.json"), encoding="utf-8"))
OUT = cfg["output_dir"]
BROWSER = cfg.get("browser", "edge")
ch_path = os.path.join(ROOT, "local", "channels.json")
if not os.path.isfile(ch_path):
    sys.exit(f"找不到订阅清单 {ch_path}，请从 config/channels.example.json 复制一份。")
channels = json.load(open(ch_path, encoding="utf-8"))

per_ch = 5
min_mins = 20
for i, a in enumerate(sys.argv[1:]):
    if a == "--per-channel" and i + 2 < len(sys.argv):
        per_ch = int(sys.argv[i + 2])
    elif a == "--min-mins" and i + 2 < len(sys.argv):
        min_mins = int(sys.argv[i + 2])

# 只排除用户已经点过并完成精读（存在 episode.json）的 BV 号
seen = set()
if os.path.isdir(OUT):
    for name in os.listdir(OUT):
        ep_f = os.path.join(OUT, name, "episode.json")
        if os.path.isfile(ep_f):
            try:
                bv = json.load(open(ep_f, encoding="utf-8")).get("bv")
                if bv:
                    seen.add(bv)
            except Exception:
                pass

bvs = []
bv_meta = {}
for ch in channels:
    uid = str(ch["uid"]).strip()
    url = f"https://space.bilibili.com/{uid}/video"
    r = subprocess.run(
        [PY, "-m", "yt_dlp", "--cookies-from-browser", BROWSER, "--flat-playlist",
         "--playlist-end", str(per_ch), "--no-warnings", "--print", "%(id)s", url],
        capture_output=True, text=True, env=ENV,
    )
    for line in (r.stdout or "").splitlines():
        bv = line.strip().split("_")[0]
        if bv.startswith("BV") and bv not in seen and bv not in bv_meta:
            bvs.append(bv)
            bv_meta[bv] = {"channel": ch.get("name", uid), "category": ch.get("category", "AI/哲学")}

results = []
if bvs:
    urls = [f"https://www.bilibili.com/video/{bv}" for bv in bvs]
    r = subprocess.run(
        [PY, "-m", "yt_dlp", "--cookies-from-browser", BROWSER, "--skip-download", "--no-warnings",
         "--print", "%(id)s\t%(upload_date)s\t%(duration)s\t%(duration_string)s\t%(uploader)s\t%(title)s", *urls],
        capture_output=True, text=True, env=ENV,
    )
    for line in (r.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        bv, udate, dur_s, dur_str, uploader, title = parts[0].split("_")[0], parts[1], parts[2], parts[3], parts[4], "\t".join(parts[5:])
        try:
            dur_val = float(dur_s)
        except Exception:
            dur_val = 0
        if dur_val < min_mins * 60:
            continue
        date = f"{udate[:4]}-{udate[4:6]}-{udate[6:]}" if len(udate) == 8 else udate
        info = bv_meta.get(bv, {})
        results.append({
            "bv": bv,
            "url": f"https://www.bilibili.com/video/{bv}",
            "date": date,
            "duration": dur_str,
            "uploader": uploader or info.get("channel", ""),
            "category": info.get("category", ""),
            "title": title,
        })

results.sort(key=lambda x: x["date"], reverse=True)
print(json.dumps(results, ensure_ascii=False, indent=1))
