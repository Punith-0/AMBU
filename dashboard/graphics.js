import {mergeGeometries} from './vendor/BufferGeometryUtils.js?v=20261104s';
import * as THREE from 'three';
const facades=[];
export function facadeMaterial(index){
 if(facades[index%4])return facades[index%4];
 const c=document.createElement('canvas');c.width=512;c.height=512;const x=c.getContext('2d');
 x.fillStyle=['#b5aca0','#9ba6aa','#c4bba7','#8f9c9a'][index%4];x.fillRect(0,0,512,512);
 for(let row=0;row<8;row++)for(let col=0;col<6;col++){
  const px=col*84+13,py=row*64+12;
  x.fillStyle='#626b6e';x.fillRect(px-3,py-3,60,45);
  const g=x.createLinearGradient(px,py,px+54,py+38);g.addColorStop(0,'#6a8490');g.addColorStop(.45,'#344a57');g.addColorStop(1,'#9aa7a7');x.fillStyle=g;x.fillRect(px,py,54,38);
  x.fillStyle='#b9c0bd';x.fillRect(px+26,py,2,38);x.fillRect(px,py+18,54,2);
  x.fillStyle='#d3cec3';x.fillRect(px-4,py+39,62,4);
 }
 const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=4;
 const wall=new THREE.MeshStandardMaterial({map:texture,roughness:.7});
 const roof=new THREE.MeshStandardMaterial({color:0x778080,roughness:.95});
 return facades[index%4]=[wall,wall,roof,roof,wall,wall];
}
export function installGraphics(city){
 // Clean satin road finish: restrained highlights, no coarse imported aggregate.
 city.asphalt=new THREE.MeshStandardMaterial({color:0x35434b,roughness:.72,metalness:.04});
 const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=512;const ctx=canvas.getContext('2d');let gradient=ctx.createLinearGradient(0,0,0,512);
 gradient.addColorStop(0,'#577da1');gradient.addColorStop(.45,'#c6d5de');gradient.addColorStop(.52,'#e5d8be');gradient.addColorStop(.6,'#6a746f');gradient.addColorStop(1,'#34453e');ctx.fillStyle=gradient;ctx.fillRect(0,0,1024,512);
 const env=new THREE.CanvasTexture(canvas);env.mapping=THREE.EquirectangularReflectionMapping;env.colorSpace=THREE.SRGBColorSpace;
 city.scene.environment=env;city.scene.background=env;city.scene.fog=new THREE.Fog(0xb5c5ca,950,2300);city.sun.color.setHex(0xffe4b6);city.sun.intensity=3;city.ambient.intensity=1.1;
}

export function batchCity(city){
 const groups=new Map();city.scene.updateMatrixWorld(true);
 const add=(geometry,material,obj)=>{const key=material.uuid+':'+obj.castShadow+':'+obj.receiveShadow;if(!groups.has(key))groups.set(key,{geos:[],material,cast:obj.castShadow,receive:obj.receiveShadow});groups.get(key).geos.push(geometry)};
 for(const obj of [...city.scene.children]){
  if(!obj.isMesh||obj.isInstancedMesh)continue;
  // Invisible intersection pick targets participate in raycasts only.
  if(obj.material.colorWrite===false){city.scene.remove(obj);continue;}
  if(Array.isArray(obj.material)){
   const geo=obj.geometry.clone().applyMatrix4(obj.matrixWorld);const flat=geo.index?geo.toNonIndexed():geo;
   for(const group of geo.groups){const part=new THREE.BufferGeometry();for(const [name,attr] of Object.entries(flat.attributes)){part.setAttribute(name,new THREE.BufferAttribute(attr.array.slice(group.start*attr.itemSize,(group.start+group.count)*attr.itemSize),attr.itemSize,attr.normalized))}add(part,obj.material[group.materialIndex],obj)}
   if(flat!==geo)flat.dispose();geo.dispose();
  }else add(obj.geometry.clone().applyMatrix4(obj.matrixWorld),obj.material,obj);
  city.scene.remove(obj);obj.geometry.dispose();
 }
 for(const group of groups.values()){
  // Normalize indexing so facade faces and solid boxes can share a material batch.
  const geos=group.geos.map(g=>g.index?g.toNonIndexed():g);const merged=mergeGeometries(geos,false);
  for(const g of new Set([...geos,...group.geos]))g.dispose();if(!merged)continue;
  const mesh=new THREE.Mesh(merged,group.material);mesh.castShadow=group.cast;mesh.receiveShadow=group.receive;city.scene.add(mesh);
 }
}

export function batchSignals(city){
 const lamps=[...city.signalMeshes.values()].flat();
 const mesh=new THREE.InstancedMesh(new THREE.SphereGeometry(.74,8,6),new THREE.MeshBasicMaterial({color:0xffffff}),lamps.length);
 mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);city.scene.updateMatrixWorld(true);
 lamps.forEach((lamp,i)=>{lamp.userData.instance=i;mesh.setMatrixAt(i,lamp.matrixWorld);mesh.setColorAt(i,new THREE.Color(0x294135));city.scene.remove(lamp);lamp.geometry.dispose()});
 mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);mesh.computeBoundingSphere();city.signalInstances=mesh;city.scene.add(mesh);
}
