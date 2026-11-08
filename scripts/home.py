"""生成知识库首页：汇总输出文件夹里所有剧集。

用法: python3 home.py [输出文件夹]（不写就用 config/settings.json 里的 output_dir）
     读取每个子文件夹里的 episode.json，生成 <输出文件夹>/首页.html
"""
import sys, os, re, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1:
    out_dir = sys.argv[1]
else:
    out_dir = json.load(open(os.path.join(os.path.dirname(HERE), "config", "settings.json"), encoding="utf-8"))["output_dir"]
e = html.escape

eps = []
for name in sorted(os.listdir(out_dir)):
    p = os.path.join(out_dir, name, "episode.json")
    if os.path.isfile(p):
        ep = json.load(open(p, encoding="utf-8"))
        ep["_folder"] = name
        eps.append(ep)
eps.sort(key=lambda x: x.get("published", ""), reverse=True)

def secs(t):
    p = [int(x) for x in t.split(":")]
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]

def strip(s):
    return re.sub(r"<[^>]+>|\{\{[^}]*\}\}", "", s)

def tc(ep, t):
    return f'<a class="tc" href="{ep["url"]}?t={secs(t)}" target="_blank" rel="noopener">{t}</a>'

def link(ep):
    return ep.get("artifact_url") or ep["url"]

# ---- episode cards ----
all_tags = []
cards = ""
for ep in eps:
    for t in ep.get("tags", []):
        if t not in all_tags:
            all_tags.append(t)
    hay = " ".join([ep["title"], ep.get("guest", ""), ep.get("show", ""), " ".join(ep.get("tags", [])),
                    " ".join(x["name"] for x in ep.get("entities", [])), " ".join(strip(x["q"]) for x in ep.get("themes", []))]).lower()
    concl = strip(ep["core"]["conclusion"])
    n_beats = sum(len(c["beats"]) for c in ep["chapters"])
    fc = ep.get("factchecks", [])
    fc_ok = sum(1 for f in fc if f["status"] == "confirmed")
    tags = "".join(f'<span class="tag">{e(t)}</span>' for t in ep.get("tags", []))
    note_link = (f'<a class="btn btn-primary" href="{e(ep["artifact_url"])}" target="_blank" rel="noopener">打开笔记</a>' if ep.get("artifact_url")
                 else '<span class="muted">笔记还没发布</span>')
    cards += f"""<article class="ep" data-tags="{e('|'.join(ep.get('tags', [])))}" data-hay="{e(hay)}">
      <div class="ep-meta"><span class="rec">{e(ep.get("show", ""))}</span><span>{ep.get("published", "")}</span><span>{ep["duration"]}</span></div>
      <h3><a href="{e(link(ep))}" target="_blank" rel="noopener">{e(ep["title"])}</a></h3>
      <p class="ep-concl">{e(concl)}</p>
      <div class="ep-stats"><span>{len(ep["chapters"])} 章 · {n_beats} 段</span><span>{len(ep.get("entities", []))} 个观点对象</span>{f'<span>事实核查 {fc_ok}/{len(fc)} 属实</span>' if fc else ''}</div>
      <div class="ep-tags">{tags}</div>
      <div class="ep-actions">{note_link}<a class="btn" href="{e(ep["url"])}" target="_blank" rel="noopener">B站原视频</a><span class="folder">文件夹：{e(ep["_folder"])}</span></div>
    </article>"""

# ---- cross-episode views on the same company / industry ----
by_name = {}
for ep in eps:
    for x in ep.get("entities", []):
        by_name.setdefault(x["name"], []).append((ep, x))
multi = {k: v for k, v in by_name.items() if len({id(ep) for ep, _ in v}) >= 2}
if multi:
    cross = ""
    for name, rows in sorted(multi.items(), key=lambda kv: -len(kv[1])):
        atts = {x["attitude"] for _, x in rows}
        flag = '<span class="flag">看法不一致</span>' if len(atts) > 1 else '<span class="flag same">看法一致</span>'
        lis = "".join(f'<li><b>{e(ep.get("guest", ""))}</b>（{e(ep.get("published", ""))}）：<span class="att">{e(x["attitude"])}</span> — {e(strip(x["text"])[:140])}… {tc(ep, x["times"][0]) if x["times"] else ""}</li>' for ep, x in rows)
        cross += f'<article class="cross"><header><h3>{e(name)}</h3>{flag}</header><ul>{lis}</ul></article>'
