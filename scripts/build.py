"""由 episode.json 生成两个版本：网页版（发布为 Artifact）和 OneNote 版（粘贴用）。

用法: python3 build.py <剧集文件夹>
     剧集文件夹里要有 episode.json，生成 网页版.html 和 OneNote版.html。
"""
import sys, os, re, json, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glossary

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ep_dir = sys.argv[1]
ep = json.load(open(os.path.join(ep_dir, "episode.json"), encoding="utf-8"))
_kt = os.path.join(ROOT, "local", "known_terms.txt")  # 已认识、不再注释的英文词，每行一个（可以没有这个文件）
known = [l for l in open(_kt, encoding="utf-8").read().splitlines() if l.strip() and not l.startswith("#")] if os.path.exists(_kt) else []

BV, URL = ep["bv"], ep["url"]
e = html.escape

def secs(t):
    p = [int(x) for x in t.split(":")]
    while len(p) < 3:
        p.insert(0, 0)
    return p[0] * 3600 + p[1] * 60 + p[2]

TOTAL = secs(ep["duration"])
LEVEL_RANK = {"必看": 3, "推荐": 2, "选看": 1, "可跳过": 0}
CHECK = {"confirmed": ("属实", "ok"), "partial": ("部分属实", "part"), "disputed": ("与公开信息不符", "bad"), "unverified": ("无法核实", "unk")}

# ======================================================================
# 网页版
# ======================================================================
def tc(t):
    return f'<a class="tc" href="{URL}?t={secs(t)}" target="_blank" rel="noopener">{t}</a>'

def rich(s):
    return re.sub(r"\{\{(\d+:\d\d:\d\d)\}\}", lambda m: tc(m.group(1)), s)

def level_at(s):
    for k in ep["skim"]:
        end = secs(k["end"]) if k["end"] else TOTAL
        if secs(k["start"]) <= s < end:
            return LEVEL_RANK[k["level"]], k["level"]
    return None, "未分级"

chapters = []
for i, c in enumerate(ep["chapters"]):
    num, _, label = c["title"].partition("、")
    rank, lname = level_at(secs(c["start"]))
    chapters.append(dict(i=i, num=num, label=label, start=c["start"], end=c["end"], beats=c["beats"], rank=rank, lname=lname))

W = []
def section(id_, title, eyebrow, inner):
    W.append(f'<section id="{id_}" class="sec"><header class="sec-head"><span class="eyebrow">{eyebrow}</span><h2>{e(title)}</h2></header>{inner}</section>')

# 精华主题
cards = "".join(f'<article class="qa"><h3>{rich(x["q"])}</h3><p>{rich(x["a"])}</p><div class="qa-foot">{tc(x["t"])}</div></article>' for x in ep["themes"])
section("themes", "精华主题", f'{len(ep["themes"])} 个问题读懂这期', f'<div class="qa-grid">{cards}</div>')

# 跳着看
lis = ""
for k in ep["skim"]:
    rank = LEVEL_RANK[k["level"]]
    rng = tc(k["start"]) + (" – " + tc(k["end"]) if k["end"] else " – 结尾")
    lis += f'<li class="skim skim-{rank}"><span class="skim-lvl">{k["level"]}</span><span class="skim-rng">{rng}</span><span class="skim-desc">{rich(k["desc"])}</span></li>'
section("skim", "跳着看指南", "时间不够时从这里挑", f'<ul class="skim-list">{lis}</ul>')

# 时间线
chs = ""
for c in chapters:
    rows = ""
    for b in c["beats"]:
        pts = "".join(f"<li>{rich(x)}</li>" for x in b["points"])
        rows += f'<li class="beat"><div class="beat-t">{tc(b["t"])}</div><div class="beat-b"><h4>{e(b["title"])}</h4><ul>{pts}</ul></div></li>'
    chip = f'<span class="chip chip-{c["rank"] if c["rank"] is not None else "x"}">{c["lname"]}</span>'
    chs += (f'<details class="chapter" id="ch-{c["i"]+1}" data-ch="{c["i"]}" open><summary>'
            f'<span class="ch-num">{c["num"]}</span><span class="ch-title">{e(c["label"])}</span>'
            f'<span class="ch-meta">{tc(c["start"])}<span class="dash">–</span>{tc(c["end"])}{chip}<span class="ch-count">{len(c["beats"])} 段</span>'
            f'<label class="read"><input type="checkbox" id="read-{c["i"]}" data-ch="{c["i"]}"><span>已读</span></label></span>'
            f'</summary><ol class="beats">{rows}</ol></details>')
tools = ('<div class="tl-tools"><button type="button" id="tl-open" class="btn-ghost">全部展开</button>'
         '<button type="button" id="tl-close" class="btn-ghost">全部收起</button>'
         '<button type="button" id="tl-unread" class="btn-ghost">只看未读</button></div>')
section("timeline", "时间线", f'{len(chapters)} 章 · {sum(len(c["beats"]) for c in chapters)} 段 · 时间戳对准到原句', tools + chs)

# 核心观点
core = ep["core"]
inner = f'<div class="verdict"><span class="label">核心结论</span><p>{rich(core["conclusion"])}</p></div>'
args = "".join(f'<li class="arg"><div class="arg-claim">{rich(a["claim"])}</div><div class="arg-why">{rich(a["why"])}</div><div class="arg-t">{tc(a["t"])}</div></li>' for a in core["arguments"])
inner += f'<h3 class="sub">主要论点与理由</h3><ol class="args">{args}</ol>'
for title, key in (("逻辑强度评估", "logic"), ("潜在立场识别", "stance")):
    dl = "".join(f'<div class="dl-row"><dt>{rich(k)}</dt><dd>{rich(v)}</dd></div>' for k, v in core[key])
    inner += f'<h3 class="sub">{title}</h3><dl class="dl">{dl}</dl>'
inner += f'<div class="advice"><span class="label">最终建议（访谈给出的行动方向）</span><p>{rich(core["advice"])}</p></div>'
section("core", "核心观点", "结论、论证与立场", inner)

# 事实核查
fcs = ep.get("factchecks", [])
if fcs:
    counts = {}
    for f in fcs:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    summary = "　".join(f'<span class="fc-badge fc-{CHECK[s][1]}">{CHECK[s][0]} {n}</span>' for s, n in counts.items())
    items = ""
    for f in fcs:
        lab, cls = CHECK[f["status"]]
        src = "".join(f'<a class="src" href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["title"])}</a>' for s in f["sources"])
        items += (f'<li class="fc fc-{cls}"><div class="fc-head"><span class="fc-badge fc-{cls}">{lab}</span>'
                  f'<span class="fc-claim">{rich(f["claim"])}</span>{tc(f["t"])}</div>'
                  f'<p>{rich(f["note"])}</p>{"<div class=fc-src>来源：" + src + "</div>" if src else ""}</li>')
    section("checks", "事实核查", "嘉宾说的事实，联网对照过", f'<p class="fc-sum">{summary}</p><ul class="fc-list">{items}</ul>')

# 和你有关
per = ep.get("personal", [])
preds = ep.get("predictions", [])
if per or preds:
    inner = ""
    for blk in per:
        lis = "".join(f"<li>{rich(x)}</li>" for x in blk["points"])
        note = f'<p class="p-note">{rich(blk["note"])}</p>' if blk.get("note") else ""
        inner += f'<article class="pcard"><h3>{e(blk["area"])}</h3>{note}<ul>{lis}</ul></article>'
    if preds:
        rows = "".join(f'<li class="pred"><span class="pred-due">{e(x["due"])}</span><span class="pred-claim">{rich(x["claim"])}</span>{tc(x["t"])}</li>' for x in preds)
        inner += f'<h3 class="sub">预测追踪</h3><p class="p-note">嘉宾给出的、可以在未来检验的判断。到期后对照看他说得准不准。</p><ul class="preds">{rows}</ul>'
    section("personal", "和你有关", "投资 · AI 趋势 · 职业成长", f'<div class="pgrid">{inner}</div>')

# 引申思考
cards = "".join(f'<article class="think"><h3>{rich(x["k"])}</h3><ul>{"".join(f"<li>{rich(p)}</li>" for p in x["points"])}</ul></article>' for x in ep["extend"])
section("extend", "引申思考", "把访谈用到自己身上", f'<div class="think-grid">{cards}</div>')

# 观点速览
LV = {"强": "strong", "中": "mid", "弱": "weak"}
types = []
cards = ""
for x in ep["entities"]:
    if x["type"] not in types:
        types.append(x["type"])
    ts_ = "、".join(tc(t) for t in x["times"])
    cards += (f'<article class="ent" data-type="{x["type"]}" data-lvl="{x["lvl"]}"><header><h3>{e(x["name"])}</h3>'
              f'<span class="tag">{x["type"]}</span><span class="lvl lvl-{LV[x["lvl"]]}">{x["lvl"]}</span></header>'
              f'<div class="ent-att">{e(x["attitude"])}</div><p>{rich(x["text"])}</p><div class="ent-t">{ts_}</div></article>')
chips_t = "".join(f'<button type="button" class="fchip" data-f="type" data-v="{t}">{t}</button>' for t in types)
chips_l = "".join(f'<button type="button" class="fchip" data-f="lvl" data-v="{l}">{l}</button>' for l in "强中弱")
filters = (f'<div class="filters"><div class="fgroup"><span class="flabel">类型</span><button type="button" class="fchip on" data-f="type" data-v="">全部</button>{chips_t}</div>'
           f'<div class="fgroup"><span class="flabel">依据</span><button type="button" class="fchip on" data-f="lvl" data-v="">全部</button>{chips_l}</div>'
           '<span class="fcount" id="fcount"></span></div>'
           '<p class="legend"><span class="lvl lvl-strong">强</span> 亲身经历或内部视角　<span class="lvl lvl-mid">中</span> 行业观察　<span class="lvl lvl-weak">弱</span> 嘉宾自称猜测或了解不多</p>')
section("entities", "观点速览", "按公司 / 行业", filters + f'<div class="ent-grid">{cards}</div>')

# 关键概念
dl = "".join(f'<div class="g-row"><dt>{rich(a)}</dt><dd>{rich(b)}</dd></div>' for a, b in ep["glossary"])
section("glossary", "关键概念", "听不懂的词在这里", f'<dl class="gloss">{dl}</dl>')

TERMS_MARK = "<!--TERMS-->"
W.append(TERMS_MARK)

# 金句
qs = "".join(f'<figure class="quote"><blockquote>{rich(x["q"])}</blockquote><figcaption>{tc(x["t"])}</figcaption></figure>' for x in ep["quotes"])
section("quotes", "金句", "值得记住的话", f'<div class="quotes">{qs}</div>')

# 自测
section("quiz", "自测题", "合上页面，试着回答", f'<ol class="quiz">{"".join(f"<li>{rich(q)}</li>" for q in ep["quiz"])}</ol>')

body = "".join(W)
body, used = glossary.annotate(body, "web", known)

# 英文对照
groups = ""
for cat, rows in glossary.term_groups(used, known):
    if not rows:
        continue
    rr = "".join(
        f'<div class="t-row" data-terms="{e("|".join(t.lower() for t in r["terms"]))}"><dt lang="en">{e(" / ".join(r["terms"]))}</dt>'
        f'<dd>{e(r["gloss"])}</dd><button type="button" class="known-btn" aria-pressed="false">认识</button></div>' for r in rows)
    groups += f'<div class="t-group"><h3 class="sub">{cat}<span class="t-n">{len(rows)}</span></h3><dl class="terms">{rr}</dl></div>'
terms_sec = (f'<section id="terms" class="sec"><header class="sec-head"><span class="eyebrow">对话里出现的英文</span><h2>英文对照</h2></header>'
             '<p class="t-intro">正文里英文词第一次出现时，后面的灰色括号就是中文意思。已经认识的词点“认识”，全页就不再显示它的中文注释。</p>'
             '<div class="t-tools"><span id="known-count" class="t-n"></span><button type="button" class="btn-ghost" id="known-copy">复制已认识的词</button>'
             '<button type="button" class="btn-ghost" id="known-reset">全部恢复</button><span id="known-status" class="t-n" role="status" aria-live="polite"></span></div>'
             f'{groups}</section>')
body = body.replace(TERMS_MARK, terms_sec)

