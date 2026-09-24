import {useEffect,useState} from 'react';
import type {Replay,Sample} from './types';
type Fault={label:string,signal:string,effect:string};
export default function FaultLab({sessions,session,sample,onCreated,onSeek}:{sessions:Replay[],session?:Replay,sample?:Sample,onCreated:(session:Replay)=>Promise<void>,onSeek:(index:number,play:boolean)=>void}){
 const [catalog,setCatalog]=useState<Record<string,Fault>>({}),[source,setSource]=useState(''),[kind,setKind]=useState('coast_down'),[start,setStart]=useState(30),[duration,setDuration]=useState(60),[severity,setSeverity]=useState(100),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const sources=sessions.filter(s=>s.source!=='fault_injected');
 const chosen=sources.find(s=>s.id===source);
 useEffect(()=>{window.aero.api('GET','/v1/desktop/faults').then(setCatalog).catch(e=>setError(String(e)));},[]);
 useEffect(()=>{if(!sources.some(s=>s.id===source))setSource(sources[0]?.id||'');},[sessions,source]);
 const create=async()=>{setBusy(true);setError('');try{const result=await window.aero.api('POST','/v1/desktop/faults',{source_id:source,kind,start_index:start,duration_samples:duration,severity:severity/100});await onCreated(result);}catch(e){setError(String(e));}finally{setBusy(false);}};
 const fault=(session?.audit as any)?.fault;
 return <details className="panel fault-lab" open><summary>Fault injection lab <span className="badge amber">EXPERIMENT ONLY</span></summary>
 <div className="fault-inputs"><label>Source session<select aria-label="Fault source" value={source} onChange={e=>setSource(e.target.value)}>{sources.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
 <label>Fault scenario<select aria-label="Fault scenario" value={kind} onChange={e=>setKind(e.target.value)}>{Object.entries(catalog).map(([key,f])=><option key={key} value={key}>{f.label}</option>)}</select></label>
 <label>Start sample (zero-based)<input aria-label="Fault start sample" type="number" min="0" max={(chosen?.count||1)-2} value={start} onChange={e=>setStart(Number(e.target.value))}/></label>
 <label>Duration (samples)<input aria-label="Fault duration" type="number" min="2" max={chosen?.count||20000} value={duration} onChange={e=>setDuration(Number(e.target.value))}/></label>
 <label>Severity: {kind==='oil_sensor_dropout'?'not applicable':`${severity}%`}<input aria-label="Fault severity" type="range" min="1" max="100" value={severity} disabled={kind==='oil_sensor_dropout'} onChange={e=>setSeverity(Number(e.target.value))}/></label>
 <button className="primary" disabled={busy||!source||!catalog[kind]} onClick={create}>{busy?'Analysing scenario…':'Create injected replay'}</button></div>
 <p className="fault-description">{catalog[kind]?.effect} Changes apply only inside the chosen interval; the original session is preserved. This is a signal-level experiment, not a validated engine-failure simulation.</p>
 {error&&<p role="alert" className="error">{error}</p>}
 {fault&&<div className="injection-state" aria-live="polite"><span className="badge amber">{sample?.injection?.active?'INJECTION ACTIVE':'INJECTED SESSION'}</span><span>{catalog[fault.kind]?.label} · samples {fault.start_index}–{fault.start_index+fault.duration_samples-1}</span><button onClick={()=>onSeek(Math.max(0,fault.start_index-3),true)}>Replay fault onset</button><button onClick={()=>onSeek(fault.start_index+fault.duration_samples-1,false)}>Inspect final fault sample</button>
 {sample?.injection&&<span>Original: {sample.injection.original_value??'unavailable'} → experimental: {sample.injection.injected_value??'unavailable'} <small>(canonical units)</small></span>}</div>}
 </details>;
}
