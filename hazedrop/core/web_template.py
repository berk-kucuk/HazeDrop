HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HazeDrop</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#000;--bg-panel:#080808;--bg-elevated:#0f0f0f;--bg-hover:#161616;
  --border:#1c1c1c;--border-focus:#2e2e2e;--border-active:#444;
  --text:#f0f0f0;--text-dim:#555;--text-muted:#2a2a2a;
  --accent:#fff;--accent-dim:#888;
  --success:#22c55e;--error:#ef4444;
}
html,body{height:100%}
body{
  background:var(--bg);color:var(--text);
  font-family:"Inter","SF Pro Text","Segoe UI",system-ui,sans-serif;
  font-size:14px;display:flex;flex-direction:column;min-height:100vh;
}

/* ── Title bar ─────────────────────────────────── */
.title-bar{
  background:rgba(4,4,6,1);border-bottom:1px solid #141414;
  height:44px;display:flex;align-items:center;gap:12px;padding:0 20px;
  flex-shrink:0;
}
.app-name{font-size:13px;font-weight:800;letter-spacing:5px;color:#fff}
.badge{
  font-size:9px;font-weight:700;letter-spacing:1.5px;color:#333;
  border:1px solid #1e1e1e;border-radius:3px;padding:3px 8px;
  transition:all .3s;
}
.badge.active{background:rgba(0,30,8,.86);color:var(--success);border-color:#0a2e12}

/* ── Main area ─────────────────────────────────── */
.main{flex:1;display:flex;align-items:center;justify-content:center;padding:40px 16px}

/* ── Card ──────────────────────────────────────── */
.card{
  background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;
  width:100%;max-width:480px;padding:32px;
}

.section-title{
  font-size:11px;font-weight:600;letter-spacing:2.5px;color:var(--text);
  margin-bottom:22px;
}
.separator{height:1px;background:var(--border);margin:24px 0}

/* ── File info ─────────────────────────────────── */
.file-row{display:flex;align-items:flex-start;gap:14px;margin-bottom:10px}
.file-icon{font-size:20px;color:var(--text);line-height:1.3;flex-shrink:0}
.file-name{font-size:15px;font-weight:600;word-break:break-all;line-height:1.4}
.file-meta{
  display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;
  font-size:11px;color:var(--text-dim);letter-spacing:.3px;
}
.meta-chip{
  background:var(--bg-elevated);border:1px solid var(--border);
  border-radius:3px;padding:2px 7px;font-size:10px;
  letter-spacing:.5px;color:var(--text-dim);
}
.meta-chip.once{color:var(--error);border-color:#2a1010}

/* ── Form ──────────────────────────────────────── */
.field-label{
  font-size:11px;font-weight:500;letter-spacing:.5px;
  color:var(--text-dim);margin-bottom:8px;
}
.input-row{display:flex;gap:6px;margin-bottom:20px}
input[type="password"],input[type="text"]{
  flex:1;background:var(--bg-elevated);color:var(--text);
  border:1px solid var(--border);border-radius:4px;
  padding:10px 12px;font-size:13px;font-family:inherit;
  outline:none;transition:border-color .15s,background .15s;
}
input:focus{border-color:var(--border-active);background:var(--bg-hover)}
input::placeholder{color:var(--text-muted)}
.btn-ghost{
  background:transparent;color:var(--text-dim);
  border:1px solid var(--border);border-radius:3px;
  padding:8px 12px;font-size:11px;font-weight:500;
  cursor:pointer;font-family:inherit;white-space:nowrap;
  transition:all .1s;
}
.btn-ghost:hover{border-color:var(--border-focus);color:var(--text)}

/* ── Primary button ────────────────────────────── */
.btn-primary{
  width:100%;background:var(--accent);color:#000;border:none;
  border-radius:4px;padding:13px 28px;font-size:12px;
  font-weight:700;letter-spacing:2px;cursor:pointer;
  font-family:inherit;transition:background .1s;
}
.btn-primary:hover:not(:disabled){background:#e8e8e8}
.btn-primary:disabled{background:var(--border);color:var(--text-muted);cursor:default}

/* ── Status ────────────────────────────────────── */
.status-row{display:flex;align-items:center;gap:8px;margin-top:20px}
.dot{font-size:7px;color:var(--text-muted)}
.dot.active{color:var(--accent)}
.dot.success{color:var(--success)}
.dot.error{color:var(--error)}
.status-text{font-size:12px;color:var(--text-dim)}
.status-text.active{color:var(--text)}
.status-text.success{color:var(--success)}
.status-text.error{color:var(--error)}

/* ── Progress bar ──────────────────────────────── */
.progress-wrap{
  height:3px;background:var(--bg-elevated);border-radius:2px;
  margin-top:14px;overflow:hidden;display:none;
}
.progress-fill{height:100%;background:var(--accent);border-radius:2px;width:0%;transition:width .2s}
.indeterminate .progress-fill{
  width:40%!important;animation:indeterminate 1.4s ease-in-out infinite;
}
@keyframes indeterminate{
  0%{transform:translateX(-100%)} 60%{transform:translateX(250%)} 100%{transform:translateX(250%)}
}

/* ── Expired / error state ─────────────────────── */
.expired-card{text-align:center;padding:12px 0}
.expired-icon{font-size:28px;color:var(--text-muted);margin-bottom:14px}
.expired-title{font-size:14px;font-weight:600;margin-bottom:8px}
.expired-sub{font-size:12px;color:var(--text-dim)}

/* ── Loading skeleton ──────────────────────────── */
.skeleton{
  background:var(--bg-elevated);border-radius:3px;
  animation:shimmer 1.5s ease-in-out infinite;
}
@keyframes shimmer{
  0%,100%{opacity:.4} 50%{opacity:.8}
}
@keyframes pulse-dot{
  0%,100%{opacity:1} 50%{opacity:.2}
}
.dot.active{animation:pulse-dot .8s ease-in-out infinite}

/* ── Footer ────────────────────────────────────── */
footer{
  text-align:center;padding:18px;
  font-size:10px;color:var(--text-muted);letter-spacing:.8px;
  border-top:1px solid #0a0a0a;
}
</style>
</head>
<body>

<div class="title-bar">
  <span class="app-name">HAZEDROP</span>
  <span class="badge active" id="badge">HAZE PROTOCOL V2</span>
</div>

<div class="main">
  <div class="card">

    <!-- Loading state -->
    <div id="view-loading">
      <div class="section-title">RECEIVE FILE</div>
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px">
        <span class="skeleton" style="width:20px;height:20px;border-radius:3px"></span>
        <span class="skeleton" style="height:16px;width:60%;border-radius:3px"></span>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:24px">
        <span class="skeleton" style="height:20px;width:60px;border-radius:3px"></span>
        <span class="skeleton" style="height:20px;width:80px;border-radius:3px"></span>
      </div>
      <div class="separator"></div>
      <span class="skeleton" style="display:block;height:42px;border-radius:4px;margin-top:24px"></span>
    </div>

    <!-- Main content -->
    <div id="view-content" style="display:none">
      <div class="section-title">RECEIVE FILE</div>

      <div class="file-row">
        <span class="file-icon">◆</span>
        <div style="flex:1;min-width:0">
          <div class="file-name" id="filename"></div>
          <div class="file-meta">
            <span id="meta-size"></span>
            <span id="meta-expiry"></span>
          </div>
        </div>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px" id="meta-chips"></div>

      <div class="separator"></div>

      <div id="pw-section">
        <div class="field-label">PASSWORD</div>
        <div class="input-row">
          <input type="password" id="pw-input" placeholder="Enter password to download">
          <button class="btn-ghost" id="pw-show-btn" onclick="togglePw()">show</button>
        </div>
      </div>

      <button class="btn-primary" id="dl-btn" onclick="startDownload()">DOWNLOAD FILE</button>

      <div class="status-row" id="status-row" style="display:none">
        <span class="dot" id="status-dot">●</span>
        <span class="status-text" id="status-text"></span>
      </div>
      <div class="progress-wrap" id="progress-wrap">
        <div class="progress-fill" id="progress-fill"></div>
      </div>
    </div>

    <!-- Expired state -->
    <div id="view-expired" style="display:none" class="expired-card">
      <div class="expired-icon">◌</div>
      <div class="expired-title">File no longer available</div>
      <div class="expired-sub">This file has expired or has already been downloaded.</div>
    </div>

  </div>
</div>

<footer>HAZEDROP &nbsp;·&nbsp; HAZE PROTOCOL V2 &nbsp;·&nbsp; ANONYMOUS ENCRYPTED FILE TRANSFER</footer>

<script>
"use strict";
var info=null,pwVisible=false;

function show(id){['view-loading','view-content','view-expired'].forEach(function(v){
  document.getElementById(v).style.display=v===id?'block':'none';
});}

function fmtBytes(b){
  if(b<1024)return b+' B';
  if(b<1048576)return(b/1024).toFixed(1)+' KB';
  if(b<1073741824)return(b/1048576).toFixed(1)+' MB';
  return(b/1073741824).toFixed(1)+' GB';
}

function fmtExpiry(ts){
  if(!ts)return'';
  var d=ts-Math.floor(Date.now()/1000);
  if(d<=0)return'expired';
  var h=Math.floor(d/3600),m=Math.floor((d%3600)/60),s=d%60;
  if(h>0)return'expires in '+h+'h '+m+'m';
  if(m>0)return'expires in '+m+'m '+s+'s';
  return'expires in '+s+'s';
}

function setStatus(text,style){
  var row=document.getElementById('status-row');
  var dot=document.getElementById('status-dot');
  var txt=document.getElementById('status-text');
  row.style.display='flex';
  dot.className='dot '+style;
  txt.className='status-text '+style;
  txt.textContent=text;
}

function setProgress(pct,indeterminate){
  var wrap=document.getElementById('progress-wrap');
  var fill=document.getElementById('progress-fill');
  wrap.style.display='block';
  if(indeterminate){wrap.classList.add('indeterminate');}
  else{wrap.classList.remove('indeterminate');fill.style.width=pct+'%';}
}

function togglePw(){
  pwVisible=!pwVisible;
  document.getElementById('pw-input').type=pwVisible?'text':'password';
  document.getElementById('pw-show-btn').textContent=pwVisible?'hide':'show';
}

function chip(text,cls){
  var s=document.createElement('span');
  s.className='meta-chip'+(cls?' '+cls:'');
  s.textContent=text;
  return s;
}

async function loadInfo(){
  try{
    var r=await fetch('/info');
    if(r.status===410){show('view-expired');return;}
    if(!r.ok){throw new Error('HTTP '+r.status);}
    info=await r.json();

    document.getElementById('filename').textContent=info.filename;
    document.getElementById('meta-size').textContent=fmtBytes(info.size);

    var chips=document.getElementById('meta-chips');
    chips.innerHTML='';
    if(info.once)chips.appendChild(chip('self-destructs after download','once'));
    if(info.password_required)chips.appendChild(chip('password protected'));
    if(info.downloads>0)chips.appendChild(chip(info.downloads+' download'+(info.downloads!==1?'s':'')));

    if(!info.password_required)document.getElementById('pw-section').style.display='none';

    if(info.expires_at){
      var expEl=document.getElementById('meta-expiry');
      expEl.textContent=fmtExpiry(info.expires_at);
      setInterval(function(){expEl.textContent=fmtExpiry(info.expires_at);},1000);
    }

    show('view-content');
    document.getElementById('badge').textContent='HAZE PROTOCOL V2';
  }catch(e){
    show('view-loading');
    document.querySelector('#view-loading .section-title').textContent='CONNECTION ERROR';
    document.querySelector('#view-loading').innerHTML+='<p style="color:#555;font-size:12px;margin-top:16px">'+e.message+'</p>';
  }
}

async function startDownload(){
  if(!info)return;
  var btn=document.getElementById('dl-btn');
  var pw=document.getElementById('pw-input').value;

  if(info.password_required&&!pw){
    setStatus('Password required','error');
    document.getElementById('pw-input').focus();
    return;
  }

  btn.disabled=true;
  setStatus('Connecting…','active');
  setProgress(0,true);

  try{
    var body={};
    if(info.password_required)body.password=pw;

    var resp=await fetch('/web-download',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)
    });

    if(resp.status===401){setStatus('Wrong password','error');btn.disabled=false;return;}
    if(resp.status===410){setStatus('File expired or already downloaded','error');return;}
    if(!resp.ok){setStatus('Error: HTTP '+resp.status,'error');btn.disabled=false;return;}

    var total=parseInt(resp.headers.get('Content-Length')||'0');
    var fname=resp.headers.get('X-HazeDrop-Filename')||info.filename;
    var reader=resp.body.getReader();
    var chunks=[],received=0;

    setProgress(0,false);
    setStatus('Downloading…','active');

    while(true){
      var _a=await reader.read(),done=_a.done,value=_a.value;
      if(done)break;
      chunks.push(value);
      received+=value.length;
      if(total){
        setProgress(Math.round(received/total*100),false);
        setStatus('Downloading  '+fmtBytes(received)+' / '+fmtBytes(total),'active');
      }else{
        setStatus('Downloading  '+fmtBytes(received),'active');
      }
    }

    setProgress(100,false);

    var blob=new Blob(chunks);
    var url=URL.createObjectURL(blob);
    var a=document.createElement('a');
    a.href=url;a.download=fname;
    document.body.appendChild(a);a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setStatus('Saved — '+fname,'success');

  }catch(e){
    setStatus('Error: '+e.message,'error');
    btn.disabled=false;
  }
}

loadInfo();
</script>
</body>
</html>"""
