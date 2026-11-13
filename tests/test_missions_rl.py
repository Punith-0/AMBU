import time, json
from engine.network import prepare
from engine.simulation import Simulation
from engine.rl import SignalLearner
from engine.missions import nearest

def test_station_pickup_timeout_transport():
    sim=Simulation(prepare(),301,.4,True)
    try:
        vid=sim.dispatch('B1B2',mission=True,scenario='home',urgency=3)
        assert sim.ambulances[vid]['station']=='Suraksha Ambulance Station'
        while sim.time<360 and sim.ambulances[vid]['stage']=='responding':sim.step(10)
        a=sim.ambulances[vid];assert a['stage']=='awaiting_hospital'
        assert a['choice_deadline']-time.monotonic()<=7
        a['choice_deadline']=time.monotonic()-1;sim.step()
        assert a['stage']=='loading' and a['hospital_id']==nearest(sim.net,a['pickup'])['id']
        a['loading_until']=time.monotonic()-1;sim.step()
        assert a['stage']=='transport'
        while sim.time<600 and a['arrival'] is None:sim.step(10)
        assert a['stage']=='complete' and sim.collisions==0
    finally:sim.close()

def test_explicit_hospital_choice_and_route_plan():
    sim=Simulation(prepare(),302,.5,True)
    try:
        vid=sim.dispatch('D3E3',mission=True,scenario='crash',urgency=3)
        sim.select_hospital(vid,'jeevan')
        planned=False
        while sim.time<360 and sim.ambulances[vid]['stage']=='responding':
            sim.step(10)
            planned|=len(sim.coordinator.plan.get(vid,[]))>=3
        a=sim.ambulances[vid];assert a['stage']=='loading' and a['hospital_id']=='jeevan'
        assert planned
        a['loading_until']=time.monotonic()-1;sim.step()
        assert a['destination']=='E1E2' and a['route'][-1]=='E1E2'
        assert sim.collisions==0
    finally:sim.close()

def test_q_learning_persists_and_freeze_does_not_mutate(tmp_path):
    prepare();path=tmp_path/'policy.json';agent=SignalLearner(path=path,learning=True)
    actions=[('Grr',10),('rGr',20)]
    agent.choose('J',[0,1],actions,0,0);agent.choose('J',[0,1],actions,15,60)
    assert agent.updates==1;agent.save()
    restored=SignalLearner(path=path,learning=False)
    assert restored.q==agent.q
    before=json.dumps(restored.q,sort_keys=True)
    for t in range(5):restored.choose('J',[0,1],actions,30+t*10,100+t)
    assert restored.updates==1 and json.dumps(restored.q,sort_keys=True)==before

def test_rl_clearance_and_disable_restoration(tmp_path):
    sim=Simulation(prepare(),303,.4,True)
    sim.rl=SignalLearner(path=tmp_path/'rl.json',learning=True);sim.rl.enabled=True
    try:
        for _ in range(240):
            sim.step()
            for tid in sim.owned-set(sim.transitions):
                assert sim.c.trafficlight.getRedYellowGreenState(tid) in [p.state for p in sim.signals[tid]['phases']]
        assert sim.rl.updates>0
        sim.rl.enabled=False;sim.step(30)
        assert not sim.owned and not sim.transitions and sim.collisions==0
    finally:sim.close()
