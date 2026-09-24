import {useEffect,useRef,useState} from 'react';
import {vibrationFrequency,vibrationShape,VIBRATION_SLOWDOWN} from './vibration';
export type VibrationSettings={enabled:boolean,roughness:number,gain:number};
export default function VibrationPanel({rpm,playing,speed,settings,onChange}:{rpm:number|null|undefined,playing:boolean,speed:number,settings:VibrationSettings,onChange:(v:VibrationSettings)=>void}){
 const canvas=useRef<HTMLCanvasElement>(null),phase=useRef(0);
 const hz=vibrationFrequency(rpm);
 useEffect(()=>{const el=canvas.current!;const ctx=el.getContext('2d');if(!ctx)return;let frame=0,last=performance.now();
  const draw=(now:number)=>{const dt=(now-last)/1000;last=now;if(playing&&settings.enabled)phase.current+=dt*hz*2*Math.PI*speed/VIBRATION_SLOWDOWN;
   const w=el.clientWidth,h=el.clientHeight,dpr=Math.min(devicePixelRatio||1,2);if(el.width!==w*dpr||el.height!==h*dpr){el.width=w*dpr;el.height=h*dpr;}ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
   ctx.lineWidth=1;ctx.strokeStyle='#293532';for(let x=0;x<w;x+=32){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(let y=16;y<h;y+=28){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
   const active=hz>0&&settings.enabled;
   for(const [axis,color] of [['x','#eab86b'],['y','#70b9ac']] as const){ctx.strokeStyle=color;ctx.lineWidth=1.6;ctx.beginPath();for(let x=0;x<=w;x++){const p=x/Math.max(w,1)*4*Math.PI+phase.current;const shape=vibrationShape(p,settings.roughness);const y=h/2-(active?shape[axis]*(.45+.55*settings.roughness)*h*.31:0);x?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();}
   frame=requestAnimationFrame(draw);
  };frame=requestAnimationFrame(draw);return()=>cancelAnimationFrame(frame);
 },[hz,playing,speed,settings]);
 return <section className="vibration-panel" aria-label="Illustrative vibration controls"><div className="vibration-intro"><span className="instrument-index">02 / MOTION STUDY</span><h3>See the vibration.</h3><p>Illustrative case motion. No accelerometer data.</p><label className="vibration-switch"><input type="checkbox" checked={settings.enabled} onChange={e=>onChange({...settings,enabled:e.target.checked})}/> Show case vibration</label></div><div className="vibration-scope"><div className="scope-caption"><span><i/> X <i/> Y <b>SYNTHETIC ORDER PATTERN</b></span><span>{hz?`${hz.toFixed(1)} Hz · 1× crank`:'No rotation'}</span></div><canvas ref={canvas} role="img" aria-label="Illustrative X and Y vibration pattern, not a measured waveform"/><div className="scope-caption"><span>2 crank cycles · normalised amplitude</span><span>{!settings.enabled?'OFF':!hz?'STOPPED':playing?'ANIMATING':'PAUSED'}</span></div></div><div className="vibration-controls"><label>Illustrative roughness <b>{Math.round(settings.roughness*100)}%</b><input type="range" aria-label="Illustrative vibration roughness" min="0" max="1" step="0.05" value={settings.roughness} onChange={e=>onChange({...settings,roughness:Number(e.target.value)})}/></label><label>Visual magnification <b>{settings.gain}×</b><input type="range" aria-label="Vibration visual magnification" min="1" max="80" step="1" value={settings.gain} onChange={e=>onChange({...settings,gain:Number(e.target.value)})}/></label><small>Vibration shown at 1/20 frequency. Rotation keeps its selected RPM scale. Roughness is manual—not a diagnosis.</small></div></section>;
}
