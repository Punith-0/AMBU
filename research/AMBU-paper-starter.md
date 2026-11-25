# AMBU research paper — evidence-first starter

Working title: Simulation-Based Ambulance Signal Priority with Grouped Evaluation of Travel-Time Prediction

## Research question
How much can coordinated emergency signal priority reduce ambulance travel time in a controlled SUMO network, and what delay does it impose on ordinary traffic? Can route and traffic features predict conventional ambulance travel time and the journey-level benefit of priority?

## System and methods
AMBU uses a 36-junction square SUMO network, TraCI vehicle and signal control, virtual E1/E2 detector readings, and Dijkstra road-distance routing via `sumolib.net.getShortestPath`. Eligible registered active ambulances request upcoming network-approved green phases. The controller enforces 3 seconds yellow and 2 seconds all-red clearance. Linear Regression and Random Forest predict conventional remaining travel time; Logistic Regression predicts a journey-level priority-benefit label but does not command a signal. Optional tabular Q-learning controls background phases under safety rules; it is not the source of the supervised model scores below.

Training uses matched AMBU ON/OFF episodes with identical seeds and a 480-second horizon. Seeds 1-140 used seven route families; seeds 141-180 added varied road pairs; seeds 181-220 sampled short, medium and long connected routes. Whole seeds divisible by five were held out. Five-fold GroupKFold tuning used only the other seeds. The priority label is 1 when ambulance time saved exceeds `3 s + 0.02 × additional ordinary-vehicle waiting seconds`. This is a study-defined tradeoff, not a real-world safety rule.

## Current measured results (2026-11-23)
- 220 paired episodes, 440 individual simulations; 2,846 ETA samples, with 2,277 training and 569 held-out samples.
- Random Forest ETA: MAE 12.38 s, RMSE 16.50 s, R² 0.932; 51.1% within 10 s. Tuned max_depth=6, min_samples_leaf=6.
- Linear Regression ETA: MAE 13.45 s, RMSE 17.44 s, R² 0.924; 44.1% within 10 s. Simple distance/speed baseline MAE 42.79 s.
- Logistic Regression: accuracy 42/44 = 95.45%, balanced accuracy 93.02%, F1 0.971; confusion TN=8, FP=1, FN=1, TP=34. Tuned C=1, class_weight=None. Majority-class baseline 79.55%.
- On the 16 held-out episodes with newer varied routes, logistic accuracy was 87.5% (14/16). Fifteen of those 16 labels were positive, so this slice remains imbalanced and small.

Earlier five-seed final-policy journey evaluation had mean ambulance times 133.6 s AMBU and 204.9 s baseline. That evaluation belongs to a separate prior policy test and must not be presented as proof that the newly retrained models or RL caused the journey reduction. Re-run an independent final-policy evaluation after any controller or model-policy change.

## Claims and limits
All measurements come from a synthetic SUMO network, not real road sensors or patient outcomes. The priority label is constructed from paired outcomes and should be evaluated under additional traffic patterns, route layouts and class balances. The new broader test set has higher ETA error than the old seven-route test, which is evidence of a harder evaluation rather than evidence that the model improved on the same test distribution. Avoid claiming field accuracy, universal safety, or that a high classification score validates signal control.

## Next experiments before submission
1. Evaluate on a separate network layout and unseen congestion regimes; keep seeds and route families disjoint.
2. Report per-density and per-route-length MAE, confusion matrices, uncertainty intervals across paired seeds, and ordinary waiting/throughput tradeoffs.
3. Compare rule-based priority, optional frozen RL, and standard signals under matched scenarios, with collision and clearance checks.
4. Profile runtime and disclose hardware, SUMO version, random seeds, software version and all exclusions.

Primary artifacts: `results/model-metrics.json`, `results/training-data.json`, `results/paired-training-runs.csv`, and exported `datasets/*.csv` with `datasets/DATA_DICTIONARY.md`.
