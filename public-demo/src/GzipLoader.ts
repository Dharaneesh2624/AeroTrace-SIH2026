import {GLTFLoader,type GLTF} from 'three/examples/jsm/loaders/GLTFLoader.js';
export class GzipLoader extends GLTFLoader {
 override load(url:string,onLoad:(gltf:GLTF)=>void,_onProgress?:(event:ProgressEvent)=>void,onError?:(err:unknown)=>void){
  fetch(url).then(async r=>{if(!r.ok||!r.body)throw Error('CAD download unavailable');const bytes=await r.arrayBuffer();const header=new Uint8Array(bytes,0,2);const buffer=header[0]===31&&header[1]===139?await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():bytes;return this.parseAsync(buffer,'./');}).then(onLoad).catch(error=>onError?.(error));
 }
}
