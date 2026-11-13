# Render deployment (free only)

Deploy this directory as the repository root. The Blueprint in `render.yaml`
selects a Docker web service with `plan: free`. No database or paid disk is required.

1. Push the AMBU source to its own GitHub repository. Never upload `.env`.
2. In Render, create a Blueprint and connect that repository.
3. Verify the service is on the Free instance plan before creating it.
4. Set `GROQ_API_KEY` privately in Render's environment settings if AI insights
   are needed. Without it, simulation works but the AI request returns an error.
5. Deploy, then verify `/healthz` reports models ready, `/api/state` responds,
   and the browser receives live WebSocket updates. Run a matched dispatch to
   completion before treating the hosted deployment as verified.

The image includes the trained model, metrics and initial signal policy.
It excludes credentials, training logs, historical archives and local caches.
SUMO, TraCI and sumolib are pinned to 1.27.1, matching the local simulator.
One Uvicorn worker is required: simulation state lives in process memory.

## Free-tier behavior

All visitors share one simulation and its controls. This is a demonstration
deployment, not a multi-user dispatch service. Render can sleep or restart the
service; active missions and newly learned policy changes are then lost.
The committed initial models remain available on the next startup.
Do not retrain models on the free web instance. Train locally and redeploy.
Free-instance performance, especially 8x paired runs, must be measured online.

Render may bill supplementary bandwidth/build usage if billing is enabled.
Keep account spend controls at zero and do not enable paid services or upgrades.
See https://render.com/docs/free for current limits.

## Local container check

```sh
docker build -t ambu-city-lab .
docker run --rm -p 10000:10000 ambu-city-lab
```

Visit http://localhost:10000. Pass secrets through environment variables only.
