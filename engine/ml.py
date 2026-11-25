"""Models trained only on measured simulation episodes, split by seed."""
from .network import ROOT
import hashlib
import joblib, numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, FunctionTransformer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score, balanced_accuracy_score, f1_score, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold

def eta_features(values):
    x=np.asarray(values,dtype=float)
    distance,count,speed,queue,edges,density=x.T
    # Derived only from inputs available at prediction time.
    return np.column_stack([x,distance/np.maximum(speed,2),queue/np.maximum(edges,1),count/np.maximum(edges,1),distance*density,queue*density])

class Models:
    def __init__(self):
        self.ready = False
        path = ROOT/'results/models.joblib'
        if path.exists():
            saved=joblib.load(path)
            if saved.get('network_sha256') == self.network_hash():
                self.__dict__.update(saved)
                self.forest.set_params(n_jobs=1)
                self.ready = True

    @staticmethod
    def network_hash():
        path=ROOT/'sumo/nightwatch.net.xml'
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

    def predict(self, x):
        return {'linear': max(0,float(self.linear.predict([x])[0])), 'forest': max(0,float(self.forest.predict([x])[0]))}

    def priority(self, x): return float(self.logistic.predict_proba([x])[0,1])

    def congestion(self, x): return self.labels[int(self.cluster.predict([x])[0])]

    def train(self, samples, decisions, traffic):
        train = [r for r in samples if r['seed']%5 != 0]
        test = [r for r in samples if r['seed']%5 == 0]
        x,y = [r['x'] for r in train], [r['y'] for r in train]
        linear_search=GridSearchCV(make_pipeline(FunctionTransformer(eta_features,validate=False),StandardScaler(),LinearRegression()),{'functiontransformer__func':[None,eta_features]},cv=GroupKFold(n_splits=5),scoring='neg_mean_absolute_error',n_jobs=2)
        linear_search.fit(x,y,groups=[r['seed'] for r in train])
        self.linear=linear_search.best_estimator_
        cv=GroupKFold(n_splits=5)
        forest_search=GridSearchCV(RandomForestRegressor(n_estimators=150,random_state=42,n_jobs=1),{'max_depth':[6,12,None],'min_samples_leaf':[1,3,6]},cv=cv,scoring='neg_mean_absolute_error',n_jobs=2)
        forest_search.fit(x,y,groups=[r['seed'] for r in train])
        self.forest=forest_search.best_estimator_

        dtrain = [r for r in decisions if r['seed']%5 != 0]
        dtest = [r for r in decisions if r['seed']%5 == 0]
        if len(set(r['y'] for r in dtrain)) != 2: raise ValueError('Priority training needs both measured outcome classes; collect more varied episodes.')
        logistic_search=GridSearchCV(make_pipeline(StandardScaler(),LogisticRegression(max_iter=3000,random_state=42)),{'logisticregression__C':[.001,.01,.1,1,10],'logisticregression__class_weight':[None,'balanced']},cv=cv,scoring='balanced_accuracy',n_jobs=2)
        logistic_search.fit([r['x'] for r in dtrain],[r['y'] for r in dtrain],groups=[r['seed'] for r in dtrain])
        self.logistic=logistic_search.best_estimator_

        self.cluster = make_pipeline(StandardScaler(), KMeans(n_clusters=3, n_init=10, random_state=42)).fit(traffic)
        centers = self.cluster[0].inverse_transform(self.cluster[1].cluster_centers_)
        order = np.argsort(centers[:,2] + centers[:,0]*.1 - centers[:,1])
        self.labels = {int(k): label for k,label in zip(order,['Low','Medium','High'])}
        xt,yt = [r['x'] for r in test], [r['y'] for r in test]
        metrics = {name: {'mae_seconds': mean_absolute_error(yt,model.predict(xt)), 'rmse_seconds': float(np.sqrt(mean_squared_error(yt,model.predict(xt))))} for name,model in [('linear',self.linear),('forest',self.forest)]}
        metrics.update(training_samples=len(train), test_samples=len(test), training_episodes=len(dtrain), test_episodes=len(dtest), logistic_accuracy=accuracy_score([r['y'] for r in dtest], self.logistic.predict([r['x'] for r in dtest])), priority_positive_labels=sum(r['y'] for r in decisions), priority_total_labels=len(decisions), split='Whole random seeds: multiples of 5 held out', priority_label='1 if ambulance seconds saved > 0.02 * additional total non-emergency waiting vehicle-seconds + 3 seconds. Paired runs; journey-level admission, not a physical signal command.')
        target=[r['y'] for r in dtest];pred=self.logistic.predict([r['x'] for r in dtest])
        metrics['logistic_confusion']={'true_negative':int(sum(t==0 and p==0 for t,p in zip(target,pred))),'false_positive':int(sum(t==0 and p==1 for t,p in zip(target,pred))),'false_negative':int(sum(t==1 and p==0 for t,p in zip(target,pred))),'true_positive':int(sum(t==1 and p==1 for t,p in zip(target,pred)))}
        novel=[r for r in dtest if r['seed']>140]
        metrics['novel_route_priority_test']={'episodes':len(novel),'accuracy':float(accuracy_score([r['y'] for r in novel],self.logistic.predict([r['x'] for r in novel]))) if novel else None,'positive_labels':sum(r['y'] for r in novel)}
        metrics.update(logistic_balanced_accuracy=balanced_accuracy_score(target,pred),logistic_f1=f1_score(target,pred,zero_division=0),majority_baseline=max(target.count(0),target.count(1))/len(target),tuning={'forest':forest_search.best_params_,'logistic':logistic_search.best_params_,'method':'Five-fold grouped CV on training seeds only'})
        for name,model in [('linear',self.linear),('forest',self.forest)]:metrics[name]['r2']=r2_score(yt,model.predict(xt))
        baseline=np.asarray(xt)[:,0]/np.maximum(np.asarray(xt)[:,2],2)
        metrics['distance_speed_baseline']={'mae_seconds':mean_absolute_error(yt,baseline)}
        for name,model in [('linear',self.linear),('forest',self.forest)]:
            errors=np.abs(model.predict(xt)-np.asarray(yt))
            metrics[name].update(within_10_seconds=float(np.mean(errors<=10)),within_20_percent=float(np.mean(errors<=.2*np.maximum(np.asarray(yt),1))))
        metrics['linear_features']='derived travel time and traffic interactions' if self.linear[0].func else 'original six inputs'
        self.forest.set_params(n_jobs=1)
        self.network_sha256=self.network_hash()
        self.ready = True
        joblib.dump(self.__dict__, ROOT/'results/models.joblib')
        return metrics
