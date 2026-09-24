"""Export only newly generated synthetic sessions. Never opens a user's data DB."""
import gzip
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'backend'), str(ROOT/'desktop/python')]
from desktop_server import desktop_app
from fastapi.testclient import TestClient
from aerotrace.faults import CATALOG

DEST = ROOT/'public-demo/public'
DEST.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='aerotrace-public-synthetic-') as scratch:
    assets = Path(scratch)/'assets'
    assets.mkdir()
    shutil.copy2(ROOT/'backend/artifacts/model.json', assets/'model.json')
    shutil.copy2(ROOT/'backend/config/cad_sensor_map.json', assets/'cad_sensor_map.json')
    # Token exists only inside this exporter; no listening HTTP server is started.
    client = TestClient(desktop_app(Path(scratch)/'data', assets, 'synthetic-export-only-not-a-public-credential'))
    client.headers['X-API-Key'] = 'synthetic-export-only-not-a-public-credential'
    def get(path):
        response=client.get(path); response.raise_for_status(); return response.json()
    source=get('/v1/desktop/sessions')[0]
    sessions=[source]
    for kind in CATALOG:
        response=client.post('/v1/desktop/faults',json={'source_id':source['id'],'kind':kind,'start_index':30,'duration_samples':60,'severity':1})
        response.raise_for_status();sessions.append(response.json())
    for i,meta in enumerate(sessions):
        sid=meta['id'];rows=get(f'/v1/desktop/sessions/{sid}/window?start=0&limit=500')['items']
        # CAD channel bindings are hydrated from a public schema at runtime.
        if i==0:
            template=rows[0]['cad']['bindings']
            for sensor in template:
                sensor['value']=None
                for reading in sensor['readings']: reading['value']=None
            (DEST/'sensor-template.json').write_text(json.dumps(template,separators=(',',':')),encoding='utf-8')
        for row in rows:
            row.pop('cad',None)
            row.pop('session_id',None)
            row.pop('engine_id',None)
        meta['name']='Synthetic systems demo' if i==0 else CATALOG[meta['audit']['fault']['kind']]['label']
        payload={'session':meta,'items':rows,'overview':get(f'/v1/desktop/sessions/{sid}/overview')}
        payload['overview']['session']=meta
        (DEST/f'{sid}.json').write_text(json.dumps(payload,allow_nan=False,separators=(',',':')),encoding='utf-8')
    (DEST/'sessions.json').write_text(json.dumps(sessions,separators=(',',':')),encoding='utf-8')
    (DEST/'faults.json').write_text(json.dumps(CATALOG,separators=(',',':')),encoding='utf-8')
with (ROOT/'desktop/public/engine.glb').open('rb') as source:
    with gzip.open(DEST/'engine.glb.gz','wb',compresslevel=9) as target: shutil.copyfileobj(source,target)
print(json.dumps({'synthetic_sessions':len(sessions),'cad_bytes':(DEST/'engine.glb.gz').stat().st_size,'files':len(list(DEST.iterdir()))}))
