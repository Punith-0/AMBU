import assert from 'node:assert/strict';
import * as THREE from 'three';
class Events {listeners=new Map();addEventListener(k,f){if(!this.listeners.has(k))this.listeners.set(k,[]);this.listeners.get(k).push(f)}removeEventListener(k,f){this.listeners.set(k,(this.listeners.get(k)||[]).filter(v=>v!==f))}emit(k,e={}){for(const fn of this.listeners.get(k)||[])fn({preventDefault(){},...e})}}
globalThis.window=new Events();globalThis.document=new Events();document.hidden=false;
let stored='[{"name":"bad","position":[null,0,1],"target":[0,0,0]},{"name":"valid","position":[10,5,8],"target":[0,0,0]}]';globalThis.localStorage={getItem:()=>stored,setItem:(k,v)=>stored=v};
const {createSandboxCamera}=await import('../dashboard/sandbox-camera.js');
const camera=new THREE.PerspectiveCamera(38,1,.1,3000);camera.position.set(20,15,30);const target=new THREE.Vector3(0,0,0);
const controls={target,minDistance:70,maxDistance:1300,minPolarAngle:0,maxPolarAngle:1.5,enableDamping:true,enabled:true,enableZoom:true,enablePan:true,update(){camera.lookAt(target)}};controls.update();const canvas=new Events();
const city={sandboxActive:true,camera,controls,renderer:{domElement:canvas},follow:false};
let notices=[],published=[];const cam=createSandboxCamera(city,{notify:t=>notices.push(t),onBookmarks:b=>published=b});assert.equal(published.length,1);cam.setMode('free');cam.update(.016,performance.now());
const start=camera.position.clone();window.emit('keydown',{code:'KeyW',target:{closest:()=>null}});cam.update(.1,performance.now());assert.ok(camera.position.distanceTo(start)>6.9);window.emit('blur');const stopped=camera.position.clone();cam.update(.1,performance.now());assert.equal(camera.position.distanceTo(stopped),0);
window.emit('keydown',{code:'KeyW',target:{closest:()=>true}});cam.update(.1,performance.now());assert.equal(camera.position.distanceTo(stopped),0);
cam.setMode('ground');assert.equal(camera.position.y,2.2);window.emit('keydown',{code:'KeyE',target:{closest:()=>null}});cam.update(.1,performance.now());assert.equal(camera.position.y,2.2);cam.stop();
assert.ok(cam.save('My view'));const saved=cam.getBookmarks()[1];camera.position.set(30,40,50);controls.target.set(10,0,0);assert.ok(cam.recall(1));assert.equal(controls.enabled,false);cam.update(.016,performance.now()+2000);assert.ok(camera.position.distanceTo(new THREE.Vector3(...saved.position))<1e-8);assert.equal(controls.enabled,true);
assert.ok(cam.tour());assert.ok(cam.isTouring());canvas.emit('pointerdown');assert.ok(!cam.isTouring());assert.equal(controls.enabled,true);
for(let i=0;i<4;i++)assert.ok(cam.save('Additional '+i));assert.equal(cam.getBookmarks().length,6);assert.equal(cam.save('Too many'),false);assert.ok(cam.remove(5));assert.equal(cam.getBookmarks().length,5);
city.sandboxActive=false;cam.update(.1,performance.now());assert.equal(controls.minDistance,70);assert.equal(camera.fov,38);cam.destroy();assert.equal(window.listeners.get('keydown').length,0);
console.log('PASS camera validation, editable-field isolation, WASD/blur, grounded elevation, exact recall, tour interruption, six-bookmark limit and cleanup');
