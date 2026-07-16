import os
import time
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from db import init_db
from middleware import log_failed_requests

init_db()

app = FastAPI(title="Dragons Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://belovolovhome.ru", "https://vk.com", "https://m.vk.com", "https://id.vk.com", "https://vk.ru", "https://m.vk.ru", "https://id.vk.ru"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BaseHTTPMiddleware, dispatch=log_failed_requests)

from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.collection import router as collection_router
from routes.payment import router as payment_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(collection_router)
app.include_router(payment_router)

# Каталог изображений — корневой <repo>/images (туда же пишет services/dragon_service).
# Раздаём через /api/static/images/{rest:path} -> <repo>/images/{rest}.


IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images")


@app.get("/api/static/images/{rest:path}")
def serve_image(rest: str):
    filepath = os.path.normpath(os.path.join(IMAGES_DIR, rest))
    if os.path.isfile(filepath):
        return FileResponse(filepath)

    dirpart = os.path.dirname(filepath)
    namepart = os.path.basename(filepath)
    if os.path.isdir(dirpart):
        low = namepart.lower()
        for f in os.listdir(dirpart):
            if f.lower() == low:
                return FileResponse(os.path.join(dirpart, f))

    raise HTTPException(status_code=404)


@app.get("/api/")
def health():
    return {"status": "ok", "service": "dragons-api"}


@app.get("/api/diag")
def diag(request: Request):
    t0 = time.time()
    headers = {k: v for k, v in request.headers.items()}
    t1 = time.time()
    return {
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
        "client_ip": request.client.host if request.client else "unknown",
        "client_port": request.client.port if request.client else 0,
        "headers": headers,
        "response_gen_ms": round((t1 - t0) * 1000, 1),
        "content_type": headers.get("content-type", "none"),
        "accept": headers.get("accept", "none"),
        "accept_encoding": headers.get("accept-encoding", "none"),
        "user_agent": headers.get("user-agent", "none"),
        "origin": headers.get("origin", "none"),
        "referer": headers.get("referer", "none"),
        "via": headers.get("via", "none"),
        "x_forwarded_for": headers.get("x-forwarded-for", "none"),
        "x_forwarded_proto": headers.get("x-forwarded-proto", "none"),
    }


DIAG_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>diagnostic</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font:16px/1.5 monospace;background:#111;color:#ddd;padding:16px}
h2{color:#9f9;margin:16px 0 8px;font-size:18px}
.card{background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:12px;margin:8px 0}
.err{color:#f66}.ok{color:#6f6}.info{color:#99f}.warn{color:#fc6}
pre{white-space:pre-wrap;word-break:break-all;font-size:13px;max-height:400px;overflow-y:auto}
button{background:#334;color:#ddd;border:1px solid #555;padding:8px 16px;border-radius:4px;cursor:pointer;margin:4px;font:inherit}
button:hover{background:#445}
#status{height:4px;background:#333;border-radius:2px;margin:8px 0}
#status.ok{background:#5a5}#status.err{background:#a55}#status.load{background:#559;animation:pulse 0.8s infinite}
@keyframes pulse{50%{opacity:.4}}
.cell{display:inline-block;min-width:140px;padding:2px 0} .key{color:#888} .val{color:#ddd}
</style>
</head>
<body>
<h1 style="color:#9cf">diagnostic</h1>
<div id="status"></div>
<div id="root"></div>
<script>
const $=(s)=>document.getElementById(s);
const api='/dragons/api/diag';
const root=$('root');
const status=$('status');

function setStatus(s){status.className=s}

async function run(){
  setStatus('load');
  root.innerHTML='<div class="info">connecting…</div>';

  let diag=null, health=null, err=null;
  const t0=performance.now();

  try{
    const r=await fetch(api);
    const t1=performance.now();
    diag=await r.json();
    diag._roundtrip_ms=Math.round(t1-t0);
  }catch(e){
    err=e.message||'fetch failed';
  }

  try{
    const r2=await fetch('/dragons/api/');
    health=await r2.json();
  }catch(e){}

  setStatus(err?'err':'ok');
  let html='';

  if(err){
    html+='<div class="card"><h2 class="err">CONNECTION FAILED</h2>';
    html+='<div class="err">'+err+'</div>';
    html+='<div class="info" style="margin-top:8px">The server did not respond. Check:</div>';
    html+='<ul style="margin:8px 0 0 20px;font-size:14px">';
    html+='<li>DNS resolution: does <code>belovolovhome.ru</code> resolve?</li>';
    html+='<li>IPv6: does your carrier use IPv6-only with NAT64?</li>';
    html+='<li>TLS: is the certificate valid? Try <code>curl -vI '+location.origin+'</code></li>';
    html+='<li>Firewall: is port 443 open?</li>';
    html+='</ul></div>';
  } else if(diag){
    const d=diag;
    html+='<div class="card"><h2 class="ok">CONNECTED</h2>';
    html+='<div class="cell"><span class="key">roundtrip:</span> <span class="val">'+d._roundtrip_ms+' ms</span></div>';
    html+='<div class="cell"><span class="key">server time:</span> <span class="val">'+d.server_time+'</span></div>';
    html+='<div class="cell"><span class="key">client IP:</span> <span class="val">'+d.client_ip+'</span></div><br>';
    html+='<div class="cell"><span class="key">origin:</span> <span class="val">'+d.origin+'</span></div>';
    html+='<div class="cell"><span class="key">referer:</span> <span class="val">'+d.referer+'</span></div><br>';
    html+='<div class="cell"><span class="key">user-agent:</span> <span class="val">'+d.user_agent+'</span></div><br>';
    html+='<div class="cell"><span class="key">via:</span> <span class="val">'+(d.via==='none'?'<span class="ok">no proxy</span>':'<span class="warn">PROXIED: '+d.via+'</span>')+'</span></div>';
    html+='<div class="cell"><span class="key">x-forwarded-for:</span> <span class="val">'+d.x_forwarded_for+'</span></div><br>';
    html+='<div class="cell"><span class="key">accept-encoding:</span> <span class="val">'+d.accept_encoding+'</span></div><br>';
    html+='<div class="cell"><span class="key">content-type:</span> <span class="val">'+d.content_type+'</span></div>';

    if(d.response_gen_ms>100){
      html+='<div class="card" style="margin-top:8px"><span class="warn">SLOW: server response generation took '+d.response_gen_ms+' ms</span></div>';
    }
    if(d.via!=='none'){
      html+='<div class="card" style="margin-top:8px"><span class="warn">PROXY DETECTED via: '+d.via+'. Carrier may be modifying HTTP traffic.</span></div>';
    }
    html+='</div>';
  }

  if(health){
    html+='<div class="card"><span class="ok">HEALTH: '+health.status+'</span></div>';
  }

  html+='<div class="card"><h2>all headers</h2><pre>'+JSON.stringify((diag||{}).headers,null,2)+'</pre></div>';
  html+='<div style="margin:16px 0"><button onclick="run()">retry</button></div>';
  root.innerHTML=html;
}
run();
</script>
</body>
</html>"""


@app.get("/api/diag/page", response_class=HTMLResponse)
def diag_page():
    return HTMLResponse(content=DIAG_HTML)
