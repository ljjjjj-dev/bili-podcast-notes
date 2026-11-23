import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.dirname(__dirname);
const PUBLIC_DIR = path.join(__dirname, 'public');
const LOCAL_DIR = path.join(ROOT_DIR, 'local');
const SCRIPTS_DIR = path.join(ROOT_DIR, 'scripts');
const SETTINGS_FILE = path.join(LOCAL_DIR, 'settings.json');
const CHANNELS_FILE = path.join(LOCAL_DIR, 'channels.json');
const PROFILE_FILE = path.join(LOCAL_DIR, 'profile.md');
const KNOWN_TERMS_FILE = path.join(LOCAL_DIR, 'known_terms.txt');
const PORT = Number(process.env.PORT || 3457);

fs.mkdirSync(LOCAL_DIR, { recursive: true });

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
};

function readJsonSafe(file, fallback) {
  try {
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, 'utf-8'));
    }
  } catch {
    // ignore malformed json
  }
  return fallback;
}

function writeAtomic(file, content) {
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, content, 'utf-8');
  fs.renameSync(tmp, file);
}

function getSettings() {
  return readJsonSafe(SETTINGS_FILE, {
    output_dir: 'data',
    tools_dir: path.join(ROOT_DIR, 'tools'),
    home_url: '',
    browser: 'edge',
  });
}

function resolveDataDir() {
  const cfg = getSettings();
  const rawOut = cfg.output_dir || 'data';
  const dir = path.isAbsolute(rawOut) ? rawOut : path.join(ROOT_DIR, rawOut);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

function resolveToolsInfo() {
  const cfg = getSettings();
  const toolsDir = cfg.tools_dir || path.join(ROOT_DIR, 'tools');
  const py = path.join(toolsDir, 'python', 'bin', 'python');
  const toolsReady = fs.existsSync(py);
  return {
    toolsDir,
    pythonPath: toolsReady ? py : 'python3',
    toolsReady,
  };
}

function parseDurationHours(dur) {
  if (!dur) return 0;
  const parts = String(dur).split(':').map((n) => Number(n) || 0);
  while (parts.length < 3) parts.unshift(0);
  return (parts[0] * 3600 + parts[1] * 60 + parts[2]) / 3600;
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk.toString('utf-8');
      if (body.length > 5 * 1024 * 1024) reject(new Error('Request body too large'));
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res, status, data) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(data));
}