else:
    cross = ('<div class="empty"><b>还需要至少两期才能对比。</b><p>以后每多总结一期，这里会自动列出不同嘉宾对同一家公司或同一个行业的看法，'
             '并标出看法一致还是相反。目前这期涉及的对象：' + "、".join(e(k) for k in by_name) + '。</p></div>')

# ---- predictions ----
preds = []
for ep in eps:
    for x in ep.get("predictions", []):
        preds.append((ep, x))
STATUS = {"pending": ("待检验", "pend"), "right": ("说对了", "ok"), "wrong": ("说错了", "bad"), "mixed": ("部分应验", "part")}
prow = "".join(
    f'<li class="pred" data-st="{x["status"]}"><span class="pred-due">{e(x["due"])}</span><span class="pred-claim">{e(strip(x["claim"]))}'
    f'<span class="pred-by">— {e(ep.get("guest", ""))}，{e(ep.get("published", ""))}</span></span>'
    f'<span class="st st-{STATUS[x["status"]][1]}">{STATUS[x["status"]][0]}</span>{tc(ep, x["t"])}</li>' for ep, x in preds)

chips = '<button type="button" class="fchip on" data-tag="">全部</button>' + "".join(f'<button type="button" class="fchip" data-tag="{e(t)}">{e(t)}</button>' for t in all_tags)
total_h = sum(secs(ep["duration"]) for ep in eps) / 3600

