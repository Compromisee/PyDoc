/* PyDoc · front-end (Material Symbols icons, no emojis)
   Talks to Python via window.pywebview.api; includes a browser mock. */

// ---------------------------------------------------------------- mock + bridge
const MOCK = {
  _cfg: { theme: "Windows 11 Dark", hotkey: "ctrl+windows+n", hotkey_add: "ctrl+windows+a",
          show_path_subtext: true, autostart: true, show_on_launch: false, max_results: 9,
          enable_calculator: true, enable_websearch: true,
          web_search_url: "https://www.google.com/search?q={q}", active_group: "All" },
  _themes: { "Windows 11 Dark": {mode:"dark",primary:"#4cc2ff"},
             "Windows 11 Light": {mode:"light",primary:"#0067c0"},
             "Graphite": {mode:"dark",primary:"#9aa0a6"},
             "Nord": {mode:"dark",primary:"#88c0d0"},
             "Mint": {mode:"dark",primary:"#34d399"},
             "Sunset": {mode:"dark",primary:"#fb923c"} },
  _items: [
    {key:"f1",name:"Visual Studio Code",target:"code",image:"ms:code",image_raw:"ms:code",subtext:"Shortcuts/Code.qllink",source:"qllink",removable:true,pinned:true,group:"Dev",alias:"vsc",hotkey:"",count:12,last:Date.now()/1000},
    {key:"f2",name:"Projects",target:"/Projects",image:"ms:folder",image_raw:"ms:folder",subtext:"Shortcuts/Projects.qllink",source:"qllink",removable:true,pinned:false,group:"",alias:"",hotkey:"",count:3,last:0},
    {key:"c1",name:"Google",target:"https://google.com",image:"ms:language",image_raw:"ms:language",subtext:"https://google.com",source:"custom",removable:true,pinned:false,group:"",alias:"",hotkey:"",count:0,last:0},
  ],
  _locked:false, _unlocked:true, _pw:"", _master:"", _profiles:[], _secret:false,
  get_state(){ return {config:this._cfg, themes:this._themes, autostart_supported:false, has_keyboard:false, has_tray:false, lock_enabled:this._locked, unlocked:this._unlocked, app_name:"PyDoc", app_version:"1.0.0", app_channel:"Stable", app_title:"PyDoc v1.0.0 Stable"}; },
  lock_status(){ return {enabled:this._locked, unlocked:this._unlocked, profile:"default", has_master:!!this._master}; },
  unlock(pw){ if(!this._locked) return {ok:true,kind:"default",profile:"default"};
    if(pw===this._pw){this._unlocked=true; return {ok:true,kind:"default",profile:"default"};}
    const p=this._profiles.find(x=>x.pw===pw); if(p){this._unlocked=true; return {ok:true,kind:"profile",profile:p.id};}
    if(this._secret&&pw===this._secret.pw){this._unlocked=true; return {ok:true,kind:"secret",profile:"__secret__"};}
    if(this._master&&pw===this._master){this._unlocked=true; return {ok:true,kind:"master",profile:"default"};}
    return {ok:false}; },
  relock(){ if(this._locked) this._unlocked=false; return true; },
  _used(pw,exc){ const all=[this._pw,this._master,...this._profiles.map(p=>p.pw)].filter((x,i)=>x&&i!==exc); return all.includes(pw); },
  set_password(pw){ if(!/^\d{6}$/.test(pw))return {ok:false,error:"6 digits"}; if([this._master,...this._profiles.map(p=>p.pw)].filter(Boolean).includes(pw))return {ok:false,error:"That code is already used"}; this._pw=pw; this._locked=true; this._unlocked=true; return {ok:true}; },
  disable_lock(pw){ if(pw===this._pw||pw===this._master){this._locked=false; this._unlocked=true; return true;} return false; },
  set_master_password(pw){ if(!/^\d{6}$/.test(pw))return {ok:false,error:"6 digits"}; if([this._pw,...this._profiles.map(p=>p.pw)].includes(pw))return {ok:false,error:"That code is already used"}; this._master=pw; return {ok:true}; },
  list_profiles(){ return this._profiles.map(p=>({name:p.name,id:p.id})); },
  add_profile(name,pw,secret){ if(!/^\d{6}$/.test(pw))return {ok:false,error:"6 digits"}; if([this._pw,this._master,...this._profiles.map(p=>p.pw)].includes(pw))return {ok:false,error:"That code is already used"}; const id="profile"+(this._profiles.length+1); this._profiles.push({name,pw,id}); return {ok:true,id}; },
  delete_profile(id){ if(id==="__secret__"){this._secret=false;return true;} this._profiles=this._profiles.filter(p=>p.id!==id); return true; },
  has_secret(){ return !!this._secret; },
  search(q,g){ if(this._locked && !this._unlocked) return {results:[],special:[],groups:["All"],locked:true};
    let r=this._items.filter(i=>(g==="All"||i.group===g)&&(!q||i.name.toLowerCase().includes(q.toLowerCase())||(i.alias||"").includes(q.toLowerCase())));
    let sp=[]; if(/^[-+*/().\d\s^%]+$/.test(q||"")&&/\d/.test(q||"")){try{sp.push({key:"calc",name:q+" = "+eval(q.replace(/\^/g,"**")),image:"ms:calculate",subtext:"Calculator",kind:"calc",value:""+eval(q.replace(/\^/g,"**"))});}catch(e){}}
    if(q&&q.length>=3&&["screenshot","snip","capture"].some(w=>w.startsWith(q.toLowerCase()))){
      sp.push({key:"shot:region",name:"Screenshot — select a region",target:"region",image:"ms:screenshot_region",kind:"shot",subtext:"Snip an area (saved + copied)"});
      sp.push({key:"shot:full",name:"Screenshot — whole screen",target:"full",image:"ms:fullscreen",kind:"shot",subtext:"Capture all monitors"});
      sp.push({key:"shot:window",name:"Screenshot — active window",target:"window",image:"ms:web_asset",kind:"shot",subtext:"Capture the focused window"});
    }
    return {results:r,special:sp,groups:["All","Dev"]}; },
  groups(){ return ["All","Dev"]; },
  launch(){return true;}, launch_special(){return true;},
  screenshot(m){ setTimeout(()=>window.qlOnScreenshot&&window.qlOnScreenshot({ok:true,path:"clipboard",mode:m}),300); return true; },
  open_screenshot_folder(){return true;},
  _pinned:["ipconfig /all","git status"], _session:[],
  run_command(c){ this._session=this._session.filter(x=>x!==c); this._session.unshift(c);
    if(/^echo /i.test(c)) return {ok:true,cmd:c,stdout:c.slice(5),stderr:"",code:0,suggestion:""};
    if(/^(ipconfig|dir|ls|whoami|ver|hostname)\b/i.test(c)) return {ok:true,cmd:c,stdout:"(demo output)\nWindows IP Configuration\n\n   IPv4 Address. . . : 192.168.1.42\n   Subnet Mask . . . : 255.255.255.0",stderr:"",code:0,suggestion:""};
    return {ok:false,cmd:c,stdout:"",stderr:"'"+c.split(" ")[0]+"' is not recognized as an internal or external command.",code:1,suggestion:this.suggest_command(c)}; },
  suggest_command(c){ const m={"ipconfgi":"ipconfig","pythn":"python","gti":"git","cd..":"cd ..","claer":"clear","sl":"ls"}; const h=c.split(/\s+/,1)[0]; const rest=c.slice(h.length); return m[h]?m[h]+rest:""; },
  cmd_history(){ const ps=new Set(this._pinned); return [...this._pinned.map(c=>({cmd:c,pinned:true})), ...this._session.filter(c=>!ps.has(c)).map(c=>({cmd:c,pinned:false}))]; },
  pin_command(c){ if(!this._pinned.includes(c))this._pinned.push(c); return true; },
  unpin_command(c){ this._pinned=this._pinned.filter(x=>x!==c); return true; },
  clear_cmd_history(){ this._session=[]; return true; },
  toggle_pin(k){let i=this._items.find(x=>x.key===k); if(i)i.pinned=!i.pinned; return i?i.pinned:false;},
  list_custom(){return [{name:"Google",target:"https://google.com",image:"ms:language"}];},
  meta_for(){return {};},
  add_custom(){return true;}, update_custom(){return true;}, delete_custom(){return true;},
  set_meta(){return true;}, save_config(c){Object.assign(this._cfg,c);return true;},
  set_theme(){return true;}, open_folder(){return true;}, hide(){}, quit(){}, hide_on_blur(){return false;},
  add_dropped(p){ this._items.push({key:"d"+Date.now(),name:p.split(/[\\/]/).pop(),target:p,image:"ms:draft",image_raw:"ms:draft",subtext:p,source:"qllink",removable:true,pinned:false,group:"",alias:"",hotkey:"",count:0,last:0}); return "ok.qllink"; },
  add_dropped_url(){return "url.qllink";}, create_qllink(){return "new.qllink";},
  delete_shortcut(k){this._items=this._items.filter(x=>x.key!==k);return true;},
  search_icons(q){ const all=["folder","folder_open","rocket_launch","language","calculate","music_note","movie","sports_esports","videogame_asset","stadia_controller","home","star","favorite","settings","code","terminal","mail","chat","image","photo_camera","download","upload","cloud","lock","key","bolt","build","palette","draw","map","place","schedule","shopping_cart","store","work","school","public","bug_report","memory","wifi","headphones","calendar_month","description","picture_as_pdf","table_chart","smart_toy","auto_awesome"]; const qq=(q||"").replace(/ /g,"_"); return all.filter(n=>!qq||n.includes(qq)).map(n=>({image:"ms:"+n,name:n})); },
  fetch_material_icon(n){return "ms:"+n;},
  resolve_image(i){return i&&i.startsWith("ms:")?i:"";},
  pick_icon_file(){return null;}, pick_target_file(){return null;},
};
let api = null;
function getApi(){ if(api) return api; api=(window.pywebview&&window.pywebview.api)?window.pywebview.api:MOCK; return api; }
async function call(name, ...args){ const a=getApi(); try{ return await a[name](...args); }catch(e){ console.warn("api",name,e); return null; } }

