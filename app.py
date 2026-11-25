import asyncio, json, csv, io, threading, logging, time, subprocess, sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from engine.network import prepare, geometry, ROOT
from engine.simulation import Simulation
from engine.ml import Models
from engine.missions import HOSPITALS,STATION,PICKUPS

logging.basicConfig(level=logging.INFO)
net = prepare()
lock = threading.RLock()
worlds = []
running = True
speed = 1
error = None
models = Models()

def reset(seed=42,density=1.,comparison=False):
    global worlds,error
    with lock:
        for w in worlds: w.close()
        worlds=[]
        worlds=[Simulation(net,seed,density,True,models)]
        if comparison: worlds.append(Simulation(net,seed,density,False,models))
        error=None

def tick():
    global running,error
    with lock:
        for w in worlds:
            w.step(speed)
            if w.collisions:
                running=False;error="SUMO detected a collision. Simulation paused for inspection."

async def loop():
    global error,running
    while True:
        started=time.monotonic()
        if running and worlds:
            try: await asyncio.to_thread(tick)
            except Exception as exc:
                logging.exception('Simulation stopped');error=str(exc);running=False
        await asyncio.sleep(max(.01,.5-(time.monotonic()-started)))

@asynccontextmanager
async def lifespan(app):
    reset()
    task=asyncio.create_task(loop())
    yield
    task.cancel()
    with lock:
        for w in worlds:w.close()

app=FastAPI(title='AMBU City Lab',lifespan=lifespan)
app.mount('/assets',StaticFiles(directory=ROOT/'dashboard'),name='assets')

@app.get('/')
def home():return FileResponse(ROOT/'dashboard/index.html')

@app.get('/healthz')
def health():
    return {'status':'ok','models_ready':models.ready}

@app.get('/api/geography')
def geography():return {'hospitals':HOSPITALS,'station':STATION,'pickups':PICKUPS}

@app.get('/api/hospital-distances/{pickup}')
def hospital_distances(pickup:str):
    if pickup not in net._id2edge:raise HTTPException(400,'Unknown pickup road')
    result=[]
    for h in HOSPITALS:
        path,distance=net.getShortestPath(net.getEdge(pickup),net.getEdge(h['edge']))
        result.append({**h,'distance_m':round(distance,1) if path else None})
    return {'pickup':pickup,'hospitals':result,'basis':'Shortest directed road route length; includes pickup and destination roads.'}

@app.get('/api/network')
def network():return geometry(net)

@app.get('/api/state')
def state():
    with lock:return {'worlds':[w.last for w in worlds],'running':running,'speed':speed,'error':error,'models':models.ready}

@app.post('/api/insights')
def insights():
    from engine.insights import generate
    with lock:
        snapshot={'worlds':[{'enabled':w.last['enabled'],'seed':w.last['seed'],'metrics':dict(w.last['metrics']),'ambulances':[dict(a) for a in w.last['ambulances']]} for w in worlds]}
    return generate(snapshot)

training_status={'state':'idle','completed':0,'total':0,'message':'Ready'}
training_guard=threading.Lock()

def training_worker(start,count):
    global models
    try:
        command=[sys.executable,'-X','utf8',str(ROOT/'train.py'),'--start',str(start),'--seeds',str(start+count-1),'--append']
        with (ROOT/'results/training-job.log').open('w',encoding='utf-8') as log, subprocess.Popen(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1) as process:
            for line in process.stdout:
                log.write(line);log.flush()
                if line.startswith('Seed '):
                    with training_guard:
                        training_status['completed']+=1
                        training_status['message']=line.strip()[:200]
            if process.wait():raise RuntimeError('Training process failed; inspect results/training-job.log')
        subprocess.run([sys.executable,'-X','utf8',str(ROOT/'export_training.py')],cwd=ROOT,check=True,capture_output=True,text=True)
        refreshed=Models()
        if not refreshed.ready:raise RuntimeError('New model artifact was not loadable')
        with lock:
            models=refreshed
            for world in worlds:world.models=refreshed
        with training_guard:training_status.update(state='complete',message='Models updated and CSV datasets exported')
    except Exception as exc:
        logging.exception('Training failed')
        with training_guard:training_status.update(state='failed',message=str(exc)[:200])

