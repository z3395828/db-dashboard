import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler
import psycopg2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# ========== CockroachDB ==========
def query_cockroachdb(sql):
    conn = psycopg2.connect(
        host=os.environ.get("COCKROACH_HOST", "dyed-muskox-27479.j77.aws-ap-southeast-1.cockroachlabs.cloud"),
        port=int(os.environ.get("COCKROACH_PORT", "26257")),
        user=os.environ.get("COCKROACH_USER", "zhangbowen"),
        password=os.environ.get("COCKROACH_PASSWORD", "9CNaITmol_9RWsG2TaNVDw"),
        dbname=os.environ.get("COCKROACH_DB", "defaultdb"),
        sslmode="require"
    )
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return cols, rows

# ========== Turso ==========
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")
TURSO_URL = os.environ.get("TURSO_URL", "https://zhangbowenmain-zhangbowen.aws-ap-south-1.turso.io/v2/pipeline")

def query_turso(sql):
    body = json.dumps({"requests": [{"type": "execute", "stmt": {"sql": sql}}]}).encode()
    req = urllib.request.Request(TURSO_URL, data=body, headers={
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    })
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read().decode())
    result = data["results"][0]["response"]["result"]
    cols = [c["name"] for c in result["cols"]]
    rows = [[v["value"] for v in row] for row in result["rows"]]
    return cols, rows

