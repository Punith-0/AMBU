export const scenarioKinds=['home','crash','critical','transfer'];
export function validateEmergency(input,edges){
 if(!input||!edges.includes(input.pickup))throw Error('Choose a valid pickup road.');
 if(!scenarioKinds.includes(input.scenario))throw Error('Choose an incident type.');
 const numeric=value=>(typeof value==='number'||typeof value==='string'&&value.trim()!=='')&&Number.isFinite(Number(value));
 if(![input.urgency,input.seed,input.density].every(numeric))throw Error('Check urgency, seed and traffic demand.');
 if(input.ghost!==undefined&&typeof input.ghost!=='boolean')throw Error('Ghost race must be on or off.');
 const urgency=Number(input.urgency),seed=Number(input.seed),density=Number(input.density);
 if(!Number.isInteger(urgency)||urgency<1||urgency>3||!Number.isInteger(seed)||seed<0||seed>999999||!Number.isFinite(density)||density<.2||density>2)throw Error('Check urgency, seed and traffic demand.');
 if(!['auto','sanjeevani','aarogya','jeevan'].includes(input.hospital))throw Error('Choose a hospital.');
 return {name:String(input.name||'My emergency').trim().slice(0,60)||'My emergency',pickup:input.pickup,scenario:input.scenario,urgency,seed,density,hospital:input.hospital,ghost:!!input.ghost};
}
export function missionReport(a,world,baseline){
 const elapsed=(a.arrival??world.metrics.time)-a.requested,b=baseline?.ambulances.find(x=>x.id===a.id);
 const paired=!!b&&a.arrival!=null&&b.arrival!=null;
 const horizonAligned=!!baseline&&world.metrics.time===baseline.metrics.time;
 return {id:a.id,complete:a.arrival!=null,stage:a.stage,scenario:a.scenario,hospital:a.hospital_name,elapsed,wait:a.wait,pickupSeconds:a.pickup_at==null?null:a.pickup_at-a.requested,transportSeconds:a.arrival!=null&&a.transport_started!=null?a.arrival-a.transport_started:null,baselineSeconds:b?.arrival!=null?b.arrival-b.requested:null,savedSeconds:paired?(b.arrival-b.requested)-elapsed:null,normalWaitDelta:paired&&horizonAligned?world.metrics.normal_wait-baseline.metrics.normal_wait:null,comparisonHorizon:world.metrics.time,horizonAligned,paired,collisions:world.metrics.collisions+(baseline?.metrics.collisions||0)};
}
export function explainSignal(signal,world){
 if(!signal)return {reason:'Signal is unavailable.',requests:[]};
 const requests=Object.entries(world.coordination||{}).flatMap(([ambulance,items])=>items.filter(x=>x.id===signal.id).map(x=>({...x,ambulance})));
 const inClearance=['yellow','all-red'].includes(signal.stage);
 const activeReservation=requests.some(r=>['ready','clearing','requested'].includes(r.status));
 let reason=signal.priority?(activeReservation?'Emergency corridor reservation: an approaching verified ambulance has priority.':'The previous emergency priority is being released back to the normal controller.'):signal.manual?'Operator override is active and expires automatically.':signal.rl?'The learned policy chose an approved phase and hold duration.':'The standard signal program is cycling through its approved phases.';
 if(inClearance)reason+=' '+(signal.stage==='yellow'?'Yellow clearance is running before the next permitted phase.':'All-red clearance is running; conflicting movements stay stopped.');
 else if(signal.priority&&activeReservation)reason+=' The compatible permitted movements are being held for the selected request.';
 if(!signal.priority&&requests.length&&!activeReservation)reason+=' Upcoming ambulance requests are scheduled but have not taken control yet.';
 return {reason,requests,clearance:'Transitions require 3 seconds yellow followed by 2 seconds all-red. Conflicting requests are ordered by urgency, then dispatch age and ETA.'};
}