@app.get('/api/training/status')
def get_training_status():
    with training_guard:return dict(training_status)

class TrainingRequest(BaseModel):
    episodes:int=Field(40,ge=10,le=100)

@app.post('/api/training/start')
def start_training(req:TrainingRequest):
    with training_guard:
        if training_status['state']=='running':raise HTTPException(409,'Training already running')
        data=ROOT/'results/training-data.json'
        existing=json.loads(data.read_text())['decisions'] if data.exists() else []
        start=max((r['seed'] for r in existing),default=0)+1
        training_status.update(state='running',completed=0,total=req.episodes,message=f'Starting at seed {start}')
    threading.Thread(target=training_worker,args=(start,req.episodes),daemon=True).start()
    return get_training_status()

@app.get('/api/models')
def model_info():
    path=ROOT/'results/model-metrics.json'
    return json.loads(path.read_text()) if path.exists() else {'status':'Not trained. Run python train.py.'}

@app.get('/api/datasets/{name}')
def dataset(name:str):
    if name not in {'eta_training.csv','priority_training.csv','congestion_training.csv','paired_experiments.csv','final_policy_evaluation.csv','DATA_DICTIONARY.md'}:
        raise HTTPException(404,'Unknown dataset')
    path=ROOT/'datasets'/name
    if not path.exists():raise HTTPException(404,'Dataset not exported yet')
    return FileResponse(path,filename=name)

class Control(BaseModel):
    action:str
    seed:int=Field(42,ge=0,le=999999)
    density:float=Field(1,ge=.2,le=2)
    comparison:bool=False
    value:bool=True
    speed:int=Field(1,ge=1,le=8)
    policy:str='off'

@app.post('/api/control')
def control(req:Control):
    global running,speed
    with lock:
        if req.action=='reset':
            reset(req.seed,req.density,req.comparison);running=True
            worlds[0].rl.enabled=req.policy=='frozen'
            worlds[0].rl.learning=False
        elif req.action=='running':running=req.value
        elif req.action=='enabled':
            if len(worlds)>1:raise HTTPException(400,'AMBU priority is fixed ON / OFF during matched comparisons. Start a single run first.')
            worlds[0].enabled=req.value
            worlds[0].log('AMBU '+('enabled' if req.value else 'disabled; restoring normal signals safely'))
        elif req.action=='speed':speed=req.speed
        elif req.action=='rl':
            if len(worlds)>1:raise HTTPException(400,'Learning is frozen during matched comparisons. Start a single run first.')
            if req.policy not in ('off','learn','frozen','reset'):raise HTTPException(400,'Unknown RL mode')
            agent=worlds[0].rl;agent.save();agent.pending.clear();agent.next_decision.clear()
            agent.enabled=req.policy in ('learn','frozen');agent.learning=req.policy=='learn'
            if req.policy=='reset':
                agent.q.clear();agent.updates=0;agent.reward_total=0;agent.learning=True;agent.save();agent.learning=False
        else:raise HTTPException(400,'Unknown control')
    return {'ok':True}

class Dispatch(BaseModel):
    start:str='A0A1'
    end:str='E3E4'
    urgency:int=Field(2,ge=1,le=3)
    active:bool=True
    registered:bool=True
    scenario:str=Field('critical',pattern='^(critical|home|crash|transfer)$')
    hospital_name:str=Field('Sanjeevani Hospital',max_length=100)
    mission:bool=False

SCENE_NAMES={'driver','home','crash','critical','transfer','handover'}

@app.get('/api/scene-videos')
def scene_videos():
    folder=ROOT/'dashboard/videos'
    return {name:'/assets/videos/'+name+'.webm' for name in SCENE_NAMES if (folder/(name+'.webm')).exists()}

@app.post('/api/scene-videos/{name}')
async def save_scene_video(name:str,request:Request):
    if name not in SCENE_NAMES:raise HTTPException(400,'Unknown scene')
    body=await request.body()
    if not 1000<len(body)<25_000_000 or not body.startswith(bytes.fromhex('1a45dfa3')):raise HTTPException(400,'Expected a WebM scene under 25 MB')
    folder=ROOT/'dashboard/videos';folder.mkdir(exist_ok=True)
    (folder/(name+'.webm')).write_bytes(body)
    return {'url':'/assets/videos/'+name+'.webm','bytes':len(body)}

