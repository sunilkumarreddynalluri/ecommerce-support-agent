from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app import config
from app.agent import chat
from app.tools import _read, _write

app = FastAPI(title="E-commerce Support Agent")


class ChatIn(BaseModel):
    message: str
    session_id: str = "default"


@app.post("/api/chat")
def chat_endpoint(body: ChatIn):
    reply, tools = chat(body.message, body.session_id)
    return {"reply": reply, "tools_used": tools}


@app.get("/api/refunds")
def refunds():
    return _read(config.REFUNDS_FILE, [])


@app.post("/api/refunds/{refund_id}/approve")
def approve(refund_id: str):
    """The human-in-the-loop step: only a person can approve a refund."""
    data = _read(config.REFUNDS_FILE, [])
    for r in data:
        if r["refund_id"] == refund_id:
            r["status"] = "approved"
            _write(config.REFUNDS_FILE, data)
            return r
    raise HTTPException(404, "refund not found")


@app.get("/api/escalations")
def escalations():
    return _read(config.ESCALATIONS_FILE, [])


PAGE = """<!doctype html><meta charset=utf-8><title>Support Agent</title>
<style>body{font-family:system-ui;margin:0;background:#111;color:#eee;display:flex;height:100vh}
#c{flex:2;display:flex;flex-direction:column;padding:16px}#side{flex:1;padding:16px;border-left:1px solid #333;overflow:auto}
#log{flex:1;overflow:auto}.m{margin:8px 0;padding:8px 12px;border-radius:8px;max-width:80%;white-space:pre-wrap}
.u{background:#2a4d8f;margin-left:auto}.a{background:#222}.t{font-size:11px;color:#888;margin-top:4px}
input{flex:1;padding:10px;border-radius:6px;border:1px solid #444;background:#1c1c1c;color:#eee}
button{padding:10px 16px;border-radius:6px;border:0;background:#3b82f6;color:#fff;cursor:pointer}
.r{background:#1c1c1c;padding:8px;margin:6px 0;border-radius:6px;font-size:13px}</style>
<div id=c><h3>Support Chat</h3><div id=log></div>
<div style="display:flex;gap:8px"><input id=i placeholder="Try: Where is my order 1002? bob@example.com" onkeydown="if(event.key=='Enter')send()"><button onclick=send()>Send</button></div></div>
<div id=side><h3>Human approval queue</h3><div id=q></div></div>
<script>
const sid=Math.random().toString(36).slice(2);
function add(t,c,tools){const d=document.createElement('div');d.className='m '+c;d.textContent=t;
 if(tools&&tools.length){const s=document.createElement('div');s.className='t';s.textContent='tools: '+tools.join(', ');d.appendChild(s)}
 log.appendChild(d);log.scrollTop=log.scrollHeight}
async function send(){const m=i.value.trim();if(!m)return;i.value='';add(m,'u');
 const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:m,session_id:sid})});
 const d=await r.json();add(d.reply,'a',d.tools_used);loadQ()}
async function loadQ(){const d=await (await fetch('/api/refunds')).json();
 q.innerHTML=d.map(r=>`<div class=r><b>${r.refund_id}</b> order ${r.order_id} · $${r.amount} · ${r.reason}<br>${r.status}
 ${r.status!='approved'?`<br><button onclick="ap('${r.refund_id}')">Approve</button>`:''}</div>`).join('')}
async function ap(id){await fetch('/api/refunds/'+id+'/approve',{method:'POST'});loadQ()}
loadQ();
</script>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE
