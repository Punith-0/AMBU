# AMBU Nightwatch

Local emergency-response simulator using FastAPI, Eclipse SUMO and Three.js. The city is Bengaluru-inspired and synthetic, not an exact geospatial twin. No real ambulance booking or physical traffic-light control occurs.

## Start
Run Start-AMBU.bat after installing Python requirements and Eclipse SUMO. Or run `python app.py`, then open http://127.0.0.1:8877 . Verified with Python 3.14 and SUMO 1.27.1 on Windows. Browser assets, textures and fitted models are bundled locally.

For the dedicated interactive city, Ghost Race, saved scenarios, camera tours, mission reports and Admin/Dispatcher/Driver views, see [City Sandbox and operations workspaces](docs/SANDBOX-WORKSPACES.md). Start with **Enter City ↗** or **Workspaces ☰**. These are local simulation workspaces, not authenticated roles.

## Present the demo
1. Open Dispatch to reveal the glass control drawer. Set traffic/seed and New run if needed.
2. Choose an Indian-named pickup and home, crash, critical or transfer scenario. Dispatch starts driver boarding and requests fullscreen.
3. The ambulance travels from Suraksha station to the patient. At pickup, choose a hospital within seven wall-clock seconds; otherwise the nearest by road distance is selected automatically.
4. Patient loading is followed by hospital transport. Driver, chase, destination and minimap views share SUMO positions. Camera buttons control the view; SUMO drives.
5. Exit immersive view to return to the city. View controls reveals camera modes and simulation speeds. Click a signal head for the hidden operator panel: approved green phase, temporary all-red or automatic. Changes use clearance, expire after 30 simulation seconds, and cannot override an active emergency reservation.
6. Intelligence contains individual signal states, live metrics, persisted Q-learning modes and training CSV downloads. Experiments creates matched ON/OFF worlds; manual overrides are disabled there. Presentation contains twelve fullscreen-capable slides with keyboard navigation.
7. Talk to AMBU supports typed booking, confirmation, location, ETA and traffic intents. Browser voice recognition/replies depend on browser support and microphone permission; no phone integration or LLM is claimed.

## Models and data
42 paired episodes on the square 36-junction road network, seven route families, 480-second matched training horizons. 482 ETA snapshots (395 train, 87 test); 42 priority episodes (34 train, eight test); 7,056 congestion snapshots. Whole seeds divisible by five are held out. Labels use measured simulated counterfactual outcomes with an explicit cost tradeoff.

Linear Regression MAE 12.48 seconds; Random Forest MAE 11.86 seconds. Logistic Regression accuracy 62.5% on eight held-out episodes. This small synthetic study does not establish real-world accuracy. Models store a network fingerprint and reject incompatible geometry.

Q-learning warm-start: six 600-second episodes, 4,510 updates and 396 states. It learns approved phase/hold choices, persists locally and can be frozen. This does not demonstrate RL superiority.

Restored matching-grid standard-controller evaluation: five seeds, fixed 400-second horizons; baseline 204.9 ± 10.6 seconds, AMBU 133.6 ± 24.1 seconds (mean ± sample SD). 0 reported collisions across ten runs. Ordinary-traffic waiting increased in 3/5 pairs. Results are simulated and route-specific.

## Reproduce
`python train.py --seeds 42`
`python export_training.py`
`python train_rl.py`
`python evaluate.py`
`python -m pytest tests -q`

The rebuilt city has square-grid roads with a clean satin finish, facade detail, landmarks, detailed vehicles, shadows and reflection lighting. Geometry is batched to reduce rendering overhead. It is a browser prototype, not GTA-level photorealism. Six original rendered WebM clips are bundled in dashboard/videos and automatically play during boarding, pickup and hospital handover. The armored crew appearance was intentionally retained by request. Regenerate clips in Intelligence > Original scene videos. These are 3D illustrations, not photoreal human footage. See docs/VALIDATION.md and docs/ASSET_CREDITS.md.


## Motion and camera update
Vehicle playback uses timestamped sample buffers with a small presentation delay to absorb WebSocket jitter. Stops commanded by SUMO remain real stops. The motion regression test simulates jittered arrivals at 60 FPS and checks continuous speed, stationary vehicles and pause behavior: `node tests/test_motion.mjs`.

The main camera selector supports driver, chase, front, left, right, overhead and free orbit. Free orbit accepts dragging/zooming. Driver view has 3D steering hands; steering follows the measured heading change. Offscreen camera rendering is skipped to reduce GPU load. Detailed crew textures and scene asphalt are bundled; city roads use the restored clean material. See ASSET_CREDITS.md.

## Hospital arrival and sound
Completed station missions automatically show stretcher unloading and a doctor-team handover at the emergency entrance. Intelligence > Original scene videos lets you preview any of six clips or regenerate them locally.

Sound unlocks after a browser interaction. Response uses a slow siren sweep; patient transport uses a different faster, quieter siren plus a soft illustrative monitor cue. Loading and hospital handover have separate cues. Pause/completion stops the driving siren; hidden tabs and the voice assistant panel quiet the mix. Sound on/off is in the header. These original synthesized cues play at runtime; the WebM files themselves are silent and contain no medical monitoring data.

`node tests/test_audio.mjs` checks stage-to-sound transitions. No physical speaker-listening test or real microphone utterance is claimed. The restored grid-city research is active. Curved-city research remains archived in results/curved-city-study-20261104.zip.

The majority-class baseline on the eight priority holdout episodes is 62.5%; Logistic Regression accuracy is 62.5%. This tiny holdout does not establish a classification gain.

## Square-grid and performance update — 4 November 2026

Restored the original 36-junction square grid and its compatible supervised models, CSVs and RL policy. Boarding/pickup/hospital handover clips, sound, free camera and steering controls are retained.

Rendering now batches signal lamps into one instanced draw and merges facade material groups. Ordinary traffic shares six reusable car templates, with five rather than nine draws per car. A local 200-car construction benchmark measured 893 ms before versus 162 ms after; this is construction timing, not a guaranteed FPS increase. Static shadows are cached at 1024 resolution; moving cars do not cast dynamic shadows. Main pixel ratio is capped at 1.25, driver at 1.2 and small views at 1. Chase/destination feeds render at most 24/15 FPS; the primary camera follows display refresh. Hidden/covered views skip rendering and catch up when reopened.

Identical simulation snapshots are no longer repeatedly sent over the WebSocket. Hidden charts, fleet/log cards and the signal grid are not rebuilt; opening their panel refreshes them immediately. Live mission/audio transitions remain active. Vehicle history is bounded, and shared car geometry survives departures/resets.

Validation: 11 backend tests pass (results/test-report-square.txt); motion, audio, batching/raycast and hidden-UI update checks pass. Live grid geometry/models/RL, unique WebSocket timestamps, dispatch, synchronized cameras and free-camera selection verified. Browser console showed no errors. Actual frame rate varies by device and viewport.

Frontend checks: `node tests/test_motion.mjs`, `node tests/test_audio.mjs`, `node tests/test_ui_render.mjs`, `node --no-warnings --loader ./tests/three-loader.mjs tests/test_batching.mjs`.