@app.get("/api/cockroachdb/tables")
def get_cockroachdb_tables():
    cols, rows = query_cockroachdb("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    return {"tables": [r[0] for r in rows]}

@app.get("/api/cockroachdb/query")
def cockroachdb_query(table: str = "test_write"):
    cols, rows = query_cockroachdb(f'SELECT * FROM "{table}" LIMIT 100')
    return {"columns": cols, "rows": [[str(c) for c in r] for r in rows]}

@app.get("/api/turso/tables")
def get_turso_tables():
    cols, rows = query_turso("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {"tables": [r[0] for r in rows]}

@app.get("/api/turso/query")
def turso_query(table: str = "test_write"):
    cols, rows = query_turso(f'SELECT * FROM "{table}" LIMIT 100')
    return {"columns": cols, "rows": [[str(c) for c in r] for r in rows]}

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>数据库面板</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e4e4e7; min-height: 100vh; }
.header { background: linear-gradient(135deg, #1a1b23 0%, #252630 100%); padding: 24px 32px; border-bottom: 1px solid #2a2b35; }
.header h1 { font-size: 24px; font-weight: 600; color: #fff; }
.header p { color: #71717a; margin-top: 4px; font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.tabs { display: flex; gap: 8px; margin-bottom: 20px; }
.tab { padding: 10px 20px; border-radius: 8px; border: 1px solid #2a2b35; background: #1a1b23; color: #a1a1aa; cursor: pointer; font-size: 14px; transition: all 0.2s; }
.tab:hover { border-color: #3b82f6; color: #e4e4e7; }
.tab.active { background: #3b82f6; border-color: #3b82f6; color: #fff; }
.info-bar { display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.info-card { background: #1a1b23; border: 1px solid #2a2b35; border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 200px; }
.info-card .label { font-size: 12px; color: #71717a; text-transform: uppercase; letter-spacing: 0.5px; }
.info-card .value { font-size: 20px; font-weight: 600; color: #fff; margin-top: 4px; }
.info-card .sub { font-size: 12px; color: #52525b; margin-top: 2px; }
.table-selector { margin-bottom: 16px; }
.table-selector select { background: #1a1b23; border: 1px solid #2a2b35; color: #e4e4e7; padding: 8px 12px; border-radius: 6px; font-size: 14px; min-width: 200px; }
.table-wrap { background: #1a1b23; border: 1px solid #2a2b35; border-radius: 12px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; }
th { background: #252630; padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid #2a2b35; position: sticky; top: 0; }
td { padding: 10px 16px; font-size: 14px; border-bottom: 1px solid #1f2028; font-family: 'SF Mono', 'Fira Code', monospace; }
tr:hover td { background: #1f2028; }
.loading { text-align: center; padding: 40px; color: #71717a; }
.error { color: #ef4444; padding: 16px; background: #1a1b23; border-radius: 8px; border: 1px solid #7f1d1d; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.badge-green { background: #064e3b; color: #34d399; }
.refresh-btn { background: #252630; border: 1px solid #2a2b35; color: #e4e4e7; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.refresh-btn:hover { background: #3b82f6; border-color: #3b82f6; }
.row-count { font-size: 13px; color: #71717a; }
</style>
</head>
<body>
<div class="header">
  <h1>📊 数据库面板</h1>
  <p>CockroachDB + Turso 双数据库管理</p>
</div>
<div class="container">
  <div class="tabs">
    <button class="tab active" onclick="switchDb('cockroachdb')">🐘 CockroachDB</button>
    <button class="tab" onclick="switchDb('turso')">⚡ Turso</button>
  </div>
  <div class="info-bar">
    <div class="info-card">
      <div class="label">数据库</div>
      <div class="value" id="db-name">CockroachDB</div>
      <div class="sub" id="db-type">PostgreSQL 兼容</div>
    </div>
    <div class="info-card">
      <div class="label">状态</div>
      <div class="value"><span class="badge badge-green" id="db-status">已连接</span></div>
      <div class="sub" id="db-region">AWS Singapore</div>
    </div>
    <div class="info-card">
      <div class="label">当前表</div>
      <div class="value" id="current-table">-</div>
      <div class="sub row-count" id="row-count">-</div>
    </div>
  </div>
  <div class="table-selector">
    <select id="table-select" onchange="loadTable()">
      <option>加载中...</option>
    </select>
    <button class="refresh-btn" onclick="loadTable()" style="margin-left: 8px;">🔄 刷新</button>
  </div>
  <div class="table-wrap">
    <div id="table-content" class="loading">加载中...</div>
  </div>
</div>
<script>
let currentDb='cockroachdb';
let tables={};
async function switchDb(db){
  currentDb=db;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  event.target.classList.add('active');
  if(db==='cockroachdb'){document.getElementById('db-name').textContent='CockroachDB';document.getElementById('db-type').textContent='PostgreSQL 兼容';document.getElementById('db-region').textContent='AWS Singapore';}
  else{document.getElementById('db-name').textContent='Turso';document.getElementById('db-type').textContent='SQLite 边缘分布式';document.getElementById('db-region').textContent='AWS Mumbai';}
  await loadTables();
}
async function loadTables(){
  const select=document.getElementById('table-select');
  select.innerHTML='<option>加载中...</option>';
  try{const resp=await fetch(`/api/${currentDb}/tables`);const data=await resp.json();tables[currentDb]=data.tables;select.innerHTML=data.tables.map(t=>`<option value="${t}">${t}</option>`).join('');if(data.tables.length>0)loadTable();}catch(e){select.innerHTML='<option>加载失败</option>';}
}
async function loadTable(){
  const table=document.getElementById('table-select').value;
  document.getElementById('current-table').textContent=table;
  document.getElementById('table-content').innerHTML='<div class="loading">查询中...</div>';
  try{
    const resp=await fetch(`/api/${currentDb}/query?table=${encodeURIComponent(table)}`);
    const data=await resp.json();
    document.getElementById('row-count').textContent=`${data.rows.length} 行`;
    if(data.rows.length===0){document.getElementById('table-content').innerHTML='<div class="loading">表为空</div>';return;}
    let html='<table><thead><tr>';
    data.columns.forEach(c=>html+=`<th>${c}</th>`);
    html+='</tr></thead><tbody>';
    data.rows.forEach(row=>{html+='<tr>';row.forEach(cell=>html+=`<td>${cell}</td>`);html+='</tr>';});
    html+='</tbody></table>';
    document.getElementById('table-content').innerHTML=html;
  }catch(e){document.getElementById('table-content').innerHTML=`<div class="error">查询失败: ${e.message}</div>`;}
}
loadTables();
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE
