import assert from 'node:assert/strict';
import * as THREE from 'three';
import {batchCity,batchSignals} from '../dashboard/graphics.js';
const scene=new THREE.Scene(),wall=new THREE.MeshStandardMaterial({color:0xabcdef}),roof=new THREE.MeshStandardMaterial({color:0xaabbcc});
const mats=[wall,wall,roof,roof,wall,wall];
for(let i=0;i<2;i++){const m=new THREE.Mesh(new THREE.BoxGeometry(10,20,10),mats);m.position.set(i*20,10,0);m.rotation.y=.3;scene.add(m)}
const lamp=new THREE.Mesh(new THREE.SphereGeometry(.74,8,8),wall);lamp.position.set(5,7,0);scene.add(lamp);
const pick=new THREE.Mesh(new THREE.SphereGeometry(2,8,6),new THREE.MeshBasicMaterial({colorWrite:false,depthWrite:false}));pick.position.set(20,2,0);scene.add(pick);
const city={scene,signalMeshes:new Map([['lane',[lamp]]])};scene.updateMatrixWorld(true);
const expected=new THREE.Box3();for(const o of scene.children)if(o!==lamp&&o!==pick)expected.expandByObject(o);
const ray=new THREE.Raycaster(new THREE.Vector3(20,2,20),new THREE.Vector3(0,0,-1));const hitBefore=ray.intersectObject(pick)[0].distance;
batchSignals(city);batchCity(city);
const total=scene.children.filter(o=>o.isMesh&&!o.isInstancedMesh).reduce((n,o)=>n+o.geometry.attributes.position.count/3,0);
assert.equal(total,24);assert.equal(scene.children.filter(o=>o.isMesh&&!o.isInstancedMesh).length,2);assert.ok(scene.children.includes(city.signalInstances));
const actual=new THREE.Box3();for(const o of scene.children)if(o.isMesh&&!o.isInstancedMesh)actual.expandByObject(o);
assert.ok(expected.min.distanceTo(actual.min)<1e-5);assert.ok(expected.max.distanceTo(actual.max)<1e-5);
assert.equal(ray.intersectObject(pick)[0].distance,hitBefore);const transform=new THREE.Matrix4();city.signalInstances.getMatrixAt(0,transform);assert.equal(transform.elements[12],5);assert.equal(transform.elements[13],7);
city.signalInstances.setColorAt(0,new THREE.Color(0xff0000));const color=new THREE.Color();city.signalInstances.getColorAt(0,color);assert.equal(color.getHex(),0xff0000);
console.log('PASS batch: all facade triangles/materials/bounds retained, pick ray still works, lamp transform and live color update preserved');
