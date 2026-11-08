(function(){
  const BV='__BV__';
  const store={
    get(k,d){try{const v=localStorage.getItem(k);return v?JSON.parse(v):d;}catch(e){return d;}},
    set(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  };

  // ---- table of contents highlight ----
  const tops=[...document.querySelectorAll('.toc > a[data-sec]')];
  const secs=[...document.querySelectorAll('section.sec')];
  if('IntersectionObserver' in window){
    const io=new IntersectionObserver(es=>{es.forEach(en=>{ if(en.isIntersecting){ const id=en.target.id;
      tops.forEach(a=>a.classList.toggle('on',a.dataset.sec===id));
      const on=tops.find(a=>a.dataset.sec===id); if(on&&window.innerWidth<=960){ on.scrollIntoView({block:'nearest',inline:'center'}); }
    }});},{rootMargin:'-30% 0px -60% 0px'});
    secs.forEach(s=>io.observe(s));
  }
  document.querySelectorAll('a[href^="#ch-"]').forEach(a=>a.addEventListener('click',()=>{const d=document.querySelector(a.getAttribute('href')); if(d) d.open=true;}));

  // ---- chapters: expand / collapse / read progress ----
  const chs=[...document.querySelectorAll('details.chapter')];
  document.getElementById('tl-open').onclick=()=>chs.forEach(d=>d.open=true);
  document.getElementById('tl-close').onclick=()=>chs.forEach(d=>d.open=false);
  const unreadBtn=document.getElementById('tl-unread');
  unreadBtn.onclick=()=>{const on=document.body.classList.toggle('hide-read'); unreadBtn.textContent=on?'显示全部':'只看未读';};
  const READ_KEY='read:'+BV;
  let read=new Set(store.get(READ_KEY,[]));
  function paintRead(){
    chs.forEach(d=>{const r=read.has(d.dataset.ch); d.classList.toggle('is-read',r); const cb=d.querySelector('.read input'); if(cb) cb.checked=r;});
    document.querySelectorAll('.seg[data-ch], .toc-ch[data-ch]').forEach(el=>el.classList.toggle('is-read',read.has(el.dataset.ch)));
    const txt='已读 '+read.size+' / '+chs.length+' 章';
    document.getElementById('read-count').textContent=txt;
    document.getElementById('toc-progress').textContent=txt;
  }
  document.querySelectorAll('.read').forEach(l=>l.addEventListener('click',ev=>ev.stopPropagation()));
  document.querySelectorAll('.read input').forEach(cb=>cb.addEventListener('change',()=>{
    cb.checked?read.add(cb.dataset.ch):read.delete(cb.dataset.ch); store.set(READ_KEY,[...read]); paintRead();
  }));
  paintRead();

  // ---- entity filters ----
  const f={type:'',lvl:''};
  const cards=[...document.querySelectorAll('.ent')];
  const count=document.getElementById('fcount');
  function apply(){let n=0; cards.forEach(c=>{const ok=(!f.type||c.dataset.type===f.type)&&(!f.lvl||c.dataset.lvl===f.lvl); c.hidden=!ok; if(ok)n++;}); count.textContent=n+' / '+cards.length;}
  document.querySelectorAll('.fchip').forEach(b=>b.addEventListener('click',()=>{
    f[b.dataset.f]=b.dataset.v;
    document.querySelectorAll('.fchip[data-f="'+b.dataset.f+'"]').forEach(x=>x.classList.toggle('on',x===b));
    apply();
  }));
  apply();

  // ---- known English terms ----
  const KNOWN_KEY='known-terms';
  let known=new Set(store.get(KNOWN_KEY,[]));
  const style=document.createElement('style'); document.head.appendChild(style);
  const rows=[...document.querySelectorAll('.t-row')];
  function paintKnown(){
    const sel=[...known].map(t=>'.gl[data-term="'+t.replace(/["\\]/g,'\\$&')+'"]');
    style.textContent=sel.length?sel.join(',')+'{display:none}':'';
    let n=0;
    rows.forEach(r=>{const k=r.dataset.terms.split('|').every(t=>known.has(t)); r.classList.toggle('known',k); const b=r.querySelector('.known-btn'); b.setAttribute('aria-pressed',k); b.textContent=k?'已认识':'认识'; if(k)n++;});
    document.getElementById('known-count').textContent='已认识 '+n+' / '+rows.length;
  }
  rows.forEach(r=>r.querySelector('.known-btn').addEventListener('click',()=>{
    const ts=r.dataset.terms.split('|'); const k=ts.every(t=>known.has(t));
    ts.forEach(t=>k?known.delete(t):known.add(t)); store.set(KNOWN_KEY,[...known]); paintKnown();
  }));
  const kst=document.getElementById('known-status');
  document.getElementById('known-reset').onclick=()=>{known=new Set(); store.set(KNOWN_KEY,[]); paintKnown(); kst.textContent='已全部恢复';};
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
    const text='把这些词加到已认识列表：\n'+[...known].sort().join('\n');
    copyText(text,()=>kst.textContent='已复制，发给 Claude 就能在以后的笔记里跳过这些词',()=>kst.textContent='浏览器拒绝了复制');
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
    say(ok?'已复制。在 OneNote 新页面里按 Cmd+V 粘贴。':'浏览器拒绝了复制，请让 Claude 把内容直接放进剪贴板。',ok);
  }
  document.getElementById('copy-onenote').addEventListener('click',()=>{
    const htmlStr=tpl.innerHTML, text=tpl.content.textContent;
    try{
      if(!(window.ClipboardItem&&navigator.clipboard&&navigator.clipboard.write)) throw 0;
      navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([htmlStr],{type:'text/html'}),'text/plain':new Blob([text],{type:'text/plain'})})])
        .then(()=>say('已复制。在 OneNote 新页面里按 Cmd+V 粘贴。',true)).catch(fallback);
    }catch(e){ fallback(); }
  });
})();