function collectOverview() {
  const dataDir = resolveDataDir();
  const episodes = [];
  const crossMap = new Map();
  const predictions = [];
  const digests = [];
  let totalHours = 0;
  let totalBeats = 0;

  const entries = fs.readdirSync(dataDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));

  for (const ent of entries) {
    if (ent.isDirectory()) {
      const folderPath = path.join(dataDir, ent.name);
      const epFile = path.join(folderPath, 'episode.json');
      if (fs.existsSync(epFile)) {
        const ep = readJsonSafe(epFile, null);
        if (!ep) continue;
        const chapters = Array.isArray(ep.chapters) ? ep.chapters : [];
        const beatCount = chapters.reduce((acc, c) => acc + (Array.isArray(c.beats) ? c.beats.length : 0), 0);
        const fcs = Array.isArray(ep.factchecks) ? ep.factchecks : [];
        const fcConfirmed = fcs.filter((f) => f.status === 'confirmed').length;
        const hasWeb = fs.existsSync(path.join(folderPath, '网页版.html'));
        const hasOneNote = fs.existsSync(path.join(folderPath, 'OneNote版.html'));
        totalHours += parseDurationHours(ep.duration);
        totalBeats += beatCount;

        episodes.push({
          folder: ent.name,
          bv: ep.bv || '',
          url: ep.url || '',
          show: ep.show || '',
          title: ep.title || ent.name,
          short_title: ep.short_title || ent.name,
          guest: ep.guest || '',
          duration: ep.duration || '',
          published: ep.published || '',
          summarized: ep.summarized || ep.published || '',
          source: ep.source || '',
          tags: Array.isArray(ep.tags) ? ep.tags : [],
          conclusion: ep.core?.conclusion || '',
          chapterCount: chapters.length,
          beatCount,
          entityCount: Array.isArray(ep.entities) ? ep.entities.length : 0,
          factcheckTotal: fcs.length,
          factcheckConfirmed: fcConfirmed,
          hasWeb,
          hasOneNote,
          noteUrl: hasWeb ? `/notes/${encodeURIComponent(ent.name)}/${encodeURIComponent('网页版.html')}` : ep.url || '',
        });

        for (const item of ep.entities || []) {
          const name = item.name;
          if (!name) continue;
          if (!crossMap.has(name)) crossMap.set(name, { name, type: item.type || '公司', views: [] });
          crossMap.get(name).views.push({
            episodeTitle: ep.short_title || ep.title || ent.name,
            episodeUrl: ep.url || '',
            noteUrl: hasWeb ? `/notes/${encodeURIComponent(ent.name)}/${encodeURIComponent('网页版.html')}` : ep.url || '',
            guest: ep.guest || '',
            published: ep.published || '',
            attitude: item.attitude || '',
            lvl: item.lvl || '中',
            times: Array.isArray(item.times) ? item.times : [],
            text: item.text || '',
          });
        }

        for (const p of ep.predictions || []) {
          predictions.push({
            claim: p.claim || '',
            t: p.t || '',
            due: p.due || '',
            status: p.status || 'pending',
            episodeTitle: ep.short_title || ep.title || ent.name,
            episodeUrl: ep.url || '',
            noteUrl: hasWeb ? `/notes/${encodeURIComponent(ent.name)}/${encodeURIComponent('网页版.html')}` : ep.url || '',
            guest: ep.guest || '',
          });
        }
      } else if (/^\d{4}-\d{2}-\d{2}$/.test(ent.name)) {
        const dayFiles = fs.readdirSync(folderPath).filter((f) => f.endsWith('.md')).sort().reverse();
        for (const df of dayFiles) {
          const content = fs.readFileSync(path.join(folderPath, df), 'utf-8');
          const firstLine = (content.split('\n').find((l) => l.startsWith('# ')) || df).replace(/^#\s+/, '').trim();
          digests.push({
            id: `${ent.name}/${df}`,
            date: ent.name,
            filename: df,
            title: firstLine,
            isChecklist: df.includes('清单'),
            content,
          });
        }
      }
    } else if (ent.isFile() && ent.name.endsWith('.md')) {
      const content = fs.readFileSync(path.join(dataDir, ent.name), 'utf-8');
      const firstLine = (content.split('\n').find((l) => l.startsWith('# ')) || ent.name).replace(/^#\s+/, '').trim();
      digests.push({
        id: ent.name,
        date: '文档规范',
        filename: ent.name,
        title: firstLine,
        isChecklist: false,
        isGuide: true,
        content,
      });
    }
  }

  episodes.sort((a, b) => (b.summarized || b.published).localeCompare(a.summarized || a.published));
  digests.sort((a, b) => {
    if (a.isGuide && !b.isGuide) return 1;
    if (!a.isGuide && b.isGuide) return -1;
    return b.id.localeCompare(a.id);
  });

  const crossViews = [...crossMap.values()].sort((a, b) => b.views.length - a.views.length || a.name.localeCompare(b.name));
  const channels = readJsonSafe(CHANNELS_FILE, []);
  const tools = resolveToolsInfo();

  return {
    stats: {
      episodeCount: episodes.length,
      totalHours: Number(totalHours.toFixed(1)),
      totalBeats,
      predictionCount: predictions.length,
      channelCount: channels.length,
      digestCount: digests.filter((d) => !d.isGuide).length,
      toolsReady: tools.toolsReady,
      toolsDir: tools.toolsDir,
      dataDir,
    },
    episodes,
    crossViews,
    predictions,
    digests,
  };
}

function isSafeChild(baseDir, relPath) {
  const resolved = path.resolve(baseDir, relPath);
  return resolved === baseDir || resolved.startsWith(baseDir + path.sep) ? resolved : null;
}

const server = http.createServer(async (req, res) => {
  const urlPath = decodeURIComponent((req.url || '/').split('?')[0]);

  try {
    if (urlPath === '/api/overview' && req.method === 'GET') return sendJson(res, 200, collectOverview());

    if (urlPath === '/api/channels') {
      if (req.method === 'GET') return sendJson(res, 200, readJsonSafe(CHANNELS_FILE, []));
      if (req.method === 'POST') {
        const body = await parseBody(req);
        if (!Array.isArray(body)) return sendJson(res, 400, { error: 'channels 必须是数组' });
        const cleaned = body
          .map((c) => ({
            uid: String(c?.uid || '').replace(/\D/g, ''),
            name: String(c?.name || '').trim(),
            category: String(c?.category || 'AI科技/深度访谈').trim(),
          }))
          .filter((c) => c.uid && c.name);
        writeAtomic(CHANNELS_FILE, JSON.stringify(cleaned, null, 2) + '\n');
        return sendJson(res, 200, { ok: true, channels: cleaned });
      }
    }

    if (urlPath === '/api/settings') {
      if (req.method === 'GET') {
        const settings = getSettings();
        const profile = fs.existsSync(PROFILE_FILE) ? fs.readFileSync(PROFILE_FILE, 'utf-8') : '';
        const knownTerms = fs.existsSync(KNOWN_TERMS_FILE) ? fs.readFileSync(KNOWN_TERMS_FILE, 'utf-8') : '';
        return sendJson(res, 200, { settings, profile, knownTerms, tools: resolveToolsInfo() });
      }
      if (req.method === 'POST') {
        const body = await parseBody(req);
        if (body.settings && typeof body.settings === 'object') {
          const cur = getSettings();
          const next = {
            ...cur,
            browser: String(body.settings.browser || cur.browser || 'edge').trim(),
            tools_dir: String(body.settings.tools_dir || cur.tools_dir || '').trim(),
            output_dir: String(body.settings.output_dir || cur.output_dir || 'data').trim(),
          };
          writeAtomic(SETTINGS_FILE, JSON.stringify(next, null, 1) + '\n');
        }
        if (typeof body.profile === 'string') writeAtomic(PROFILE_FILE, body.profile);
        if (typeof body.knownTerms === 'string') writeAtomic(KNOWN_TERMS_FILE, body.knownTerms);
        return sendJson(res, 200, { ok: true, tools: resolveToolsInfo() });
      }
    }

    if (urlPath === '/api/clip' && req.method === 'POST') {
      const body = await parseBody(req);
      const folder = String(body.folder || '');
      if (!folder || folder.includes('/') || folder.includes('\\') || folder.includes('..')) {
        return sendJson(res, 400, { error: '无效的剧集文件夹名' });
      }
      const targetDir = isSafeChild(resolveDataDir(), folder);
      if (!targetDir || !fs.existsSync(path.join(targetDir, 'OneNote版.html'))) {
        return sendJson(res, 404, { error: '未找到 OneNote版.html' });
      }
      const { pythonPath } = resolveToolsInfo();
      const { stdout } = await execFileAsync(pythonPath, [path.join(SCRIPTS_DIR, 'clip.py'), targetDir], {
        cwd: ROOT_DIR,
        timeout: 15000,
      });
      return sendJson(res, 200, { ok: true, message: (stdout || '').trim() });
    }

    if (urlPath === '/api/rebuild-home' && req.method === 'POST') {
      const { pythonPath } = resolveToolsInfo();
      const { stdout } = await execFileAsync(pythonPath, [path.join(SCRIPTS_DIR, 'home.py')], {
        cwd: ROOT_DIR,
        timeout: 15000,
      });
      return sendJson(res, 200, { ok: true, message: (stdout || '').trim() });
    }

    if (urlPath === '/api/discover' && req.method === 'POST') {
      const tools = resolveToolsInfo();
      if (!tools.toolsReady) return sendJson(res, 400, { error: `未找到本地运行环境：${tools.toolsDir}` });
      const { stdout } = await execFileAsync(
        tools.pythonPath,
        [path.join(SCRIPTS_DIR, 'discover.py'), '--per-channel', '4'],
        { cwd: ROOT_DIR, timeout: 90000 }
      );
      return sendJson(res, 200, { ok: true, items: JSON.parse(stdout || '[]') });
    }

    if (urlPath === '/api/open-folder' && req.method === 'POST') {
      const body = await parseBody(req);
      const dataDir = resolveDataDir();
      const sub = String(body.sub || '');
      const target = sub ? isSafeChild(dataDir, sub) : dataDir;
      if (!target || !fs.existsSync(target)) return sendJson(res, 404, { error: '目录不存在' });
      await execFileAsync('open', [target]);
      return sendJson(res, 200, { ok: true });
    }

    if (urlPath === '/首页.html' || urlPath === '/notes/首页.html') {
      res.statusCode = 302;
      res.setHeader('Location', '/');
      return res.end();
    }

    if (urlPath.startsWith('/notes/')) {
      const rel = urlPath.slice('/notes/'.length);
      const safeFile = isSafeChild(resolveDataDir(), rel);
      if (safeFile && fs.existsSync(safeFile) && fs.statSync(safeFile).isFile()) {
        const ext = path.extname(safeFile);
        res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
        res.statusCode = 200;
        return fs.createReadStream(safeFile).pipe(res);
      }
      res.statusCode = 404;
      return res.end('Not found');
    }

    const relPublic = urlPath === '/' ? 'index.html' : urlPath.replace(/^\/+/, '');
    let filePath = isSafeChild(PUBLIC_DIR, relPublic);
    if (!filePath || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(PUBLIC_DIR, 'index.html');
    }
    const ext = path.extname(filePath);
    res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
    res.statusCode = 200;
    return fs.createReadStream(filePath).pipe(res);
  } catch (err) {
    return sendJson(res, 500, { error: err?.message || 'Internal Server Error' });
  }
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`\n  ✦ B站播客总结已启动: http://127.0.0.1:${PORT}`);
  console.log(`  ✦ 数据目录: ${resolveDataDir()}\n`);
});
