"""第一步：根据B站链接取视频信息和字幕，没有字幕就下载音频在本地转写。

用法: python3 fetch.py "<链接 / BV号 / av号 / App 分享文字>" [--whisper]
     --whisper  不用B站字幕，强制用本地 Whisper 重新转写（更准，但要多等几分钟）

结果: 在输出文件夹里建 "<发布日期> <标题前 20 字>/"，里面有
      info.json      视频信息
      subtitles.srt  字幕（每句带时间）
      transcript.txt 给 Claude 读的文字稿：每 30 秒一段，段首是时间
"""
import sys, os, re, json, subprocess, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SETTINGS = os.path.join(ROOT, "config", "settings.json")
if not os.path.exists(SETTINGS):
    sys.exit("缺少 config/settings.json：请复制 config/settings.example.json 为 settings.json 并填好输出文件夹和浏览器。")
CFG = json.load(open(SETTINGS, encoding="utf-8"))
OUT = os.environ.get("PODCAST_OUT") or CFG["output_dir"]  # 测试时可用环境变量换输出位置
BROWSER = CFG.get("browser", "chrome")  # 从这个浏览器读取B站登录信息
COOKIES = ["--cookies-from-browser", BROWSER]
# 所有工具都在本文件夹的 tools/ 里：Python 环境（含 yt-dlp、mlx-whisper）、ffmpeg、语音模型
TOOLS = os.path.join(ROOT, "tools")
PY = os.path.join(TOOLS, "python", "bin", "python")
ENV = dict(os.environ,
           PATH=os.path.join(TOOLS, "bin") + os.pathsep + os.environ.get("PATH", ""),
           HF_HOME=os.path.join(TOOLS, "models", "huggingface"),
           HF_HUB_OFFLINE="1")
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

args = [a for a in sys.argv[1:] if not a.startswith("--")]
force_whisper = "--whisper" in sys.argv
if not args:
    sys.exit(__doc__)
raw = " ".join(args)

# ---- 解析链接 ----
m = re.search(r"https?://(?:www\.|m\.)?(?:bilibili\.com/video/[^\s]+|b23\.tv/[^\s]+)", raw)
if m:
    url = m.group(0).rstrip("，。)）】")
elif re.search(r"\bBV[0-9A-Za-z]{10}\b", raw):
    url = "https://www.bilibili.com/video/" + re.search(r"BV[0-9A-Za-z]{10}", raw).group(0)
elif re.search(r"\bav\d+\b", raw, re.I):
    url = "https://www.bilibili.com/video/" + re.search(r"av\d+", raw, re.I).group(0)
else:
    sys.exit("没认出链接，请发B站视频网址、BV号、av号或 App 分享文字。")

def ytdlp(*a, capture=True):
    r = subprocess.run([PY, "-m", "yt_dlp", *COOKIES, "--no-warnings", "--ffmpeg-location", os.path.join(TOOLS, "bin"), *a, url],
                       capture_output=capture, text=True, env=ENV)
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()[-1:] or ["未知错误"]
        if "412" in err[0]:
            sys.exit(f"B站拒绝了请求（412）。请确认 {BROWSER} 浏览器里已经登录B站，再试一次。")
        sys.exit("yt-dlp 出错：" + err[0])
    return r.stdout

# 注意：B站只有在要求写字幕时才会列出字幕，所以这里要带 --write-subs
info = json.loads(ytdlp("-J", "--no-playlist", "--write-subs", "--sub-langs", "all"))
title = info.get("title", "")
date = info.get("upload_date") or ""
date = f"{date[:4]}-{date[4:6]}-{date[6:]}" if len(date) == 8 else "未知日期"
bv = info.get("id", "").split("_")[0]
short = re.sub(r'[\\/:*?"<>|]', "", re.split(r"[：:|｜！!？?]", title)[0])[:20].strip() or bv
ep_dir = os.path.join(OUT, f"{date} {short}")
os.makedirs(ep_dir, exist_ok=True)

