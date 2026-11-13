# Verification record — 4 November 2026

Current network: sumo/nightwatch.net.xml (square grid, 36 junctions at 150 m spacing). The compatible archived grid study is restored; the curved-road study is preserved in results/curved-city-study-20261104.zip.

- Full SUMO regression suite after grid restoration: 11 passed in 46.03 seconds (see results/test-report-square.txt); two non-fatal SUMO stop-duration API warnings. Includes eligibility, signal clearance/restoration, conflicting ambulance coordination, pickup/timeout/hospital selection, completion, manual override expiry, RL persistence/freeze and rejection of an incompatible trained model.
- Frontend motion test passed: jittered packet arrivals, no false stops, stationary stop and pause. At 10 m/s input, rendered velocity was 9.26–10.27 m/s after warm-up.
- Sound mode test passed: responding, patient transport, loading, completed, paused, inactive and mixed fleets. Browser mute/unmute verified; audio is synthesized locally. Physical speaker output was not independently listened to.
- Prior browser verification before this layout restoration: smooth-road city rendering; free camera selection; steering hands; station dispatch; completed journey followed by automatic hospital handover video; six saved scene clips and preview; mute toggle; no frontend console errors at verification. Manual signal selection/clearance, comparison initialization and presentation navigation were also checked.
- Video files are original rendered illustrations using the requested armored crew. Runtime sound is separate from the silent WebM files. Not photoreal footage or a geographic Bengaluru replica.
- Microphone/speech recognition was not tested with a real utterance; typed assistant intents are available. No telephone call or actual emergency booking occurs.

## Restored matching-grid research

42 paired episodes on the square 36-junction road network, seven route families, 480-second matched training horizons. 482 ETA snapshots (395 train, 87 test); 42 priority episodes (34 train, eight test); 7,056 congestion snapshots. Whole seeds divisible by five are held out. Labels use measured simulated counterfactual outcomes with an explicit cost tradeoff.

Linear Regression MAE 12.48 seconds; Random Forest MAE 11.86 seconds. Logistic Regression accuracy 62.5% on eight held-out episodes. This small synthetic study does not establish real-world accuracy. Models store a network fingerprint and reject incompatible geometry.

Q-learning warm-start: six 600-second episodes, 4,510 updates and 396 states. It learns approved phase/hold choices, persists locally and can be frozen. This does not demonstrate RL superiority.

Independent standard-controller evaluation: five seeds, fixed 400-second horizons; baseline 204.9 ± 10.6 seconds, AMBU 133.6 ± 24.1 seconds (mean ± sample SD). 0 reported collisions across ten runs. Ordinary-traffic waiting increased in 3/5 pairs. Results are simulated and route-specific.


See results/final-policy-evaluation.csv, model-metrics.json and rl-training.json. Evaluation does not establish field safety, generalization or RL superiority.

The majority-class baseline on the eight priority holdout episodes is 62.5%; Logistic Regression accuracy is 62.5%. This tiny holdout does not establish a classification gain.

## Square-grid and performance update — 4 November 2026

Restored the original 36-junction square grid and its compatible supervised models, CSVs and RL policy. Boarding/pickup/hospital handover clips, sound, free camera and steering controls are retained.

Rendering now batches signal lamps into one instanced draw and merges facade material groups. Ordinary traffic shares six reusable car templates, with five rather than nine draws per car. A local 200-car construction benchmark measured 893 ms before versus 162 ms after; this is construction timing, not a guaranteed FPS increase. Static shadows are cached at 1024 resolution; moving cars do not cast dynamic shadows. Main pixel ratio is capped at 1.25, driver at 1.2 and small views at 1. Chase/destination feeds render at most 24/15 FPS; the primary camera follows display refresh. Hidden/covered views skip rendering and catch up when reopened.

Identical simulation snapshots are no longer repeatedly sent over the WebSocket. Hidden charts, fleet/log cards and the signal grid are not rebuilt; opening their panel refreshes them immediately. Live mission/audio transitions remain active. Vehicle history is bounded, and shared car geometry survives departures/resets.

Validation: 11 backend tests pass (results/test-report-square.txt); motion, audio, batching/raycast and hidden-UI update checks pass. Live grid geometry/models/RL, unique WebSocket timestamps, dispatch, synchronized cameras and free-camera selection verified. Browser console showed no errors. Actual frame rate varies by device and viewport.

Frontend checks: `node tests/test_motion.mjs`, `node tests/test_audio.mjs`, `node tests/test_ui_render.mjs`, `node --no-warnings --loader ./tests/three-loader.mjs tests/test_batching.mjs`.
