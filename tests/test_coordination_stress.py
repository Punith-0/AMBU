from engine.network import prepare
from engine.simulation import Simulation

def test_conflicting_ambulances_restore_without_collision():
    sim=Simulation(prepare(),707,1.6,True)
    try:
        sim.step(120)
        ids=[sim.dispatch('A0A1','E3E4',urgency=3),sim.dispatch('E4E3','A1A0',urgency=2)]
        saw_reservations=False
        while sim.time<480:
            sim.step(10);saw_reservations|=bool(sim.coordinator.reservations)
        assert saw_reservations
        assert all(sim.ambulances[v]['arrival'] is not None for v in ids)
        assert sim.collisions==0
        assert not sim.owned
    finally:sim.close()
