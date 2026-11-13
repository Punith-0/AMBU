import json
import pytest
from engine.network import prepare, ROOT
from engine.simulation import Simulation
from engine.ml import Models

@pytest.fixture(scope='module')
def net():return prepare()

def test_trained_models_and_seed_separation():
    model=Models();assert model.ready
    data=json.loads((ROOT/'results/training-data.json').read_text())
    train={r['seed'] for r in data['samples'] if r['seed']%5!=0}
    test={r['seed'] for r in data['samples'] if r['seed']%5==0}
    assert not train&test and train and test
    assert set(r['y'] for r in data['decisions'])=={0,1}
    result=model.predict(data['samples'][0]['x'])
    assert all(0<=v<10000 for v in result.values())
    assert 0<=model.priority(data['samples'][0]['x'])<=1

def test_routine_and_unregistered_do_not_request_priority(net):
    sim=Simulation(net,101,.4,True)
    try:
        sim.dispatch(active=False)
        sim.dispatch('E0E1','A3A4',registered=False)
        sim.step(100)
        assert not sim.owned and not sim.transitions
        assert len(sim.last['sensors'])==len(sim.e2) and len(sim.e2)>0
        assert sim.last['vehicles']
    finally:sim.close()

def test_low_model_score_does_not_block_verified_emergency(net):
    sim=Simulation(net,104,.4,True)
    try:
        vid=sim.dispatch()
        sim.ambulances[vid]['probability']=0.01
        saw_priority=False
        while sim.time<300 and sim.ambulances[vid]['arrival'] is None:
            sim.step()
            saw_priority |= any(r['vehicle']==vid for r in sim.coordinator.reservations.values())
        assert saw_priority
        assert sim.ambulances[vid]['arrival'] is not None
        assert sim.collisions==0
    finally:sim.close()

def test_multi_ambulance_clearance_and_restore(net):
    sim=Simulation(net,102,.6,True)
    try:
        sim.step(60)
        a=sim.dispatch(urgency=3)
        b=sim.dispatch('E0E1','A3A4',urgency=2)
        saw_yellow=saw_red=saw_priority=False
        for i in range(180):
            sim.step()
            for tid,transition in sim.transitions.items():
                state=sim.c.trafficlight.getRedYellowGreenState(tid)
                if transition['stage']=='yellow':
                    saw_yellow=True;assert not any(ch in 'gG' for ch in state)
                if transition['stage']=='all-red':
                    saw_red=True;assert set(state)=={'r'}
            for tid in sim.owned-set(sim.transitions):
                state=sim.c.trafficlight.getRedYellowGreenState(tid)
                assert state in [p.state for p in sim.signals[tid]['phases']]
                saw_priority=True
        assert saw_yellow and saw_red and saw_priority
        sim.enabled=False;sim.step(30)
        assert not sim.owned and not sim.transitions
        while sim.time<360 and any(sim.ambulances[v]['arrival'] is None for v in [a,b]):sim.step(10)
        assert all(sim.ambulances[v]['arrival'] is not None for v in [a,b])
        assert sim.collisions==0
    finally:sim.close()

def test_reproducible_demand(net):
    snapshots=[]
    for _ in range(2):
        sim=Simulation(net,103,.4,False)
        try:
            sim.step(100);snapshots.append([(v['id'],round(v['x'],3),round(v['y'],3)) for v in sim.last['vehicles']])
        finally:sim.close()
    assert snapshots[0]==snapshots[1]

def test_models_reject_a_different_road_network(tmp_path,monkeypatch):
    import engine.ml as ml
    import joblib
    (tmp_path/'results').mkdir();(tmp_path/'sumo').mkdir()
    (tmp_path/'sumo/nightwatch.net.xml').write_text('<net changed="true"/>')
    joblib.dump({'ready':True,'network_sha256':'old-network'},tmp_path/'results/models.joblib')
    monkeypatch.setattr(ml,'ROOT',tmp_path)
    assert not ml.Models().ready