css = open(os.path.join(HERE, "assets", "page.css"), encoding="utf-8").read()
css += r"""
.home{max-width:1080px;margin:0 auto;padding-block:40px 80px}
.home-hero{padding-bottom:28px;border-bottom:1px solid var(--line)}
.home-hero h1{margin:10px 0 8px}
.home-hero p{color:var(--muted);margin:0;max-width:62ch}
.numbers{display:flex;flex-wrap:wrap;gap:8px 28px;margin-top:18px;font-family:var(--f-mono);font-size:12.5px;color:var(--muted)}
.numbers b{font-size:20px;color:var(--ink);font-weight:600;margin-right:4px}
.search{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:28px 0 16px}
.search input{font:inherit;flex:1;min-width:min(100%,260px);padding:9px 14px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink)}
.search input:focus-visible{outline:2px solid var(--rec);outline-offset:1px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.fchip{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--surface);color:var(--muted);border-radius:999px;padding:2px 12px;cursor:pointer}
.fchip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.eps{display:flex;flex-direction:column;gap:14px}
.ep{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px 22px;display:flex;flex-direction:column;gap:8px}
.ep-meta{font-family:var(--f-mono);font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 14px}
.ep h3{margin:0;font-family:var(--f-display);font-size:20px;line-height:1.45;text-wrap:balance}
.ep h3 a{text-decoration:none}
.ep h3 a:hover{color:var(--rec-ink)}
.ep-concl{margin:0;color:var(--muted);max-width:75ch}
.ep-stats{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:12.5px;color:var(--muted);font-family:var(--f-mono)}
.ep-tags{display:flex;flex-wrap:wrap;gap:6px}
.tag{font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:4px;padding:0 7px}
.ep-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:6px}
.folder{font-size:12px;color:var(--muted);font-family:var(--f-mono)}
.muted{color:var(--muted);font-size:13px}
.no-match{color:var(--muted);padding:20px 0}
.cross-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,420px),1fr));gap:14px}
.cross{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px}
.cross header{display:flex;gap:10px;align-items:center}
.cross h3{margin:0;font-size:16px}
.cross ul{margin:8px 0 0;padding-left:1.1em;font-size:14px;display:flex;flex-direction:column;gap:6px}
.att{color:var(--rec-ink);font-weight:600}
.flag{font-size:11.5px;font-weight:700;padding:0 8px;border-radius:999px;background:var(--strong-bg);color:var(--strong)}
.flag.same{background:var(--weak-bg);color:var(--weak)}
.empty{background:var(--surface);border:1px dashed var(--line);border-radius:10px;padding:18px 20px;color:var(--muted)}
.empty b{color:var(--ink)}
.empty p{margin:6px 0 0}
.preds{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.pred{display:grid;grid-template-columns:9.5em minmax(0,1fr) auto auto;gap:6px 14px;padding:12px 0;border-bottom:1px solid var(--line);align-items:baseline}
.pred-due{font-family:var(--f-mono);font-size:12.5px;color:var(--rec-ink);font-weight:600}
.pred-by{display:block;color:var(--muted);font-size:12.5px}
.st{font-size:12px;font-weight:700;padding:0 8px;border-radius:4px;line-height:1.8;white-space:nowrap}
.st-pend{background:var(--weak-bg);color:var(--weak)}.st-ok{background:#e1f1e4;color:#1f6f37}.st-bad{background:var(--strong-bg);color:var(--strong)}.st-part{background:var(--mid-bg);color:var(--mid)}
@media (max-width:640px){.pred{grid-template-columns:minmax(0,1fr) auto}.pred-due{grid-column:1/-1}}
"""
js = r"""
(function(){
  const q=document.getElementById('q'); const eps=[...document.querySelectorAll('.ep')]; const none=document.getElementById('no-match');
  let tag='';
  function apply(){const s=q.value.trim().toLowerCase(); let n=0;
    eps.forEach(el=>{const ok=(!tag||el.dataset.tags.split('|').includes(tag))&&(!s||s.split(/\s+/).every(w=>el.dataset.hay.includes(w))); el.hidden=!ok; if(ok)n++;});
    none.hidden=n>0; document.getElementById('ep-count').textContent=n+' / '+eps.length+' 期';}
  q.addEventListener('input',apply);
  document.querySelectorAll('.fchip[data-tag]').forEach(b=>b.addEventListener('click',()=>{tag=b.dataset.tag; document.querySelectorAll('.fchip[data-tag]').forEach(x=>x.classList.toggle('on',x===b)); apply();}));
  apply();
})();
"""
page = f"""<title>播客笔记库</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Noto+Serif+SC:wght@700;900&display=swap">
<style>{css}</style>
<div class="home">
  <header class="home-hero">
    <div class="meta"><span class="rec">播客笔记库</span><span>更新于 {max((ep.get("summarized", ep.get("published", "")) for ep in eps), default="")}</span></div>
    <h1>播客笔记库</h1>
    <p>所有总结过的B站播客。每期都有分章时间线、核心观点、事实核查和英文对照，时间戳可以直接跳到原视频。</p>
    <div class="numbers"><span><b>{len(eps)}</b>期</span><span><b>{total_h:.1f}</b>小时内容</span><span><b>{sum(sum(len(c["beats"]) for c in ep["chapters"]) for ep in eps)}</b>个要点</span><span><b>{len(preds)}</b>条预测待追踪</span></div>
  </header>
  <section class="sec" id="episodes"><header class="sec-head"><span class="eyebrow" id="ep-count"></span><h2>全部剧集</h2></header>
    <div class="search"><input type="search" id="q" placeholder="搜索标题、嘉宾、公司、话题…" aria-label="搜索剧集"><div class="chips">{chips}</div></div>
    <div class="eps">{cards}</div><p class="no-match" id="no-match" hidden>没有匹配的剧集，换个关键词试试。</p>
  </section>
  <section class="sec" id="cross"><header class="sec-head"><span class="eyebrow">同一个对象，不同嘉宾怎么看</span><h2>观点对照</h2></header><div class="cross-grid">{cross}</div></section>
  <section class="sec" id="predictions"><header class="sec-head"><span class="eyebrow">嘉宾说过的、可以检验的判断</span><h2>预测追踪</h2></header><ul class="preds">{prow}</ul></section>
  <footer class="note">每总结一期新的播客，这一页会自动更新。内容为嘉宾的个人观点，不构成投资建议。</footer>
</div>
<script>{js}</script>
"""
open(os.path.join(out_dir, "首页.html"), "w", encoding="utf-8").write(page)
print("首页", len(eps), "期", len(page))
