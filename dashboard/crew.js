import {GLTFLoader} from './vendor/GLTFLoader.js';
import {clone} from './vendor/SkeletonUtils.js';
import * as THREE from 'three';
function fabric(color){const canvas=document.createElement('canvas');canvas.width=128;canvas.height=128;const c=canvas.getContext('2d');c.fillStyle=color;c.fillRect(0,0,128,128);for(let y=0;y<128;y+=3){c.fillStyle='#ffffff12';c.fillRect(0,y,128,1)}for(let x=0;x<128;x+=3){c.fillStyle='#00000012';c.fillRect(x,0,1,128)}const map=new THREE.CanvasTexture(canvas);map.colorSpace=THREE.SRGBColorSpace;return new THREE.MeshStandardMaterial({map,roughness:.88})}
const skin=new THREE.MeshStandardMaterial({color:0xb58a70,roughness:.78}),uniform=fabric('#326c79'),trousers=fabric('#293c4e'),hair=new THREE.MeshStandardMaterial({color:0x25201c,roughness:1}),shoe=new THREE.MeshStandardMaterial({color:0x20252a,roughness:.8});
function ellipsoid(parent,mat,x,y,z,sx,sy,sz){let m=new THREE.Mesh(new THREE.SphereGeometry(1,16,12),mat);m.position.set(x,y,z);m.scale.set(sx,sy,sz);m.castShadow=true;parent.add(m);return m}
function simplePerson(){
 const g=new THREE.Group();ellipsoid(g,uniform,0,1.24,0,.27,.39,.16);ellipsoid(g,trousers,0,.91,0,.23,.16,.15);
 ellipsoid(g,skin,0,1.65,0,.08,.12,.08);ellipsoid(g,skin,0,1.86,0,.135,.19,.14);ellipsoid(g,hair,0,1.97,-.015,.14,.1,.14);ellipsoid(g,skin,0,1.85,.14,.035,.045,.04);
 for(let x of [-.047,.047]){ellipsoid(g,hair,x,1.9,.126,.015,.012,.008);ellipsoid(g,skin,Math.sign(x)*.137,1.85,0,.025,.05,.025)}
 const legs=[],arms=[];for(let sign of [-1,1]){let leg=new THREE.Group();leg.position.set(sign*.13,.92,0);g.add(leg);ellipsoid(leg,trousers,0,-.24,0,.095,.28,.105);ellipsoid(leg,trousers,0,-.62,.015,.075,.24,.08);ellipsoid(leg,shoe,0,-.83,.07,.09,.065,.17);legs.push(leg);let arm=new THREE.Group();arm.position.set(sign*.26,1.48,0);g.add(arm);ellipsoid(arm,uniform,sign*.035,-.18,0,.085,.23,.085);ellipsoid(arm,skin,sign*.04,-.46,.025,.06,.17,.065);ellipsoid(arm,skin,sign*.04,-.64,.03,.065,.09,.04);arms.push(arm)}
 g.userData.walk=(t,pushing=false)=>{legs.forEach((leg,i)=>leg.rotation.x=Math.sin(t*7+i*Math.PI)*.38);arms.forEach((arm,i)=>arm.rotation.x=pushing?-.85:Math.sin(t*7+i*Math.PI+Math.PI)*.28);g.position.y=Math.abs(Math.sin(t*7))*.018};return g;
}
export function cockpitRig(){
 const g=new THREE.Group();const wheel=new THREE.Group();wheel.position.set(.34,-.39,-.74);wheel.rotation.x=-.18;g.add(wheel);
 const rim=new THREE.Mesh(new THREE.TorusGeometry(.2,.025,10,40),shoe);wheel.add(rim);
 const hub=ellipsoid(wheel,shoe,0,0,0,.075,.065,.035);for(let angle of [0,2.1,4.2]){let spoke=new THREE.Mesh(new THREE.BoxGeometry(.17,.022,.025),shoe);spoke.position.set(Math.cos(angle)*.09,Math.sin(angle)*.09,0);spoke.rotation.z=angle;wheel.add(spoke)}
 for(let sign of [-1,1]){ellipsoid(wheel,skin,sign*.17,.07,.025,.052,.073,.042);for(let finger=0;finger<4;finger++)ellipsoid(wheel,skin,sign*(.15+finger*.013),.06,.045,.009,.043,.014);ellipsoid(wheel,skin,sign*.135,.035,.045,.016,.04,.02);ellipsoid(wheel,skin,sign*.22,-.1,.16,.052,.19,.055);ellipsoid(wheel,uniform,sign*.25,-.27,.24,.07,.13,.07)}
 g.userData.wheel=wheel;return g;
}

const humanAsset=await new GLTFLoader().loadAsync('/assets/models/crew.glb').catch(()=>null);
export function person(){
 if(!humanAsset)return simplePerson();
 const group=new THREE.Group(),model=clone(humanAsset.scene);group.add(model);group.scale.setScalar(.95);
 model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;o.geometry=o.geometry.clone();if(o.material)o.material=o.material.clone()}});
 const mixer=new THREE.AnimationMixer(model),walk=humanAsset.animations.find(c=>c.name==='Walk'),idle=humanAsset.animations.find(c=>c.name==='Idle');if(idle)mixer.clipAction(idle).play();mixer.setTime(0);let walking=false;
 group.userData.walk=(t,pushing=false)=>{if(!walking&&walk){mixer.stopAllAction();mixer.clipAction(walk).play();walking=true}mixer.setTime(t*.8);};return group;
}
