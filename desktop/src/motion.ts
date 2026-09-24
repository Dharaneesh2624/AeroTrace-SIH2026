// Speed is physical by default. Phase remains an illustration, not a measurement.
export function motionRate(rpm:number|null|undefined, playing:boolean, enabled:boolean, speed:number,slowdown=1){
 return crankMotionRate(rpm==null?rpm:rpm*1.69,playing,enabled,speed,slowdown);
}
export function advancePhase(phase:number,rate:number,delta:number){
 return (phase+rate*Math.min(Math.max(delta,0),.1))%720;
}

export function crankMotionRate(crankRpm:number|null|undefined,playing:boolean,enabled:boolean,speed:number,slowdown=1){
 return playing&&enabled&&crankRpm!=null&&Number.isFinite(crankRpm)&&crankRpm>0&&speed>0&&Number.isFinite(speed)&&slowdown>0&&Number.isFinite(slowdown) ? crankRpm*6/slowdown*speed : 0;
}

export function advanceTotal(phase:number,rate:number,elapsedSeconds:number){
 return phase+rate*Math.max(0,elapsedSeconds);
}

export function rotorAngle(totalCrankDegrees:number,ratio:number,phase:number){
 return (phase-totalCrankDegrees*ratio)*Math.PI/180;
}
