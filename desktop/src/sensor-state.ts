import type {Sample} from './types';
export function sensorStates(sample?:Sample):Record<string,string>{
 const states:Record<string,string>={};
 for(const sensor of sample?.cad.bindings||[]){
  if(sample?.injection?.active&&sensor.readings.some(r=>r.canonical_signal===sample.injection?.signal))states[sensor.object]='injected';
  else if(sensor.readings.length&&sensor.readings.some(r=>r.value==null))states[sensor.object]='missing';
  else if(sample?.analysis.candidate_anomaly&&sensor.readings.some(r=>Math.abs(sample.analysis.residuals[r.canonical_signal]?.signed_z||0)>=3))states[sensor.object]='deviation';
 }
 return states;
}
