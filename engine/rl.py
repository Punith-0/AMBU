"""Persistent tabular Q-learning over network-approved phases and bounded holds.

Exploration is for this simulator only. The existing clearance controller owns
all physical transitions. Emergency requests override the learned scheduler.
"""
import json, random, hashlib, math
from pathlib import Path
from .network import ROOT

class SignalLearner:
    def __init__(self, seed=42, path=None, learning=False):
        self.path=Path(path or ROOT/'results/signal-policy.json')
        self.fingerprint=hashlib.sha256((ROOT/'sumo/nightwatch.net.xml').read_bytes()).hexdigest()
        self.q={};self.updates=0;self.reward_total=0.;self.learning=learning
        self.rng=random.Random(seed);self.pending={};self.next_decision={};self.enabled=False
        if self.path.exists():
            saved=json.loads(self.path.read_text())
            if saved.get('network_sha256')==self.fingerprint:
                self.q=saved.get('q',{});self.updates=saved.get('updates',0);self.reward_total=saved.get('reward_total',0.)

    @property
    def epsilon(self):return max(.03,.2/(1+self.updates/2000)) if self.learning else 0.

    def choose(self,tid,state,actions,time,cost):
        key=tid+'|'+','.join(map(str,state))
        values=self.q.get(key,[0.]*len(actions))
        if len(values)!=len(actions):values=[0.]*len(actions)
        prior=self.pending.pop(tid,None)
        if prior and self.learning:
            old,action,previous_cost,started=prior
            duration=max(.5,time-started)
            reward=-(cost-previous_cost)/duration
            old_values=self.q.setdefault(old,[0.]*len(actions))
            old_values[action]+=.12*(reward+.92*max(values)-old_values[action])
            self.updates+=1;self.reward_total+=reward
        if self.rng.random()<self.epsilon:index=self.rng.randrange(len(actions))
        else:
            best=max(values);choices=[i for i,v in enumerate(values) if abs(v-best)<1e-9]
            index=self.rng.choice(choices)
        if self.learning:
            self.q.setdefault(key,values)
            self.pending[tid]=(key,index,cost,time)
        phase,hold=actions[index];self.next_decision[tid]=time+hold+5
        if self.learning and self.updates and self.updates%100==0:self.save()
        return phase,hold

    def interrupt(self,tid):
        # Emergency override must not be credited to the previous learned action.
        self.pending.pop(tid,None);self.next_decision.pop(tid,None)

    def save(self):
        if not self.learning:return
        self.path.parent.mkdir(exist_ok=True,parents=True)
        tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'version':1,'network_sha256':self.fingerprint,'updates':self.updates,'reward_total':self.reward_total,'q':self.q}),encoding='utf-8')
        tmp.replace(self.path)

    def status(self):return {'enabled':self.enabled,'learning':self.learning,'updates':self.updates,'states':len(self.q),'epsilon':self.epsilon,'mean_reward':self.reward_total/max(1,self.updates),'algorithm':'Tabular Q-learning','persisted':self.path.exists()}
