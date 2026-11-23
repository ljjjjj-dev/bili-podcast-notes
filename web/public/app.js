const state = {
  tab: 'library',
  overview: null,
  channels: [],
  settingsBundle: null,
  search: '',
  activeTag: '',
  selectedDigestId: '',
  predFilter: 'all',
  discovered: [],
  discovering: false,
  dark: localStorage.getItem('bili-theme') === 'dark',
};

if (state.dark) document.documentElement.classList.add('dark');

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function toast(msg) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove('show'), 2600);
}

async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `请求失败 (${res.status})`);
  return data;
}

function renderMd(md) {
  const lines = String(md || '').replace(/\r\n/g, '\n').split('\n');
  let html = '';
  let inUl = false;
  let inOl = false;
  let inCode = false;
  let tableRows = [];

  const flushLists = () => {
    if (inUl) { html += '</ul>'; inUl = false; }
    if (inOl) { html += '</ol>'; inOl = false; }
  };

  const inline = (txt) => {
    let out = esc(txt);
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+|\.[^)]+)\)/g, (_, label, href) => {
      if (href.startsWith('http')) {
        return `<a href="${href}" target="_blank" rel="noopener">${label}</a>`;
      }
      return `<code>${label}</code>`;
    });
    out = out.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    out = out.replace(/\b(BV[0-9A-Za-z]{10})\b/g, '<code>$1</code>');
    return out;
  };

  const flushTable = () => {
    if (!tableRows.length) return;
    const rows = tableRows.filter((r) => !/^\|[\s:-|]+\|$/.test(r.trim()));
    if (rows.length) {
      html += '<table>';
      rows.forEach((r, idx) => {
        const cells = r.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
        const tag = idx === 0 ? 'th' : 'td';
        html += '<tr>' + cells.map((c) => `<${tag}>${inline(c)}</${tag}>`).join('') + '</tr>';
      });
      html += '</table>';
    }
    tableRows = [];
  };

  for (const raw of lines) {
    const line = raw;
    if (line.trim().startsWith('```')) {
      flushLists();
      flushTable();
      if (!inCode) { html += '<pre><code>'; inCode = true; }
      else { html += '</code></pre>'; inCode = false; }
      continue;
    }
    if (inCode) {
      html += esc(line) + '\n';
      continue;
    }
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      flushLists();
      tableRows.push(line);
      continue;
    } else {
      flushTable();
    }

    if (!line.trim()) {
      flushLists();
      continue;
    }
    if (/^---+$/.test(line.trim())) {
      flushLists();
      html += '<hr />';
      continue;
    }
    const h = line.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      flushLists();
      const lvl = h[1].length;
      html += `<h${lvl}>${inline(h[2])}</h${lvl}>`;
      continue;
    }
    if (line.startsWith('> ')) {
      flushLists();
      html += `<blockquote>${inline(line.slice(2))}</blockquote>`;
      continue;
    }
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    if (ul) {
      if (inOl) { html += '</ol>'; inOl = false; }
      if (!inUl) { html += '<ul>'; inUl = true; }
      html += `<li>${inline(ul[1])}</li>`;
      continue;
    }
    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ol) {
      if (inUl) { html += '</ul>'; inUl = false; }
      if (!inOl) { html += '<ol>'; inOl = true; }
      html += `<li>${inline(ol[1])}</li>`;
      continue;
    }
    flushLists();
    html += `<p>${inline(line)}</p>`;
  }
  flushLists();
  flushTable();
  if (inCode) html += '</code></pre>';
  return html;
}

async function loadAll() {
  const [overview, channels, settingsBundle] = await Promise.all([
    api('/api/overview'),
    api('/api/channels'),
    api('/api/settings'),
  ]);
  state.overview = overview;
  state.channels = channels;
  state.settingsBundle = settingsBundle;
  if (!state.selectedDigestId && overview.digests.length) {
    state.selectedDigestId = overview.digests[0].id;
  }
  render();
}

function navIcon(name) {
  const icons = {
    library: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    digests: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>',
    insights: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20V10M18 20V4M6 20v-4"/></svg>',
    channels: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-6 8-6s8 2 8 6"/></svg>',
    settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.26.6.77 1.02 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
  };
  return icons[name] || '';
}

