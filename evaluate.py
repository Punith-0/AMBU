"""Independent evaluation of the final trained, gated AMBU policy."""
import csv,json,statistics
from engine.network import prepare,ROOT
from engine.simulation import Simulation
from engine.ml import Models

def main():
    net=prepare();models=Models();assert models.ready
    rows=[]
    for seed in [101,102,103,104,105]:
        for mode in [False,True]:
            sim=Simulation(net,seed,.6+(seed%3)*.4,mode,models)
            try:
                sim.step(120);vid=sim.dispatch()
                while sim.time<400:sim.step(10)
                a=sim.ambulances[vid]
                assert a['arrival'] is not None, f'Journey incomplete at seed {seed}'
                rows.append({'seed':seed,'mode':'AMBU' if mode else 'baseline','ambulance_seconds':a['arrival']-a['requested'],'normal_wait_vehicle_seconds':sim.wait_integral,'throughput':sim.arrived,'mean_queue':sim.queue_integral/sim.steps,'signal_wait_seconds':a['wait'],'priority_probability':a['probability'],'collisions':sim.collisions,'horizon':sim.time})
                print(rows[-1],flush=True)
            finally:sim.close()
    with (ROOT/'results/final-policy-evaluation.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    summary={}
    for mode in ['baseline','AMBU']:
        values=[r['ambulance_seconds'] for r in rows if r['mode']==mode]
        summary[mode]={'mean_seconds':statistics.mean(values),'std_seconds':statistics.stdev(values),'n':len(values)}
    (ROOT/'results/final-policy-summary.json').write_text(json.dumps(summary,indent=2))
    print(summary)
if __name__=='__main__':main()
