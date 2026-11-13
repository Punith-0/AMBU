"""Warm-start persistent RL using actual SUMO experience, not scripted targets."""
import json
from engine.network import prepare,ROOT
from engine.simulation import Simulation
from engine.ml import Models
def main():
    net=prepare();models=Models();rows=[]
    for seed in range(201,207):
        sim=Simulation(net,seed,.5+.3*(seed%4),True,models)
        sim.rl.enabled=True;sim.rl.learning=True
        try:
            for i in range(120):
                sim.step(10)
                if i==12:sim.dispatch()
            rows.append({'seed':seed,**sim.rl.status(),'collisions':sim.collisions,'time':sim.time})
            print(rows[-1],flush=True)
        finally:sim.close()
    (ROOT/'results/rl-training.json').write_text(json.dumps(rows,indent=2))
if __name__=='__main__':main()
