import React, {Suspense, useEffect, useMemo, useRef, useState} from 'react';
import {Canvas, useFrame, useLoader, useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import {crankMotionRate,rotorAngle,advanceTotal} from './motion';
import rotors from './cad-rotors.json';
import {OrbitControls} from 'three/examples/jsm/controls/OrbitControls.js';
import {vibrationFrequency,vibrationOffset,VIBRATION_SLOWDOWN} from './vibration';
import type {VibrationSettings} from './VibrationPanel';

type Props={mode:string,selected:string,onSelect:(name:string)=>void,animate:boolean,reset:number,playing:boolean,speed:number,slowdown:number,crankRpm:number|null|undefined,phase:number,sampleKey:string,objectStates:Record<string,string>,vibration?:VibrationSettings};
type Pose={phase:number,pistonY:number,ready:boolean,caseX:number,caseY:number};
function Assembly({mode,selected,onSelect,animate,reset,playing,speed,slowdown,crankRpm,phase,sampleKey,objectStates,vibration,onPose}:Props&{onPose:(pose:Pose)=>void}){
  const gltf=useLoader(GLTFLoader,'./engine.glb');
  const {camera,gl,invalidate}=useThree();
  const controls=useRef<OrbitControls|null>(null);
  const displayPhase=useRef(phase);
  const caseGroup=useRef<THREE.Group>(null);
  const vibrationPhase=useRef(0);
  const rate=crankMotionRate(crankRpm,playing,animate,speed,slowdown);
  const lastFrame=useRef(performance.now());
  const lastPublish=useRef(0);
  const clipStart=1/30,clipSpan=8; // verified baked frames 1..241 at 30 fps cover 720 degrees
  const mixer=useMemo(()=>new THREE.AnimationMixer(gltf.scene),[gltf.scene]);
  const meshes=useMemo(()=>{const result:THREE.Mesh[]=[];gltf.scene.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.material=(obj.material as THREE.Material).clone();result.push(obj);}});return result;},[gltf.scene]);
  useEffect(()=>{
    const orbit=new OrbitControls(camera,gl.domElement);orbit.enableDamping=false;orbit.minDistance=.35;orbit.maxDistance=5;orbit.addEventListener('change',()=>invalidate());controls.current=orbit;
    return()=>{orbit.dispose();};
  },[camera,gl,invalidate]);
  useEffect(()=>{if(gltf.animations[0])mixer.clipAction(gltf.animations[0]).play();return()=>{mixer.stopAllAction();};},[mixer,gltf]);
  useEffect(()=>{
    for(const mesh of meshes){
      const u=mesh.userData;
      const external=['12_Aircraft_Integration','13_Routing_Concepts','14_EECU','17_Aircraft_Electrics'].includes(u.subsystem);
      mesh.visible=mode==='integration' || (!external && !(mode==='cutaway' && (u.hide_for_section || mesh.name.includes('HeadCover_Screw') || mesh.name.startsWith('Cover_Rib'))));
      const mat=mesh.material as THREE.MeshStandardMaterial;
      if(mat.emissive){const state=objectStates[mesh.name];const color=state==='injected'?'#f49b38':state==='missing'?'#7d8492':state==='deviation'?'#e75656':mesh.name===selected?'#15b6ac':'#000000';mat.emissive.set(color);mat.emissiveIntensity=state?.85:mesh.name===selected?.7:0;}
    }
    invalidate();
  },[meshes,mode,selected,objectStates,invalidate]);
  useEffect(()=>{
    gltf.scene.updateMatrixWorld(true);
    const box=new THREE.Box3();meshes.filter(m=>m.visible).forEach(m=>box.union(new THREE.Box3().setFromObject(m)));
    const center=box.getCenter(new THREE.Vector3());const size=box.getSize(new THREE.Vector3()).length();
    camera.position.copy(center.clone().add(new THREE.Vector3(-1.05,.7,1.15).normalize().multiplyScalar(size*1.1)));
    camera.lookAt(center);if(controls.current){controls.current.target.copy(center);controls.current.update();}invalidate();
  },[mode,reset,meshes,camera,gltf.scene,invalidate]);
  const applyPose=()=>{
    mixer.setTime(clipStart+(displayPhase.current%720)/720*clipSpan);
    // Non-integer gear ratios must not reset when the 720-degree piston clip loops.
    for(const rotor of rotors){const obj=gltf.scene.getObjectByName(rotor.name);if(obj)obj.rotation.set(rotorAngle(displayPhase.current,rotor.ratio,rotor.phase),0,0);}
  };
  const publish=()=>onPose({phase:displayPhase.current%720,pistonY:gltf.scene.getObjectByName('Piston_C1')?.position.y??0,ready:gltf.animations.length>0,caseX:caseGroup.current?.position.x??0,caseY:caseGroup.current?.position.y??0});
  useEffect(()=>{displayPhase.current=phase;lastFrame.current=performance.now();applyPose();publish();invalidate();},[sampleKey,phase,mixer,invalidate]);
  useFrame((state)=>{const now=performance.now();const elapsed=(now-lastFrame.current)/1000;lastFrame.current=now;if(rate>0){displayPhase.current=advanceTotal(displayPhase.current,rate,elapsed);applyPose();vibrationPhase.current+=elapsed*vibrationFrequency(crankRpm)*2*Math.PI*speed/VIBRATION_SLOWDOWN;if(state.clock.elapsedTime-lastPublish.current>.2){publish();lastPublish.current=state.clock.elapsedTime;}invalidate();}
    if(caseGroup.current){const offset=vibrationOffset(vibrationPhase.current,crankRpm,vibration?.roughness??0,vibration?.gain??1,Boolean(vibration?.enabled&&animate));caseGroup.current.position.set(offset.x,offset.y,0);caseGroup.current.rotation.z=offset.roll;}
  });
  useEffect(()=>{invalidate();},[vibration,crankRpm,animate,invalidate]);
  useEffect(()=>{lastFrame.current=performance.now();invalidate();},[rate,invalidate]);
  return <group ref={caseGroup}><primitive object={gltf.scene} onClick={(e:any)=>{e.stopPropagation();onSelect(e.object.name);}}/></group>;
}
class ModelBoundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return{failed:true};}render(){return this.state.failed?<div className="model-fallback"><img src="./engine-preview.png" alt="AE300 assembly preview"/><p>3D is unavailable on this graphics setup. Static preview shown.</p></div>:this.props.children;}}
export default function Engine(props:Props){const [pose,setPose]=useState<Pose>({phase:0,pistonY:0,ready:false,caseX:0,caseY:0});return <ModelBoundary><Canvas frameloop="demand" dpr={[1,1.5]} camera={{fov:38,near:.01,far:50}} gl={{antialias:true,powerPreference:'low-power'}}>
  <color attach="background" args={['#151d20']}/><ambientLight intensity={1.4}/><hemisphereLight args={['#f1ece2','#172321',2]}/>
  <directionalLight position={[-2,4,3]} intensity={3}/><directionalLight position={[3,1,-2]} color="#a9c8c0" intensity={2}/>
  <Suspense fallback={null}><Assembly {...props} onPose={setPose}/></Suspense>
</Canvas><div className="motion-readout" data-testid="motion-readout" data-phase={pose.phase.toFixed(3)} data-piston-y={pose.pistonY.toFixed(7)} data-case-x={pose.caseX.toFixed(7)} data-case-y={pose.caseY.toFixed(7)} data-degrees-per-second={crankMotionRate(props.crankRpm,props.playing,props.animate,props.speed,props.slowdown)}>{pose.ready?`${props.slowdown===1?'REAL SPEED':'SLOW MOTION 1/120'} · ${pose.phase.toFixed(0)}° / 720°`:'Loading mechanism…'} · crank {props.crankRpm==null?'unavailable':`${props.crankRpm.toFixed(0)} rpm (derived)`} · playback {props.speed}×<br/><span className="vibration-readout">{props.vibration?.enabled?`ILLUSTRATIVE VIBRATION · ${props.vibration.gain}× displacement · 1/20 frequency`:'CASE VIBRATION OFF'}</span></div></ModelBoundary>;}
