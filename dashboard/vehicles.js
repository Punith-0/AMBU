import {mergeGeometries} from './vendor/BufferGeometryUtils.js?v=20261104s';
import * as THREE from 'three';
const trafficTemplates=new Map();
// Traffic vehicles reuse six immutable models. Per-vehicle transforms and wheel
// groups are still independent; do not dispose resources marked `shared`.
export function createVehicle(ambulance,id){
 if(ambulance)return buildVehicle(true,id);
 const key=[...id].reduce((a,c)=>a+c.charCodeAt(0),0)%6;
 let template=trafficTemplates.get(key);
 if(!template){
  template=buildVehicle(false,id);
  for(const wheel of template.userData.wheels)wheel.userData.isWheel=true;
  delete template.userData.wheels;
  template.traverse(o=>{if(o.geometry)o.geometry.userData.shared=true;if(o.material)o.material.userData.shared=true});
  trafficTemplates.set(key,template);
 }
 const vehicle=template.clone(true);
 vehicle.userData.id=id;
 vehicle.userData.wheels=vehicle.children.filter(o=>o.userData.isWheel);
 return vehicle;
}
function buildVehicle(ambulance,id){
 const g=new THREE.Group(),hash=[...id].reduce((a,c)=>a+c.charCodeAt(0),0),variant=hash%3;
 const paint=new THREE.MeshPhysicalMaterial({color:ambulance?0xe5ecec:[0x597785,0x9cabb0,0x936b5b,0xc9c4ae,0x3d5969,0x737f69][hash%6],roughness:.38,metalness:.25,clearcoat:.6});
 const dark=new THREE.MeshStandardMaterial({color:0x182630,roughness:.45}),glass=new THREE.MeshPhysicalMaterial({color:0x294b5c,roughness:.12,metalness:.3,clearcoat:1});
 const silver=new THREE.MeshStandardMaterial({color:0x9daab0,roughness:.35,metalness:.75}),red=new THREE.MeshStandardMaterial({color:0xb85653,emissive:0x5d2422,emissiveIntensity:.3});
 const box=(x,y,z,w,h,d,mat)=>{let m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);m.position.set(x,y+h/2,z);m.castShadow=true;g.add(m);return m};
 const rounded=(x,y,z,w,h,d,mat)=>{let shape=new THREE.Shape(),r=.1;shape.moveTo(-w/2+r,-h/2);shape.lineTo(w/2-r,-h/2);shape.quadraticCurveTo(w/2,-h/2,w/2,-h/2+r);shape.lineTo(w/2,h/2-r);shape.quadraticCurveTo(w/2,h/2,w/2-r,h/2);shape.lineTo(-w/2+r,h/2);shape.quadraticCurveTo(-w/2,h/2,-w/2,h/2-r);shape.lineTo(-w/2,-h/2+r);shape.quadraticCurveTo(-w/2,-h/2,-w/2+r,-h/2);let geo=new THREE.ExtrudeGeometry(shape,{depth:d-.16,bevelEnabled:true,bevelSegments:ambulance?2:1,steps:1,bevelSize:.08,bevelThickness:.08,curveSegments:ambulance?5:3});geo.translate(0,0,-d/2+.08);let m=new THREE.Mesh(geo,mat);m.position.set(x,y+h/2,z);m.castShadow=true;g.add(m);return m};
 let length=ambulance?5.5:4.5,width=ambulance?2.15:1.78;
 rounded(0,.47,0,width,ambulance?1.05:.65,length,paint);
 if(ambulance){rounded(0,1.15,-.65,2.12,1.55,3.9,paint);rounded(0,1.15,1.55,1.98,1.22,1.5,paint);box(0,1.74,2.28,1.75,.56,.05,glass);for(let x of [-1,1]){box(x,1.78,1.5,.035,.55,1.1,glass);box(x*1.075,1.1,-.5,.035,.22,4,red);box(x*1.08,1.75,-.8,.04,.65,.16,red);box(x*1.08,1.98,-.8,.04,.16,.65,red);box(x*1.075,1.45,-1.8,.04,.5,.7,glass)}box(0,2.75,1.15,1.5,.13,.34,new THREE.MeshStandardMaterial({color:0x8ab6c6,emissive:0x3b697d,emissiveIntensity:.5}));for(let x of [-.5,.5]){box(x,1.4,-2.76,.94,1.15,.03,paint);box(x,1.9,-2.79,.7,.4,.02,glass);box(x,.9,-2.79,.18,.4,.04,red)}box(0,.65,-2.8,1.9,.14,.16,dark)}
 else{let high=variant===1?.95:.72,cabinLength=variant===2?2.65:2.35;rounded(0,1.02,-.25,1.56,high,cabinLength,paint);let front=box(0,1.25,cabinLength/2-.21,1.4,.45,.04,glass);front.rotation.x=-.18;box(0,1.25,-cabinLength/2-.28,1.36,.42,.04,glass);for(let x of [-.79,.79]){box(x,1.25,-.25,.03,.42,cabinLength-.25,glass);box(x*1.02,1.2,-.25,.05,.55,.1,paint);box(x*1.1,.98,-.1,.04,.06,.24,silver)}if(variant===1)for(let x of [-.62,.62])box(x,2,-.3,.07,.05,2,silver)}
 box(0,.65,length/2+.02,width*.7,.25,.045,dark);for(let x of [-.6,.6])box(x,.92,length/2+.04,.38,.18,.05,new THREE.MeshStandardMaterial({color:0xe8dec1,emissive:0xb9aa7c,emissiveIntensity:.5}));for(let x of [-.65,.65])box(x,.91,-length/2-.03,.28,.18,.04,red);
 for(let x of [-width/2-.07,width/2+.07])box(x,1.45,length*.2,.18,.14,.26,paint);
 g.userData.wheels=[];for(let x of [-width/2,width/2])for(let z of [-length*.31,length*.29]){let wheel=new THREE.Group();wheel.position.set(x,.43,z);let tyre=new THREE.Mesh(new THREE.CylinderGeometry(.36,.36,.23,ambulance?20:12),dark);tyre.rotation.z=Math.PI/2;wheel.add(tyre);let hub=new THREE.Mesh(new THREE.CylinderGeometry(.21,.21,.245,ambulance?12:8),silver);hub.rotation.z=Math.PI/2;wheel.add(hub);if(!ambulance){
   const wheelGeometries=[];
   for(const part of [tyre,hub]){part.updateMatrix();const geometry=part.geometry.clone().applyMatrix4(part.matrix).toNonIndexed();const rgb=new Float32Array(geometry.attributes.position.count*3);for(let i=0;i<rgb.length;i+=3){rgb[i]=part.material.color.r;rgb[i+1]=part.material.color.g;rgb[i+2]=part.material.color.b}geometry.setAttribute('color',new THREE.BufferAttribute(rgb,3));wheelGeometries.push(geometry)}
   const geometry=mergeGeometries(wheelGeometries,false);wheelGeometries.forEach(g=>g.dispose());
   if(geometry){wheel.clear();tyre.geometry.dispose();hub.geometry.dispose();wheel.add(new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.55,metalness:.3})))}
  }g.add(wheel);g.userData.wheels.push(wheel)}
 if(ambulance){let canvas=document.createElement('canvas');canvas.width=512;canvas.height=96;let c=canvas.getContext('2d');c.fillStyle='#e5ecec';c.fillRect(0,0,512,96);c.fillStyle='#254352';c.font='bold 52px Arial';c.textAlign='center';c.fillText('AMBULANCE',256,66);let texture=new THREE.CanvasTexture(canvas);let sign=new THREE.Mesh(new THREE.PlaneGeometry(1.55,.29),new THREE.MeshBasicMaterial({map:texture}));sign.position.set(0,1.37,2.77);g.add(sign)}

 // Batch painted geometry into one draw call per vehicle; retain wheels and lettering.
 const parts=g.children.filter(o=>o.isMesh&&!o.material.map),geometries=[];
 for(const part of parts){part.updateMatrix();let geo=part.geometry.clone().applyMatrix4(part.matrix);if(geo.index){const indexed=geo;geo=geo.toNonIndexed();indexed.dispose();}const rgb=[];for(let i=0;i<geo.attributes.position.count;i++)rgb.push(part.material.color.r,part.material.color.g,part.material.color.b);geo.setAttribute('color',new THREE.Float32BufferAttribute(rgb,3));geometries.push(geo)}
 const merged=mergeGeometries(geometries,false);if(merged){const body=new THREE.Mesh(merged,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.4,metalness:.25}));body.castShadow=true;parts.forEach(p=>{g.remove(p);p.geometry.dispose();p.material.dispose()});g.add(body)}geometries.forEach(g=>g.dispose());
 g.userData.id=id;return g;
}
