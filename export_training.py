"""Export measured training samples and provenance without fabricated rows."""
import csv, json, zipfile, shutil
from pathlib import Path
from engine.network import ROOT

FEATURES=['remaining_route_length_m','route_vehicle_count','route_mean_speed_mps','route_halting_count','remaining_edge_count','demand_vehicles_per_second']

def write(name, rows):
    if not rows: return
    with (ROOT/'datasets'/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)

def export():
    dest=ROOT/'datasets';dest.mkdir(exist_ok=True)
    data=json.loads((ROOT/'results/training-data.json').read_text())
    eta=[]
    for i,r in enumerate(data['samples']):
        eta.append({'sample_id':i+1,'seed':r['seed'],'split':'test' if r['seed']%5==0 else 'train',**dict(zip(FEATURES,r['x'])),'actual_remaining_travel_time_s':r['y']})
    priority=[]
    for r in data['decisions']:
        priority.append({'seed':r['seed'],'split':'test' if r['seed']%5==0 else 'train',**dict(zip(FEATURES,r['x'])),'ambulance_time_saved_s':r['benefit'],'additional_normal_wait_vehicle_s':r['cost'],'priority_beneficial_label':r['y']})
    with (ROOT/'results/paired-training-runs.csv').open() as f:runs=list(csv.DictReader(f))
    provenance=[(int(r['seed']),r['mode'],60+5*(i+1)) for r in runs for i in range(round((float(r['end_time'])-60)/5))]
    if len(provenance)!=len(data['traffic']):raise ValueError('Traffic provenance count does not match measured samples')
    traffic=[{'sample_id':i+1,'seed':seed,'mode':mode,'simulation_time_s':t,'usage':'unsupervised_fit','vehicle_count':x[0],'mean_speed_mps':x[1],'detector_halting_count':x[2]} for i,(x,(seed,mode,t)) in enumerate(zip(data['traffic'],provenance))]
    write('eta_training.csv',eta);write('priority_training.csv',priority);write('congestion_training.csv',traffic);write('paired_experiments.csv',runs)
    evaluation=ROOT/'results/final-policy-evaluation.csv'
    if evaluation.exists():shutil.copy2(evaluation,dest/'final_policy_evaluation.csv')
    readme='''# AMBU measured training data

All numeric observations originate from SUMO runs in the included city network. No real-world patient, vehicle or location data is included.

- eta_training.csv: ordinary-operation journey snapshots. Target = actual seconds remaining until arrival. Linear Regression and Random Forest use the same six features. Whole random seeds divisible by five are held out. Route length includes the whole current edge; it is not GPS-adjusted remaining distance. Correlated snapshots stay in their seed group.
- priority_training.csv: one dispatch-time feature vector and measured counterfactual label per paired episode. Label is 1 when ambulance seconds saved exceed 3 + 0.02 * additional total normal waiting vehicle-seconds. This is an explicit research tradeoff, not a real-world validated safety policy. Baseline and priority runs use the same seed, traffic, dispatch and end horizon. Priority training runs use rule-driven priority, to collect both outcomes before fitting the classifier.
- congestion_training.csv: network snapshots every five simulation seconds after a 60-second warm-up. All rows fit the unsupervised K-Means model; there is no supervised accuracy claim or held-out classification label. Units are m/s and vehicle counts. Provenance is reconstructed from the recorded ordered experiment horizons and checked against sample count.
- final_policy_evaluation.csv: independent seeds 101-105, fixed 400-second horizons, fitted Logistic Regression gated standard AMBU versus baseline. This is a separate evaluation, not an RL comparison.
- paired_experiments.csv: raw baseline/priority outcomes, including total normal waiting vehicle-seconds, mean summed detector queue, throughput and collisions. These training-policy results are NOT the evaluation of the final Logistic Regression gated policy.

Seeds 1-42 use seven route families on the square 36-junction road network (sumo/nightwatch.net.xml), with identical 480-second paired horizons. Short trips with no priority benefit provide negative labels. This small synthetic training set supports the demonstrator, not citywide generalization.
'''
    (dest/'DATA_DICTIONARY.md').write_text(readme,encoding='utf-8')
    counts={'eta_samples':len(eta),'priority_episodes':len(priority),'congestion_samples':len(traffic),'paired_runs':len(runs)}
    (dest/'counts.json').write_text(json.dumps(counts,indent=2));print(json.dumps(counts))
    with zipfile.ZipFile(ROOT.parent/'AMBU-training-data.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dest.iterdir()):z.write(p,p.name)


if __name__=='__main__':export()
