import importlib.util
from pathlib import Path
import shutil
import pytest
from fastapi.testclient import TestClient
from aerotrace.faults import CATALOG, inject

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fault_service', ROOT/'python/desktop_server.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

@pytest.mark.parametrize('kind', CATALOG)
def test_faults_are_bounded_and_original_is_unchanged(kind):
    records = service.synthetic_records()
    original = [dict(r.values) for r in records]
    modified, truth = inject(records, kind, 10, 20, 1)
    assert [r.values for r in records] == original
    assert modified[9].values == original[9] and modified[30].values == original[30]
    assert not truth[9]['active'] and truth[10]['active'] and not truth[30]['active']
    assert any(p['changed'] for p in truth[10:30])
    if kind == 'coast_down': assert modified[29].values['propeller_rpm'] == 0
    if kind == 'oil_sensor_dropout':
        assert modified[15].values['oil_c'] is None
        assert modified[15].quality['oil_c'] == 'missing'

def test_fault_invalid_and_missing_inputs():
    records = service.synthetic_records()
    for args in [('bad',0,2,1),('voltage_drop',479,2,1),('voltage_drop',0,2,0)]:
        with pytest.raises(ValueError): inject(records,*args)
    with pytest.raises(ValueError): inject(records,'oil_sensor_dropout',390,10,1)

def test_fault_endpoint_provenance_reanalysis_and_motion(tmp_path):
    assets=tmp_path/'assets';assets.mkdir()
    for origin in ['artifacts/model.json','config/cad_sensor_map.json']:
        shutil.copy(ROOT.parent/'backend'/origin,assets/Path(origin).name)
    app=service.desktop_app(tmp_path/'data',assets,'t'*64)
    client=TestClient(app)
    assert client.get('/v1/desktop/faults').status_code == 401
    client.headers['X-API-Key']='t'*64
    source=client.get('/v1/desktop/sessions').json()[0]
    path=f"/v1/desktop/sessions/{source['id']}/window?start=0&limit=120"
    before=client.get(path).json()
    request={'source_id':source['id'],'kind':'coast_down','start_index':10,'duration_samples':20,'severity':1}
    response=client.post('/v1/desktop/faults',json=request)
    assert response.status_code == 200, response.text
    experiment=response.json()
    assert experiment['source']=='fault_injected' and experiment['id']!=source['id']
    assert client.get(path).json()==before
    rows=client.get(f"/v1/desktop/sessions/{experiment['id']}/window?start=0&limit=120").json()['items']
    assert rows[29]['values']['propeller_rpm']==0
    assert rows[29]['analysis']['regime']=='stopped'
    assert rows[29]['physics']['crankshaft_rpm']['value']==0
    assert rows[29]['injection']['original_value']>0
    assert rows[29]['motion']['display_phase_deg'] != before['items'][29]['motion']['display_phase_deg']
    assert rows[30]['values']==before['items'][30]['values']
    report=client.get(f"/v1/desktop/sessions/{experiment['id']}/report").json()
    assert report['session']['audit']['fault']==request and report['rul_hours'] is None
    assert client.post('/v1/desktop/faults',json={**request,'source_id':experiment['id']}).status_code==422
    for change in [{'duration_samples':99999},{'start_index':479},{'severity':0},{'kind':'unknown'},{'start_index':1.5}]:
        assert client.post('/v1/desktop/faults',json={**request,**change}).status_code==422
