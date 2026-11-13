"""Route-wide rolling ETA schedule with compatible-phase arbitration."""
import traci.constants as tc

class CorridorCoordinator:
    def __init__(self):
        self.plan={};self.reservations={};self.trace=[];self.previous={}

    def schedule(self,sim):
        requests={};self.plan={}
        readings=sim.c.lanearea.getAllSubscriptionResults()
        for vid,a in sim.ambulances.items():
            if vid not in sim.vdata or not sim.eligible(a):continue
            speed=max(7,min(13.89,sim.vdata[vid][tc.VAR_SPEED] or 10))
            routeplan=[]
            cumulative_delay=0.
            for tid,index,distance,state in sim.c.vehicle.getNextTLS(vid):
                links=sim.signals[tid]['links'][index]
                lanes={link[0] for link in links}
                queue=sum(readings.get('e2_'+lane,{}).get(tc.LAST_STEP_VEHICLE_HALTING_NUMBER,0) for lane in lanes)
                eta=distance/speed+cumulative_delay
                clearance=5+min(20,queue*2)
                due=eta<=min(45,clearance+10)
                item={'id':tid,'index':index,'distance_m':round(distance,1),'eta_s':round(eta,1),'prepare_at':round(sim.time+max(0,eta-clearance-10),1),'queue':queue,'status':'scheduled'}
                if due:
                    # Earlier dispatch provides aging within the same urgency.
                    rank=(-a['urgency'],a['requested'],eta,vid)
                    candidates=[p.state for p in sim.signals[tid]['phases'] if p.state[index] in 'gG' and 'y' not in p.state]
                    target=next((s for s in candidates if s[index]=='G'),candidates[0] if candidates else None)
                    if target:
                        item['status']='requested'
                        if tid not in requests or rank<requests[tid]['rank']:
                            requests[tid]={'rank':rank,'index':index,'vehicle':vid,'target':target,'eta':eta}
                routeplan.append(item)
                cumulative_delay+=min(8,queue*.5)
            self.plan[vid]=routeplan
        self.reservations=requests
        for vid,plan in self.plan.items():
            for item in plan:
                tid=item['id'];request=requests.get(tid)
                if item['status']=='requested':
                    if request and request['vehicle']==vid:
                        actual=sim.c.trafficlight.getRedYellowGreenState(tid)
                        item['status']='ready' if actual[item['index']] in 'gG' and tid not in sim.transitions else 'clearing'
                    else:item['status']='yielding to higher priority'
                key=(vid,tid);status=item['status']
                if self.previous.get(key)!=status:
                    event={'time':sim.time,'ambulance':vid,'junction':tid,'status':status,'eta_s':item['eta_s']}
                    self.trace.append(event);self.previous[key]=status
        self.trace=self.trace[-10000:]
        return {tid:(r['rank'],r['index'],r['vehicle']) for tid,r in requests.items()}
