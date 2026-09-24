"""Development/browser verification only. Not a substitute for packaged EXE validation."""
import importlib.util
import json
import secrets
from pathlib import Path
import shutil
import tempfile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('desktop_server',ROOT/'python/desktop_server.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assets=ROOT/'preview-assets';assets.mkdir(exist_ok=True)
shutil.copy2(ROOT.parent/'backend/artifacts/model.json',assets/'model.json')
shutil.copy2(ROOT.parent/'backend/config/cad_sensor_map.json',assets/'cad_sensor_map.json')
token=secrets.token_hex(32)
app=module.desktop_app(ROOT/'preview-data',assets,token)
# Static UI has no API authorization dependencies; API routes keep their token checks.
from fastapi import FastAPI
host=FastAPI(docs_url=None,redoc_url=None)
@host.get('/')
def index():
    html=(ROOT/'dist/index.html').read_text(encoding='utf-8')
    return HTMLResponse(html.replace('<head>','<head><script src="/preview-bridge.js"></script>'))
@host.get('/preview-bridge.js')
def bridge():
    script='const previewToken='+json.dumps(token)+';'
    script+='''
    const call=async(method,path,body)=>{const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-API-Key':previewToken},body:body===undefined?undefined:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));return d;};
    window.aero={api:call,info:async()=>({version:'0.1-preview',offline:true}),importCSV:()=>new Promise(resolve=>{const input=document.createElement('input');input.type='file';input.accept='.csv';input.oncancel=()=>resolve(null);input.onchange=async()=>{if(!input.files[0])return resolve(null);const file=input.files[0];if(file.size>10000000){alert('CSV must be below 10 MB');return resolve(null);}try{resolve(await call('POST','/v1/desktop/import',{filename:file.name,content:await file.text()}));}catch(e){alert(String(e));resolve(null);}};input.click();}),exportReport:async id=>{const d=await call('GET','/v1/desktop/sessions/'+id+'/report');const url=URL.createObjectURL(new Blob([JSON.stringify(d,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='AeroTrace-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);return true;}};
    '''
    return Response(script,media_type='text/javascript')
host.mount('/api',app)
host.mount('/',StaticFiles(directory=ROOT/'dist'))
if __name__=='__main__':uvicorn.run(host,host='127.0.0.1',port=8010,access_log=False)
