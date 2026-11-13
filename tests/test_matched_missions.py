import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from engine.network import prepare
from engine.simulation import Simulation
from engine.ml import Models


def test_matched_station_missions_are_independent_and_complete(monkeypatch):
    import app
    net=prepare()
    models=Models()
    assert models.ready
    worlds=[]
    try:
        for enabled in (True,False):
            worlds.append(Simulation(net,610,.6,enabled,models))
        assert worlds[0].label!=worlds[1].label
        assert worlds[0].c is not worlds[1].c
        for sim in worlds:sim.step(120)
        assert {sim.time for sim in worlds}=={60.}
        ids=[sim.dispatch('D3E3',mission=True,scenario='crash',urgency=3) for sim in worlds]
        assert ids==['AMBU-001','AMBU-001']
        monkeypatch.setattr(app,'worlds',worlds)
        app.choose_hospital(ids[0],app.HospitalChoice(hospital_id='sanjeevani'))
        journeys=[sim.ambulances[ids[0]] for sim in worlds]
        assert journeys[0] is not journeys[1]
        assert all(a['selected_hospital']=='sanjeevani' for a in journeys)
        observed=[set(),set()]
        while worlds[0].time<600 and any(a['arrival'] is None for a in journeys):
            for i,sim in enumerate(worlds):
                sim.step(10)
                a=journeys[i]
                observed[i].add(a['stage'])
                if a['stage']=='loading':
                    # Remove only the wall-clock animation delay; traffic and
                    # pickup timing still come from independent SUMO runs.
                    a['loading_until']=time.monotonic()-1
        assert worlds[0].time==worlds[1].time
        for sim,a,stages in zip(worlds,journeys,observed):
            assert {'responding','loading','transport','complete'}<=stages
            assert a['stage']=='complete' and a['arrival'] is not None
            assert a['requested']<a['pickup_at']<a['transport_started']<a['arrival']
            assert a['hospital_id']=='sanjeevani' and a['destination']=='E3E4'
            assert a['route'][-1]=='E3E4'
            assert sim.last['ambulances'][0]['arrival']==a['arrival']
            assert sim.collisions==0
        elapsed=[a['arrival']-a['requested'] for a in journeys]
        assert elapsed[0]!=elapsed[1]
        assert journeys[0]['pickup_at']!=journeys[1]['pickup_at']
        print(f'Matched mission: AMBU {elapsed[0]}s, baseline {elapsed[1]}s; both completed without collisions.')
    finally:
        for sim in worlds:sim.close()


def test_hospital_choice_preflight_prevents_partial_matched_mutation(monkeypatch):
    import app
    calls=[]
    first=SimpleNamespace(ambulances={'AMBU-001':{'stage':'loading','selected_hospital':'aarogya'}},select_hospital=lambda *args:calls.append(args))
    second=SimpleNamespace(ambulances={'AMBU-001':{'stage':'transport','selected_hospital':'aarogya'}},select_hospital=lambda *args:calls.append(args))
    monkeypatch.setattr(app,'worlds',[first,second])
    with pytest.raises(HTTPException) as exc:
        app.choose_hospital('AMBU-001',app.HospitalChoice(hospital_id='sanjeevani'))
    assert exc.value.status_code==400
    assert calls==[]
    assert first.ambulances['AMBU-001']['selected_hospital']=='aarogya'
