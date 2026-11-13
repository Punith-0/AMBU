import * as THREE from 'three';

const STORAGE_KEY='ambu.sandbox.cameras.v1';
const MODES=new Set(['orbit','free','ground']);
const finitePoint=v=>Array.isArray(v)&&v.length===3&&v.every(n=>Number.isFinite(n)&&Math.abs(n)<100000);
const cleanName=(value,fallback)=>String(value||'').replace(/[\u0000-\u001f\u007f]/g,'').trim().slice(0,44)||fallback;
const copyBookmark=b=>({...b,position:[...b.position],target:[...b.target]});

/** Shared city camera controller; no extra renderer, animation loop or simulation clock. */
export function createSandboxCamera(city,{notify=()=>{},onBookmarks=()=>{}}={}){
 const camera=city.camera,controls=city.controls,keys=new Set();
 const initial={minDistance:controls.minDistance,maxDistance:controls.maxDistance,minPolarAngle:controls.minPolarAngle,maxPolarAngle:controls.maxPolarAngle,enableDamping:controls.enableDamping,enableZoom:controls.enableZoom,enablePan:controls.enablePan,enabled:controls.enabled,fov:camera.fov};
 let mode='orbit',transition=null,tourState=null,activeLast=false,destroyed=false;
 let bookmarks=[];
 try{
  const saved=JSON.parse(globalThis.localStorage?.getItem(STORAGE_KEY)||'[]');
  if(Array.isArray(saved))bookmarks=saved.filter(b=>b&&finitePoint(b.position)&&finitePoint(b.target)&&new THREE.Vector3(...b.position).distanceTo(new THREE.Vector3(...b.target))>.1).slice(0,6).map((b,i)=>({name:cleanName(b.name,`View ${i+1}`),position:[...b.position],target:[...b.target],mode:MODES.has(b.mode)?b.mode:'orbit',fov:Number.isFinite(b.fov)&&b.fov>=20&&b.fov<=100?b.fov:38}));
 }catch{/* A damaged or blocked browser-storage entry must not prevent city startup. */}
 const publish=()=>onBookmarks(bookmarks.map(copyBookmark));
 const persist=()=>{try{globalThis.localStorage?.setItem(STORAGE_KEY,JSON.stringify(bookmarks));}catch{notify('Camera saved for this session. Browser storage is unavailable.');}publish();};
 const editable=target=>target?.isContentEditable||!!target?.closest?.('input,textarea,select,[contenteditable="true"]');
 const forward=new THREE.Vector3(),right=new THREE.Vector3(),motion=new THREE.Vector3(),up=new THREE.Vector3(0,1,0);
 function configure(){
  controls.enabled=true;controls.enableDamping=initial.enableDamping;controls.minDistance=2;controls.maxDistance=1600;
  controls.enableZoom=true;controls.enablePan=true;controls.minPolarAngle=.03;controls.maxPolarAngle=Math.PI-.03;
  if(mode==='orbit'){controls.maxPolarAngle=Math.PI/2.05;controls.maxDistance=1600;}
  if(mode==='ground'){controls.minPolarAngle=controls.maxPolarAngle=Math.PI/2;controls.enableZoom=false;controls.enablePan=false;}
 }
 function flushControls(){const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;}
 function stop(){transition=null;tourState=null;keys.clear();if(city.sandboxActive)configure();}
 function setMode(next){
  if(!MODES.has(next))return false;
  stop();city.follow=false;flushControls();mode=next;configure();
  if(mode==='ground'){
   camera.getWorldDirection(forward);forward.y=0;if(forward.lengthSq()<.0001)forward.set(0,0,-1);forward.normalize();
   camera.position.y=2.2;controls.target.copy(camera.position).addScaledVector(forward,20);
  }
  camera.fov=mode==='orbit'?38:65;camera.updateProjectionMatrix();controls.update();return true;
 }
 function save(name){
  if(bookmarks.length>=6){notify('Six camera positions are saved. Remove one to make room.');return false;}
  const b={name:cleanName(name,`View ${bookmarks.length+1}`),position:camera.position.toArray(),target:controls.target.toArray(),mode,fov:camera.fov};
  if(!finitePoint(b.position)||!finitePoint(b.target)||camera.position.distanceTo(controls.target)<.1){notify('Move the camera before saving this position.');return false;}
  bookmarks.push(b);persist();notify(`Saved ${b.name}.`);return true;
 }
 function begin(bookmark,now=performance.now()){
  city.follow=false;flushControls();
  transition={from:camera.position.clone(),fromTarget:controls.target.clone(),fromFov:camera.fov,to:new THREE.Vector3(...bookmark.position),toTarget:new THREE.Vector3(...bookmark.target),toFov:bookmark.fov,mode:bookmark.mode,started:now,duration:1800};
  // OrbitControls.update() is called by City even while input is disabled; remove
  // its constraints during the shot so it cannot clamp the interpolated path.
  controls.enabled=false;controls.enableDamping=false;controls.minDistance=0;controls.maxDistance=Infinity;controls.minPolarAngle=0;controls.maxPolarAngle=Math.PI;
 }
 function recall(index){
  if(!Number.isInteger(index)||!bookmarks[index])return false;
  stop();begin(bookmarks[index]);return true;
 }
 function remove(index){
  if(!Number.isInteger(index)||!bookmarks[index])return false;
  stop();bookmarks.splice(index,1);persist();return true;
 }
 function tour(){
  if(bookmarks.length<2){notify('Save at least two camera positions for a Director tour.');return false;}
  stop();tourState={shots:bookmarks.map(copyBookmark),index:0,nextAt:null};begin(tourState.shots[0]);notify('Director tour started. Click the city or press Esc to stop.');return true;
 }
 function onKeyDown(event){
  if(!city.sandboxActive||editable(event.target)||event.ctrlKey||event.metaKey||event.altKey)return;
  if(event.code==='Escape'){stop();return;}
  if(/^Digit[1-6]$/.test(event.code)){if(!event.repeat)recall(Number(event.code.at(-1))-1);event.preventDefault();return;}
  if(mode==='orbit'||!['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','ShiftLeft','ShiftRight'].includes(event.code))return;
  if(transition||tourState)stop();keys.add(event.code);event.preventDefault();
 }
 const onKeyUp=event=>keys.delete(event.code);
 const onBlur=()=>keys.clear();
 const onVisibility=()=>{if(document.hidden)stop();};
 const onPointerDown=()=>{if(city.sandboxActive&&(transition||tourState))stop();};
 window.addEventListener('keydown',onKeyDown);window.addEventListener('keyup',onKeyUp);window.addEventListener('blur',onBlur);
 document.addEventListener('visibilitychange',onVisibility);city.renderer.domElement.addEventListener('pointerdown',onPointerDown,true);
 function update(dt,now=performance.now()){
  if(destroyed)return;
  if(!city.sandboxActive){
   if(activeLast){stop();Object.assign(controls,{minDistance:initial.minDistance,maxDistance:initial.maxDistance,minPolarAngle:initial.minPolarAngle,maxPolarAngle:initial.maxPolarAngle,enableDamping:initial.enableDamping,enableZoom:initial.enableZoom,enablePan:initial.enablePan,enabled:initial.enabled});camera.fov=initial.fov;camera.updateProjectionMatrix();}
   activeLast=false;return;
  }
  if(!activeLast){activeLast=true;if(!transition)configure();}
  if(transition){
   const t=Math.min(1,Math.max(0,(now-transition.started)/transition.duration)),u=t*t*(3-2*t);
   camera.position.lerpVectors(transition.from,transition.to,u);controls.target.lerpVectors(transition.fromTarget,transition.toTarget,u);camera.fov=THREE.MathUtils.lerp(transition.fromFov,transition.toFov,u);camera.updateProjectionMatrix();camera.lookAt(controls.target);
   if(t===1){mode=transition.mode;transition=null;configure();if(tourState)tourState.nextAt=now+1700;}
   return;
  }
  if(tourState&&tourState.nextAt!==null&&now>=tourState.nextAt){
   tourState.index++;
   if(tourState.index>=tourState.shots.length){stop();notify('Director tour complete.');}
   else{const shot=tourState.shots[tourState.index];tourState.nextAt=null;begin(shot,now);}
  }
  if(mode==='orbit'||!keys.size)return;
  city.follow=false;camera.getWorldDirection(forward);
  if(mode==='ground')forward.y=0;
  if(forward.lengthSq()<.0001)forward.set(0,0,-1);forward.normalize();right.crossVectors(forward,up).normalize();motion.set(0,0,0);
  if(keys.has('KeyW'))motion.add(forward);if(keys.has('KeyS'))motion.sub(forward);if(keys.has('KeyD'))motion.add(right);if(keys.has('KeyA'))motion.sub(right);
  if(mode==='free'){if(keys.has('KeyE'))motion.y+=1;if(keys.has('KeyQ'))motion.y-=1;}
  if(motion.lengthSq()){
   const speed=(mode==='ground'?12:70)*(keys.has('ShiftLeft')||keys.has('ShiftRight')?2.5:1);
   motion.normalize().multiplyScalar(speed*Math.min(.1,Math.max(0,dt)));const old=camera.position.clone();camera.position.add(motion);
   camera.position.x=THREE.MathUtils.clamp(camera.position.x,-250,1100);camera.position.z=THREE.MathUtils.clamp(camera.position.z,-1100,250);camera.position.y=mode==='ground'?2.2:THREE.MathUtils.clamp(camera.position.y,2.2,1200);
   controls.target.add(camera.position.clone().sub(old));
  }
 }
 function destroy(){stop();destroyed=true;window.removeEventListener('keydown',onKeyDown);window.removeEventListener('keyup',onKeyUp);window.removeEventListener('blur',onBlur);document.removeEventListener('visibilitychange',onVisibility);city.renderer.domElement.removeEventListener('pointerdown',onPointerDown,true);}
 publish();
 return {setMode,save,recall,remove,tour,stop,update,destroy,getMode:()=>mode,getBookmarks:()=>bookmarks.map(copyBookmark),isTouring:()=>!!tourState};
}
