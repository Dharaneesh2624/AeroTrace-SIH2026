const fs=require('node:fs');const path=require('node:path');const assert=require('node:assert/strict');const zlib=require('node:zlib');
const root=path.resolve(__dirname,'..'),data=path.join(root,'public');global.window={};
global.fetch=async url=>{assert.match(url,/^\.\/[a-z0-9-]+\.json$/);return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(data,url.slice(2)),'utf8'))};};
const {publicApi,thermalBench}=require('../src/public-api.ts');
(async()=>{
 const sessions=await publicApi('GET','/v1/desktop/sessions');assert.equal(sessions.length,7);assert.ok(sessions.every(s=>['synthetic','fault_injected'].includes(s.source)));
 for(const s of sessions){const window=await publicApi('GET',`/v1/desktop/sessions/${s.id}/window?start=0&limit=500`);assert.equal(window.items.length,480);assert.equal(window.items[0].cad.bindings.length,32);assert.equal(window.items[0].values.propeller_rpm,2200);assert.equal(window.items[0].cad.bindings[0].readings[0].value,205000);
  if(s.audit.fault?.kind==='coast_down')assert.equal(window.items[89].physics.crankshaft_rpm.value,0);
  if(s.audit.fault?.kind==='oil_sensor_dropout')assert.equal(window.items[50].values.oil_c,null);
 }
 await assert.rejects(publicApi('POST','/v1/desktop/import',{content:'private'}),/disabled/);
 await assert.rejects(publicApi('POST','/v1/desktop/faults',{}),/disabled/);
 await assert.rejects(publicApi('GET','/v1/desktop/sessions/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/window'),/Unknown/);
 const result=thermalBench({initial_c:25,segments:[{duration_s:600,shaft_power_kw:60,ambient_c:25,cooling_factor:1}]});assert.equal(result.samples.length,600);assert.ok(result.samples[599].coolant_c>25);assert.ok(result.samples[599].coolant_c<100);
 assert.throws(()=>thermalBench({}),/range/);
 const glb=zlib.gunzipSync(fs.readFileSync(path.join(data,'engine.glb.gz')));assert.equal(glb.toString('ascii',0,4),'glTF');assert.equal(glb.length,46738532);
 const html=fs.readFileSync(path.join(root,'dist/index.html'),'utf8');for(const m of html.matchAll(/src="\.\/([^\"]+)"/g))assert.ok(fs.existsSync(path.join(root,'dist',m[1])));
 for(const name of fs.readdirSync(path.join(root,'dist'))){assert.ok(!/sqlite|\.env|preview-bridge|model\.json/.test(name));assert.ok(fs.statSync(path.join(root,'dist',name)).size<25*1024*1024);}
 console.log('PASS: seven synthetic sessions, hydrated CAD, zero-RPM and dropout scenarios, upload rejection, thermal bench, compressed model integrity and public asset audit.');
})().catch(e=>{console.error(e);process.exit(1)});
