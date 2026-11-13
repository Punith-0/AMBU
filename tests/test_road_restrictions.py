import pytest
from engine.network import prepare
from engine.simulation import Simulation


def test_road_restriction_reversible_and_reset():
    net=prepare()
    edge_id='B1B2'
    original={lane.getID():lane.getSpeed() for lane in net.getEdge(edge_id).getLanes()}
    sim=Simulation(net,501,.2,True)
    try:
        before=sim.last
        sim.restrict_road(edge_id,True)
        assert sim.last is not before
        assert sim.last['road_restrictions']==[{'edge_id':edge_id,'speed_limit_mps':3.}]
        assert all(sim.c.lane.getMaxSpeed(lane_id)==3 for lane_id in original)
        # Repeated activation must not replace the saved original limits with 3.
        sim.restrict_road(edge_id,True)
        sim.step(10)
        assert sim.collisions==0
        sim.restrict_road(edge_id,False)
        assert sim.last['road_restrictions']==[]
        assert all(sim.c.lane.getMaxSpeed(lane_id)==speed for lane_id,speed in original.items())
        with pytest.raises(ValueError):sim.restrict_road('missing-road',True)
        internal=next(edge.getID() for edge in net.getEdges() if edge.getFunction()=='internal')
        with pytest.raises(ValueError):sim.restrict_road(internal,True)
        sim.restrict_road(edge_id,True)
    finally:sim.close()
    restarted=Simulation(net,501,.2,True)
    try:
        assert restarted.last['road_restrictions']==[]
        assert all(restarted.c.lane.getMaxSpeed(lane_id)==speed for lane_id,speed in original.items())
    finally:restarted.close()


def test_road_api_rejects_comparison(monkeypatch):
    import app
    from fastapi import HTTPException
    monkeypatch.setattr(app,'worlds',[object(),object()])
    with pytest.raises(HTTPException) as exc:
        app.restrict_road('B1B2',app.RoadRestriction(restricted=True))
    assert exc.value.status_code==400
