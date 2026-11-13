// Original, locally synthesized sound design. These are illustrative cues, not medical readings.
export function audioStage(world,running=true,selected=null){
 if(!running)return 'idle';
 const fleet=world?.ambulances||[];const chosen=fleet.find(a=>a.id===selected);const active=(chosen?[chosen]:fleet).filter(a=>a.active&&a.arrival===null);
 if(active.some(a=>a.stage==='transport'))return 'transport';
 if(active.some(a=>a.stage==='responding'))return 'responding';
 if(active.some(a=>a.stage==='loading'||a.stage==='awaiting_hospital'))return 'loading';
 return 'idle';
}
class MissionAudio{
 constructor(){this.stage='idle';this.overlay=null;this.enabled=true;this.ctx=null;this.tick=0;}
 install(){
  const host=document.querySelector('.connection');if(!host)return;
  const b=document.createElement('button');b.id='mission-sound';b.className='secondary';b.textContent='Sound on';b.setAttribute('aria-pressed','true');b.title='Mission sound: responding siren / patient transport / hospital handover';host.prepend(b);
  b.onclick=()=>{this.enabled=!this.enabled;b.textContent=this.enabled?'Sound on':'Sound off';b.setAttribute('aria-pressed',String(this.enabled));this.unlock();this.apply()};
  document.addEventListener('pointerdown',()=>this.unlock(),{once:true});
  document.addEventListener('visibilitychange',()=>this.apply());
  this.timer=setInterval(()=>this.pulse(),70);
 }
 unlock(){
  if(!this.ctx){const AC=globalThis.AudioContext||globalThis.webkitAudioContext;if(!AC)return;this.ctx=new AC();this.master=this.ctx.createGain();this.master.gain.value=0;this.master.connect(this.ctx.destination);this.osc=this.ctx.createOscillator();this.osc.type='sine';this.siren=this.ctx.createGain();this.siren.gain.value=0;this.osc.connect(this.siren);this.siren.connect(this.master);this.osc.start();}
  this.ctx.resume().catch(()=>{});this.apply();
 }
 update(w,running,selected){this.stage=audioStage(w,running,selected);const b=document.getElementById('mission-sound');if(b)b.dataset.stage=this.stage;this.apply();}
 scene(kind){this.overlay=kind;this.apply();}
 apply(){const b=document.getElementById('mission-audio-toggle');if(b){b.textContent=this.enabled?'Sound on':'Sound off';b.setAttribute('aria-pressed',String(this.enabled));}if(!this.ctx)return;const quiet=document.body.dataset.view==='compare'||document.hidden||document.getElementById('voice-panel')?.hidden===false;this.master.gain.setTargetAtTime(this.enabled && !quiet ? .13 : 0,this.ctx.currentTime,.15);}
 tone(f,d=.1,volume=.3){if(!this.ctx)return;const t=this.ctx.currentTime,o=this.ctx.createOscillator(),g=this.ctx.createGain();o.frequency.value=f;g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(volume,t+.012);g.gain.exponentialRampToValueAtTime(.0001,t+d);o.connect(g);g.connect(this.master);o.start(t);o.stop(t+d+.03);o.onended=()=>{o.disconnect();g.disconnect()};}
 pulse(){
  if(!this.ctx)return;this.apply();const t=this.ctx.currentTime,mode=this.overlay||this.stage;
  const siren=mode==='responding'||mode==='transport';this.siren.gain.setTargetAtTime(siren?(mode==='transport'?.22:.42):0,t,.1);
  if(siren){const cycle=mode==='responding'?3.4:1.15;this.osc.frequency.setTargetAtTime(690+220*Math.sin(t*2*Math.PI/cycle),t,.06);}
  if(mode!==this.previous){this.previous=mode;this.lastBeat=t;if(mode==='handover'){this.tone(660,.22);setTimeout(()=>this.tone(880,.3),260)}else if(mode==='driver')this.tone(520,.2);}
  if(mode==='transport'&&t-(this.lastBeat||0)>1.6){this.lastBeat=t;this.tone(1050,.07,.12)}
  if((mode==='patient'||mode==='loading')&&t-(this.lastBeat||0)>2){this.lastBeat=t;this.tone(740,.09,.13)}
 }
}
export const missionAudio=new MissionAudio();
