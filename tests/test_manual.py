import pytest
from engine.network import prepare
from engine.simulation import Simulation

def test_manual_signal_clearance_expiry_and_validation():
    sim=Simulation(prepare(),401,.3,True)
    try:
        tid=next(iter(sim.signals))
        with pytest.raises(ValueError):sim.manual_signal(tid,'-1')
        sim.manual_signal(tid,'red');sim.step()
        assert sim.transitions[tid]['stage']=='yellow'
        sim.step(6)
        assert sim.transitions[tid]['stage']=='all-red'
        sim.step(5)
        assert set(sim.c.trafficlight.getRedYellowGreenState(tid))=={'r'}
        assert tid in sim.manual
        sim.step(70)
        assert tid not in sim.manual and tid not in sim.owned
        sim.coordinator.reservations[tid]={'target':'r'}
        with pytest.raises(ValueError):sim.manual_signal(tid,'0')
    finally:sim.close()
