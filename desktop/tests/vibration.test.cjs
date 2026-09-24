const {test}=require('node:test');
const assert=require('node:assert/strict');
const {vibrationFrequency,vibrationShape,vibrationOffset}=require('../src/vibration.ts');
test('vibration order uses crank RPM and does not invent missing or stopped rotation',()=>{
 assert.equal(vibrationFrequency(3600),60);
 for(const rpm of [null,undefined,NaN,0,-1]){assert.equal(vibrationFrequency(rpm),0);assert.deepEqual(vibrationOffset(1,rpm,1,60,true),{x:0,y:0,roll:0});}
 assert.deepEqual(vibrationOffset(1,3600,1,60,false),{x:0,y:0,roll:0});
});
test('visual gain scales displacement, not RPM, with bounded manual roughness',()=>{
 const a=vibrationOffset(1,3600,.6,1,true),b=vibrationOffset(1,3600,.6,60,true);
 assert.ok(Math.abs(b.x-a.x*60)<1e-10);assert.deepEqual(vibrationShape(1,2),vibrationShape(1,1));
 assert.deepEqual(vibrationOffset(1,3600,1,999,true),vibrationOffset(1,3600,1,80,true));
});
