const names={linear:'Linear Regression',forest:'Random Forest'};
let selected='forest';
try {const saved=globalThis.localStorage?.getItem('ambu.eta-model');if(Object.hasOwn(names,saved))selected=saved;} catch {}
export function getEtaModel(){return selected;}
export function setEtaModel(value){if(!Object.hasOwn(names,value))throw new Error('Unknown ETA model');selected=value;try{globalThis.localStorage?.setItem('ambu.eta-model',value);}catch{}return value;}
export function resolveEta(a,model=selected){
 const name=names[model]||names.forest;
 if(a.arrival!=null)return {seconds:0,name,source:'arrival'};
 const value=a.remaining_prediction?.[model];
 if(Number.isFinite(value)&&value>=0&&!(value<1&&a.remaining_distance>10))return {seconds:value,name,source:'model'};
 return {seconds:Number.isFinite(a.kinematic_eta)&&a.kinematic_eta>=0?a.kinematic_eta:null,name,source:'kinematic'};
}
