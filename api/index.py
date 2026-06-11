import os
import json
import urllib.request
import psycopg2
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI()

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

TURSO_TOKEN=os.environ.get("TURSO_TOKEN", "")
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
    cols, rows = query_cockroachdb(f'SELECT * FROM "{table}" LIMIT 500')
    return {"columns": cols, "rows": [[str(c) for c in r] for r in rows]}

@app.get("/api/cockroachdb/sql")
def cockroachdb_sql(q: str = Query(...)):
    cols, rows = query_cockroachdb(q)
    return {"columns": cols, "rows": [[str(c) for c in r] for r in rows]}

@app.get("/api/turso/tables")
def get_turso_tables():
    cols, rows = query_turso("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {"tables": [r[0] for r in rows]}

@app.get("/api/turso/query")
def turso_query(table: str = "test_write"):
    cols, rows = query_turso(f'SELECT * FROM "{table}" LIMIT 500')
    return {"columns": cols, "rows": [[str(c) for c in r] for r in rows]}

@app.get("/api/turso/sql")
def turso_sql(q: str = Query(...)):
    cols, rows = query_turso(q)
    return {"columns": cols, "rows": [[str(c) for c in r] for r in rows]}

@app.get("/", response_class=HTMLResponse)
def index():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>数据库面板</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0a0b0f;--card:#12131a;--border:#1e1f2e;--text:#e4e4e7;--dim:#71717a;--accent:#3b82f6;--accent2:#8b5cf6;--green:#10b981;--red:#ef4444;--hover:#1a1b26}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.header{background:linear-gradient(135deg,#0f1018 0%,#1a1b2e 100%);padding:28px 36px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}
.header-left{display:flex;align-items:center;gap:16px}
.logo{width:42px;height:42px;background:linear-gradient(135deg,var(--accent),var(--accent2));border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px}
.header h1{font-size:22px;font-weight:700;letter-spacing:-0.5px}
.header p{color:var(--dim);font-size:13px;margin-top:2px}
.tabs{display:flex;gap:6px}
.tab{padding:9px 18px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--dim);cursor:pointer;font-size:13px;font-weight:500;transition:all .2s;display:flex;align-items:center;gap:6px}
.tab:hover{border-color:var(--accent);color:var(--text);background:rgba(59,130,246,.06)}
.tab.active{background:var(--accent);border-color:var(--accent);color:#fff;box-shadow:0 0 20px rgba(59,130,246,.25)}
.container{max-width:1400px;margin:0 auto;padding:24px 32px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px;transition:border-color .2s}
.stat:hover{border-color:var(--accent)}
.stat .label{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:1px;font-weight:600}
.stat .value{font-size:22px;font-weight:700;margin-top:6px;display:flex;align-items:center;gap:8px}
.stat .sub{font-size:12px;color:#52525b;margin-top:4px}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.badge-green{background:rgba(16,185,129,.12);color:var(--green)}
.badge-green::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.toolbar{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:center}
.toolbar select{background:var(--card);border:1px solid var(--border);color:var(--text);padding:8px 14px;border-radius:8px;font-size:13px;min-width:180px;cursor:pointer;transition:border-color .2s}
.toolbar select:hover{border-color:var(--accent)}
.toolbar select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(59,130,246,.15)}
.btn{padding:8px 16px;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text);cursor:pointer;font-size:13px;font-weight:500;transition:all .15s;display:flex;align-items:center;gap:6px}
.btn:hover{background:var(--hover);border-color:var(--accent)}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-primary:hover{background:#2563eb}
.search-box{flex:1;min-width:200px;position:relative}
.search-box input{width:100%;background:var(--card);border:1px solid var(--border);color:var(--text);padding:8px 14px 8px 36px;border-radius:8px;font-size:13px;transition:border-color .2s}
.search-box input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(59,130,246,.15)}
.search-box input::placeholder{color:#52525b}
.search-box svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--dim);pointer-events:none}
.table-wrap{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.table-inner{overflow-x:auto;max-height:65vh;overflow-y:auto}
table{width:100%;border-collapse:collapse}
th{background:#161722;padding:12px 18px;text-align:left;font-size:11px;font-weight:700;color:var(--dim);text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:10;cursor:pointer;user-select:none;white-space:nowrap}
th:hover{color:var(--text)}
th .sort-icon{opacity:.3;margin-left:4px;font-size:10px}
th.sorted .sort-icon{opacity:1;color:var(--accent)}
td{padding:10px 18px;font-size:13px;border-bottom:1px solid rgba(30,31,46,.5);font-family:'SF Mono','Fira Code','JetBrains Mono',monospace;font-size:12px;white-space:nowrap}
tr:hover td{background:rgba(59,130,246,.04)}
tr:nth-child(even) td{background:rgba(255,255,255,.015)}
tr:nth-child(even):hover td{background:rgba(59,130,246,.06)}
.loading{text-align:center;padding:60px 20px;color:var(--dim)}
.spinner{display:inline-block;width:28px;height:28px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite;margin-bottom:12px}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{text-align:center;padding:60px 20px;color:var(--dim)}
.empty svg{width:48px;height:48px;margin-bottom:12px;opacity:.3}
.error{color:var(--red);padding:16px 20px;background:rgba(239,68,68,.06);border-radius:10px;border:1px solid rgba(239,68,68,.2);margin:16px;font-size:13px}
.table-footer{display:flex;justify-content:space-between;align-items:center;padding:12px 18px;border-top:1px solid var(--border);font-size:12px;color:var(--dim)}
.sql-panel{margin-top:24px;background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.sql-header{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--border)}
.sql-header h3{font-size:14px;font-weight:600;display:flex;align-items:center;gap:8px}
.sql-body{display:flex;flex-direction:column}
.sql-editor{width:100%;min-height:80px;background:transparent;border:none;color:var(--text);padding:14px 18px;font-family:'SF Mono','Fira Code','JetBrains Mono',monospace;font-size:13px;resize:vertical}
.sql-editor:focus{outline:none}
.sql-editor::placeholder{color:#52525b}
.sql-actions{display:flex;gap:8px;padding:0 18px 14px;justify-content:space-between;align-items:center}
.sql-hint{font-size:11px;color:#52525b}
.sql-result{border-top:1px solid var(--border);max-height:300px;overflow:auto}
.toast{position:fixed;top:20px;right:20px;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:500;z-index:1000;transform:translateX(120%);transition:transform .3s ease}
.toast.show{transform:translateX(0)}
.toast-success{background:#065f46;color:#6ee7b7;border:1px solid #10b981}
.toast-error{background:#7f1d1d;color:#fca5a5;border:1px solid #ef4444}
@media(max-width:768px){
  .header{padding:20px}
  .container{padding:16px}
  .stats{grid-template-columns:1fr 1fr}
  .toolbar{flex-direction:column}
  .search-box{min-width:100%}
}
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <div class="logo">📊</div>
    <div>
      <h1>数据库面板</h1>
      <p>CockroachDB + Turso 双数据库管理</p>
    </div>
  </div>
  <div class="tabs">
    <button class="tab active" onclick="switchDb('cockroachdb')">🐘 CockroachDB</button>
    <button class="tab" onclick="switchDb('turso')">⚡ Turso</button>
  </div>
</div>

<div class="container">
  <div class="stats">
    <div class="stat">
      <div class="label">数据库</div>
      <div class="value" id="db-name">CockroachDB</div>
      <div class="sub" id="db-type">PostgreSQL 兼容</div>
    </div>
    <div class="stat">
      <div class="label">连接状态</div>
      <div class="value"><span class="badge badge-green" id="db-status">已连接</span></div>
      <div class="sub" id="db-region">AWS Singapore</div>
    </div>
    <div class="stat">
      <div class="label">当前表</div>
      <div class="value" id="current-table">-</div>
      <div class="sub" id="row-count">-</div>
    </div>
    <div class="stat">
      <div class="label">筛选结果</div>
      <div class="value" id="filtered-count">-</div>
      <div class="sub" id="filter-info">全部显示</div>
    </div>
  </div>

  <div class="toolbar">
    <select id="table-select" onchange="loadTable()">
      <option>加载中...</option>
    </select>
    <div class="search-box">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" id="search-input" placeholder="搜索表格内容..." oninput="filterTable()">
    </div>
    <button class="btn" onclick="loadTable()">🔄 刷新</button>
    <button class="btn" onclick="exportCSV()">📥 导出 CSV</button>
  </div>

  <div class="table-wrap">
    <div class="table-inner" id="table-content">
      <div class="loading"><div class="spinner"></div><br>加载中...</div>
    </div>
    <div class="table-footer">
      <span id="footer-left">-</span>
      <span id="footer-right">-</span>
    </div>
  </div>

  <div class="sql-panel">
    <div class="sql-header">
      <h3>⌨️ SQL 查询</h3>
      <div style="display:flex;gap:8px">
        <button class="btn" onclick="clearSql()">清空</button>
        <button class="btn btn-primary" onclick="runSql()">▶ 执行</button>
      </div>
    </div>
    <div class="sql-body">
      <textarea class="sql-editor" id="sql-editor" placeholder="输入 SQL 查询语句...&#10;&#10;示例: SELECT * FROM test_write WHERE id > 0"></textarea>
      <div class="sql-actions">
        <span class="sql-hint">Ctrl+Enter 执行 | 仅支持 SELECT 查询</span>
        <span class="sql-hint" id="sql-time"></span>
      </div>
    </div>
    <div class="sql-result" id="sql-result"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let currentDb='cockroachdb';
let currentData={columns:[],rows:[]};
let sortCol=-1,sortAsc=true;

function showToast(msg,type='success'){
  const t=document.getElementById('toast');
  t.className='toast toast-'+type+' show';
  t.textContent=msg;
  setTimeout(()=>t.classList.remove('show'),3000);
}

async function switchDb(db){
  currentDb=db;
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  event.target.classList.add('active');
  const info={cockroachdb:{name:'CockroachDB',type:'PostgreSQL 兼容',region:'AWS Singapore'},turso:{name:'Turso',type:'SQLite 边缘分布式',region:'AWS Mumbai'}};
  const i=info[db];
  document.getElementById('db-name').textContent=i.name;
  document.getElementById('db-type').textContent=i.type;
  document.getElementById('db-region').textContent=i.region;
  document.getElementById('search-input').value='';
  await loadTables();
}

async function loadTables(){
  const sel=document.getElementById('table-select');
  sel.innerHTML='<option>加载中...</option>';
  try{
    const r=await fetch('/api/'+currentDb+'/tables');
    const d=await r.json();
    sel.innerHTML=d.tables.map(t=>'<option value="'+t+'">'+t+'</option>').join('');
    if(d.tables.length>0)loadTable();
    else{document.getElementById('table-content').innerHTML='<div class="empty"><p>暂无数据表</p></div>';}
  }catch(e){sel.innerHTML='<option>加载失败</option>';showToast('加载表失败','error');}
}

async function loadTable(){
  const table=document.getElementById('table-select').value;
  if(!table||table==='加载中...')return;
  document.getElementById('current-table').textContent=table;
  document.getElementById('table-content').innerHTML='<div class="loading"><div class="spinner"></div><br>查询中...</div>';
  const start=Date.now();
  try{
    const r=await fetch('/api/'+currentDb+'/query?table='+encodeURIComponent(table));
    const d=await r.json();
    currentData=d;
    sortCol=-1;
    document.getElementById('row-count').textContent=d.rows.length+' 行';
    document.getElementById('filtered-count').textContent=d.rows.length;
    document.getElementById('filter-info').textContent='全部显示';
    document.getElementById('footer-left').textContent=d.columns.length+' 列 × '+d.rows.length+' 行';
    document.getElementById('footer-right').textContent='耗时 '+(Date.now()-start)+'ms';
    renderTable(d.columns,d.rows);
    showToast('查询完成，'+d.rows.length+' 行');
  }catch(e){
    document.getElementById('table-content').innerHTML='<div class="error">❌ 查询失败: '+e.message+'</div>';
    showToast('查询失败','error');
  }
}

function renderTable(cols,rows){
  if(!rows.length){
    document.getElementById('table-content').innerHTML='<div class="empty"><p>表为空</p></div>';
    document.getElementById('filtered-count').textContent='0';
    return;
  }
  let h='<table><thead><tr>';
  cols.forEach((c,i)=>{h+='<th onclick="sortBy('+i+')">'+c+'<span class="sort-icon">↕</span></th>';});
  h+='</tr></thead><tbody>';
  rows.forEach(r=>{
    h+='<tr>';
    r.forEach(c=>{h+='<td>'+escapeHtml(String(c))+'</td>';});
    h+='</tr>';
  });
  h+='</tbody></table>';
  document.getElementById('table-content').innerHTML=h;
  document.getElementById('filtered-count').textContent=rows.length;
}

function escapeHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

function filterTable(){
  const q=document.getElementById('search-input').value.toLowerCase();
  if(!q){renderTable(currentData.columns,currentData.rows);document.getElementById('filter-info').textContent='全部显示';return;}
  const filtered=currentData.rows.filter(r=>r.some(c=>String(c).toLowerCase().includes(q)));
  renderTable(currentData.columns,filtered);
  document.getElementById('filter-info').textContent='搜索: '+q;
}

function sortBy(col){
  if(sortCol===col)sortAsc=!sortAsc;else{sortCol=col;sortAsc=true;}
  const rows=[...currentData.rows].sort((a,b)=>{
    const va=a[col],vb=b[col];
    const na=parseFloat(va),nb=parseFloat(vb);
    if(!isNaN(na)&&!isNaN(nb))return sortAsc?na-nb:nb-na;
    return sortAsc?String(va).localeCompare(String(vb)):String(vb).localeCompare(String(va));
  });
  renderTable(currentData.columns,rows);
  document.querySelectorAll('th').forEach((th,i)=>{
    th.classList.toggle('sorted',i===col);
    th.querySelector('.sort-icon').textContent=i===col?(sortAsc?'↑':'↓'):'↕';
  });
}

function exportCSV(){
  if(!currentData.rows.length){showToast('没有数据可导出','error');return;}
  let csv=currentData.columns.join(',')+'\n';
  currentData.rows.forEach(r=>{csv+=r.map(c=>'"'+String(c).replace(/"/g,'""')+'"').join(',')+'\n';});
  const blob=new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8;'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=currentDb+'_'+document.getElementById('table-select').value+'.csv';
  a.click();
  showToast('CSV 已导出');
}

async function runSql(){
  const sql=document.getElementById('sql-editor').value.trim();
  if(!sql){showToast('请输入 SQL 语句','error');return;}
  if(!sql.match(/^\s*select/i)){showToast('仅支持 SELECT 查询','error');return;}
  const start=Date.now();
  document.getElementById('sql-result').innerHTML='<div class="loading"><div class="spinner"></div></div>';
  try{
    const r=await fetch('/api/'+currentDb+'/sql?q='+encodeURIComponent(sql));
    const d=await r.json();
    const ms=Date.now()-start;
    document.getElementById('sql-time').textContent=ms+'ms';
    if(d.error){document.getElementById('sql-result').innerHTML='<div class="error">'+escapeHtml(d.error)+'</div>';return;}
    if(!d.rows||!d.rows.length){document.getElementById('sql-result').innerHTML='<div class="empty"><p>无结果</p></div>';return;}
    let h='<table><thead><tr>';
    d.columns.forEach(c=>{h+='<th>'+c+'</th>';});
    h+='</tr></thead><tbody>';
    d.rows.forEach(r=>{h+='<tr>';r.forEach(c=>{h+='<td>'+escapeHtml(String(c))+'</td>';});h+='</tr>';});
    h+='</tbody></table>';
    document.getElementById('sql-result').innerHTML=h;
    showToast('查询完成，'+d.rows.length+' 行，'+ms+'ms');
  }catch(e){
    document.getElementById('sql-result').innerHTML='<div class="error">❌ '+e.message+'</div>';
    showToast('查询失败','error');
  }
}

function clearSql(){document.getElementById('sql-editor').value='';document.getElementById('sql-result').innerHTML='';document.getElementById('sql-time').textContent='';}

document.getElementById('sql-editor').addEventListener('keydown',e=>{
  if(e.ctrlKey&&e.key==='Enter'){e.preventDefault();runSql();}
});

loadTables();
</script>
</body>
</html>"""
