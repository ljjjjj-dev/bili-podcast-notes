"""英文术语的中文注释：术语表 T 和 annotate()。
新术语直接加到 T 里：(英文, 中文解释, 类别, 是否忽略大小写)。
"""
import sys, re, html

# term, gloss, category, case_insensitive
T = [
 # ---- 概念 ----
 ("Train with finite context, use as infinite context", "用有限的上下文训练，在近乎无限的上下文里使用", "概念", False),
 ("agentic coding", "智能体编程：AI 自己动手改代码、跑测试", "概念", True),
 ("ML coding", "让 AI 写代码、做实验来完成机器学习研究", "概念", False),
 ("long horizon", "长程任务：让 AI 连续完成很长、很多步骤的工作", "概念", True),
 ("scaling laws", "规模定律：模型越大、数据和算力越多，效果越好的经验规律", "概念", True),
 ("scaling law", "规模定律：模型越大、数据和算力越多，效果越好的经验规律", "概念", True),
 ("continual learning", "持续学习：模型边用边学", "概念", True),
 ("context management", "上下文管理：让模型自己决定记住、丢掉或取回哪些信息", "概念", True),
 ("feature engineering", "特征工程：靠人工设计规则的老方法", "概念", True),
 ("policy gradient", "策略梯度：最基础的强化学习算法", "概念", True),
 ("post-training", "后训练", "概念", True),
 ("centralized technology", "集中化的技术：让少数人更强", "概念", True),
 ("multi-agent", "多个 AI 协作", "概念", True),
 ("tool use", "工具调用", "概念", True),
 ("token horizon", "每种规模的模型对应多少训练数据", "概念", True),
 ("training FLOPs", "训练时消耗的算力", "概念", False),
 ("sampling FLOPs", "生成答案时消耗的算力", "概念", False),
 ("3D torus", "三维环形互联：芯片按立体网格首尾相连", "概念", False),
 ("not even wrong", "连错都算不上（指说法模糊到无法判断对错）", "概念", True),
 ("party is over", "好日子到头了", "概念", True),
 ("idea is cheap", "想法不值钱", "概念", True),
 ("super app", "超级应用", "概念", True),
 ("AI for Science", "用 AI 做科学研究", "概念", False),
 ("AI for Physics", "用 AI 做物理研究", "概念", False),
 ("scale up", "扩大规模", "概念", True),
 ("scaling", "规模化扩展", "概念", True),
 ("scale", "规模化扩展", "概念", True),
 ("top-down", "自上而下，由领导决定方向", "概念", True),
 ("bottom-up", "自下而上，由一线自己决定", "概念", True),
 ("benchmark", "评测基准：给模型做的标准化考题", "概念", True),
 ("chatbot", "聊天机器人", "概念", True),
 ("underdog", "不被看好的一方", "概念", True),
 ("coding", "写代码、编程", "概念", True),
 ("SWE-bench", "软件工程编程评测", "概念", False),
 ("ARC-AGI", "抽象推理能力评测", "概念", False),
 ("Seq2Seq", "序列到序列模型，早期机器翻译用的方法", "概念", False),
 ("Transformer", "当今所有大模型的基础架构（2017 年由 Google 提出）", "概念", False),
 ("Ablation", "消融实验", "概念", False),
 ("reasoning", "推理能力", "概念", True),
 ("insight", "洞察", "概念", True),
 ("serving", "把模型部署上线、给用户使用所需的算力", "概念", True),
 ("Agent", "智能体：能自己调用工具完成任务的 AI", "概念", False),
 ("RL", "强化学习", "概念", False),
 ("SFT", "监督微调：用标准答案教模型", "概念", False),
 ("VLA", "视觉-语言-动作模型，用于机器人", "概念", False),
 ("token", "词元：模型处理文字的最小单位", "概念", True),
 ("KV", "模型记住上下文用的缓存", "概念", False),
 ("API", "接口：按调用量付费使用模型", "概念", False),
 ("GPU", "图形处理器，英伟达的 AI 芯片", "概念", False),
 ("TPU", "Google 自研的 AI 芯片", "概念", False),
 ("NVLink", "英伟达的芯片间高速互联技术", "概念", False),
 ("pod", "一组互相高速连接的芯片", "概念", False),
 ("hack", "钻空子，刷高指标", "概念", False),
 ("bug", "程序错误", "概念", True),
 ("demo", "演示原型", "概念", True),
 ("offer", "录用通知", "概念", False),
 ("scope", "职责范围", "概念", False),
 ("leader", "负责人", "概念", False),
 ("bet", "押注", "概念", False),
 ("idea", "想法", "概念", False),
 ("senior", "资深", "概念", False),
 ("research", "研究", "概念", False),
 ("to B", "面向企业客户", "概念", False),
 ("CS", "计算机科学", "概念", False),
 ("3.5 new", "3.5 新版", "公司与产品", False),
 ("CEO", "首席执行官", "概念", False),
 ("CTO", "首席技术官", "概念", False),
 ("SVP", "高级副总裁", "概念", False),
 # ---- 公司与产品 ----
 ("Google DeepMind", "Google 的 AI 研究部门", "公司与产品", False),
 ("Gemini Deep Think", "Gemini 的深度推理版本", "公司与产品", False),
 ("Claude Code", "Anthropic 的 AI 编程工具", "公司与产品", False),
 ("Nano Banana", "Google 的 AI 生图模型", "公司与产品", False),
 ("Isomorphic Labs", "DeepMind 旗下的 AI 制药公司", "公司与产品", False),
 ("Thinking Machines", "一家新成立的 AI 实验室", "公司与产品", False),
 ("Anthropic", "Claude 背后的公司，嘉宾的前东家", "公司与产品", False),
 ("OpenAI", "ChatGPT 背后的公司", "公司与产品", False),
 ("ChatGPT", "OpenAI 的聊天机器人", "公司与产品", False),
 ("Gemini", "Google 的 AI 模型，嘉宾现在的团队", "公司与产品", False),
 ("Claude", "Anthropic 的 AI 模型", "公司与产品", False),
 ("Opus", "Claude 里最强的一档模型", "公司与产品", False),
 ("Codex", "OpenAI 的编程模型", "公司与产品", False),
 ("Cursor", "AI 编程编辑器", "公司与产品", False),
 ("Composer", "Cursor 自研的模型", "公司与产品", False),
 ("Cowork", "Anthropic 的办公 AI 产品", "公司与产品", False),
 ("OpenClaw", "开源的 AI 智能体项目", "公司与产品", False),
 ("Manus", "通用 AI 智能体产品，后被 Meta 收购", "公司与产品", False),
 ("Seedance", "字节跳动的 AI 视频生成模型", "公司与产品", False),
 ("DeepSeek", "深度求索，中国 AI 公司", "公司与产品", False),
 ("Lovable", "用 AI 做网站的工具", "公司与产品", False),
 ("Midjourney", "AI 绘画工具", "公司与产品", False),
 ("Windsurf", "AI 编程工具", "公司与产品", False),
 ("xAI", "马斯克的 AI 公司", "公司与产品", False),
 ("Strawberry", "OpenAI 推理模型的内部代号“草莓”", "公司与产品", False),
 ("Horizon", "Anthropic 内部的强化学习团队", "公司与产品", False),
 ("o1", "OpenAI 第一代推理模型", "公司与产品", False),
 ("GPT-1", "OpenAI 2018 年的第一代 GPT 模型", "公司与产品", False),
 ("GPT-3", "OpenAI 2020 年的模型", "公司与产品", False),
 ("GPT-4", "OpenAI 2023 年的模型", "公司与产品", False),
 ("Dyna", "做叠衣服机器人的公司", "公司与产品", False),
 ("GitHub", "全球最大的代码托管平台", "公司与产品", False),
 ("Colab", "Google 的在线编程笔记本", "公司与产品", False),
 ("Slack", "美国常用的办公聊天软件", "公司与产品", False),
 ("Siri", "苹果的语音助手", "公司与产品", False),
 # ---- 人物 ----
 ("Jared Kaplan", "Anthropic 联合创始人、首席科学家，物理出身", "人物", False),
 ("Sam McCandlish", "Anthropic 联合创始人，物理出身", "人物", False),
 ("Sergey Brin", "Google 联合创始人", "人物", False),
 ("Noam Shazeer", "Transformer 论文作者之一", "人物", False),
 ("Dario", "Anthropic 的 CEO", "人物", False),
 ("Ilya", "OpenAI 联合创始人、前首席科学家", "人物", False),
 ("Karpathy", "知名 AI 研究者，OpenAI 创始成员", "人物", False),
 ("Boris", "Claude Code 的创造者", "人物", False),
 ("Koray", "DeepMind 首席技术官", "人物", False),
 ("Demis", "DeepMind CEO，诺贝尔化学奖得主", "人物", False),
 ("Haldane", "诺贝尔物理学奖得主", "人物", False),
 ("Hinton", "深度学习先驱，诺贝尔物理学奖得主", "人物", False),
 ("Pauli", "泡利，著名物理学家", "人物", False),
 ("Kaplan", "即 Jared Kaplan，Anthropic 联合创始人", "人物", False),
]

