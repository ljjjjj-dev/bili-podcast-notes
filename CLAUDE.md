# B站播客总结流程

用户发来一个B站链接（网址、BV号、av号或 App 分享文字都行），就按下面的流程生成一期笔记：一个发布成 Artifact 的网页版，和一个可以粘贴进 OneNote 的版本。

**开始前先读 `config/profile.md`**，里面是用户的阅读习惯、英文水平和关心的方向。“和你有关”一节按里面列的方向写。没有这个文件就按 `config/profile.example.md` 的默认情况来，并提醒用户可以复制一份改成自己的。

## 位置

- 本文件夹：`scripts/` 放脚本，`tools/` 放所有工具（由 `setup.sh` 安装，不进 git），`config/` 放设置。
- `config/settings.json`（个人设置，不进 git；模板是 `settings.example.json`）：
  - `output_dir`：笔记输出文件夹，每期一个子文件夹 `<发布日期> <短标题>/`，根目录有 `首页.html`。
  - `home_url`：知识库首页 Artifact 的链接。为空表示还没发布过首页：第一次发布首页后把链接写进来，以后都用这个 url 更新，不要新建。
  - `browser`：从哪个浏览器读取B站登录信息（`edge`、`chrome`、`safari`、`firefox` 等）。
- `config/known_terms.txt`（不进 git）：用户已认识、不用再注释的英文词，每行一个。
- 本文件夹是公开的 git 仓库（github.com/ljjjjj-dev/bili-podcast-notes）。个人信息（路径、链接、关注方向、已认识的词）只能放在被 `.gitignore` 排除的文件里，不要写进会提交的文件。提交和推送要先经过用户同意。
- `使用说明.html`（不进 git）是写给用户本人看的说明书；`README.md` 是公开的说明。流程、功能或文件位置有改动时，两份都要同步更新。

## 环境

所有工具都在本文件夹的 `tools/` 里（约 2.8 GB），由 `./setup.sh` 一次装好，不依赖 Homebrew，也不依赖系统里的 Python，整个文件夹挪到别处也能用。如果 `tools/python/bin/python` 不存在，先让用户运行 `./setup.sh`（或在用户同意后替他运行）。
- `tools/python/`：独立版 Python 3.13.18（来自 astral-sh/python-build-standalone 的 `cpython-3.13.18+20261026-aarch64-apple-darwin-install_only`，已用官方 SHA256 校验过），yt-dlp、mlx-whisper、imageio-ffmpeg 直接装在它的 site-packages 里，没有另建 venv。
- `tools/bin/ffmpeg`：指向 imageio-ffmpeg 自带 ffmpeg 的相对路径快捷方式。
- `tools/models/huggingface/`：Whisper 模型 `mlx-community/whisper-large-v3-turbo`（`fetch.py` 运行时把 `HF_HOME` 设到这里，离线使用）。
- 更新 yt-dlp（B站改版、取不到字幕时）：`tools/python/bin/python -m pip install -U yt-dlp`。

B站不登录会返回 412，所以 `fetch.py` 用 `--cookies-from-browser <settings.json 里的 browser>` 读取用户浏览器里的B站登录信息。**不要伪装请求头去绕过 412**，会被安全规则拦下；如果还是 412，就让用户在那个浏览器里重新登录B站。

所有脚本都用 `tools/python/bin/python scripts/xxx.py` 运行（下文写成 `python3 scripts/...` 的地方也这样运行）。

## 步骤

1. **取字幕**：`python3 scripts/fetch.py "<链接>"`。有 UP主字幕先用 UP主字幕，其次用 B站 AI 字幕，都没有就下载音频本地转写。如果是很重要的一期，或者 AI 字幕错得太多，加 `--whisper` 重新转写。输出 `info.json`、`subtitles.srt`、`transcript.txt`。
2. **通读全文**：把 `transcript.txt` 从头到尾读完（每 30 秒一段，段首是时间），一段都不要跳。人名、公司名、英文术语经常被识别错（比如把 Claude 识别成"cloud"、Gemini 识别成"詹姆乃"），要根据上下文更正。如果 `info.json` 里有 UP主自己分的章节，时间线按它的结构来。
3. **写 `episode.json`**：格式见下文。每个时间线要点都要写 `anchor`，内容是从 transcript.txt **原样抄下来**的、这个话题开头那句话（通常是主持人的提问），至少 12 个字，有错别字也照抄。对齐脚本会按这句话把时间戳精确对准到那一秒。
4. **事实核查**：挑出 8–15 条嘉宾说的、可以公开核实的事实（收购、人事变动、发布时间、数据、别人说过的话），用 WebSearch 核实，写进 `factchecks`，并附上来源链接。嘉宾自己的观点、预测、内部信息不需要核查；内部信息标为 `unverified`。
5. **对齐时间戳**：`python3 scripts/align.py <剧集文件夹>/episode.json <剧集文件夹>/subtitles.srt`。然后抽查几处：用 `subtitles.srt` 看要点时间附近的原文，确认对得上；对不上的写 `t_exact` 手动指定时间，再跑一次。
6. **生成两个版本**：`python3 scripts/build.py <剧集文件夹>`，生成 `网页版.html` 和 `OneNote版.html`。
7. **发布网页版**：用 Artifact 工具发布 `网页版.html`（新的一期不传 url，icon 用 `notes`）。把返回的链接写进 episode.json 的 `artifact_url`，同时写上 `summarized`（今天的日期），再跑一次 build.py。
8. **更新首页**：`python3 scripts/home.py`（默认用 settings.json 里的 output_dir），然后用 `home_url` 发布 `首页.html`；`home_url` 为空时新建（icon 用 `podcast`），并把链接写回 settings.json。
9. **放进剪贴板**：`python3 scripts/clip.py <剧集文件夹>`，告诉用户在 OneNote 新页面里按 Cmd+V。
10. **回复用户**：给出网页版链接和首页链接，用几句话说明这期讲了什么，以及事实核查里有没有值得注意的地方。

