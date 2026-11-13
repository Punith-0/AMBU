// Timestamped playback keeps network arrival jitter out of vehicle velocity.
export class PlaybackClock {
 constructor(){this.time=null;this.latest=0;this.rate=1;this.running=true;this.delay=.8;this.received=0;}
 receive(time,now,rate=1,running=true){
  if(this.time===null||time<this.latest){this.time=Math.max(0,time-.8*rate);}
  this.latest=time;this.rate=rate;this.running=running;this.received=now;
 }
 advance(dt,now){
  if(this.time===null)return 0;
  const target=this.latest-this.delay*this.rate;
  // Never jump the playback cursor at packet boundaries; correct small drift gently.
  const error=target-this.time;
  const speed=this.running?this.rate*Math.max(.85,Math.min(1.15,1+error*.12)):this.rate;
  this.time=Math.min(this.latest,this.time+Math.max(0,dt)*speed);
  return this.time;
 }
}
export function samplePose(samples,time){
 if(!samples.length)return null;
 while(samples.length>2&&samples[1].time<=time)samples.shift();
 const a=samples[0],b=samples[1];if(!b||time<=a.time)return {...a};
 const t=Math.max(0,Math.min(1,(time-a.time)/(b.time-a.time||1)));
 const da=((b.angle-a.angle+540)%360)-180,distance=Math.hypot(b.x-a.x,b.y-a.y);
 let x=a.x+(b.x-a.x)*t,y=a.y+(b.y-a.y)*t;
 if(Math.abs(da)>2&&Math.abs(da)<100&&distance<15){
  const ar=a.angle*Math.PI/180,br=b.angle*Math.PI/180,h00=2*t*t*t-3*t*t+1,h10=t*t*t-2*t*t+t,h01=-2*t*t*t+3*t*t,h11=t*t*t-t*t;
  x=h00*a.x+h10*distance*Math.sin(ar)+h01*b.x+h11*distance*Math.sin(br);
  y=h00*a.y+h10*distance*Math.cos(ar)+h01*b.y+h11*distance*Math.cos(br);
 }
 return {x,y,angle:a.angle+da*t,speed:distance/Math.max(.001,b.time-a.time),turn:da};
}