TOC = [("themes", "精华主题"), ("skim", "跳着看"), ("timeline", "时间线"), ("core", "核心观点")]
if fcs: TOC.append(("checks", "事实核查"))
if per or preds: TOC.append(("personal", "和你有关"))
TOC += [("extend", "引申思考"), ("entities", "观点速览"), ("glossary", "关键概念"), ("terms", "英文对照"), ("quotes", "金句"), ("quiz", "自测题")]
toc = ""
for sid, t in TOC:
    toc += f'<a href="#{sid}" data-sec="{sid}">{t}</a>'
    if sid == "timeline":
        toc += '<div class="chs">' + "".join(
            f'<a href="#ch-{c["i"]+1}" class="toc-ch" data-ch="{c["i"]}"><span>{c["num"]}</span>{e(re.split("[：，]", c["label"])[0])}</a>' for c in chapters) + "</div>"

ruler = ""
for k, c in enumerate(chapters):
    s0 = secs(c["start"]) if k else 0
    s1 = secs(chapters[k + 1]["start"]) if k + 1 < len(chapters) else TOTAL
    r = "x" if c["rank"] is None else c["rank"]
    ruler += f'<a class="seg seg-{r}" data-ch="{c["i"]}" style="width:{(s1-s0)/TOTAL*100:.3f}%" href="#ch-{k+1}" title="{e(c["num"]+"、"+c["label"])}（{c["start"]}–{c["end"]}）"><span>{c["num"]}</span></a>'
