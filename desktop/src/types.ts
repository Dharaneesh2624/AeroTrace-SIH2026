export type Values = Record<string, number|null>;
export type Injection = {kind:string,active:boolean,changed:boolean,signal:string,original_value:number|null,injected_value:number|null};
export type Reading = {canonical_signal:string,value:number|null,unit:string,quality:string};
export type Sensor = {sensor_id:string,object:string,canonical_signal:string|null,value:number|null,unit:string|null,quality:string,readings:Reading[],source_scope:string};
export type Sample = {injection?:Injection,motion?:{display_phase_deg:number,display_total_deg?:number,slowdown:number},index:number,timestamp:string,data_origin:string,values:Values,quality:Record<string,string>,physics:Record<string,{value:number|null,unit?:string,quality:string}>,analysis:{status:string,regime:string,score_ratio:number|null,candidate_anomaly:boolean,residuals:Record<string,{observed:number,expected:number,residual:number,signed_z:number}>},persistent_anomaly:boolean,hypotheses:{signal:string,alternatives:string[]}[],warnings:{type:string,signals?:string[]}[],reference_alignment_index:number|null,cad:{bindings:Sensor[],visual_crank_angle_deg:number},rul:{hours:null}};
export type Replay = {id:string,name:string,source:string,count:number,start:string,end:string,counts:Record<string,number>,model_id:string,audit:Record<string,unknown>,analysis_seconds:number};
export type Point = {index:number,timestamp:string,values:Values,ratio:number|null,alert:boolean};
export type Overview = {session:Replay,points:Point[],events:{start:number,end:number,timestamp:string,signals:string[]}[]};
declare global {interface Window {aero:{publicDemo?:boolean,api:(method:string,path:string,body?:unknown)=>Promise<any>,importCSV:()=>Promise<Replay|null>,exportReport:(id:string)=>Promise<boolean>,info:()=>Promise<any>}}}
