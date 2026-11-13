import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {validateEmergency,missionReport,explainSignal} from '../dashboard/sandbox-data.js';

// Lightweight DOM adapter exercises the actual sandbox wiring without WebGL.
const nodes=new Map(),storage=new Map(),calls=[],selected=[],modes=[];let now=1000;
class Node {
 constructor(tag='div'){this.tagName=tag.toUpperCase();this.children=[];this.options=[];this._value='';this.hidden=false;this.checked=false;this.dataset={};this.listeners={};this.attributes={};this.textContent='';this.classList={add(){},remove(){},contains(){return false;}};}
 set id(v){this._id=v;nodes.set(v,this);}get id(){return this._id;}
 set value(v){v=String(v);this._value=this.tagName==='SELECT'&&!this.options.some(o=>o.value===v)?'':v;}get value(){return this._value;}
 set innerHTML(v){this._html=v;for(const m of v.matchAll(/<([\w-]+)([^>]*)>/g)){const id=m[2].match(/\bid="([^"]+)"/);if(!id)continue;const n=new Node(m[1]);n.id=id[1];n.hidden=/\bhidden\b/.test(m[2]);const value=m[2].match(/\bvalue="([^"]*)"/);if(value)n._value=value[1];}for(const m of v.matchAll(/<select\b([^>]*)>([\s\S]*?)<\/select>/g)){const id=m[1].match(/\bid="([^"]+)"/);if(!id)continue;const n=nodes.get(id[1]);for(const o of m[2].matchAll(/<option\b([^>]*)>([^<]*)<\/option>/g)){const value=o[1].match(/\bvalue="?([^"\s>]+)"?/);n.add(new Option(o[2],value?.[1]??o[2]));if(/\bselected\b/.test(o[1]))n.value=value?.[1]??o[2];}}}
 get innerHTML(){return this._html||'';}
 add(o){this.options.push(o);if(this.options.length===1)this._value=o.value;}
 append(...items){for(const i of items){this.children.push(i);i.parentNode=this;}}
 replaceChildren(...items){this.children=[];if(this.tagName==='SELECT'){this.options=[];this._value='';}this.append(...items);}
 insertBefore(n){this.append(n);}after(n){this.parentNode?.append(n);}setAttribute(k,v){this.attributes[k]=v;}
 addEventListener(type,f){(this.listeners[type]??=[]).push(f);}dispatchEvent(e){for(const f of this.listeners[e.type]||[])f(e);}
 click(){return this.onclick?.();}getContext(){return new Proxy({},{get:()=>()=>{},set:()=>true});}
}
class Option{constructor(text,value){this.textContent=text;this.value=String(value);}}
const body=new Node('body'),topline=new Node(),tab=new Node('button'),parent=new Node();
const document={body,head:new Node('head'),createElement:t=>new Node(t),createComment:()=>new Node(),getElementById:id=>nodes.get(id),querySelector:s=>s==='.topline'?topline:tab,addEventListener(){},documentElement:{requestFullscreen:()=>Promise.resolve()}};
const city={container:new Node(),network:{roads:[{id:'A0A1',shape:[[0,0],[0,150]]}]},setSandboxActive(v){this.sandboxActive=v;},resize(){},getSelectableObjects:()=>[],roadName:e=>e,clearSelection(){},clearGhost(){},updateGhost(){},home(){this.homed=true;},toggleNight(){},focusObject(){}};parent.append(city.container);
const journey={id:'AMBU-001',scenario:'home',stage:'responding',requested:10,arrival:null,wait:0,pickup_at:null,transport_started:null,hospital_name:'Sanjeevani Hospital'};
let payload={running:true,speed:1,worlds:[{ambulances:[journey],vehicles:[],signals:[],coordination:{},metrics:{time:20,vehicles:0,active:1,normal_wait:0,collisions:0}}]};
const context=vm.createContext({document,Option,validateEmergency,missionReport,explainSignal,performance:{now:()=>now},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},createSandboxCamera:()=>({setMode:m=>modes.push(m),stop(){},update(){},getBookmarks:()=>[],save(){},tour(){},recall(){},remove(){}}),setTimeout,URL,Blob,console});
const source=fs.readFileSync(new URL('../dashboard/sandbox.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace('export function setupSandbox','function setupSandbox')+'\nglobalThis.setupSandbox=setupSandbox;';vm.runInContext(source,context);
const sandbox=context.setupSandbox({city,api:async(path,data)=>{calls.push({path,data});return {ids:['AMBU-001']};},getState:()=>payload,select:id=>selected.push(id),notify:()=>{}});
const $=id=>nodes.get(id);

// Save/load must preserve a select's canonical option value, including 0.4.
$('em-density').value='0.4';$('em-save').onclick();assert.equal(JSON.parse(storage.get('ambu.emergencies.v1'))[0].density,.4);
$('em-density').value='2';$('em-load').onclick();assert.equal($('em-density').value,'0.4');
$('emergency-form').onsubmit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));assert.equal(calls[0].path,'control');assert.equal(calls[0].data.density,.4);assert.ok(calls.some(c=>c.path==='dispatch'));assert.equal($('em-error').textContent,'Loaded. Start scenario to reproduce these settings.');

// Debrief remains live when opened from the website, outside the sandbox.
sandbox.openDebrief();assert.match($('debrief-content').innerHTML,/10\.0 s/);payload.worlds[0].metrics.time=25;sandbox.update(payload);assert.match($('debrief-content').innerHTML,/15\.0 s/);

sandbox.enter();$('sb-home').onclick();assert.equal(modes.at(-1),'orbit');assert.equal(city.homed,true);
payload.error='SUMO detected a collision. Simulation paused for inspection.';payload.running=false;now+=500;sandbox.update(payload);assert.match($('sb-status').textContent,/SIMULATION PAUSED.*collision/);assert.equal($('sb-status').attributes.role,'alert');

// Following ordinary traffic must not replace the ambulance selected for telemetry.
city.container.dispatchEvent({type:'object-select',detail:{type:'vehicle',id:'car-12',name:'Car',edge:'A0A1'}});const selectionsBefore=selected.length;$('sb-object-actions').children.find(b=>b.textContent==='Follow vehicle').click();assert.equal(city.selected,'car-12');assert.equal(city.follow,true);assert.equal(selected.length,selectionsBefore);assert.equal(modes.at(-1),'orbit');

// Hospital action must use current fleet state rather than the inspected snapshot.
city.container.dispatchEvent({type:'object-select',detail:{type:'hospital',id:'hospital:1',name:'Aarogya',edge:'A0A1',hospitalKey:'aarogya'}});payload.worlds[0]={...payload.worlds[0],ambulances:[{...journey,id:'AMBU-002',stage:'responding'}]};$('sb-object-actions').children.find(b=>b.textContent==='Choose for active mission').click();assert.equal(calls.at(-1).path,'hospital/AMBU-002');
console.log('PASS saved Quiet scenario round-trip/launch, live website debrief, paused-error visibility, camera follow and current hospital target');
