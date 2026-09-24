const {test}=require('node:test');
const assert=require('node:assert/strict');
const {sensorStates}=require('../src/sensor-state.ts');
test('CAD colours follow injection, data quality and backend residual evidence',()=>{
 const sample={cad:{bindings:[{object:'sensor',readings:[{canonical_signal:'oil_c',value:80}]}]},analysis:{candidate_anomaly:true,residuals:{oil_c:{signed_z:4}}}};
 assert.equal(sensorStates(sample).sensor,'deviation');
 sample.cad.bindings[0].readings[0].value=null;
 assert.equal(sensorStates(sample).sensor,'missing');
 sample.injection={active:true,signal:'oil_c'};
 assert.equal(sensorStates(sample).sensor,'injected');
 assert.deepEqual(sensorStates(undefined),{});
});