// ---------------------------------------------------------------- state
let CONFIG = {}, THEMES = {}, CAPS = {};
let results = [], special = [], groups = ["All"];
let activeGroup = "All", selected = 0, lastQuery = "";
let editKey = null, iconTarget = null;
let pendingIcon = { image: "" }, editIcon = { image: "" };
let recordTarget = null, confirmCb = null;
let LOCK = { enabled:false, unlocked:true };
const el = (s) => document.getElementById(s);

// ---------------------------------------------------------------- lock screen
async function refreshLock(){
  const st = await call("lock_status");
  if (st){ LOCK = st; }
  applyLockUI();
}
let _lockFails = 0;
const PIN_LEN = 6;
let _pinReveal = false;
function renderPin(){
  const inp = el("lock-pw");
  // keep only digits, max 6
  let v = (inp.value || "").replace(/\D/g, "").slice(0, PIN_LEN);
  if (v !== inp.value) inp.value = v;
  const box = el("lock-boxes");
  const focused = document.activeElement === inp;
  el("lock-pin").classList.toggle("focused", focused);
  let html = "";
  for (let i=0;i<PIN_LEN;i++){
    const filled = i < v.length;
    const isCaret = focused && i === v.length;        // next empty slot
    html += `<div class="ql-otp-box ${filled?"filled":""} ${isCaret?"caret":""}">${filled ? (_pinReveal ? esc(v[i]) : "•") : ""}</div>`;
  }
  box.innerHTML = html;
  // pop the most recently filled box
  const boxes = box.querySelectorAll(".ql-otp-box.filled");
  const last = boxes[boxes.length-1];
  if (last && v.length){ last.classList.add("pop"); setTimeout(()=>last && last.classList.remove("pop"), 150); }
  // auto-submit once all 6 digits are entered
  if (v.length === PIN_LEN) tryUnlock();
}
function applyLockUI(){
  const show = LOCK.enabled && !LOCK.unlocked;
  el("lockscreen").classList.toggle("show", show);
  el("card").style.filter = show ? "blur(2px)" : "";
  if (show){
    el("lock-pw").value=""; el("lock-err").textContent="";
    el("lock-profile").innerHTML="";
    el("lock-forgot").style.display = (LOCK.has_master && _lockFails>=2) ? "block" : "none";
    renderPin();
    focusInput("lock-pw");
  }
}
const PROFILE_LABEL = { default:"", master:"Recovered with master password",
  secret:"Hidden space", profile:"Profile" };