@app.post('/api/dispatch')
def dispatch(req:Dispatch):
    with lock:
        if req.start not in net._id2edge or req.end not in net._id2edge:raise HTTPException(400,'Unknown road')
        if any(sum(a['arrival'] is None for a in w.ambulances.values())>=6 for w in worlds):raise HTTPException(400,'Maximum 6 concurrent ambulances')
        try:ids=[w.dispatch(**req.model_dump()) for w in worlds]
        except ValueError as exc:raise HTTPException(400,str(exc))
    return {'ids':ids}

class HospitalChoice(BaseModel):
    hospital_id:str

@app.post('/api/hospital/{vid}')
def choose_hospital(vid:str,req:HospitalChoice):
    with lock:
        if not any(h['id']==req.hospital_id for h in HOSPITALS):
            raise HTTPException(400,'Unknown hospital')
        # Preflight every matched world before mutating any journey. Different
        # arrival times can leave one world in transport while another is loading.
        for w in worlds:
            a=w.ambulances.get(vid)
            if not a:raise HTTPException(400,'Unknown ambulance')
            if a.get('stage') not in ('responding','awaiting_hospital','loading'):
                raise HTTPException(400,'Hospital selection is closed for this journey')
        try:
            for w in worlds:w.select_hospital(vid,req.hospital_id)
        except ValueError as exc:raise HTTPException(400,str(exc))
    return {'ok':True}

class RoadRestriction(BaseModel):
    restricted:bool

@app.post('/api/road/{edge_id}')
def restrict_road(edge_id:str, req:RoadRestriction):
    with lock:
        if len(worlds)>1:raise HTTPException(400,'Road restrictions are disabled in matched experiments')
        try:worlds[0].restrict_road(edge_id,req.restricted)
        except ValueError as exc:raise HTTPException(400,str(exc))
    return {'ok':True,'edge_id':edge_id,'restricted':req.restricted,'speed_limit_mps':3. if req.restricted else None}

class ManualSignal(BaseModel):
    phase:str

@app.post('/api/signals/reset')
def reset_signals():
    with lock:
        for w in worlds:
            overridden=set(w.manual)|set(w.manual_owned)
            w.manual.clear()
            for tid in overridden:
                if tid not in w.coordinator.reservations and tid in w.transitions:
                    w.transitions[tid]['target']=None
            w.log('All manual signal overrides cleared; automatic control resumes through clearance')
    return {'ok':True,'message':'All manual overrides cleared. Active emergency corridors remain coordinated.'}

@app.post('/api/signal/{tid}')
def manual_signal(tid:str,req:ManualSignal):
    with lock:
        if len(worlds)>1:raise HTTPException(400,'Manual signals are disabled in matched experiments')
        try:worlds[0].manual_signal(tid,req.phase)
        except ValueError as exc:raise HTTPException(409,str(exc))
    return {'ok':True}

@app.post('/api/deactivate/{vid}')
def deactivate(vid:str):
    with lock:
        try:
            for w in worlds:w.deactivate(vid)
        except ValueError as exc:raise HTTPException(404,str(exc))
    return {'ok':True}

@app.get('/api/export')
def export():
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['mode','seed','ambulance','emergency','requested_s','arrival_s','elapsed_s','waiting_s','linear_prediction_s','forest_prediction_s'])
    with lock:
        for w in worlds:
            for a in w.ambulances.values():writer.writerow(['AMBU' if w.enabled else 'baseline',w.seed,a['id'],a['active'],a['requested'],a['arrival'],a['arrival']-a['requested'] if a['arrival'] is not None else '',a['wait'],(a['prediction'] or {}).get('linear',''),(a['prediction'] or {}).get('forest','')])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=ambu-journeys.csv'})

@app.websocket('/ws')
async def ws(websocket:WebSocket):
    await websocket.accept()
    try:
        previous=None
        while True:
            payload=await asyncio.to_thread(state)
            signature=(tuple(id(w) for w in payload['worlds']),payload['running'],payload['speed'],payload['error'],payload['models'])
            if signature!=previous:
                await websocket.send_json(payload)
                previous=signature
            await asyncio.sleep(.1)
    except (WebSocketDisconnect,RuntimeError):pass

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8877)
