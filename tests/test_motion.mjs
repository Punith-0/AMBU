import assert from 'node:assert/strict';
import {PlaybackClock,samplePose} from '../dashboard/motion.js';
const clock=new PlaybackClock(),samples=[];let next=0,last=null,velocities=[];
for(let frame=0;frame<900;frame++){
 const now=frame/60;
 const arrival=next*.5+([.05,.17,0,.1][next%4]);
 if(now>=arrival){const time=next*.5;samples.push({time,x:time*10,y:0,angle:90});clock.receive(time,now*1000,1,true);next++}
 const t=clock.advance(1/60,now*1000),pose=samplePose(samples,t);
 if(pose){if(last!==null&&now>3)velocities.push((pose.x-last)*60);last=pose.x}
}
assert(Math.min(...velocities)>7,'Unwanted stop between packets');assert(Math.max(...velocities)<13,'Velocity surge between packets');
const stopped=[{time:0,x:0,y:0,angle:0},{time:.5,x:0,y:0,angle:0}];assert.equal(samplePose(stopped,.25).y,0);
clock.running=false;for(let i=0;i<200;i++)clock.advance(1/60,16000+i);assert.equal(clock.time,clock.latest);
console.log('PASS jittered 60-FPS motion, stationary stop, pause. Velocity range:',Math.min(...velocities).toFixed(2),Math.max(...velocities).toFixed(2));