let _unlocking = false;
async function tryUnlock(){
  const pw = el("lock-pw").value;
  if (pw.length !== PIN_LEN || _unlocking) return;   // need full 6-digit code
  _unlocking = true;
  const r = await call("unlock", pw);
  _unlocking = false;
  if (r && r.ok){
    _lockFails = 0; LOCK.unlocked = true; LOCK.profile = r.profile;
    if (r.kind && r.kind!=="default"){
      flashTop(r.kind==="master" ? "Master unlock" : "Switched space");
    }
    applyLockUI(); doSearch(); focusInput("search");
  } else {
    _lockFails++;
    el("lock-err").textContent = "Incorrect code";
    el("lock-forgot").style.display = (LOCK.has_master && _lockFails>=2) ? "block" : "none";
    const card = document.querySelector(".ql-lock-card");
    card.classList.remove("shake"); void card.offsetWidth; card.classList.add("shake");
    el("lock-pw").value = ""; renderPin(); el("lock-pw").focus();
  }
}
function updateCaps(e){
  try { el("lock-caps").style.display = e.getModifierState && e.getModifierState("CapsLock") ? "flex" : "none"; }
  catch(_){}
}

// ---------------------------------------------------------------- icons
function imgHtml(image){
  if (!image) return `<span class="msr">draft</span>`;
  if (image.startsWith("ms:")) return `<span class="msr">${esc(image.slice(3))}</span>`;
  // resolved file:// or http url
  return `<img src="${esc(image)}" alt="" onerror="this.outerHTML='<span class=\\'msr\\'>draft</span>'" />`;
}
function iconHtml(it){ return imgHtml(it.image); }

// ---------------------------------------------------------------- theme
function applyTheme(name){
  const t = THEMES[name]; if (!t) return;
  document.documentElement.setAttribute("data-theme", t.mode);
  document.documentElement.style.setProperty("--accent", t.primary);
  el("theme-name").textContent = name;
}
function nextTheme(){
  const names = Object.keys(THEMES);
  CONFIG.theme = names[(names.indexOf(CONFIG.theme) + 1) % names.length];
  applyTheme(CONFIG.theme); call("set_theme", CONFIG.theme);
}

// ---------------------------------------------------------------- search/render
async function doSearch(){
  const q = el("search").value; lastQuery = q;
  el("btn-clear").style.display = q ? "grid" : "none";
  const r = await call("search", q, activeGroup);
  if (!r) return;
  results = r.results || []; special = r.special || []; groups = r.groups || ["All"];
  selected = 0; renderGroups(); renderResults();
}
function renderGroups(){
  const box = el("groups");
  if (groups.length <= 1){ box.innerHTML = ""; return; }
  box.innerHTML = "";
  groups.forEach(g => { const c=document.createElement("div"); c.className="ql-chip"+(g===activeGroup?" active":""); c.textContent=g; c.onclick=()=>{activeGroup=g;doSearch();}; box.appendChild(c); });
}
function combined(){ return [...special, ...results]; }
function highlight(text, q){
  if (!q) return esc(text);
  const t=text, tl=t.toLowerCase(), ql=q.toLowerCase();
  const idx = tl.indexOf(ql);
  if (idx>=0) return esc(t.slice(0,idx))+`<span class="ql-hl">`+esc(t.slice(idx,idx+q.length))+`</span>`+esc(t.slice(idx+q.length));
  let out="", qi=0;
  for (let i=0;i<t.length;i++){ if(qi<ql.length&&tl[i]===ql[qi]){out+=`<span class="ql-hl">${esc(t[i])}</span>`;qi++;} else out+=esc(t[i]); }
  return out;
}
function renderResults(){
  const box = el("results"); const list = combined();
  const max = CONFIG.max_results || 9; const shown = list.slice(0, special.length + max);
  if (!shown.length){ box.innerHTML = `<div class="ql-empty">No matching shortcuts</div>`; return; }
  if (selected >= shown.length) selected = shown.length - 1;
  box.innerHTML = "";
  shown.forEach((it, i) => {
    const row = document.createElement("div");
    row.className = "ql-row" + (i===selected?" sel":"") + (it.source==="child"?" child":"");
    const showSub = CONFIG.show_path_subtext && it.subtext;
    const badges = [];
    if (it.group) badges.push(`<span class="ql-badge">${esc(it.group)}</span>`);
    if (it.alias) badges.push(`<span class="ql-badge">${esc(it.alias)}</span>`);
    if (it.hotkey) badges.push(`<span class="ql-badge">${esc(it.hotkey)}</span>`);
    const pin = (it.kind || !it.removable) ? "" :
      `<button class="pinbtn ${it.pinned?"on":""}" data-pin="${esc(it.key)}" title="Pin (Ctrl+P)"><span class="msr">push_pin</span></button>`;
    const numHint = i < 9 ? `<span class="ql-numhint">Alt+${i+1}</span>` : "";
    row.innerHTML = `
      <div class="ico">${iconHtml(it)}</div>
      <div class="body">
        <div class="name">${it.kind?esc(it.name):highlight(it.name,lastQuery)} ${badges.join(" ")}</div>
        ${showSub?`<div class="sub">${esc(it.subtext)}</div>`:""}
      </div>${numHint}${pin}`;
    row.onclick = (e) => {
      const pb = e.target.closest("[data-pin]");
      if (pb){ togglePin(pb.dataset.pin); return; }
      selected = i; activate();
    };
    box.appendChild(row);
  });
  const sel = box.querySelector(".ql-row.sel"); if (sel) sel.scrollIntoView({block:"nearest"});
}
function move(d){ const n=combined().length; if(!n)return; selected=(selected+d+n)%n; renderResults(); }
async function activate(){
  const it = combined()[selected]; if (!it) return;
  if (it.kind==="calc"){ try{await navigator.clipboard.writeText(it.value);}catch(e){} flashTop("Copied "+it.value); return; }
  if (it.kind==="url"){ await call("launch_special", it.target); hide(); return; }
  if (it.kind==="shot"){ hide(); await call("screenshot", it.target); return; }
  if (it.kind==="runcmd"){ openRunner(it.target || ""); return; }
  await call("launch", it.key); hide();
}
async function togglePin(key){ await call("toggle_pin", key); doSearch(); }
function hide(){ el("search").value=""; call("hide"); }
function deleteSelected(){
  const it = combined()[selected];
  if (!it || it.kind || !it.removable) return;
  showConfirm(`Remove “${it.name}” from your shortcuts?`, async () => { await call("delete_shortcut", it.key); flashTop("Removed "+it.name); doSearch(); });
}

// ---------------------------------------------------------------- command runner
let runnerOpen = false, histSel = -1, suggestTimer = null;

