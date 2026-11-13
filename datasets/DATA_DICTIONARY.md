# AMBU measured training data

All numeric observations originate from SUMO runs in the included city network. No real-world patient, vehicle or location data is included.

- eta_training.csv: ordinary-operation journey snapshots. Target = actual seconds remaining until arrival. Linear Regression and Random Forest use the same six features. Whole random seeds divisible by five are held out. Route length includes the whole current edge; it is not GPS-adjusted remaining distance. Correlated snapshots stay in their seed group.
- priority_training.csv: one dispatch-time feature vector and measured counterfactual label per paired episode. Label is 1 when ambulance seconds saved exceed 3 + 0.02 * additional total normal waiting vehicle-seconds. This is an explicit research tradeoff, not a real-world validated safety policy. Baseline and priority runs use the same seed, traffic, dispatch and end horizon. Priority training runs use rule-driven priority, to collect both outcomes before fitting the classifier.
- congestion_training.csv: network snapshots every five simulation seconds after a 60-second warm-up. All rows fit the unsupervised K-Means model; there is no supervised accuracy claim or held-out classification label. Units are m/s and vehicle counts. Provenance is reconstructed from the recorded ordered experiment horizons and checked against sample count.
- final_policy_evaluation.csv: independent seeds 101-105, fixed 400-second horizons, fitted Logistic Regression gated standard AMBU versus baseline. This is a separate evaluation, not an RL comparison.
- paired_experiments.csv: raw baseline/priority outcomes, including total normal waiting vehicle-seconds, mean summed detector queue, throughput and collisions. These training-policy results are NOT the evaluation of the final Logistic Regression gated policy.

Seeds 1-42 use seven route families on the square 36-junction road network (sumo/nightwatch.net.xml), with identical 480-second paired horizons. Short trips with no priority benefit provide negative labels. This small synthetic training set supports the demonstrator, not citywide generalization.