GLOSS = {}
for term, g, cat, ci in T:
    GLOSS[term.lower() if ci else term] = (term, g, cat, ci)

pat = "|".join(sorted((re.escape(t) for t, *_ in T), key=len, reverse=True))
RX_CS = re.compile(r"(?<![A-Za-z0-9\-])(" + pat + r")(?![A-Za-z0-9\-])")
RX_CI = re.compile(r"(?<![A-Za-z0-9\-])(" + pat + r")(?![A-Za-z0-9\-])", re.I)

def lookup(word):
    if word in GLOSS:
        return GLOSS[word]
    v = GLOSS.get(word.lower())
    if v and v[3]:
        return v
    return None

def annotate(doc, mode, known=()):
    """mode: "web" 或 "onenote"。known: 已经认识、不再注释的英文（小写）。"""
    known = {k.strip().lower() for k in known if k.strip()}

    def wrap(g, term, inner=False):
        o, c = ("〔", "〕") if inner else ("（", "）")
        if mode == "onenote":
            return f'<span style="color:#8a7f70">{o}{g}{c}</span>'
        return f'<span class="gl" data-term="{html.escape(term.lower())}">{o}{g}{c}</span>'

    parts = re.split(r"(<[^>]+>)", doc)
    seen = set()
    skip_depth = 0  # inside tags we never annotate
    SKIP = ("h1", "h2", "h3", "h4", "summary", "title", "style", "script", "template", "a", "dt", "figcaption")
    used = set()
    out = []
    # text that follows each token, ignoring tags (used to spot an existing Chinese gloss)
    nxt = [""] * len(parts)
    acc = ""
    for k in range(len(parts) - 1, -1, -1):
        nxt[k] = acc
        if not parts[k].startswith("<"):
            acc = (parts[k] + acc)[:6]
    for ti, tok in enumerate(parts):
        if tok.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", tok)
            if m:
                closing, name = m.group(1) == "/", m.group(2).lower()
                if not closing and name in ("h2", "h3", "section", "details"):
                    seen = set()
                if name in SKIP and not tok.endswith("/>"):
                    if closing:
                        skip_depth = max(0, skip_depth - 1)
                    else:
                        skip_depth += 1
            out.append(tok)
            continue
        if skip_depth or not tok.strip():
            out.append(tok)
            continue
        res, last = [], 0
        for mm in RX_CI.finditer(tok):
            word = mm.group(1)
            info = lookup(word)
            if not info:
                continue
            key = info[0].lower()
            res.append(tok[last:mm.end()])
            last = mm.end()
            before = tok[:mm.start()]
            inside_paren = before.count("（") > before.count("）")
            after = (tok[mm.end():] + nxt[ti])[:3]
            already = after.lstrip("”\"' ").startswith("（")
            if key in seen or already or key in known:
                continue
            seen.add(key)
            used.add(info[0])
            res.append(wrap(info[1], info[0], inside_paren))
        res.append(tok[last:])
        out.append("".join(res))
    return "".join(out), used



def term_groups(used, known=()):
    """按类别汇总用到的术语；中文解释相同的合并成一行。"""
    known = {k.strip().lower() for k in known if k.strip()}
    cats, by_gloss = {}, {}
    for term, g, cat, ci in T:
        if term not in used or term == "Kaplan" or term.lower() in known:
            continue
        if g in by_gloss:
            by_gloss[g]["terms"].append(term)
            continue
        row = {"terms": [term], "gloss": g}
        by_gloss[g] = row
        cats.setdefault(cat, []).append(row)
    return [(c, cats.get(c, [])) for c in ("概念", "公司与产品", "人物")]
