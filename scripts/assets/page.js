(function(){
  const BV='__BV__';
  const store={
    get(k,d){try{const v=localStorage.getItem(k);return v?JSON.parse(v):d;}catch(e){return d;}},
    set(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  };

  // ---- theme toggle (sync with console localStorage) ----
  const rootEl=document.documentElement;
  const savedTheme=(()=>{try{return localStorage.getItem('bili-podcast-theme')||localStorage.getItem('theme')||'';}catch(e){return '';}})();
  if(savedTheme==='dark'||savedTheme==='light') rootEl.dataset.theme=savedTheme;
  const tbtn=document.getElementById('theme-toggle');
  if(tbtn){
    const isDark=()=>rootEl.dataset.theme==='dark'||(!rootEl.dataset.theme&&window.matchMedia('(prefers-color-scheme: dark)').matches);
    const syncBtn=()=>{tbtn.textContent=isDark()?'☀ 浅色':'☾ 深色';};
    tbtn.addEventListener('click',()=>{
      const next=isDark()?'light':'dark';
      rootEl.dataset.theme=next;
      try{localStorage.setItem('bili-podcast-theme',next);localStorage.setItem('theme',next);}catch(e){}
      syncBtn();
    });
    syncBtn();
  }

  // ---- table of contents highlight ----
  const tops=[...document.querySelectorAll('.toc > a[data-sec]')];
  const secs=[...document.querySelectorAll('section.sec')];
  if('IntersectionObserver' in window){
    const io=new IntersectionObserver(es=>{es.forEach(en=>{ if(en.isIntersecting){ const id=en.target.id;
      tops.forEach(a=>{const on=a.dataset.sec===id; a.classList.toggle('on',on); on?a.setAttribute('aria-current','location'):a.removeAttribute('aria-current');});
      const on=tops.find(a=>a.dataset.sec===id); if(on&&window.innerWidth<=960){ on.scrollIntoView({block:'nearest',inline:'center'}); }
    }});},{rootMargin:'-25% 0px -65% 0px'});
    secs.forEach(s=>io.observe(s));
  }
  document.querySelectorAll('a[href^="#ch-"]').forEach(a=>a.addEventListener('click',()=>{
    const d=document.querySelector(a.getAttribute('href'));
    if(!d) return;
    d.open=true;
    d.classList.remove('is-flash');
    void d.offsetWidth;
    d.classList.add('is-flash');
    setTimeout(()=>d.classList.remove('is-flash'),1400);
  }));

  // ---- chapters: expand / collapse / read progress / search ----
  const chs=[...document.querySelectorAll('details.chapter')];
  const unreadBtn=document.getElementById('tl-unread');
  const searchInput=document.getElementById('page-search');
  const searchCount=document.getElementById('search-count');
  const tlEmpty=document.getElementById('tl-empty');
  const tlEmptyMsg=document.getElementById('tl-empty-msg');
  const tlReset=document.getElementById('tl-reset');
  let hideRead=false;

  document.getElementById('tl-open').onclick=()=>chs.forEach(d=>{if(!d.hidden) d.open=true;});
  document.getElementById('tl-close').onclick=()=>chs.forEach(d=>d.open=false);

  const READ_KEY='read:'+BV;
  let read=new Set(store.get(READ_KEY,[]));

  function refreshTimeline(){
    const q=(searchInput?searchInput.value:'').trim().toLowerCase();
    let visibleCh=0, matchBeats=0;
    chs.forEach(d=>{
      const isRead=read.has(d.dataset.ch);
      const beats=[...d.querySelectorAll('.beat')];
      let chHasMatch=false;
      if(!q){
        beats.forEach(b=>b.hidden=false);
        chHasMatch=true;
      }else{
        const titleHit=d.querySelector('.ch-title').textContent.toLowerCase().includes(q);
        beats.forEach(b=>{
          const hit=titleHit||b.textContent.toLowerCase().includes(q);
          b.hidden=!hit;
          if(hit){chHasMatch=true; matchBeats++;}
        });
      }
      const hide=(hideRead&&isRead)||!chHasMatch;
      d.hidden=hide;
      if(!hide){
        visibleCh++;
        if(q) d.open=true;
      }
    });
    if(searchCount) searchCount.textContent=q?(matchBeats+' 条匹配'):'';
    if(tlEmpty){
      tlEmpty.hidden=visibleCh>0;
      if(visibleCh===0&&tlEmptyMsg){
        tlEmptyMsg.textContent=q?('没有找到包含「'+searchInput.value.trim()+'」的要点。'):'全部章节都已标记为已读。';
      }
    }
  }

  function paintRead(){
    chs.forEach(d=>{const r=read.has(d.dataset.ch); d.classList.toggle('is-read',r); const cb=d.querySelector('.read input'); if(cb) cb.checked=r;});
    document.querySelectorAll('.seg[data-ch], .toc-ch[data-ch]').forEach(el=>el.classList.toggle('is-read',read.has(el.dataset.ch)));
    const txt='已读 '+read.size+' / '+chs.length+' 章';
    document.getElementById('read-count').textContent=txt;
    document.getElementById('toc-progress').textContent=txt;
    const fp=document.getElementById('footer-progress'); if(fp) fp.textContent='本期阅读进度：'+txt;
    refreshTimeline();
  }

  unreadBtn.onclick=()=>{
    hideRead=!hideRead;
    unreadBtn.classList.toggle('on',hideRead);
    unreadBtn.setAttribute('aria-pressed',String(hideRead));
    unreadBtn.textContent=hideRead?'显示全部':'只看未读';
    refreshTimeline();
  };
  if(searchInput) searchInput.addEventListener('input',refreshTimeline);
  if(tlReset) tlReset.onclick=()=>{
    hideRead=false;
    unreadBtn.classList.remove('on');
    unreadBtn.setAttribute('aria-pressed','false');
    unreadBtn.textContent='只看未读';
    if(searchInput) searchInput.value='';
    refreshTimeline();
  };

  // Prevent clicking checkbox or timestamps inside <summary> from toggling <details>
  document.querySelectorAll('.chapter > summary .read, .chapter > summary .tc').forEach(el=>el.addEventListener('click',ev=>ev.stopPropagation()));
  document.querySelectorAll('.read input').forEach(cb=>cb.addEventListener('change',()=>{
    cb.checked?read.add(cb.dataset.ch):read.delete(cb.dataset.ch); store.set(READ_KEY,[...read]); paintRead();
  }));
  paintRead();

  // Keyboard shortcut `/` to focus timeline search
  document.addEventListener('keydown',ev=>{
    if(ev.key==='/'&&!ev.metaKey&&!ev.ctrlKey&&!ev.altKey&&!/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)){
      if(searchInput){ev.preventDefault(); searchInput.focus(); searchInput.scrollIntoView({block:'center',behavior:'smooth'});}
    }
  });

  // ---- entity filters ----
  const f={type:'',lvl:''};
  const cards=[...document.querySelectorAll('.ent')];
  const count=document.getElementById('fcount');
  const entEmpty=document.getElementById('ent-empty');
  const entReset=document.getElementById('ent-reset');
  function apply(){
    let n=0;
    cards.forEach(c=>{const ok=(!f.type||c.dataset.type===f.type)&&(!f.lvl||c.dataset.lvl===f.lvl); c.hidden=!ok; if(ok)n++;});
    count.textContent=n+' / '+cards.length;
    if(entEmpty) entEmpty.hidden=n>0;
  }
  document.querySelectorAll('.fchip').forEach(b=>b.addEventListener('click',()=>{
    f[b.dataset.f]=b.dataset.v;
    document.querySelectorAll('.fchip[data-f="'+b.dataset.f+'"]').forEach(x=>{const on=x===b; x.classList.toggle('on',on); x.setAttribute('aria-pressed',String(on));});
    apply();
  }));
  if(entReset) entReset.onclick=()=>{
    f.type=''; f.lvl='';
    document.querySelectorAll('.fchip').forEach(x=>{const on=x.dataset.v===''; x.classList.toggle('on',on); x.setAttribute('aria-pressed',String(on));});
    apply();
  };
  apply();

  // ---- known English terms (with inline click-to-dismiss & safe Undo) ----
  const KNOWN_KEY='known-terms';
  let known=new Set(store.get(KNOWN_KEY,[]));
  const style=document.createElement('style'); document.head.appendChild(style);
  const rows=[...document.querySelectorAll('.t-row')];
  const kst=document.getElementById('known-status');
  function paintKnown(){
    const sel=[...known].map(t=>'.gl[data-term="'+t.replace(/["\\]/g,'\\$&')+'"]');
    style.textContent=sel.length?sel.join(',')+'{display:none}':'';
    let n=0;
    rows.forEach(r=>{const k=r.dataset.terms.split('|').every(t=>known.has(t)); r.classList.toggle('known',k); const b=r.querySelector('.known-btn'); b.setAttribute('aria-pressed',String(k)); b.textContent=k?'已认识':'认识'; if(k)n++;});
    document.getElementById('known-count').textContent='已认识 '+n+' / '+rows.length;
  }
  rows.forEach(r=>r.querySelector('.known-btn').addEventListener('click',()=>{
    const ts=r.dataset.terms.split('|'); const k=ts.every(t=>known.has(t));
    ts.forEach(t=>k?known.delete(t):known.add(t)); store.set(KNOWN_KEY,[...known]); paintKnown();
  }));
  // Click inline gloss in body to mark as known immediately
  document.querySelectorAll('.gl[data-term]').forEach(el=>{
    el.title='点击标为「已认识」，全页不再显示该注释';
    el.addEventListener('click',()=>{
      const t=el.dataset.term;
      if(t){known.add(t); store.set(KNOWN_KEY,[...known]); paintKnown();}
    });
  });

  let undoSnapshot=null, undoTimer=null;
  document.getElementById('known-reset').onclick=()=>{
    if(!known.size){kst.textContent='当前没有已标记的词'; return;}
    undoSnapshot=[...known];
    known=new Set(); store.set(KNOWN_KEY,[]); paintKnown();
    kst.innerHTML='已恢复全部注释 <button type="button" class="undo-btn" id="known-undo">撤销</button>';
    clearTimeout(undoTimer);
    const ub=document.getElementById('known-undo');
    if(ub) ub.onclick=()=>{
      if(undoSnapshot){known=new Set(undoSnapshot); store.set(KNOWN_KEY,[...known]); paintKnown(); kst.textContent='已撤销恢复'; undoSnapshot=null;}
    };
    undoTimer=setTimeout(()=>{if(undoSnapshot){kst.textContent='已恢复全部注释'; undoSnapshot=null;}},8000);
  };
  function copyText(text,ok,fail){
    try{ navigator.clipboard.writeText(text).then(ok,()=>fallbackText(text)?ok():fail()); }
    catch(e){ fallbackText(text)?ok():fail(); }
  }
  function fallbackText(text){
    const ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.left='-9999px'; document.body.appendChild(ta); ta.select();
    let ok=false; try{ok=document.execCommand('copy');}catch(e){} ta.remove(); return ok;
  }
  document.getElementById('known-copy').onclick=()=>{
    if(!known.size){kst.textContent='还没有标记认识的词';return;}
    const text='已认识英文术语列表：\n'+[...known].sort().join('\n');
    copyText(text,()=>kst.textContent='已复制到剪贴板，可添加到 local/known_terms.txt 持久化',()=>kst.textContent='浏览器拒绝了复制');
  };
  paintKnown();

  // ---- copy to OneNote ----
  const tpl=document.getElementById('onenote-src');
  const status=document.getElementById('copy-status');
  function say(t,ok){status.textContent=t;status.classList.toggle('ok',!!ok);}
  function fallback(){
    const sink=document.createElement('div'); sink.className='sink'; sink.appendChild(tpl.content.cloneNode(true));
    document.body.appendChild(sink);
    const r=document.createRange(); r.selectNodeContents(sink);
    const sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
    let ok=false; try{ ok=document.execCommand('copy'); }catch(e){}
    sel.removeAllRanges(); sink.remove();
    say(ok?'已复制。在 OneNote 新页面里按 Cmd+V 粘贴。':'浏览器拒绝了复制，请使用命令行 clip.py 写入剪贴板。',ok);
  }
  document.getElementById('copy-onenote').addEventListener('click',()=>{
    const htmlStr=tpl.innerHTML, text=tpl.content.textContent;
    try{
      if(!(window.ClipboardItem&&navigator.clipboard&&navigator.clipboard.write)) throw 0;
      navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([htmlStr],{type:'text/html'}),'text/plain':new Blob([text],{type:'text/plain'})})])
        .then(()=>say('已复制。在 OneNote 新页面里按 Cmd+V 粘贴。',true)).catch(fallback);
    }catch(e){ fallback(); }
  });

  // ---- back to top ----
  const fab=document.getElementById('fab-top');
  const footTop=document.getElementById('back-top-foot');
  const scrollTop=()=>window.scrollTo({top:0,behavior:'smooth'});
  if(fab){
    fab.addEventListener('click',scrollTop);
    window.addEventListener('scroll',()=>{fab.hidden=window.scrollY<600;},{passive:true});
  }
  if(footTop) footTop.addEventListener('click',scrollTop);
})();
