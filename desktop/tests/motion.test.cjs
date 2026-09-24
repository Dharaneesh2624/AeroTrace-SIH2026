const {test}=require('node:test');
const assert=require('node:assert/strict');
const {motionRate,advancePhase,crankMotionRate,rotorAngle,advanceTotal}=require('../src/motion.ts');
test('RPM controls real-speed motion; zero, missing, pause and disabled freeze',()=>{
 const rate=motionRate(2200,true,true,1);
 assert.ok(Math.abs(rate-22308)<1e-8);
 assert.equal(motionRate(1100,true,true,1),rate/2);
 assert.equal(motionRate(2200,true,true,2),rate*2);
 for(const rpm of [0,null,undefined,NaN,-1])assert.equal(motionRate(rpm,true,true,1),0);
 assert.equal(motionRate(2200,false,true,1),0);
 assert.equal(motionRate(2200,true,false,1),0);
 assert.equal(advancePhase(710,200,.1),10);
 assert.equal(advancePhase(100,0,.1),100);
});
test('renderer uses authoritative backend crank RPM',()=>{
 assert.equal(crankMotionRate(3718,true,true,1),22308);
 assert.equal(crankMotionRate(0,true,true,1),0);
 assert.equal(crankMotionRate(null,true,true,1),0);
 assert.equal(crankMotionRate(3718,false,true,1),0);
 assert.equal(crankMotionRate(3718,true,false,1),0);
 assert.equal(crankMotionRate(3718,true,true,2),44616);
 assert.equal(crankMotionRate(3718,true,true,1,120),185.9);
});
test('2000 propeller RPM produces 2000 actual output rotations in a minute at any frame rate',()=>{
 for(const fps of [24,30,60,144]){
  const rate=motionRate(2000,true,true,1);
  let total=0;
  for(let frame=0;frame<60*fps;frame++)total=advanceTotal(total,rate,1/fps);
  assert.ok(Math.abs(total/360/1.69-2000)<1e-7);
  assert.ok(Math.abs(total/360-3380)<1e-7);
 }
 assert.equal(advanceTotal(0,12000,.5),6000,'a dropped frame must not silently slow rotation');
});
test('propeller rotation stays continuous across a 720-degree crank cycle',()=>{
 const a=rotorAngle(719.9,1/1.69,0),b=rotorAngle(720.1,1/1.69,0);
 assert.ok(Math.abs(b-a)<.003);
 assert.ok(Math.abs(rotorAngle(608.4,1/1.69,0)+2*Math.PI)<1e-10);
});
