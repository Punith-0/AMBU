"""Refit the exact bundled observed dataset, without running new scenarios."""
import json
from engine.network import ROOT
from engine.ml import Models
data=json.loads((ROOT/'results/training-data.json').read_text())
metrics=Models().train(data['samples'],data['decisions'],data['traffic'])
(ROOT/'results/model-metrics.json').write_text(json.dumps(metrics,indent=2))
print(json.dumps(metrics,indent=2))