function renderLibrary(ov) {
  const tags = [...new Set(ov.episodes.flatMap((e) => e.tags))];
  const q = state.search.trim().toLowerCase();
  const filtered = ov.episodes.filter((ep) => {
    const tagOk = !state.activeTag || ep.tags.includes(state.activeTag);
    const hay = `${ep.title} ${ep.guest} ${ep.show} ${ep.conclusion} ${ep.tags.join(' ')} ${ep.bv}`.toLowerCase();
    const qOk = !q || q.split(/\s+/).every((w) => hay.includes(w));
    return tagOk && qOk;
  });

  return `
    <div class="kpi-grid">
      <div class="card"><div class="kpi-label">已精读长播客</div><div class="kpi-value tabular">${ov.stats.episodeCount}</div><div class="kpi-foot">带时间戳对齐与事实核查</div></div>
      <div class="card"><div class="kpi-label">累计浓缩时长</div><div class="kpi-value tabular">${ov.stats.totalHours}h</div><div class="kpi-foot">共提炼 ${ov.stats.totalBeats} 个核心要点</div></div>
      <div class="card"><div class="kpi-label">每日精选清单</div><div class="kpi-value tabular">${ov.stats.digestCount}</div><div class="kpi-foot">S 级嘉宾点菜与简报</div></div>
      <div class="card"><div class="kpi-label">订阅 S 级 UP 主</div><div class="kpi-value tabular">${ov.stats.channelCount}</div><div class="kpi-foot">${ov.stats.toolsReady ? '本地 Whisper 环境就绪' : '需检查本地 tools 路径'}</div></div>
    </div>

    <div class="card toolbar">
      <input class="input" id="search-input" type="search" value="${esc(state.search)}" placeholder="搜索标题、嘉宾、节目、话题或 BV 号…" />
      <div class="chips">
        <button class="chip ${!state.activeTag ? 'active' : ''}" data-tag="">全部 (${ov.episodes.length})</button>
        ${tags.map((t) => `<button class="chip ${state.activeTag === t ? 'active' : ''}" data-tag="${esc(t)}">${esc(t)}</button>`).join('')}
      </div>
    </div>

    <div class="ep-list">
      ${filtered.length ? filtered.map((ep) => `
        <article class="ep-card">
          <div class="ep-meta">
            <span class="ep-show">${esc(ep.show || 'B站播客')}</span>
            <span>播出：${esc(ep.published)}</span>
            <span>整理：${esc(ep.summarized)}</span>
            <span class="tabular">${esc(ep.duration)}</span>
            <span>${esc(ep.bv)}</span>
          </div>
          <h3 class="ep-title"><a href="${esc(ep.noteUrl)}" target="_blank" rel="noopener">${esc(ep.title)}</a></h3>
          <p class="ep-concl">${esc(ep.conclusion)}</p>
          <div class="ep-stats tabular">
            <span>${ep.chapterCount} 章 · ${ep.beatCount} 段</span>
            <span>${ep.entityCount} 个观点对象</span>
            ${ep.factcheckTotal ? `<span>事实核查 ${ep.factcheckConfirmed}/${ep.factcheckTotal} 属实</span>` : ''}
            <span>目录：${esc(ep.folder)}</span>
          </div>
          <div class="ep-tags">${ep.tags.map((t) => `<span class="tag">${esc(t)}</span>`).join('')}</div>
          <div class="ep-actions">
            ${ep.hasWeb ? `<a class="btn btn-primary" href="${esc(ep.noteUrl)}" target="_blank" rel="noopener">打开精读网页版</a>` : ''}
            ${ep.hasOneNote ? `<button class="btn" data-clip="${esc(ep.folder)}">复制到 OneNote</button>` : ''}
            <a class="btn" href="${esc(ep.url)}" target="_blank" rel="noopener">B站原视频</a>
            <button class="btn" data-open-dir="${esc(ep.folder)}">访达显示</button>
          </div>
        </article>
      `).join('') : '<div class="card"><p class="ep-concl">没有匹配的精读笔记，换个关键词或标签试试。</p></div>'}
    </div>
  `;
}

