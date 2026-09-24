import {useEffect,useRef} from 'react';
import {flushSync} from 'react-dom';
import type {Replay} from './types';
export function useDemoTools(sessions:Replay[],select:(id:string)=>void){
 const current=useRef({sessions,select});current.current={sessions,select};
 useEffect(()=>{const context=(document as any).modelContext;if(!context?.registerTool)return;const lifecycle=new AbortController();const register=(tool:any)=>{try{Promise.resolve(context.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}};
  register({name:'list_demo_sessions',description:'List the available synthetic AeroTrace replay sessions. Does not change the page.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:false},execute(input:unknown){if(input==null||typeof input!=='object'||Object.keys(input).length)throw Error('Expected an empty object');return current.current.sessions.map(s=>({id:s.id,name:s.name,source:s.source}));}});
  register({name:'select_demo_session',description:'Select a synthetic replay in the visible engine workspace and pause playback. The chosen session data loads asynchronously.',inputSchema:{type:'object',properties:{id:{type:'string'}},required:['id'],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute(input:any){if(!input||typeof input.id!=='string'||Object.keys(input).length!==1||!current.current.sessions.some(s=>s.id===input.id))throw Error('Select a session ID returned by list_demo_sessions');flushSync(()=>current.current.select(input.id));return {selected_session_id:input.id,playback:'paused'};}});
  return()=>lifecycle.abort();
 },[]);
}