如果用户发来一串"已认识"的英文词（网页英文对照表里的"复制已认识的词"按钮生成的），就把这些词追加到 `config/known_terms.txt`，每行一个。以后的笔记不再给这些词加中文注释。

## episode.json 格式

正文字段里可以用 `<b>`、`<i>`；用 `{{H:MM:SS}}` 引用视频里的时间，生成页面时会变成可点击的时间戳。时间统一写成 `H:MM:SS`。

```json
{
 "bv": "BV...", "url": "https://www.bilibili.com/video/BV...",
 "show": "节目或UP主", "title": "视频原标题", "short_title": "页面标题，2-4 个词",
 "guest": "嘉宾", "duration": "3:48:00", "published": "2026-05-11", "source": "B站 AI 字幕",
 "guest_html": "嘉宾一句话背景，容易混淆的人要说明",
 "tags": ["AI", "..."],
 "themes": [{"q": "问题", "a": "嘉宾的回答", "t": "0:05:33"}],
 "skim": [{"level": "必看|推荐|选看|可跳过", "start": "0:05:33", "end": "0:50:04 或 null", "desc": "看点"}],
 "chapters": [{"title": "一、章节名", "start": "0:00:09", "end": "0:05:33",
   "beats": [{"t": "0:01:28", "anchor": "从字幕原样抄的开头句", "title": "小标题", "points": ["要点", "要点"]}]}],
 "core": {"conclusion": "", "arguments": [{"claim": "", "why": "", "t": ""}],
   "logic": [["维度", "评估"]], "stance": [["立场", "说明"]], "advice": ""},
 "factchecks": [{"claim": "嘉宾的说法", "t": "", "status": "confirmed|partial|disputed|unverified",
   "note": "核查结果", "sources": [{"title": "", "url": ""}]}],
 "personal": [{"area": "投资与市场", "note": "不构成投资建议", "points": []},
   {"area": "AI 与科技趋势", "points": []}, {"area": "职业与个人成长", "points": []}],
 "predictions": [{"claim": "嘉宾给出的可检验预测", "t": "", "due": "检验时间", "status": "pending|right|wrong|mixed"}],
 "extend": [{"k": "认知升级", "points": []}],
 "entities": [{"name": "公司或行业", "type": "公司|行业|产品", "attitude": "正面|中性|偏负面…",
   "lvl": "强|中|弱", "times": ["0:00:00"], "text": "嘉宾的看法"}],
 "glossary": [["概念", "解释"]],
 "quotes": [{"q": "金句原话", "t": ""}],
 "quiz": ["自测题"]
}
```

## 写作要求

- **要详细**：用户靠时间线代替看视频。每 1–3 分钟一个要点，每个要点 2–4 条内容，写清楚具体的论据、例子、数字和嘉宾原话里的判断，不要只写"讨论了 X"。
- **立场提醒**：嘉宾在哪家公司、和谁有利益关系，写进 `core.stance`。
- **依据强弱**：`entities.lvl` 中，"强"表示亲身经历或内部视角，"中"表示行业观察，"弱"表示嘉宾自称猜测或了解不多。
- **和你有关**：三个方向都要写，每条都要连回访谈里的具体位置（用 `{{时间}}`）。投资部分只做观察、提供可跟踪的信号，**不给买卖建议**，开头注明"不构成投资建议"。
- **预测追踪**：嘉宾说过的、带时间或可以检验的判断都收进来；到期的旧预测，在之后的会话里可以帮用户核实，并更新 `status`。
- **英文**：正文照常写英文术语，`build.py` 会自动在每章第一次出现时加中文注释。遇到 `scripts/glossary.py` 的术语表 `T` 里没有的新英文词，要把它加进去，格式是 (英文, 中文解释, 类别, 是否忽略大小写)。类别是 概念 / 公司与产品 / 人物。
- 语言朴素直接，不用营销腔。