ticks = "".join(f'<span class="tick" style="left:{h*3600/TOTAL*100:.3f}%">{h}:00</span>' for h in range(TOTAL // 3600 + 1))
keys = '<span><i style="background:var(--l3)"></i>必看</span><span><i style="background:var(--l2)"></i>推荐</span><span><i style="background:var(--l1)"></i>选看</span><span><i style="background:var(--lx)"></i>可跳过 / 未分级</span><span><i class="k-read"></i>已读</span>'

guest, _ = glossary.annotate(f'<p class="guest">{rich(ep["guest_html"])}</p>', "web", known)

# ======================================================================
# OneNote 版（只用内联样式和表格，OneNote 粘贴时能保留）
# ======================================================================
ACC, MUT, BRD = "#9a5b13", "#6b6255", "#e3d6bf"
O = []
def ots(t):
    return f'<a href="{URL}?t={secs(t)}" style="color:{ACC};font-family:Menlo,Consolas,monospace;font-weight:bold;text-decoration:none">{t}</a>'
def orich(s):
    return re.sub(r"\{\{(\d+:\d\d:\d\d)\}\}", lambda m: ots(m.group(1)), s)
def oh2(s): O.append(f'<h2 style="color:{ACC};border-bottom:2px solid {BRD};padding-bottom:4px">{e(s)}</h2>')
def oh3(s): O.append(f'<h3 style="color:#3b2a14">{s}</h3>')
def op(s, muted=False): O.append(f'<p style="color:{MUT if muted else "#222"}">{s}</p>')
def oul(items): return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
def otable(headers, rows, widths=None):
    th = "".join(f'<td style="background:#ead9bd;padding:6px;border:1px solid {BRD}"><b>{e(h)}</b></td>' for h in headers)
    trs = ""
    for ri, r in enumerate(rows):
        zb = "#fbf7ef" if ri % 2 else "#ffffff"
        trs += "<tr>" + "".join(f'<td style="background:{zb};padding:7px 8px;border:1px solid {BRD};vertical-align:top{";width:"+widths[i] if widths else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
    O.append(f'<table style="border-collapse:collapse;width:100%"><tr>{th}</tr>{trs}</table><br>')
def ocallout(title, body):
    O.append(f'<table style="border-collapse:collapse;width:100%"><tr><td style="background:#f7f1e6;border-left:4px solid {ACC};padding:10px"><b style="color:{ACC}">{e(title)}</b><br>{body}</td></tr></table><br>')
OLV = {"强": "<span style='background:#fde2df;color:#b42318;font-weight:bold;padding:1px 6px'>强</span>",
       "中": "<span style='background:#fdefd6;color:#9a5a00;font-weight:bold;padding:1px 6px'>中</span>",
       "弱": "<span style='background:#ececec;color:#666;font-weight:bold;padding:1px 6px'>弱</span>"}
OCK = {"confirmed": "<span style='background:#e3f2e5;color:#1f6f37;font-weight:bold;padding:1px 6px'>✓ 属实</span>",
       "partial": "<span style='background:#fdefd6;color:#9a5a00;font-weight:bold;padding:1px 6px'>◐ 部分属实</span>",
       "disputed": "<span style='background:#fde2df;color:#b42318;font-weight:bold;padding:1px 6px'>✗ 与公开信息不符</span>",
       "unverified": "<span style='background:#ececec;color:#666;font-weight:bold;padding:1px 6px'>? 无法核实</span>"}

O.append(f'<h1 style="color:#3b2a14">{e(ep["title"])}</h1>')
op(f'{e(ep["show"])} ｜ 时长 {ep["duration"]} ｜ 发布 {ep["published"]} ｜ <a href="{URL}">B站原视频</a>', True)
op(orich(ep["guest_html"]))
op("💡 所有<b>时间戳都可以点击</b>，会跳到B站对应那句话。英文词后面的灰色括号是中文意思。", True)

oh2("精华主题")
otable(["问题", "嘉宾的回答", "位置"], [[orich(x["q"]), orich(x["a"]), ots(x["t"])] for x in ep["themes"]], ["24%", "64%", "12%"])
oh2("跳着看指南")
otable(["推荐度", "片段", "看点"], [[k["level"], ots(k["start"]) + " – " + (ots(k["end"]) if k["end"] else "结尾"), orich(k["desc"])] for k in ep["skim"]], ["12%", "28%", "60%"])
oh2("时间线")
for c in chapters:
    oh3(f'{e(c["num"] + "、" + c["label"])}　<span style="color:{MUT};font-weight:normal;font-size:90%">{ots(c["start"])} – {ots(c["end"])}</span>')
    otable(["时间", "内容"], [[ots(b["t"]), f"<b>{e(b['title'])}</b>" + oul([orich(x) for x in b["points"]])] for b in c["beats"]], ["10%", "90%"])
oh2("核心观点")
ocallout("核心结论", orich(core["conclusion"]))
oh3("主要论点与理由")
otable(["论点", "理由与证据", "位置"], [[orich(a["claim"]), orich(a["why"]), ots(a["t"])] for a in core["arguments"]], ["28%", "60%", "12%"])
oh3("逻辑强度评估")
otable(["维度", "评估"], [[orich(k), orich(v)] for k, v in core["logic"]], ["18%", "82%"])
oh3("潜在立场识别")
otable(["立场", "说明"], [[orich(k), orich(v)] for k, v in core["stance"]], ["22%", "78%"])
ocallout("最终建议（访谈给出的行动方向）", orich(core["advice"]))
if fcs:
    oh2("事实核查")
    otable(["结论", "嘉宾的说法", "核查结果", "位置"],
           [[OCK[f["status"]], orich(f["claim"]), orich(f["note"]) + ("<br>" + "；".join(f'<a href="{e(s["url"])}">{e(s["title"])}</a>' for s in f["sources"]) if f["sources"] else ""), ots(f["t"])] for f in fcs],
           ["13%", "24%", "53%", "10%"])
if per or preds:
    oh2("和你有关")
    for blk in per:
        oh3(e(blk["area"]))
        if blk.get("note"):
            op(orich(blk["note"]), True)
        O.append(oul([orich(x) for x in blk["points"]]))
    if preds:
        oh3("预测追踪")
        otable(["检验时间", "预测", "位置"], [[e(x["due"]), orich(x["claim"]), ots(x["t"])] for x in preds], ["16%", "72%", "12%"])
oh2("引申思考")
otable(["方向", "思考"], [[orich(x["k"]), "<br>".join("• " + orich(p) for p in x["points"])] for x in ep["extend"]], ["16%", "84%"])
oh2("观点速览")
op("依据：" + OLV["强"] + " 亲身经历或内部视角　" + OLV["中"] + " 行业观察　" + OLV["弱"] + " 嘉宾自称猜测或了解不多", True)
otable(["对象", "类型", "态度", "依据", "时间", "要点"],
       [[f"<b>{e(x['name'])}</b>", x["type"], e(x["attitude"]), OLV[x["lvl"]], "、".join(ots(t) for t in x["times"]), orich(x["text"])] for x in ep["entities"]],
       ["13%", "7%", "10%", "6%", "14%", "50%"])
oh2("关键概念")
otable(["概念", "解释"], [[orich(a), orich(b)] for a, b in ep["glossary"]], ["22%", "78%"])
O.append(TERMS_MARK)
oh2("金句")
otable(["金句", "位置"], [[f'“{orich(x["q"])}”', ots(x["t"])] for x in ep["quotes"]], ["88%", "12%"])
oh2("自测题")
O.append(oul([orich(q) for q in ep["quiz"]]))
op(f'基于{e(ep["source"])}整理，人名和术语已按上下文更正。内容为嘉宾的个人观点，不构成投资建议。', True)

onenote = "".join(O)
onenote, oused = glossary.annotate(onenote, "onenote", known)
tt = f'<h2 style="color:{ACC};border-bottom:2px solid {BRD};padding-bottom:4px">英文对照</h2><p style="color:{MUT}">正文里英文词第一次出现时，后面的灰色括号就是中文意思。</p>'
for cat, rows in glossary.term_groups(oused, known):
    if rows:
        tt += f'<h3 style="color:#3b2a14">{cat}</h3>'
        tt += "<table style='border-collapse:collapse;width:100%'>" + "".join(
            f'<tr><td style="background:{"#fbf7ef" if i % 2 else "#ffffff"};padding:6px 8px;border:1px solid {BRD};width:28%"><b>{e(" / ".join(r["terms"]))}</b></td>'
            f'<td style="background:{"#fbf7ef" if i % 2 else "#ffffff"};padding:6px 8px;border:1px solid {BRD}">{e(r["gloss"])}</td></tr>' for i, r in enumerate(rows)) + "</table><br>"
onenote = onenote.replace(TERMS_MARK, tt)
onenote = f'<div style="font-family:-apple-system,PingFang SC,Microsoft YaHei,sans-serif;font-size:14px;line-height:1.6;color:#222">{onenote}</div>'
open(os.path.join(ep_dir, "OneNote版.html"), "w", encoding="utf-8").write(
    f'<!doctype html><html><head><meta charset="utf-8"><title>{e(ep["short_title"])}</title></head><body style="max-width:960px;margin:24px auto;padding:0 16px">{onenote}</body></html>')

# ======================================================================
# 组装网页
# ======================================================================
css = open(os.path.join(HERE, "assets", "page.css"), encoding="utf-8").read() + open(os.path.join(HERE, "assets", "extra.css"), encoding="utf-8").read()
js = open(os.path.join(HERE, "assets", "page.js"), encoding="utf-8").read().replace("__BV__", BV)
page = f"""<title>{e(ep["short_title"])}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600&family=Noto+Serif+SC:wght@700;900&display=swap">
<style>{css}</style>
<div class="shell">
  <nav class="toc" aria-label="目录"><span class="toc-label">目录</span><span class="toc-progress" id="toc-progress"></span>{toc}</nav>
  <main>
    <header class="hero">
      <div class="meta"><span class="rec">{e(ep["show"])}</span><span>{BV}</span><span>{ep["duration"]}</span><span>{ep["published"]}</span></div>
      <h1>{e(ep["title"])}</h1>
      {guest}
      <div class="actions">
        <a class="btn" href="{URL}" target="_blank" rel="noopener">在B站打开</a>
        <button type="button" class="btn btn-primary" id="copy-onenote">复制到 OneNote</button>
        <span class="copy-status" id="copy-status" role="status" aria-live="polite">时间戳都能点，会跳到B站对应那句话</span>
      </div>
      <div class="ruler">
        <div class="ruler-head"><span>全片 <b>{ep["duration"]}</b> · 按章节，颜色表示推荐程度，点色块跳到对应章节 · <b id="read-count"></b></span><span class="keys">{keys}</span></div>
        <div class="bar">{ruler}</div>
        <div class="ticks">{ticks}</div>
      </div>
    </header>
    {body}
    <footer class="note">基于{e(ep["source"])}整理，人名和术语已按上下文更正；时间戳已对准到原句开头。内容为嘉宾的个人观点，不构成投资建议。</footer>
  </main>
</div>
<template id="onenote-src">{onenote}</template>
<script>{js}</script>
"""
open(os.path.join(ep_dir, "网页版.html"), "w", encoding="utf-8").write(page)
print("网页版", len(page), "| OneNote版", len(onenote), "| 注释术语", len(used))