subs = info.get("subtitles") or {}
langs = [k for k in subs if k != "danmaku"]
human = [k for k in langs if not k.startswith("ai-") and k.startswith("zh")]
ai = [k for k in langs if k.startswith("ai-zh")]
meta = {
    "bv": bv, "url": "https://www.bilibili.com/video/" + bv + (f"?p={info['playlist_index']}" if info.get("playlist_index") and info.get("n_entries", 1) > 1 else ""),
    "title": title, "uploader": info.get("uploader"), "duration": info.get("duration_string"),
    "duration_seconds": info.get("duration"), "published": date, "description": (info.get("description") or "")[:1500],
    "chapters": [{"start": int(c["start_time"]), "title": c["title"]} for c in (info.get("chapters") or [])],
    "subtitle_langs": langs,
}

srt_path = os.path.join(ep_dir, "subtitles.srt")
source = None
if not force_whisper and (human or ai):
    lang = (human or ai)[0]
    tmp = tempfile.mkdtemp()
    ytdlp("--skip-download", "--write-subs", "--sub-langs", lang, "--no-playlist", "-o", os.path.join(tmp, "s.%(ext)s"))
    got = [f for f in os.listdir(tmp) if f.endswith(".srt")]
    if got:
        shutil.move(os.path.join(tmp, got[0]), srt_path)
        source = "UP主上传的字幕" if lang in human else "B站 AI 字幕"
    shutil.rmtree(tmp, ignore_errors=True)

if source is None:
    why = "按要求用本地 Whisper 转写" if force_whisper else "没有可用字幕"
    print(f"{why}，下载音频并在本地转写（1 小时音频大约要几分钟到十几分钟）…", flush=True)
    tmp = tempfile.mkdtemp()
    ytdlp("-f", "bestaudio", "-x", "--audio-format", "m4a", "--no-playlist", "-o", os.path.join(tmp, "a.%(ext)s"))
    audio = os.path.join(tmp, "a.m4a")
    code = f"""
import mlx_whisper, sys
r = mlx_whisper.transcribe({audio!r}, path_or_hf_repo={WHISPER_MODEL!r}, language='zh', initial_prompt='以下是普通话的句子，包含一些英文专业术语。')
def f(t):
    h=int(t//3600); m=int(t%3600//60); s=t%60
    return f"{{h:02d}}:{{m:02d}}:{{s:06.3f}}".replace('.', ',')
out=[]
for i, seg in enumerate(r['segments'], 1):
    out.append(f"{{i}}\\n{{f(seg['start'])}} --> {{f(seg['end'])}}\\n{{seg['text'].strip()}}\\n")
open({srt_path!r}, 'w', encoding='utf-8').write('\\n'.join(out))
"""
    r = subprocess.run([PY, "-c", code], env=ENV)
    shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        sys.exit("转写失败，请检查 tools/python 里的 mlx-whisper。")
    source = "本地 Whisper 转写"

meta["source"] = source
json.dump(meta, open(os.path.join(ep_dir, "info.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- 给 Claude 读的文字稿：每 30 秒一段 ----
cues = []
for block in open(srt_path, encoding="utf-8").read().strip().split("\n\n"):
    lines = block.strip().split("\n")
    if len(lines) >= 3 and "-->" in lines[1]:
        h, mi, s = lines[1][:8].split(":")
        cues.append((int(h) * 3600 + int(mi) * 60 + int(s), " ".join(lines[2:]).strip()))
fmt = lambda t: f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"
out, cur, buf = [], None, []
for t, text in cues:
    if cur is None or t - cur >= 30:
        if buf:
            out.append(f"[{fmt(cur)}] " + "，".join(buf))
        cur, buf = t, []
    buf.append(text)
if buf:
    out.append(f"[{fmt(cur)}] " + "，".join(buf))
open(os.path.join(ep_dir, "transcript.txt"), "w", encoding="utf-8").write("\n".join(out))

print(json.dumps({"folder": ep_dir, "title": title, "duration": meta["duration"], "source": source,
                  "chars": sum(len(x) for x in out), "chapters_from_uploader": len(meta["chapters"])}, ensure_ascii=False, indent=1))
