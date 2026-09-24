import type {Replay,Sample,Sensor} from './types';
const cache=new Map<string,Promise<any>>();
async function asset(name:string){if(!cache.has(name))cache.set(name,fetch('./'+name).then(r=>{if(!r.ok)throw Error('Demo asset could not load. Refresh and try again.');return r.json();}).catch(e=>{cache.delete(name);throw e;}));return cache.get(name)!;}
async function session(id:string){const list:Replay[]=await asset('sessions.json');if(!list.some(s=>s.id===id))throw Error('Unknown demo session');return asset(id+'.json');}
function hydrate(row:Sample,template:Sensor[]):Sample{return {...row,cad:{visual_crank_angle_deg:0,bindings:template.map(s=>({...s,value:s.canonical_signal?row.values[s.canonical_signal]:null,quality:s.canonical_signal?row.quality[s.canonical_signal]:'unavailable',readings:s.readings.map(r=>({...r,value:row.values[r.canonical_signal],quality:row.quality[r.canonical_signal]}))}))}};}
export function thermalBench(input:any){
 const p=input?.segments?.[0];if(!p||input.segments.length!==1||!Number.isInteger(p.duration_s)||p.duration_s<1||p.duration_s>600||![p.shaft_power_kw,p.ambient_c,p.cooling_factor,input.initial_c].every(Number.isFinite)||p.shaft_power_kw<0||p.shaft_power_kw>123.5||p.ambient_c< -30||p.ambient_c>55||p.cooling_factor<.2||p.cooling_factor>1.5)throw Error('Inputs outside the demonstration range');
 let coolant=input.initial_c,oil=input.initial_c;const fuelW=p.shaft_power_kw*1000/.34,samples=[];
 for(let t=1;t<=p.duration_s;t++){for(let j=0;j<4;j++){const coupling=100*(coolant-oil);const dc=(.2*fuelW-p.cooling_factor*1200*(coolant-p.ambient_c)-coupling)/75000;const dOil=(.06*fuelW-p.cooling_factor*420*(oil-p.ambient_c)+coupling)/35000;coolant+=.25*dc;oil+=.25*dOil;}samples.push({time_s:t,coolant_c:coolant,oil_c:oil,synthetic_fuel_flow_l_h:fuelW/43e6/.8*3600});}
 return {quality:'uncalibrated_synthetic_bench_only',samples};
}
export async function publicApi(method:string,path:string,body?:any){
 if(method==='POST'&&path==='/v1/simulate/bench')return thermalBench(body);
 if(method!=='GET')throw Error('Public demo is read-only. Private uploads and custom fault processing are disabled.');
 if(path==='/health')return {status:'synthetic_demo'};
 if(path==='/v1/desktop/sessions')return asset('sessions.json');
 if(path==='/v1/desktop/faults')return asset('faults.json');
 const match=path.match(/^\/v1\/desktop\/sessions\/([a-f0-9]{32})\/(overview|window|report)(?:\?(.*))?$/);if(!match)throw Error('Not available in public demo');
 const data=await session(match[1]);if(match[2]==='overview')return data.overview;
 if(match[2]==='report')return {format:'AeroTrace synthetic research report',session:data.session,confirmed_faults:null,rul_hours:null,disclaimer:'Precomputed analysis of generated data. Not a diagnosis or airworthiness assessment. Vibration display is illustrative, not measured.'};
 const query=new URLSearchParams(match[3]||'');const start=Number(query.get('start')||0),limit=Number(query.get('limit')||120);if(!Number.isInteger(start)||start<0||!Number.isInteger(limit)||limit<1||limit>500)throw Error('Invalid replay window');
 const template=await asset('sensor-template.json');return {session:data.session,items:data.items.slice(start,start+limit).map((r:Sample)=>hydrate(r,template))};
}
window.aero={publicDemo:true,api:publicApi,info:async()=>({publicDemo:true,syntheticOnly:true}),importCSV:async()=>{throw Error('Uploads disabled in public demo');},exportReport:async(id:string)=>{const result=await publicApi('GET',`/v1/desktop/sessions/${id}/report`);const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='AeroTrace-synthetic-report.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return true;}};