function openRunner(prefill){
  runnerOpen = true;
  el("runner").classList.add("show");
  document.querySelector(".ql-searchbar").style.display = "none";
  el("groups").style.display = "none";
  el("results").style.display = "none";
  el("run-output").innerHTML = "";
  el("run-suggest").innerHTML = "";
  el("run-cmd").value = prefill || "";
  loadHistory();
  setTimeout(()=>el("run-cmd").focus(), 30);
  onSuggest();
}
function closeRunner(){
  runnerOpen = false;
  el("runner").classList.remove("show");
  document.querySelector(".ql-searchbar").style.display = "";
  el("groups").style.display = "";
  el("results").style.display = "";
  el("search").focus(); doSearch();
}
async function loadHistory(){
  const hist = (await call("cmd_history")) || [];
  const box = el("run-history"); box.innerHTML = "";
  if (!hist.length){ box.innerHTML = `<div class="ql-run-empty">No commands yet — pinned ones stick around, the rest clear on reboot.</div>`; return; }
  hist.forEach((h, i) => {
    const d = document.createElement("div");
    d.className = "ql-run-hitem" + (i===histSel ? " sel" : "");
    d.innerHTML = `
      <span class="msr ${h.pinned?"pin":""}">${h.pinned?"push_pin":"history"}</span>
      <span class="hi-cmd">${esc(h.cmd)}</span>
      <span class="hi-act">
        <button data-act="copy" title="Copy"><span class="msr">content_copy</span></button>
        <button data-act="pin" title="${h.pinned?"Unpin":"Pin"}"><span class="msr">${h.pinned?"keep_off":"push_pin"}</span></button>
      </span>`;
    d.querySelector('[data-act="copy"]').onclick = (e)=>{ e.stopPropagation(); navigator.clipboard.writeText(h.cmd).catch(()=>{}); flashTop("Copied"); };
    d.querySelector('[data-act="pin"]').onclick = async (e)=>{ e.stopPropagation(); await call(h.pinned?"unpin_command":"pin_command", h.cmd); loadHistory(); };
    d.onclick = ()=>{ el("run-cmd").value = h.cmd; el("run-cmd").focus(); onSuggest(); };
    box.appendChild(d);
  });
}
function onSuggest(){
  clearTimeout(suggestTimer);
  suggestTimer = setTimeout(async ()=>{
    const cmd = el("run-cmd").value.trim();
    const box = el("run-suggest");
    if (!cmd){ box.innerHTML = "Tip: pinned commands are saved; session ones clear on reboot."; return; }
    const fix = await call("suggest_command", cmd);
    box.innerHTML = fix ? `Did you mean <span class="fix">${esc(fix)}</span>?`
                        : `Press <b>Enter</b> to run · <b>↑↓</b> history · <b>Ctrl+P</b> pin`;
    const f = box.querySelector(".fix");
    if (f) f.onclick = ()=>{ el("run-cmd").value = fix; onSuggest(); el("run-cmd").focus(); };
  }, 140);
}
function highlightCmd(cmd){
  // simple shell syntax highlight for the echoed command line
  let h = esc(cmd);
  h = h.replace(/(^|\s)(-{1,2}[\w-]+)/g, '$1<span class="ln-flag">$2</span>');
  h = h.replace(/(&quot;[^&]*?&quot;|&#39;[^&]*?&#39;)/g, '<span class="ln-str">$1</span>');
  h = h.replace(/\b(\d+(?:\.\d+)*)\b/g, '<span class="ln-num">$1</span>');
  h = h.replace(/([A-Za-z]:\\[^\s]+|\/[^\s]+\/[^\s]*)/g, '<span class="ln-path">$1</span>');
  return h;
}
function colorOutputLine(line){
  const e = esc(line);
  if (/error|fail|exception|not recognized|not found|denied|fatal/i.test(line)) return `<span class="ln-err">${e}</span>`;
  if (/warning|deprecat/i.test(line)) return `<span class="ln-warn">${e}</span>`;
  if (/success|done|complete|ok\b|listening|started/i.test(line)) return `<span class="ln-ok">${e}</span>`;
  // paths & IPs
  let h = e.replace(/([A-Za-z]:\\[^\s]+|(?:\/[\w.-]+){2,})/g, '<span class="ln-path">$1</span>');
  h = h.replace(/\b(\d{1,3}(?:\.\d{1,3}){3})\b/g, '<span class="ln-num">$1</span>');
  return h;
}
async function runCurrent(){
  const cmd = el("run-cmd").value.trim();
  if (!cmd) return;
  const out = el("run-output");
  out.innerHTML += `<div><span class="ln-muted">&gt;</span> <span class="ln-cmd">${highlightCmd(cmd)}</span></div>`;
  const r = await call("run_command", cmd);
  if (r){
    const body = (r.stdout||"") + (r.stderr?("\n"+r.stderr):"");
    body.split("\n").forEach(l => { out.innerHTML += `<div>${colorOutputLine(l)}</div>`; });
    if (!r.ok) out.innerHTML += `<div class="ln-err">[exit code ${r.code}]</div>`;
    if (r.suggestion) out.innerHTML += `<div class="ln-warn">did you mean: <span class="fix" onclick="document.getElementById('run-cmd').value=this.textContent.replace('','');">${esc(r.suggestion)}</span> ?</div>`;
  }
  out.scrollTop = out.scrollHeight;
  el("run-cmd").value = ""; histSel = -1; onSuggest(); loadHistory();
}
function runnerKey(e){
  if (e.key === "Escape"){ closeRunner(); e.preventDefault(); return; }
  if (e.key === "Enter"){ runCurrent(); e.preventDefault(); return; }
  if (e.key === "p" && e.ctrlKey){ const c=el("run-cmd").value.trim(); if(c){ call("pin_command",c).then(loadHistory); flashTop("Pinned"); } e.preventDefault(); return; }
  if (e.key === "ArrowUp" || e.key === "ArrowDown"){
    const items = [...document.querySelectorAll("#run-history .ql-run-hitem")];
    if (!items.length) return;
    histSel = e.key==="ArrowUp" ? Math.max(0, histSel-1) : Math.min(items.length-1, histSel+1);
    items.forEach((it,i)=>it.classList.toggle("sel", i===histSel));
    const cmd = items[histSel].querySelector(".hi-cmd").textContent;
    el("run-cmd").value = cmd; onSuggest();
    items[histSel].scrollIntoView({block:"nearest"});
    e.preventDefault();
  }
}

// ---------------------------------------------------------------- drag & drop
let dragDepth = 0;
function wireDnd(){
  window.addEventListener("dragenter", e=>{ e.preventDefault(); dragDepth++; el("dropzone").classList.add("show"); });
  window.addEventListener("dragover", e=>e.preventDefault());
  window.addEventListener("dragleave", e=>{ e.preventDefault(); if(--dragDepth<=0){dragDepth=0; el("dropzone").classList.remove("show");} });
  window.addEventListener("drop", async e=>{
    e.preventDefault(); dragDepth=0; el("dropzone").classList.remove("show");
    if (!(window.pywebview && window.pywebview.api)){
      const txt=e.dataTransfer.getData("text"); if(txt){await call("add_dropped_url",txt);}
      for(const f of e.dataTransfer.files){ await call("add_dropped", f.name); }
      doSearch();
    }
  });
}
window.qlOnDrop = function(names){ flashTop("Added "+(names&&names.length?names.length:"")+" shortcut"+(names&&names.length===1?"":"s")); doSearch(); };

// ---------------------------------------------------------------- add/edit dialog
function openAdd(prefill){
  pendingIcon = { image: "" };
  el("add-title").textContent = "Add shortcut";
  el("add-name").value=(prefill&&prefill.name)||""; el("add-target").value=(prefill&&prefill.target)||"";
  el("add-group").value=""; el("add-alias").value=""; el("add-hotkey").value="";
  el("add-status").textContent="";
  updateIconPreview("add-iconbtn", pendingIcon);
  el("add-overlay").classList.add("show");
  setTimeout(()=>el("add-name").focus(),30);
}
function closeAdd(){ el("add-overlay").classList.remove("show"); }
async function saveAdd(){
  const name=el("add-name").value.trim(), target=el("add-target").value.trim();
  if (!name||!target){ el("add-status").textContent="Name and target required"; return; }
  await call("create_qllink", name, target, "", pendingIcon.image||"");
  await new Promise(r=>setTimeout(r,60));
  const r=await call("search", name, "All");
  const item=(r&&r.results||[]).find(x=>x.name===name);
  if (item) await call("set_meta", item.key, el("add-group").value.trim(), el("add-alias").value.trim(), el("add-hotkey").value.trim(), "", pendingIcon.image||"");
  flashTop("Added "+name); closeAdd(); doSearch();
}

// ---------------------------------------------------------------- settings
function openSettings(){ fillSettings(); el("overlay").classList.add("show"); setTab("general"); }
function closeSettings(){ el("overlay").classList.remove("show"); }
function fillSettings(){
  const ts=el("set-theme"); ts.innerHTML="";
  Object.keys(THEMES).forEach(n=>{const o=document.createElement("option");o.value=n;o.textContent=n;if(n===CONFIG.theme)o.selected=true;ts.appendChild(o);});
  ts.onchange=()=>{CONFIG.theme=ts.value;applyTheme(ts.value);};
  el("set-websearch").value=CONFIG.web_search_url||"";
  el("set-maxresults").value=CONFIG.max_results||9;
  el("set-paths").checked=!!CONFIG.show_path_subtext;
  el("set-onlaunch").checked=!!CONFIG.show_on_launch;
  el("set-blur").checked=CONFIG.hide_on_blur!==false;
  el("set-calc").checked=!!CONFIG.enable_calculator;
  el("set-web").checked=!!CONFIG.enable_websearch;
  el("set-shot").checked=CONFIG.enable_screenshot!==false;
  el("set-shotcopy").checked=CONFIG.screenshot_copy!==false;
  el("set-run").checked=CONFIG.enable_runcmd!==false;
  el("set-autocorrect").checked=CONFIG.cmd_autocorrect!==false;
  const auto=el("set-autostart"); auto.checked=!!CONFIG.autostart; auto.disabled=!CAPS.autostart_supported;
  el("autostart-note").textContent=CAPS.autostart_supported?"":"(Windows only)";
  el("key-toggle").value=CONFIG.hotkey||""; el("key-add").value=CONFIG.hotkey_add||""; el("key-shot").value=CONFIG.hotkey_screenshot||""; el("key-run").value=CONFIG.hotkey_runcmd||"";
  renderThemeGrid(); loadCustomList(); fillSecurity();
}
function setTab(name){
  document.querySelectorAll("#overlay .ql-tab").forEach(t=>t.classList.toggle("active",t.dataset.tab===name));
  document.querySelectorAll("#overlay .ql-pane").forEach(p=>p.classList.toggle("active",p.dataset.pane===name));
}
function renderThemeGrid(){
  const grid=el("theme-grid"); grid.innerHTML="";
  Object.entries(THEMES).forEach(([name,t])=>{
    const card=document.createElement("div"); card.className="ql-theme-card"+(name===CONFIG.theme?" active":"");
    card.innerHTML=`<div class="ql-swatch" style="background:linear-gradient(135deg, ${t.primary}, ${t.mode==='dark'?'#202020':'#f3f3f3'})"></div><div class="tc-name">${esc(name)}</div><div class="tc-mode">${t.mode}</div>`;
    card.onclick=()=>{CONFIG.theme=name;applyTheme(name);el("set-theme").value=name;renderThemeGrid();};
    grid.appendChild(card);
  });
}
async function loadCustomList(){
  const r=await call("search","","All");
  const items=(r&&r.results||[]).filter(it=>it.source!=="child");
  const box=el("custom-list"); box.innerHTML="";
  items.forEach(it=>{
    const d=document.createElement("div"); d.className="ql-citem"+(editKey===it.key?" sel":"");
    d.innerHTML=`<span class="ci-ico">${iconHtml(it)}</span><span class="ci-name">${esc(it.name)}</span><span class="ci-tag">${it.source}</span>`;
    d.onclick=()=>selectItem(it); box.appendChild(d);
  });
}
function selectItem(it){
  editKey=it.key; editIcon={ image: it.image_raw||it.image||"" };
  el("f-name").value=it.name; el("f-target").value=it.target;
  el("f-group").value=it.group||""; el("f-alias").value=it.alias||""; el("f-hotkey").value=it.hotkey||"";
  el("f-name").readOnly=false; el("f-target").readOnly=(it.source==="file");
  updateIconPreview("edit-iconbtn", editIcon); loadCustomList();
}
function clearEditForm(){
  editKey=null; editIcon={ image:"" };
  ["f-name","f-target","f-group","f-alias","f-hotkey"].forEach(id=>{el(id).value="";el(id).readOnly=false;});
  updateIconPreview("edit-iconbtn", editIcon); loadCustomList();
}
async function saveEdit(){
  if (!editKey){ flashStatus("Select an item or use New shortcut"); return; }
  const name=el("f-name").value.trim(), target=el("f-target").value.trim();
  const r=await call("search","","All");
  const it=(r&&r.results||[]).find(x=>x.key===editKey);
  if (!it){ flashStatus("Item not found"); return; }
  if (it.source==="custom"){
    const cl=await call("list_custom"); const idx=(cl||[]).findIndex(c=>c.name===it.name);
    if (idx>=0) await call("update_custom", idx, name, target, "", editIcon.image||"");
  }
  await call("set_meta", editKey, el("f-group").value.trim(), el("f-alias").value.trim(), el("f-hotkey").value.trim(), "", editIcon.image||"");
  flashStatus("Saved"); doSearch(); loadCustomList();
}
function deleteEdit(){
  if (!editKey){ flashStatus("Select an item"); return; }
  showConfirm("Delete this shortcut?", async()=>{ await call("delete_shortcut", editKey); flashStatus("Deleted"); clearEditForm(); doSearch(); });
}
async function saveSettings(){
  const cfg={
    theme: el("set-theme").value,
    web_search_url: el("set-websearch").value.trim()||"https://www.google.com/search?q={q}",
    max_results: parseInt(el("set-maxresults").value)||9,
    show_path_subtext: el("set-paths").checked,
    show_on_launch: el("set-onlaunch").checked,
    hide_on_blur: el("set-blur").checked,
    enable_calculator: el("set-calc").checked,
    enable_websearch: el("set-web").checked,
    enable_screenshot: el("set-shot").checked,
    screenshot_copy: el("set-shotcopy").checked,
    enable_runcmd: el("set-run").checked,
    cmd_autocorrect: el("set-autocorrect").checked,
    autostart: el("set-autostart").checked,
    hotkey: el("key-toggle").value.trim()||"ctrl+windows+n",
    hotkey_add: el("key-add").value.trim(),
    hotkey_screenshot: el("key-shot").value.trim(),
    hotkey_runcmd: el("key-run").value.trim(),
  };
  Object.assign(CONFIG,cfg); await call("save_config",cfg); applyTheme(CONFIG.theme);
  flashStatus("Saved"); doSearch(); setTimeout(closeSettings,350);
}

// ---------------------------------------------------------------- icon picker
function updateIconPreview(btnId, ic){ el(btnId).innerHTML = ic.image ? imgHtml(ic._url||ic.image) : `<span class="msr">image</span>`; }
function openIconPicker(which){
  iconTarget=which; el("icon-overlay").classList.add("show"); setITab("material");
  el("icon-search").value=""; renderIcons("");
  setTimeout(()=>el("icon-search").focus(),30);
}
function closeIconPicker(){ el("icon-overlay").classList.remove("show"); }
function setITab(name){
  document.querySelectorAll("#icon-overlay .ql-tab").forEach(t=>t.classList.toggle("active",t.dataset.itab===name));
  document.querySelectorAll("#icon-overlay .ql-pane").forEach(p=>p.classList.toggle("active",p.dataset.ipane===name));
}
async function renderIcons(q){
  const list=await call("search_icons", q, 120);
  const grid=el("icon-grid"); grid.innerHTML="";
  (list||[]).forEach(ic=>{
    const c=document.createElement("div"); c.className="ql-iconcell"; c.title=ic.name;
    c.innerHTML=`<span class="msr">${esc(ic.name)}</span>`;
    c.onclick=()=>chooseIcon({ image: ic.image });
    grid.appendChild(c);
  });
}
async function pickIconFile(){
  const res=await call("pick_icon_file");
  if (res && res.image) chooseIcon({ image: res.image, _url: res.url });
}
function chooseIcon(ic){
  if (iconTarget==="add"){ pendingIcon=ic; updateIconPreview("add-iconbtn",ic); }
  else if (iconTarget==="edit"){ editIcon=ic; updateIconPreview("edit-iconbtn",ic); }
  closeIconPicker();
}

// ---------------------------------------------------------------- keybind recorder
function startRecording(inputId, btn){
  recordTarget=inputId;
  document.querySelectorAll(".ql-btn.recording").forEach(b=>b.classList.remove("recording"));
  if (btn) btn.classList.add("recording");
  const note=el("key-recording"); if (note) note.style.display="block";
}
function stopRecording(){
  recordTarget=null;
  document.querySelectorAll(".ql-btn.recording").forEach(b=>b.classList.remove("recording"));
  const note=el("key-recording"); if (note) note.style.display="none";
}
function comboFromEvent(e){
  if (e.key==="Escape") return null;
  const mods=[];
  if (e.ctrlKey) mods.push("ctrl");
  if (e.altKey) mods.push("alt");
  if (e.shiftKey) mods.push("shift");
  if (e.metaKey) mods.push("windows");
  let k=e.key.toLowerCase();
  const named={" ":"space","arrowup":"up","arrowdown":"down","arrowleft":"left","arrowright":"right","escape":"esc"};
  if (named[k]) k=named[k];
  if (["control","alt","shift","meta"].includes(k)) return mods.length?mods.join("+")+"+":"";
  return [...mods,k].join("+");
}

// ---------------------------------------------------------------- confirm
function showConfirm(msg,cb){ el("confirm-msg").textContent=msg; confirmCb=cb; el("confirm").classList.add("show"); }
function hideConfirm(){ el("confirm").classList.remove("show"); confirmCb=null; }

// ---------------------------------------------------------------- utils + events
function esc(s){ return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function flashStatus(msg){ const s=el("status"); s.textContent=msg; setTimeout(()=>{if(s.textContent===msg)s.textContent="";},2200); }
function flashTop(msg){ const s=el("theme-name"); s.textContent=msg; setTimeout(()=>{s.textContent=CONFIG.theme||"";},1600); }

function onKey(e){
  // command runner has its own key handling on its input
  if (runnerOpen) return;
  // when locked, only Esc (hide) is allowed; the lock input handles Enter itself
  if (el("lockscreen").classList.contains("show")){
    if (e.key==="Escape"){ hide(); e.preventDefault(); }
    return;
  }
  if (recordTarget){
    e.preventDefault();
    const combo=comboFromEvent(e);
    if (combo===null){ stopRecording(); return; }
    if (combo && !combo.endsWith("+")){ el(recordTarget).value=combo; stopRecording(); }
    return;
  }
  if (el("confirm").classList.contains("show")){ if(e.key==="Enter"){if(confirmCb)confirmCb();hideConfirm();e.preventDefault();} if(e.key==="Escape"){hideConfirm();e.preventDefault();} return; }
  if (el("icon-overlay").classList.contains("show")){ if(e.key==="Escape"){closeIconPicker();e.preventDefault();} return; }
  if (el("add-overlay").classList.contains("show")){ if(e.key==="Escape"){closeAdd();e.preventDefault();} return; }
  if (el("overlay").classList.contains("show")){ if(e.key==="Escape"){closeSettings();e.preventDefault();} return; }
  // Alt+1..9 quick-launch the corresponding result
  if (e.altKey && /^[1-9]$/.test(e.key)){
    const idx = parseInt(e.key,10) - 1;
    if (idx < combined().length){ selected = idx; activate(); }
    e.preventDefault(); return;
  }
  switch (e.key){
    case "ArrowDown": move(1); e.preventDefault(); break;
    case "ArrowUp": move(-1); e.preventDefault(); break;
    case "Enter": if(e.ctrlKey){call("open_folder");hide();}else activate(); e.preventDefault(); break;
    case "Escape": hide(); e.preventDefault(); break;
    case "Tab": nextTheme(); e.preventDefault(); break;
    case "Delete": if(!el("search").value){deleteSelected();e.preventDefault();} break;
    case "p": if(e.ctrlKey){const it=combined()[selected];if(it&&!it.kind)togglePin(it.key);e.preventDefault();} break;
    case "d": if(e.ctrlKey){deleteSelected();e.preventDefault();} break;
    case "n": if(e.ctrlKey){openAdd();e.preventDefault();} break;
    case "r": if(e.ctrlKey){openRunner("");e.preventDefault();} break;
    case ",": if(e.ctrlKey){openSettings();e.preventDefault();} break;
    case "PageDown": move(5); e.preventDefault(); break;
    case "PageUp": move(-5); e.preventDefault(); break;
  }
}
function wireEvents(){
  el("search").addEventListener("input", doSearch);
  document.addEventListener("keydown", onKey);
  wireBlurHide();
  el("btn-settings").onclick=openSettings;
  el("btn-add").onclick=()=>openAdd();
  el("btn-run").onclick=()=>openRunner("");
  el("btn-clear").onclick=()=>{ el("search").value=""; doSearch(); el("search").focus(); };
  // command runner
  el("run-cmd").addEventListener("keydown", runnerKey);
  el("run-cmd").addEventListener("input", onSuggest);
  el("run-go").onclick=runCurrent;
  el("run-close").onclick=closeRunner;
  el("run-clear").onclick=async()=>{ await call("clear_cmd_history"); loadHistory(); };
  el("settings-close").onclick=closeSettings; el("settings-cancel").onclick=closeSettings; el("settings-save").onclick=saveSettings;
  el("overlay").addEventListener("mousedown",e=>{if(e.target.id==="overlay")closeSettings();});
  document.querySelectorAll("#overlay .ql-tab").forEach(t=>t.onclick=()=>setTab(t.dataset.tab));
  el("open-folder").onclick=()=>call("open_folder");
  el("new-shortcut").onclick=()=>{closeSettings();openAdd();};
  el("f-update").onclick=saveEdit; el("f-delete").onclick=deleteEdit; el("f-clear").onclick=clearEditForm;
  el("edit-iconbtn").onclick=()=>openIconPicker("edit");
  el("f-hotkey-rec").onclick=e=>startRecording("f-hotkey",e.currentTarget);
  el("f-hotkey-clr").onclick=()=>el("f-hotkey").value="";
  document.querySelectorAll(".key-rec").forEach(b=>b.onclick=()=>startRecording(b.dataset.target,b));
  el("add-close").onclick=closeAdd; el("add-cancel").onclick=closeAdd; el("add-save").onclick=saveAdd;
  el("add-overlay").addEventListener("mousedown",e=>{if(e.target.id==="add-overlay")closeAdd();});
  el("add-iconbtn").onclick=()=>openIconPicker("add");
  el("add-browse").onclick=async()=>{const p=await call("pick_target_file");if(p){el("add-target").value=p;if(!el("add-name").value)el("add-name").value=p.split(/[\\/]/).pop().replace(/\.[^.]+$/,"");}};
  el("add-hotkey-rec").onclick=e=>startRecording("add-hotkey",e.currentTarget);
  el("add-hotkey-clr").onclick=()=>el("add-hotkey").value="";
  el("icon-close").onclick=closeIconPicker; el("icon-cancel").onclick=closeIconPicker;
  el("icon-overlay").addEventListener("mousedown",e=>{if(e.target.id==="icon-overlay")closeIconPicker();});
  document.querySelectorAll("#icon-overlay .ql-tab").forEach(t=>t.onclick=()=>setITab(t.dataset.itab));
  el("icon-search").addEventListener("input",e=>renderIcons(e.target.value));
  el("icon-pick-file").onclick=pickIconFile;
  el("icon-use-default").onclick=()=>chooseIcon({ image:"" });
  el("confirm-yes").onclick=()=>{if(confirmCb)confirmCb();hideConfirm();};
  el("confirm-no").onclick=hideConfirm;
  // lock screen
  el("lock-unlock").onclick=tryUnlock;
  el("lock-pw").addEventListener("keydown",e=>{ updateCaps(e); if(e.key==="Enter"){tryUnlock();e.preventDefault();} });
  el("lock-pw").addEventListener("input", ()=>{ renderPin(); });
  el("lock-pw").addEventListener("keyup", updateCaps);
  el("lock-pw").addEventListener("focus", renderPin);
  el("lock-pw").addEventListener("blur", renderPin);
  el("lock-pin").addEventListener("mousedown", e=>{ e.preventDefault(); el("lock-pw").focus(); });
  el("lock-reveal").onclick=()=>{ _pinReveal=!_pinReveal;
    el("lock-reveal").querySelector(".msr").textContent=_pinReveal?"visibility_off":"visibility";
    el("lock-reveal").lastChild.textContent = _pinReveal ? " Hide" : " Show";
    renderPin(); el("lock-pw").focus(); };
  el("lock-forgot").onclick=()=>{ el("lock-sub").textContent="Enter your master password"; el("lock-forgot").style.display="none"; el("lock-pw").placeholder="Master password"; el("lock-pw").focus(); };
  // security tab
  el("sec-enable").onclick=enableLock;
  el("sec-disable").onclick=disableLockUI;
  el("sec-master-save").onclick=async()=>{
    const v=el("sec-master").value;
    if(!isPin(v)){ el("sec-master-msg").textContent="Master code must be exactly 6 digits"; return; }
    const r=await call("set_master_password",v);
    if(r&&r.ok){ el("sec-master").value=""; el("sec-master-msg").textContent="Master code saved ✓"; LOCK.has_master=true; }
    else el("sec-master-msg").textContent=(r&&r.error)||"Could not save";
  };
  el("prof-add").onclick=addProfile;
  wireDnd();
}

function isPin(v){ return /^\d{6}$/.test(v||""); }

async function addProfile(){
  const name=el("prof-name").value.trim(), pw=el("prof-pw").value;
  if(!name){ el("prof-msg").textContent="Name required"; return; }
  if(!isPin(pw)){ el("prof-msg").textContent="Code must be exactly 6 digits"; return; }
  const r=await call("add_profile", name, pw, false);
  if(!r||!r.ok){ el("prof-msg").textContent=(r&&r.error)||"Could not add"; return; }
  el("prof-name").value=""; el("prof-pw").value=""; el("prof-msg").textContent="Added “"+name+"” ✓";
  fillSecurity();
}
async function loadProfiles(){
  const list=(await call("list_profiles"))||[];
  const box=el("prof-list"); box.innerHTML="";
  if(!list.length){ box.innerHTML='<div class="ql-note" style="opacity:.7">No alternate spaces yet.</div>'; }
  list.forEach(p=>{
    const d=document.createElement("div"); d.className="ql-prof-item";
    d.innerHTML=`<span class="msr">folder_shared</span><span class="pf-name">${esc(p.name)}</span>
      <button class="pf-del" title="Delete"><span class="msr">delete</span></button>`;
    d.querySelector(".pf-del").onclick=async()=>{ await call("delete_profile",p.id); fillSecurity(); };
    box.appendChild(d);
  });
}

async function enableLock(){
  const a=el("sec-pw1").value, b=el("sec-pw2").value;
  if (!isPin(a)){ el("sec-msg").textContent="Password must be exactly 6 digits"; return; }
  if (a!==b){ el("sec-msg").textContent="Codes don't match"; return; }
  const r=await call("set_password", a);
  if (!r||!r.ok){ el("sec-msg").textContent=(r&&r.error)||"Could not enable"; return; }
  LOCK={enabled:true, unlocked:true, has_master:LOCK.has_master};
  el("sec-pw1").value=""; el("sec-pw2").value=""; el("sec-msg").textContent="";
  flashStatus("Password lock enabled"); fillSecurity();
}
async function disableLockUI(){
  const pw=el("sec-pwcur").value;
  const ok=await call("disable_lock", pw);
  if (ok){ LOCK={enabled:false, unlocked:true}; el("sec-pwcur").value=""; el("sec-msg2").textContent=""; flashStatus("Lock disabled"); fillSecurity(); }
  else { el("sec-msg2").textContent="Incorrect password"; }
}
function fillSecurity(){
  el("sec-disabled").style.display = LOCK.enabled ? "none" : "block";
  el("sec-enabled").style.display = LOCK.enabled ? "block" : "none";
  if (LOCK.enabled) loadProfiles();
}

// Close/hide the window when it loses focus (Flow-Launcher style).
// Debounced + guarded so brief internal focus changes don't trigger it.
let _justShown = 0;
function wireBlurHide(){
  window.addEventListener("blur", () => {
    // ignore blur right after showing (window settling) and while typing in a
    // native control that the OS may briefly focus
    if (Date.now() - _justShown < 350) return;
    setTimeout(() => {
      // only hide if focus truly left the document
      if (!document.hasFocus()) call("hide_on_blur");
    }, 120);
  });
}

// Robustly focus an input: retries because WebView2 can be slow to accept
// focus right after the window is shown via a global hotkey.
function focusInput(target){
  let tries = 0;
  const tick = () => {
    const inDialog = el("overlay").classList.contains("show")
      || el("add-overlay").classList.contains("show")
      || el("icon-overlay").classList.contains("show");
    const elx = (LOCK.enabled && !LOCK.unlocked) ? el("lock-pw")
              : runnerOpen ? el("run-cmd")
              : inDialog ? null
              : el(target || "search");
    if (elx){
      try { window.focus(); } catch(e){}
      elx.focus();
      // place the caret at the end so typing goes straight in
      try { const v = elx.value; elx.value = ""; elx.value = v; } catch(e){}
      if (document.activeElement === elx) return;   // success
    }
    if (++tries < 12) setTimeout(tick, 40);
  };
  tick();
}
window.qlOnShow=function(){ _justShown=Date.now(); el("search").value=""; refreshLock(); doSearch(); focusInput("search"); };
window.qlAddShortcut=function(){ openAdd(); };
window.qlRunCommand=function(){ openRunner(""); };
window.qlOnScreenshot=function(r){ if(!r||!r.ok){ flashTop("Screenshot cancelled"); return; } flashTop(r.path==="clipboard"?"Screenshot copied to clipboard":"Saved "+(r.path.split(/[\\/]/).pop())); };

function bridgeReady(){
  return new Promise(resolve=>{
    if (window.pywebview&&window.pywebview.api) return resolve(true);
    let done=false; const finish=v=>{if(!done){done=true;resolve(v);}};
    window.addEventListener("pywebviewready",()=>finish(true),{once:true});
    let n=0; const t=setInterval(()=>{ if(window.pywebview&&window.pywebview.api){clearInterval(t);finish(true);} else if(++n>12){clearInterval(t);finish(false);} },50);
  });
}
async function init(){
  wireEvents(); await bridgeReady();
  const st=await call("get_state");
  if (st){ CONFIG=st.config||{}; THEMES=st.themes||{}; CAPS=st; LOCK={enabled:!!st.lock_enabled, unlocked:st.unlocked!==false}; }
  if (!Object.keys(THEMES).length) THEMES=MOCK._themes;
  if (!CONFIG.theme) CONFIG.theme=Object.keys(THEMES)[0];
  // version badge (About + lock subtitle)
  const ver = st && st.app_version ? `v${st.app_version} ${st.app_channel||""}`.trim() : "v1.0.0 Stable";
  const av = el("about-version"); if (av) av.textContent = ver;
  activeGroup=CONFIG.active_group||"All";
  applyTheme(CONFIG.theme); await doSearch();
  applyLockUI();
  focusInput("search");
}
document.addEventListener("DOMContentLoaded", init);