function renderDigests(ov) {
  const cur = ov.digests.find((d) => d.id === state.selectedDigestId) || ov.digests[0];
  return `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
        <div>
          <h3 style="font-size:15px;font-weight:700">实时扫描订阅 UP 主（最新未精读长播客）</h3>
          <p class="page-sub" style="margin-top:2px">从 ${ov.stats.channelCount} 个订阅频道抓取 ≥20 分钟长视频，自动排除已生成精读的期数。</p>
        </div>
        <button class="btn btn-primary" id="btn-discover" ${state.discovering ? 'disabled' : ''}>
          ${state.discovering ? '正在拉取 B站最新视频…' : '一键扫描 B站最新候选'}
        </button>
      </div>
      ${state.discovered.length ? `
        <div class="discover-grid">
          ${state.discovered.map((item) => `
            <div class="discover-card">
              <div class="ep-meta"><span class="ep-show">${esc(item.uploader)}</span><span>${esc(item.date)}</span><span class="tabular">${esc(item.duration)}</span></div>
              <div style="font-size:14px;font-weight:600;line-height:1.4">${esc(item.title)}</div>
              <div style="font-size:12px;color:var(--text-tertiary)">${esc(item.bv)} · ${esc(item.category)}</div>
              <div class="ep-actions">
                <a class="btn" href="${esc(item.url)}" target="_blank" rel="noopener">B站查看</a>
                <button class="btn btn-primary" data-copy-prompt="帮我总结 ${esc(item.bv)}">复制精读指令</button>
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}
    </div>

    <div class="split-grid">
      <div class="card digest-nav">
        <div class="kpi-label" style="padding:2px 6px 8px">已归档精选清单与规范</div>
        ${ov.digests.map((d) => `
          <button class="digest-item ${cur && cur.id === d.id ? 'active' : ''}" data-digest="${esc(d.id)}">
            <div class="digest-item-date">${esc(d.date)}${d.isChecklist ? ' · 点菜清单' : ''}</div>
            <div class="digest-item-title">${esc(d.title)}</div>
          </button>
        `).join('')}
      </div>
      <div class="card md-body">
        ${cur ? renderMd(cur.content) : '<p>暂无每日精选文档</p>'}
      </div>
    </div>
  `;
}

function renderInsights(ov) {
  const predLabels = { pending: '待检验', right: '说对了', wrong: '说错了', mixed: '部分应验' };
  const predFiltered = ov.predictions.filter((p) => state.predFilter === 'all' || p.status === state.predFilter);

  return `
    <div class="card">
      <h3 style="font-size:16px;font-weight:700;margin-bottom:4px">跨期观点对照（按公司 / 行业）</h3>
      <p class="page-sub" style="margin-bottom:14px">汇总不同嘉宾对同一家公司或技术路线的看法及依据强弱。</p>
      <div class="two-col">
        ${ov.crossViews.map((g) => `
          <div class="discover-card">
            <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
              <strong style="font-size:15px">${esc(g.name)}</strong>
              <span class="badge badge-blue">${esc(g.type)} · ${g.views.length} 条观点</span>
            </div>
            ${g.views.map((v) => {
              const cls = v.lvl === '强' ? 'badge-strong' : v.lvl === '中' ? 'badge-mid' : 'badge-weak';
              return `
                <div style="padding-top:8px;border-top:0.5px solid var(--hairline);font-size:13px">
                  <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:4px">
                    <span class="badge ${cls}">依据:${esc(v.lvl)}</span>
                    <span style="font-weight:600">${esc(v.attitude)}</span>
                    <a href="${esc(v.noteUrl)}" target="_blank" style="color:var(--blue);font-size:12px">《${esc(v.episodeTitle)}》</a>
                  </div>
                  <p style="color:var(--text-secondary)">${esc(v.text)}</p>
                </div>
              `;
            }).join('')}
          </div>
        `).join('')}
      </div>
    </div>

    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px">
        <div>
          <h3 style="font-size:16px;font-weight:700">嘉宾预测追踪</h3>
          <p class="page-sub">记录播客中带明确时间线或可检验标准的判断，方便日后复盘。</p>
        </div>
        <div class="chips">
          ${[['all', '全部'], ['pending', '待检验'], ['right', '说对了'], ['mixed', '部分应验'], ['wrong', '说错了']].map(([k, lbl]) => `
            <button class="chip ${state.predFilter === k ? 'active' : ''}" data-pred="${k}">${lbl}</button>
          `).join('')}
        </div>
      </div>
      ${predFiltered.map((p) => `
        <div class="pred-row">
          <div>
            <div style="font-size:14px;font-weight:500">${esc(p.claim)}</div>
            <div style="font-size:12px;color:var(--text-tertiary);margin-top:3px">
              <a href="${esc(p.noteUrl)}" target="_blank" style="color:var(--blue)">${esc(p.episodeTitle)}</a> · ${esc(p.guest)} · 位置 ${esc(p.t)}
            </div>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-shrink:0">
            <span class="badge badge-blue">到期：${esc(p.due)}</span>
            <span class="badge badge-mid">${predLabels[p.status] || p.status}</span>
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function renderChannels() {
  return `
    <div class="card">
      <h3 style="font-size:16px;font-weight:700;margin-bottom:4px">新增 B站订阅 UP 主</h3>
      <p class="page-sub" style="margin-bottom:14px">支持直接粘贴 <code>https://space.bilibili.com/数字UID</code> 或纯数字 UID，保存后实时生效。</p>
      <form id="add-channel-form" class="form-row">
        <div><label class="field-label">B站空间链接或数字 UID</label><input class="input" id="ch-uid" placeholder="如 14145636 或 space.bilibili.com/14145636" required /></div>
        <div><label class="field-label">UP 主名称</label><input class="input" id="ch-name" placeholder="如 WhynotTV" required /></div>
        <div><label class="field-label">类别标签</label><input class="input" id="ch-cat" value="AI科技/深度访谈" /></div>
        <button class="btn btn-primary" type="submit">添加订阅</button>
      </form>
    </div>

    <div class="card">
      <h3 style="font-size:16px;font-weight:700;margin-bottom:10px">当前订阅内容池（${state.channels.length} 个频道）</h3>
      ${state.channels.map((c, idx) => `
        <div class="channel-item">
          <div>
            <div style="font-size:14.5px;font-weight:600">${esc(c.name)} <span class="badge badge-blue" style="margin-left:6px">${esc(c.category)}</span></div>
            <div style="font-size:12px;color:var(--text-tertiary);margin-top:2px">UID: ${esc(c.uid)} · <a href="https://space.bilibili.com/${esc(c.uid)}" target="_blank" rel="noopener" style="color:var(--blue)">打开 B站主页 ↗</a></div>
          </div>
          <button class="btn btn-danger" data-del-ch="${idx}">移除</button>
        </div>
      `).join('')}
    </div>
  `;
}

function renderSettings() {
  const sb = state.settingsBundle;
  if (!sb) return '';
  return `
    <div class="card" style="display:flex;flex-direction:column;gap:14px">
      <div>
        <h3 style="font-size:16px;font-weight:700">运行环境与读取配置</h3>
        <p class="page-sub">大体积 Python / MLX Whisper 运行时保留在本地，不占同步盘空间。</p>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div>
          <label class="field-label">读取 B站登录态的浏览器</label>
          <select class="select" id="set-browser">
            ${['edge', 'chrome', 'safari', 'firefox'].map((b) => `<option value="${b}" ${sb.settings.browser === b ? 'selected' : ''}>${b}</option>`).join('')}
          </select>
        </div>
        <div>
          <label class="field-label">本地 Python / Whisper 工具目录 (${sb.tools.toolsReady ? '已就绪' : '未检测到'})</label>
          <input class="input" id="set-tools" value="${esc(sb.settings.tools_dir || '')}" />
        </div>
      </div>
      <div>
        <label class="field-label">个人阅读偏好与关注方向（local/profile.md）</label>
        <textarea class="textarea" id="set-profile">${esc(sb.profile)}</textarea>
      </div>
      <div>
        <label class="field-label">已认识英文术语表（local/known_terms.txt，每行一个，生成笔记时自动跳过注释）</label>
        <textarea class="textarea" id="set-terms" style="min-height:100px">${esc(sb.knownTerms)}</textarea>
      </div>
      <div><button class="btn btn-primary" id="btn-save-settings">保存全部设置</button></div>
    </div>
  `;
}

function render() {
  const ov = state.overview;
  if (!ov) return;
  const titles = {
    library: ['精读知识库', '全部已总结的 B站长播客与知识库入口'],
    digests: ['每日精选清单', '实时扫描 B站 7 频道最新候选与每日清单阅读'],
    insights: ['跨期观点 & 预测', '不同嘉宾的观点交叉对照与预测追踪'],
    channels: ['订阅 UP 主池', '管理每日清单扫描的 B站高质量频道'],
    settings: ['偏好与环境设置', '配置阅读画像、已认识词表与本地 Whisper 工具路径'],
  };
  const [title, sub] = titles[state.tab];

  document.getElementById('app').innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand">
          <img class="brand-logo" src="/icon.png" alt="" />
          <div><div class="brand-title">B站播客总结</div><div class="brand-sub">本地知识库工作台</div></div>
        </div>
        <div class="nav-section-label">导航</div>
        <nav class="nav-list">
          <button class="nav-btn ${state.tab === 'library' ? 'active' : ''}" data-tab="library"><span class="nav-left">${navIcon('library')}精读知识库</span><span class="nav-badge tabular">${ov.stats.episodeCount}</span></button>
          <button class="nav-btn ${state.tab === 'digests' ? 'active' : ''}" data-tab="digests"><span class="nav-left">${navIcon('digests')}点菜与清单</span><span class="nav-badge tabular">${ov.stats.digestCount}</span></button>
          <button class="nav-btn ${state.tab === 'insights' ? 'active' : ''}" data-tab="insights"><span class="nav-left">${navIcon('insights')}观点与预测</span><span class="nav-badge tabular">${ov.stats.predictionCount}</span></button>
          <button class="nav-btn ${state.tab === 'channels' ? 'active' : ''}" data-tab="channels"><span class="nav-left">${navIcon('channels')}订阅 UP 主</span><span class="nav-badge tabular">${ov.stats.channelCount}</span></button>
          <button class="nav-btn ${state.tab === 'settings' ? 'active' : ''}" data-tab="settings"><span class="nav-left">${navIcon('settings')}偏好与设置</span></button>
        </nav>
        <div class="sidebar-footer">
          <div class="sync-status"><span class="sync-dot ${ov.stats.toolsReady ? '' : 'warn'}"></span><span>${ov.stats.toolsReady ? '本地转写环境在线' : 'tools 目录未找到'}</span></div>
        </div>
      </aside>
      <div class="main-wrap">
        <header class="topbar">
          <div class="topbar-inner">
            <div class="page-title-group"><h1 class="page-title">${title}</h1><span class="page-sub">${sub}</span></div>
            <div class="topbar-actions">
              <button class="btn" id="btn-rebuild">重建静态首页</button>
              <button class="btn" id="btn-open-root">在访达打开</button>
              <button class="btn" id="btn-theme">${state.dark ? '浅色外观' : '深色外观'}</button>
            </div>
          </div>
        </header>
        <main class="content">
          ${state.tab === 'library' ? renderLibrary(ov) : ''}
          ${state.tab === 'digests' ? renderDigests(ov) : ''}
          ${state.tab === 'insights' ? renderInsights(ov) : ''}
          ${state.tab === 'channels' ? renderChannels() : ''}
          ${state.tab === 'settings' ? renderSettings() : ''}
        </main>
      </div>
    </div>
  `;

  bindEvents();
}

function bindEvents() {
  document.querySelectorAll('[data-tab]').forEach((b) => {
    b.onclick = () => { state.tab = b.dataset.tab; render(); };
  });

  document.getElementById('btn-theme').onclick = () => {
    state.dark = !state.dark;
    document.documentElement.classList.toggle('dark', state.dark);
    localStorage.setItem('bili-theme', state.dark ? 'dark' : 'light');
    render();
  };

  document.getElementById('btn-open-root').onclick = async () => {
    await api('/api/open-folder', { method: 'POST', body: JSON.stringify({}) });
  };

  document.getElementById('btn-rebuild').onclick = async () => {
    const r = await api('/api/rebuild-home', { method: 'POST' });
    await loadAll();
    toast(`已更新静态首页（${r.message}）`);
  };

  const si = document.getElementById('search-input');
  if (si) {
    si.oninput = (e) => {
      state.search = e.target.value;
      const pos = si.selectionStart;
      render();
      const nsi = document.getElementById('search-input');
      if (nsi) { nsi.focus(); nsi.setSelectionRange(pos, pos); }
    };
  }

  document.querySelectorAll('[data-tag]').forEach((b) => {
    b.onclick = () => { state.activeTag = b.dataset.tag; render(); };
  });

  document.querySelectorAll('[data-clip]').forEach((b) => {
    b.onclick = async () => {
      const r = await api('/api/clip', { method: 'POST', body: JSON.stringify({ folder: b.dataset.clip }) });
      toast(r.message || '已写入剪贴板，去 OneNote 按 Cmd+V 粘贴');
    };
  });

  document.querySelectorAll('[data-open-dir]').forEach((b) => {
    b.onclick = async () => {
      await api('/api/open-folder', { method: 'POST', body: JSON.stringify({ sub: b.dataset.openDir }) });
    };
  });

  document.querySelectorAll('[data-digest]').forEach((b) => {
    b.onclick = () => { state.selectedDigestId = b.dataset.digest; render(); };
  });

  document.querySelectorAll('[data-pred]').forEach((b) => {
    b.onclick = () => { state.predFilter = b.dataset.pred; render(); };
  });

  const btnDisc = document.getElementById('btn-discover');
  if (btnDisc) {
    btnDisc.onclick = async () => {
      state.discovering = true;
      render();
      try {
        const r = await api('/api/discover', { method: 'POST' });
        state.discovered = r.items || [];
        toast(`扫描完成，发现 ${state.discovered.length} 条候选长播客`);
      } catch (err) {
        toast(`扫描失败：${err.message}`);
      } finally {
        state.discovering = false;
        render();
      }
    };
  }

  document.querySelectorAll('[data-copy-prompt]').forEach((b) => {
    b.onclick = async () => {
      await navigator.clipboard.writeText(b.dataset.copyPrompt);
      toast(`已复制「${b.dataset.copyPrompt}」，发给 Antigravity 即可开始精读`);
    };
  });

  const chForm = document.getElementById('add-channel-form');
  if (chForm) {
    chForm.onsubmit = async (e) => {
      e.preventDefault();
      const rawUid = document.getElementById('ch-uid').value;
      const uidMatch = rawUid.match(/(\d{4,})/);
      const uid = uidMatch ? uidMatch[1] : '';
      const name = document.getElementById('ch-name').value.trim();
      const category = document.getElementById('ch-cat').value.trim() || 'AI科技/深度访谈';
      if (!uid || !name) return toast('请填写有效的数字 UID 和 UP 主名称');
      const next = [...state.channels.filter((c) => c.uid !== uid), { uid, name, category }];
      const r = await api('/api/channels', { method: 'POST', body: JSON.stringify(next) });
      state.channels = r.channels;
      await loadAll();
      toast(`已添加订阅：${name}`);
    };
  }

  document.querySelectorAll('[data-del-ch]').forEach((b) => {
    b.onclick = async () => {
      const idx = Number(b.dataset.delCh);
      const next = state.channels.filter((_, i) => i !== idx);
      const r = await api('/api/channels', { method: 'POST', body: JSON.stringify(next) });
      state.channels = r.channels;
      await loadAll();
      toast('已移除该订阅频道');
    };
  });

  const btnSave = document.getElementById('btn-save-settings');
  if (btnSave) {
    btnSave.onclick = async () => {
      const payload = {
        settings: {
          browser: document.getElementById('set-browser').value,
          tools_dir: document.getElementById('set-tools').value.trim(),
        },
        profile: document.getElementById('set-profile').value,
        knownTerms: document.getElementById('set-terms').value,
      };
      await api('/api/settings', { method: 'POST', body: JSON.stringify(payload) });
      await loadAll();
      toast('设置已保存');
    };
  }
}

loadAll().catch((err) => {
  document.getElementById('app').innerHTML = `<div style="padding:40px;font-family:sans-serif"><h2>加载失败</h2><p>${esc(err.message)}</p></div>`;
});
