"""Run paired episodes, collect actual outcomes, train and evaluate models."""
import json, csv, argparse, random
from engine.network import prepare, ROOT
from engine.simulation import Simulation
from engine.ml import Models

def run(seeds, append=False):
    net = prepare()
    samples, decisions, traffic, rows = [], [], [], []
    if append:
        previous=json.loads((ROOT/'results/training-data.json').read_text())
        existing={r['seed'] for r in previous['decisions']}
        seeds=[seed for seed in seeds if seed not in existing]
        samples,decisions,traffic=previous['samples'],previous['decisions'],previous['traffic']
        with (ROOT/'results/paired-training-runs.csv').open() as f: rows=list(csv.DictReader(f))
    trips = [('A0A1','E3E4'),('A0B0','D4E4'),('E0E1','A3A4'),('A2B2','D2E2'),('B1B2','B1B2'),('C2D2','D2E2'),('C1C2','C1C2')]
    for seed in seeds:
        density = [.4,.8,1.3,1.8][seed%4]
        pair = []
        for enabled in [False,True]:
            sim = Simulation(net,seed,density,enabled)
            try:
                sim.step(120)
                if seed<=140:
                    start,end=trips[seed%len(trips)]
                else:
                    rng=random.Random(seed)
                    edges=[e for e in net.getEdges() if e.getFunction()!='internal']
                    start_edge=rng.choice(edges)
                    candidates=[]
                    for target in edges:
                        if target==start_edge:continue
                        path,cost=net.getShortestPath(start_edge,target)
                        if path:candidates.append((target.getID(),cost))
                    candidates.sort(key=lambda item:item[1])
                    segment=len(candidates)//3
                    band=candidates[:segment] if seed%3==0 else candidates[segment:2*segment] if seed%3==1 else candidates[2*segment:]
                    start,end=start_edge.getID(),rng.choice(band or candidates)[0]
                vid = sim.dispatch(start,end)
                while sim.time < 480:
                    snap = sim.step(10)
                    m = snap['metrics']
                    traffic.append([m['vehicles'],m['speed']/3.6,m['queue']])
                    # Fixed 480-second horizon for both members of every pair.
                a = sim.ambulances[vid]
                if a['arrival'] is None: raise RuntimeError(f'Incomplete ambulance journey at seed {seed}')
                total = a['arrival']-a['requested']
                # Prediction model concerns ordinary operation; avoids omitting mode from features.
                if not enabled:
                    samples.append({'seed':seed,'x':a['features'],'y':total})
                    samples.extend({'seed':seed,'x':x,'y':a['arrival']-t} for t,x in a['samples'] if t<a['arrival'])
                row = {'seed':seed,'density':density,'mode':'AMBU' if enabled else 'baseline','ambulance_seconds':total,'ambulance_wait_seconds':a['wait'],'normal_wait_vehicle_seconds':sim.wait_integral,'mean_detector_queue':sim.queue_integral/sim.steps,'throughput':sim.arrived,'end_time':sim.time,'collisions':sim.collisions}
                pair.append((a['features'],row))
                rows.append(row)
            finally: sim.close()
        x,off = pair[0]; _,on = pair[1]
        benefit = off['ambulance_seconds']-on['ambulance_seconds']
        cost = max(0,on['normal_wait_vehicle_seconds']-off['normal_wait_vehicle_seconds'])
        decisions.append({'seed':seed,'x':x,'y':int(benefit>3+.02*cost),'benefit':benefit,'cost':cost})
        print(f'Seed {seed}: baseline {off["ambulance_seconds"]:.1f}s; priority {on["ambulance_seconds"]:.1f}s; label {decisions[-1]["y"]}',flush=True)
    (ROOT/'results/training-data.json').write_text(json.dumps({'samples':samples,'decisions':decisions,'traffic':traffic}),encoding='utf-8')
    with (ROOT/'results/paired-training-runs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    metrics = Models().train(samples,decisions,traffic)
    (ROOT/'results/model-metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2),flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--seeds',type=int,default=42);p.add_argument('--start',type=int,default=1);p.add_argument('--append',action='store_true');args=p.parse_args()
    run(range(args.start,args.seeds+1),args.append)
