import importlib.util
from pathlib import Path
import sys
import csv
import io
from fastapi.testclient import TestClient
from aerotrace.schema import CHANNELS

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('desktop_server',ROOT/'python/desktop_server.py')
service=importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

def test_desktop_replay_auth_and_persistence(tmp_path):
    assets=tmp_path/'assets';assets.mkdir()
    import shutil
    shutil.copy(ROOT.parent/'backend/artifacts/model.json',assets/'model.json')
    shutil.copy(ROOT.parent/'backend/config/cad_sensor_map.json',assets/'cad_sensor_map.json')
    app=service.desktop_app(tmp_path/'data',assets,'t'*64)
    c=TestClient(app)
    assert c.get('/v1/desktop/sessions').status_code==401
    c.headers['X-API-Key']='t'*64
    session=c.get('/v1/desktop/sessions').json()[0]
    assert session['source']=='synthetic' and session['count']==480
    sid=session['id']
    win=c.get(f'/v1/desktop/sessions/{sid}/window?start=180&limit=40').json()
    assert len(win['items'])==40
    assert len(win['items'][0]['cad']['bindings'])==32
    assert any(r['persistent_anomaly'] for r in win['items'])
    overview=c.get(f'/v1/desktop/sessions/{sid}/overview').json()
    assert len(overview['points'])==480
    assert overview['events']
    assert c.get(f'/v1/desktop/sessions/{sid}/report').json()['rul_hours'] is None
    assert c.get('/v1/desktop/sessions/nope/window').status_code==404
    assert c.get(f'/v1/desktop/sessions/{sid}/window?limit=501').status_code==422
    other=TestClient(service.desktop_app(tmp_path/'data',assets,'t'*64),headers={'X-API-Key':'t'*64})
    assert other.get('/v1/desktop/sessions').json()[0]['id']==sid
    stream=io.StringIO()
    writer=csv.writer(stream)
    writer.writerow(['Timestamp',*[channel[1] for channel in CHANNELS]])
    for record in service.synthetic_records()[:103]:
        writer.writerow([record.time.isoformat(),*[
            record.values[name]/(100 if '[hPa]' in header else 100000 if '[bar]' in header else 1)
            for _,header,name,_,_,_ in CHANNELS]])
    content=stream.getvalue()
    response=c.post('/v1/desktop/import',json={'filename':'example.csv','content':content})
    assert response.status_code==200,response.text
    imported=response.json()
    assert imported['source']=='imported_log' and imported['count']==103
    assert c.post('/v1/desktop/import',json={'filename':'example.csv','content':content}).json()['id']==imported['id']
    assert c.post('/v1/desktop/import',json={'filename':'broken.csv','content':'bad,headers\n1,2'}).status_code==422
    assert c.post('/v1/desktop/import',json={'filename':'raw.ae3','content':'abc'}).status_code==422
