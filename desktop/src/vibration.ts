// A visual teaching signal, not a model of measured AE300 vibration or bearing health.
export const VIBRATION_SLOWDOWN = 20;
export function vibrationFrequency(rpm:number|null|undefined){
  return rpm!=null && Number.isFinite(rpm) && rpm>0 ? rpm/60 : 0;
}
export function vibrationShape(phase:number,roughness:number){
  const r=Math.max(0,Math.min(1,roughness));
  return {x:Math.sin(phase)+.35*r*Math.sin(2*phase+.6),y:.55*Math.cos(phase+.4)+.25*r*Math.sin(2*phase)};
}
export function vibrationOffset(phase:number,rpm:number|null|undefined,roughness:number,gain:number,enabled:boolean){
  if(!enabled||!vibrationFrequency(rpm))return {x:0,y:0,roll:0};
  const r=Math.max(0,Math.min(1,roughness));
  const shape=vibrationShape(phase,r);
  // Illustrative 0.2..0.6 mm source displacement, not fitted to engine data.
  const safeGain=Math.max(1,Math.min(80,gain));
  const amplitude=(.0002+.0004*r)*safeGain;
  return {x:shape.x*amplitude,y:shape.y*amplitude,roll:Math.sin(phase+.2)*.001*r*safeGain/20};
}
