"""Independent SUMO runs, virtual sensors, and clearance-safe priority control."""
import math, uuid, tempfile, shutil, heapq, time
from pathlib import Path
from .network import ROOT, SUMO, traci, demand
import traci.constants as tc
from .rl import SignalLearner
from .coordination import CorridorCoordinator
from .missions import STATION, hospital, nearest

class Simulation:
    def __init__(self, net, seed=42, density=1.0, enabled=True, models=None):
        self.net, self.seed, self.density, self.enabled, self.models = net, seed, density, enabled, models
        self.folder = Path(tempfile.mkdtemp(prefix='ambu_'))
        routefile = demand(net, seed, density, self.folder)
        self.label = str(uuid.uuid4())
        traci.start([str(SUMO), '-n', str(ROOT/'sumo/nightwatch.net.xml'), '-r', str(routefile), '-a', str(ROOT/'sumo/sensors.add.xml'), '--seed', str(seed), '--step-length', '0.5', '--no-step-log', 'true', '--duration-log.disable', 'true', '--no-warnings', 'true', '--time-to-teleport', '-1', '--collision.action', 'warn', '--collision.check-junctions', 'true', '--log', str(self.folder/'sumo.log')], label=self.label, stdout=open(self.folder/'stdout.log', 'w'))
        self.c = traci.getConnection(self.label)
        self.time = 0
        self.ambulances = {}
        self.transitions = {}
        self.owned = set()
        self.vdata = {}
        self.rl = SignalLearner(seed)
        self.rl_owned = set()
        self.rl_cost = {}
        self.coordinator = CorridorCoordinator()
        self.motion = {}
        self.manual = {}
        self.manual_owned = set()
        self.road_restrictions = {}
        self.history, self.events = [], []
        self.arrived = self.wait_integral = self.queue_integral = self.steps = self.collisions = 0
        self.signals = {}
        for tid in self.c.trafficlight.getIDList():
            logic = self.c.trafficlight.getAllProgramLogics(tid)[0]
            self.signals[tid] = {'program': logic.programID, 'phases': logic.phases, 'links': self.c.trafficlight.getControlledLinks(tid)}
        self.e2 = self.c.lanearea.getIDList()
        self.e1 = self.c.inductionloop.getIDList()
        for d in self.e2:
            self.c.lanearea.subscribe(d, [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_VEHICLE_HALTING_NUMBER, tc.LAST_STEP_OCCUPANCY, tc.LAST_STEP_MEAN_SPEED])
        self.detector_lanes = {d:self.c.lanearea.getLaneID(d) for d in self.e2}
        self.last = self.snapshot()

    def log(self, message):
        self.events.append({'time': self.time, 'message': message})
        self.events = self.events[-60:]

    def restrict_road(self, edge_id, restricted):
        """Apply a reversible, directed-road speed restriction in the traffic engine."""
        if edge_id not in self.net._id2edge or self.net.getEdge(edge_id).getFunction() == 'internal':
            raise ValueError('Choose a valid external road')
        if restricted:
            if edge_id in self.road_restrictions:
                return
            limits = {lane.getID(): self.c.lane.getMaxSpeed(lane.getID()) for lane in self.net.getEdge(edge_id).getLanes()}
            for lane_id, original in limits.items():
                self.c.lane.setMaxSpeed(lane_id, min(3., original))
            self.road_restrictions[edge_id] = limits
            self.log(f'{edge_id}: temporary traffic restriction, 3 m/s speed limit')
        else:
            limits = self.road_restrictions.pop(edge_id, None)
            if limits is None:
                return
            for lane_id, original in limits.items():
                self.c.lane.setMaxSpeed(lane_id, original)
            self.log(f'{edge_id}: original road speed limits restored')
        # Publish even when the simulation clock is paused.
        self.last = self.snapshot()

    def route(self, start, end):
        # Physical road distance, independent of traffic queues and signal policy.
        path, distance = self.net.getShortestPath(self.net.getEdge(start), self.net.getEdge(end))
        if not path: raise ValueError('No connected route between selected roads')
        return [edge.getID() for edge in path]

    def features(self, route):
        edges = [self.net.getEdge(e) for e in route if not e.startswith(':')]
        count = sum(self.c.edge.getLastStepVehicleNumber(e.getID()) for e in edges)
        queue = sum(self.c.edge.getLastStepHaltingNumber(e.getID()) for e in edges)
        speed = sum(max(0, self.c.edge.getLastStepMeanSpeed(e.getID())) for e in edges)/max(1, len(edges))
        distance = sum(e.getLength() for e in edges)
        return [distance, count, speed, queue, len(edges), self.density]

    def dispatch(self, start='A0A1', end='E3E4', urgency=2, active=True, registered=True, vehicle_id=None, scenario='critical', hospital_name='Sanjeevani Hospital', mission=False):
        vid = vehicle_id or f'AMBU-{len(self.ambulances)+1:03d}'
        if vid in self.ambulances: raise ValueError('Duplicate ambulance ID')
        pickup=start
        if mission:start,end=STATION['edge'],pickup
        path = self.route(start, end)
        x = self.features(path)
        prediction = self.models.predict(x) if self.models and self.models.ready else None
        probability = self.models.priority(x) if self.models and self.models.ready else None
        self.c.route.add(vid+'_route', path)
        self.c.vehicle.add(vid, vid+'_route', typeID='ambulance', departLane='best', departSpeed='0')
        self.ambulances[vid] = {'id': vid, 'scenario':scenario,'hospital_name':hospital_name,'origin':start, 'route': path, 'destination': end, 'urgency': urgency, 'active': active, 'registered': registered, 'requested': self.time, 'departed': None, 'arrival': None, 'wait': 0., 'features': x, 'prediction': prediction, 'probability': probability, 'samples': [], 'last_reroute': self.time, 'last_seen': self.time}
        if mission:
            a=self.ambulances[vid]
            a.update(stage='responding',pickup=pickup,station=STATION['name'],hospital_id=None,selected_hospital=None,pickup_at=None,choice_deadline=None,loading_until=None)
            lane=self.net.getEdge(pickup).getLanes()[0]
            self.c.vehicle.setStop(vid,pickup,pos=lane.getLength()-10,laneIndex=0,duration=100000)
        else:self.ambulances[vid]['stage']='transport'
        self.log(f'{vid}: '+('emergency dispatch verified' if active and registered else 'routine trip — no emergency priority'))
        return vid

    def select_hospital(self,vid,hid,automatic=False):
        a=self.ambulances.get(vid)
        h=hospital(hid)
        if not a or not h:raise ValueError('Unknown ambulance or hospital')
        if a.get('stage') not in ('responding','awaiting_hospital','loading'):raise ValueError('Hospital selection is closed for this journey')
        a['selected_hospital']=hid
        if a.get('stage')=='responding':return
        a.update(hospital_id=hid,hospital_name=h['name'],destination=h['edge'],stage='loading',choice_deadline=None,loading_until=time.monotonic()+6.5)
        self.log(f'{vid}: {h["name"]} '+('automatically selected by road distance' if automatic else 'selected')+'; patient loading')

    def advance_missions(self):
        for vid,a in self.ambulances.items():
            if vid not in self.vdata:continue
            if a.get('stage')=='responding' and self.c.vehicle.isStopped(vid):
                a.update(stage='awaiting_hospital',pickup_at=self.time,choice_deadline=time.monotonic()+7)
                self.log(f'{vid}: reached patient; hospital choice open for 7 seconds')
                if a.get('selected_hospital'):self.select_hospital(vid,a['selected_hospital'])
            if a.get('stage')=='awaiting_hospital' and time.monotonic()>=a['choice_deadline']:
                self.select_hospital(vid,nearest(self.net,a['pickup'])['id'],True)
            if a.get('stage')=='loading' and time.monotonic()>=a['loading_until']:
                road=self.c.vehicle.getRoadID(vid)
                path=self.route(road,a['destination'])
                # If the closest hospital is on the pickup edge, continue to its endpoint.
                self.c.vehicle.setRoute(vid,path);self.c.vehicle.resume(vid)
                a.update(stage='transport',route=path,transport_started=self.time,last_reroute=self.time)
                self.log(f'{vid}: patient aboard; departing to {a["hospital_name"]}')

    def deactivate(self, vid):
        if vid not in self.ambulances: raise ValueError('Unknown ambulance')
        self.ambulances[vid]['active'] = False
        self.log(f'{vid}: emergency deactivated')

    def manual_signal(self,tid,phase):
        if tid not in self.signals:raise ValueError('Unknown junction')
        if tid in self.coordinator.reservations:raise ValueError('An emergency corridor owns this junction; manual override is unavailable')
        if phase=='auto':
            self.manual.pop(tid,None);return
        phases=list(dict.fromkeys(p.state for p in self.signals[tid]['phases'] if 'y' not in p.state and any(ch in 'gG' for ch in p.state)))
        if phase=='red':target='r'*len(self.c.trafficlight.getRedYellowGreenState(tid))
        else:
            try:
                index=int(phase)
                if not 0<=index<len(phases):raise ValueError()
                target=phases[index]
            except (ValueError,IndexError):raise ValueError('Choose an approved green phase')
        self.manual[tid]={'target':target,'expires':self.time+30}
        self.log(f'{tid}: operator override requested for 30 simulation seconds')

    def eligible(self, a):
        # Journey-level benefit predictions are advisory, not emergency eligibility.
        # A low score must not disable the corridor for a verified active mission.
        return a.get('stage') not in ('awaiting_hospital','loading','complete') and self.enabled and a['registered'] and a['active'] and self.time-a['last_seen'] <= 2

    def transition(self, tid, target):
        c = self.c
        state = c.trafficlight.getRedYellowGreenState(tid)
        if tid in self.transitions: return
        if state == target: return
        yellow = ''.join('y' if ch in 'gGyY' else 'r' for ch in state)
        c.trafficlight.setRedYellowGreenState(tid, yellow)
        self.owned.add(tid)
        self.transitions[tid] = {'stage': 'yellow', 'until': self.time+3, 'target': target, 'post_ambulance_hold': 2 if target is None and tid not in self.manual_owned and tid not in self.rl_owned else 0}

    def control(self):
        c = self.c
        requests = self.coordinator.schedule(self)
        self.manual={tid:r for tid,r in self.manual.items() if r['expires']>self.time}
        for tid in set(requests) | self.owned | set(self.transitions) | set(self.manual) | (set(self.signals) if self.rl.enabled and self.enabled else set()):
            if tid in requests:
                self.rl.interrupt(tid)
                self.rl_owned.discard(tid)
                self.manual_owned.discard(tid)
                self.manual.pop(tid,None)
            if tid in self.transitions:
                t = self.transitions[tid]
                if self.time >= t['until']:
                    if t['stage'] == 'yellow':
                        c.trafficlight.setRedYellowGreenState(tid, 'r'*len(c.trafficlight.getRedYellowGreenState(tid)))
                        t.update(stage='all-red', until=self.time+2+t.get('post_ambulance_hold',0))
                    else:
                        if t['target'] is None:
                            c.trafficlight.setProgram(tid, self.signals[tid]['program'])
                            c.trafficlight.setPhase(tid, 0)
                            self.owned.discard(tid)
                            self.rl_owned.discard(tid)
                            self.manual_owned.discard(tid)
                        else:
                            # Revalidate a pending target after clearance; cancel stale emergency reservations.
                            reservation=self.coordinator.reservations.get(tid)
                            target=reservation['target'] if reservation else self.manual[tid]['target'] if tid in self.manual else t['target'] if tid in self.rl_owned and self.rl.enabled and self.enabled else None
                            if target is None:
                                c.trafficlight.setProgram(tid,self.signals[tid]['program']);c.trafficlight.setPhase(tid,0);self.owned.discard(tid);self.rl_owned.discard(tid)
                            else:c.trafficlight.setRedYellowGreenState(tid,target)
                        del self.transitions[tid]
                continue
            if tid in requests:
                _, idx, vid = requests[tid]
                state = c.trafficlight.getRedYellowGreenState(tid)
                candidates = [p.state for p in self.signals[tid]['phases'] if p.state[idx] in 'gG' and 'y' not in p.state]
                target = next((s for s in candidates if s[idx]=='G'), candidates[0] if candidates else state)
                if state != target: self.transition(tid, target)
                else:
                    c.trafficlight.setRedYellowGreenState(tid,target)
                    self.owned.add(tid)
            elif tid in self.owned and tid not in self.manual_owned and tid not in self.rl_owned:
                # End emergency ownership with clearance plus the requested extra hold.
                self.transition(tid, None)
            elif tid in self.manual:
                self.rl.interrupt(tid);self.rl_owned.discard(tid);self.manual_owned.add(tid)
                target=self.manual[tid]['target']
                if c.trafficlight.getRedYellowGreenState(tid)!=target:self.transition(tid,target)
                else:c.trafficlight.setRedYellowGreenState(tid,target);self.owned.add(tid)
            elif self.rl.enabled and self.enabled:
                if self.time < self.rl.next_decision.get(tid, 0): continue
                phases=list(dict.fromkeys(p.state for p in self.signals[tid]['phases'] if 'y' not in p.state and any(ch in 'gG' for ch in p.state)))
                if not phases: continue
                lanes=list(dict.fromkeys(link[0][0] for link in self.signals[tid]['links'] if link))
                readings=self.c.lanearea.getAllSubscriptionResults()
                queues=[readings.get('e2_'+lane,{}).get(tc.LAST_STEP_VEHICLE_HALTING_NUMBER,0) for lane in lanes]
                current=self.c.trafficlight.getRedYellowGreenState(tid)
                state=[min(3,int(q)//3) for q in queues]+[phases.index(current) if current in phases else len(phases)]
                actions=[(phase,hold) for phase in phases for hold in (10,20,30)]
                target,hold=self.rl.choose(tid,state,actions,self.time,self.rl_cost.get(tid,0.))
                self.rl_owned.add(tid)
                if current!=target:self.transition(tid,target)
                else:
                    self.c.trafficlight.setRedYellowGreenState(tid,target)
                    self.owned.add(tid)
            elif tid in self.owned: self.transition(tid, None)

    def step(self, n=1):
        self.motion = {}
        for _ in range(n):
            self.c.simulationStep()
            self.time = self.c.simulation.getTime()
            for v in self.c.simulation.getDepartedIDList():
                self.c.vehicle.subscribe(v,[tc.VAR_POSITION,tc.VAR_SPEED,tc.VAR_ANGLE,tc.VAR_LENGTH])
            self.vdata = self.c.vehicle.getAllSubscriptionResults()
            ids = set(self.vdata)
            for vid,data in self.vdata.items():
                x,y=data[tc.VAR_POSITION];angle=data[tc.VAR_ANGLE];length=data[tc.VAR_LENGTH]
                radians=math.radians(angle)
                # SUMO positions are front-bumper coordinates; render physical centres.
                self.motion.setdefault(vid,[]).append({'time':self.time,'x':x-math.sin(radians)*length/2,'y':y-math.cos(radians)*length/2,'angle':angle})
            arrived = set(self.c.simulation.getArrivedIDList())
            self.arrived += len(arrived)
            self.collisions += self.c.simulation.getCollidingVehiclesNumber()
            for vid, a in self.ambulances.items():
                if vid in ids:
                    a['last_seen'] = self.time
                    if a['departed'] is None: a['departed'] = self.time
                    a['wait'] += .5 if self.vdata[vid][tc.VAR_SPEED]<.1 else 0
                    if int(self.time*2)%4 == 0:
                        path = list(self.c.vehicle.getRoute(vid))[self.c.vehicle.getRouteIndex(vid):]
                        fx = self.features(path)
                        a['remaining_distance'] = max(0,fx[0]-self.c.vehicle.getLanePosition(vid))
                        a['remaining_prediction'] = self.models.predict(fx) if self.models and self.models.ready else None
                        a['kinematic_eta'] = a['remaining_distance']/max(4,fx[2])+fx[3]*1.5
                        a['next_signals'] = [{'id':tid,'distance':dist,'state':state} for tid,idx,dist,state in self.c.vehicle.getNextTLS(vid)[:3]]
                        if int(self.time*2)%20 == 0: a['samples'].append((self.time, fx))
                    if self.eligible(a) and self.time-a['last_reroute'] >= 15:
                        road = self.c.vehicle.getRoadID(vid)
                        if road and not road.startswith(':'):
                            path = self.route(road, a['destination'])
                            self.c.vehicle.setRoute(vid, path)
                            a['route'] = list(self.c.vehicle.getRoute(vid))
                            a['last_reroute'] = self.time
                if vid in arrived:
                    a['arrival'] = self.time
                    a['stage']='complete'
                    self.log(f'{vid}: hospital reached in {self.time-a["requested"]:.1f}s')
            self.advance_missions()
            if self.rl.enabled:
                readings=self.c.lanearea.getAllSubscriptionResults()
                for tid,signal in self.signals.items():
                    lanes=set(link[0][0] for link in signal['links'] if link)
                    queue=sum(readings.get('e2_'+lane,{}).get(tc.LAST_STEP_VEHICLE_HALTING_NUMBER,0) for lane in lanes)
                    emergency_wait=sum(1 for vid,a in self.ambulances.items() if vid in self.vdata and a['active'] and self.vdata[vid][tc.VAR_SPEED]<.1 and self.c.vehicle.getLaneID(vid) in lanes)
                    self.rl_cost[tid]=self.rl_cost.get(tid,0.)+.5*(queue+5*emergency_wait)
            self.control()
            self.wait_integral += .5*sum(self.vdata[v][tc.VAR_SPEED]<.1 for v in ids if v not in self.ambulances)
            self.queue_integral += sum(v[tc.LAST_STEP_VEHICLE_HALTING_NUMBER] for v in self.c.lanearea.getAllSubscriptionResults().values())
            self.steps += 1
        self.last = self.snapshot()
        if int(self.time)%5 == 0:
            self.history.append({k:self.last['metrics'][k] for k in ['time','vehicles','queue','speed','arrived','normal_wait']})
            self.history = self.history[-360:]
        return self.last

    def snapshot(self):
        c = self.c
        vehicles = []
        for v, data in self.vdata.items():
            x,y = data[tc.VAR_POSITION]
            length=data[tc.VAR_LENGTH];radians=math.radians(data[tc.VAR_ANGLE]);x-=math.sin(radians)*length/2;y-=math.cos(radians)*length/2
            vehicles.append({'id': v, 'x': x, 'y': y, 'angle': data[tc.VAR_ANGLE], 'speed': data[tc.VAR_SPEED], 'ambulance': v in self.ambulances,'path':self.motion.get(v,[])})
        sensors = [{'id': d, 'lane': self.detector_lanes[d], 'count': data[tc.LAST_STEP_VEHICLE_NUMBER], 'queue': data[tc.LAST_STEP_VEHICLE_HALTING_NUMBER], 'occupancy': data[tc.LAST_STEP_OCCUPANCY], 'speed': max(0,data[tc.LAST_STEP_MEAN_SPEED])} for d,data in c.lanearea.getAllSubscriptionResults().items()]
        signals = []
        for tid in self.signals:
            links = self.signals[tid]['links']
            state = c.trafficlight.getRedYellowGreenState(tid)
            signals.append({'id': tid, 'state': state, 'priority': tid in self.owned and tid not in self.rl_owned and tid not in self.manual_owned, 'rl':tid in self.rl_owned,'manual':tid in self.manual,'phases':list(dict.fromkeys(p.state for p in self.signals[tid]['phases'] if 'y' not in p.state and any(ch in 'gG' for ch in p.state))), 'stage': self.transitions.get(tid,{}).get('stage','Manual override' if tid in self.manual else 'RL adaptive' if tid in self.rl_owned else 'priority green' if tid in self.owned else 'normal'), 'remaining': max(0,self.transitions.get(tid,{}).get('until',c.trafficlight.getNextSwitch(tid))-self.time) if tid not in self.owned or tid in self.transitions else None, 'links': [{'lane': link[0][0], 'state': state[i]} for i,link in enumerate(links) if link]})
        ambulances = [{**{k:v for k,v in a.items() if k not in ('samples','features','choice_deadline','loading_until')},'loading_remaining_s':max(0,a['loading_until']-time.monotonic()) if a.get('loading_until') else None,'choice_remaining_s':max(0,a['choice_deadline']-time.monotonic()) if a.get('choice_deadline') else None} for a in self.ambulances.values()]
        speed = sum(v['speed'] for v in vehicles)/max(1,len(vehicles))
        queue = sum(s['queue'] for s in sensors)
        completed = [a['arrival']-a['requested'] for a in self.ambulances.values() if a['arrival'] is not None]
        congestion = self.models.congestion([len(vehicles), speed, queue]) if self.models and self.models.ready else 'Untrained'
        return {'road_restrictions':[{'edge_id':edge_id,'speed_limit_mps':3.} for edge_id in sorted(self.road_restrictions)],'coordination':self.coordinator.plan,'coordination_events':self.coordinator.trace[-30:],'rl':self.rl.status(), 'enabled': self.enabled, 'seed': self.seed, 'vehicles': vehicles, 'signals': signals, 'sensors': sensors, 'ambulances': ambulances, 'events': self.events[-12:], 'history': self.history[-90:], 'metrics': {'time': self.time, 'vehicles': len(vehicles), 'speed': speed*3.6, 'queue': queue, 'arrived': self.arrived, 'normal_wait': self.wait_integral, 'mean_queue': self.queue_integral/max(1,self.steps), 'ambulance_time': sum(completed)/len(completed) if completed else None, 'active': sum(a['arrival'] is None for a in ambulances), 'corridors': sum(s['priority'] for s in signals), 'congestion': congestion, 'collisions': self.collisions}}

    def close(self):
        try:
            self.rl.save()
            self.c.close()
        finally: shutil.rmtree(self.folder, ignore_errors=True)
