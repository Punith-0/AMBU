# City Sandbox and operations workspaces

Run `Start-AMBU.bat` or `python app.py`, then open `http://127.0.0.1:8877`. These views use the same running SUMO simulation. Switching workspaces does not start a separate run.

## Enter and explore

Choose **Enter City ↗**, or **Workspaces ☰ → City Sandbox**. The city fills a dedicated screen, hides the website controls and requests browser fullscreen. If the browser declines fullscreen, it still fills the page. Floating object names are hidden; click an object to open its inspector.

Use **Controls** to search objects, pause/resume, change simulation speed, switch day/night, build an emergency or open the mission debrief. **Exit to website ↙** restores the normal website. Escape closes a scenario/debrief dialog first, or toggles the controls and stops a camera tour; the browser may also use Escape to leave native fullscreen.

| Camera control | Action |
| --- | --- |
| Orbit / inspect | Drag to orbit; scroll to zoom. |
| Free fly | WASD moves relative to the camera; Q lowers and E raises it. |
| Ground level | WASD explores at a fixed street-level height. |
| Shift | Move faster in free/ground mode. |
| Save angle | Save up to six named camera positions in this browser. |
| Keys 1–6 | Recall the corresponding saved angle when not editing a field. |
| Director tour | Smoothly visit saved angles; requires at least two. Click the city, press Escape or select Stop tour to interrupt. |

Camera movement is exploration, not vehicle control. SUMO continues driving all vehicles; ground mode has no walking-character or building-collision physics.

## Click-to-info and live actions

- **Vehicles and ambulances:** inspect live speed and mission state, focus the camera or follow the vehicle.
- **Signals:** see the current phase, clearance, upcoming ambulance reservations and their estimated arrival. Choose an approved phase or temporary all-red with **Apply safe override**, or **Return to automatic**. Changes retain three seconds of yellow and two seconds of all-red clearance, expire after 30 simulation seconds, and cannot override an active emergency reservation.
- **Roads:** **Apply 3 m/s restriction** caps the selected directed road's lanes at 10.8 km/h; **Restore road speed** restores their original limits. This affects actual SUMO traffic, including ambulances. It is a speed restriction, not a closed road or a guaranteed reroute.
- **Hospitals:** inspect the destination and choose it for the first mission currently accepting a hospital choice. Capacity and services are illustrative, not live hospital data.
- **Buildings and other selectable city objects:** inspect their identity and associated road, focus the camera or choose **Create emergency here**. The pickup uses an accessible ambulance stop on that road, not the exact clicked point or a building interior.

Signal overrides and road restrictions are unavailable in matched comparison runs. A new run clears temporary restrictions and current missions.

## Build and save an emergency

Open **Controls → Build emergency**, **Create emergency here** in an inspector, or **Dispatcher → Create emergency**.

1. Choose Home emergency, Road accident, Critical care or Patient transfer, then urgency and pickup road.
2. Choose Sanjeevani Hospital, Aarogya General, Jeevan Heart Centre, or **Choose at pickup / nearest after 7s**. Without a choice, the nearest hospital by road distance is selected after seven wall-clock seconds at pickup.
3. Set the seed and demand for a new scenario. **Save scenario** stores up to twelve named configurations in this browser; **Load selected** fills the form without starting it.
4. **Start scenario →** replaces the current run using the chosen seed, demand and Ghost Race setting, then dispatches from Suraksha station. It resets speed to 1×. **Dispatch into current city** preserves the existing seed, traffic and single/matched-world mode.
5. Follow station departure, patient pickup/loading, hospital transport and handover. The scene clips illustrate these stages; motion and journey data come from SUMO.

Saved scenarios store configuration, not an exact replay of vehicle positions. Hospital-choice and loading windows use wall-clock time, so operator timing can affect reproducibility even with the same seed. Camera bookmarks and scenarios remain local to this browser profile; clearing browser storage removes them.

## Ghost Ambulance Race and mission debrief

Enable **Ghost race: matched AMBU ON / OFF worlds** and use **Start scenario →**. Two independent SUMO worlds receive the same seed, demand and dispatch: one uses AMBU coordination, the other conventional signals. Select the same hospital in advance for a straightforward comparison. Starting a Ghost Race replaces the current run; checking the box alone cannot convert a current single-world run.

In Sandbox, the translucent blue ambulance is the baseline world; the solid ambulance is AMBU. The minimap also shows both positions. They are separate traffic worlds, so their overlaid vehicles do not collide with each other. A faster AMBU arrival is not guaranteed.

Open **Controls → Mission debrief** or **Workspaces ☰ → Mission debrief** for elapsed journey time, time stopped in traffic, station-to-pickup time and hospital transport time. Paired savings appear only after both ambulances finish. The ordinary-traffic waiting difference is total vehicle-seconds across the two worlds at the displayed common simulation horizon; it is not a per-car delay or a clinical outcome. The report also displays reported SUMO collisions. Use **Download report JSON** to keep the measurements before starting a new run.

## Administrator, Dispatcher and Driver

Use **Operations ↗** or **Workspaces ☰** to open a dedicated workspace. The sidebar switches roles; **Fullscreen** expands the workspace and **Back to city** returns to the site.

| Workspace | Available controls |
| --- | --- |
| Administrator | Engine/model status, Q-learning state/updates, collisions and network counts; pause/resume, speed, seed/demand and Start new run; Standard AMBU, Frozen policy or Continue learning. |
| Dispatcher | Create emergencies, enter City Sandbox, select a live fleet mission, inspect its elapsed time/wait/speed/destination, read operations events and open its Driver workspace. |
| Driver | Select an ambulance; view the synchronized primary, chase and hospital cameras, live route map, ETA and upcoming signals. Existing camera controls select the viewpoint. Request dispatch opens the emergency builder. |

**These are local interface workspaces, not authenticated accounts or access-control boundaries.** Admin's Start new run creates a single-world run and clears active journeys, while fitted models and the saved policy remain available. Learning controls require a single-world run; matched comparisons do not accept policy changes. Q-learning persists approved phase/hold choices locally; improvement over standard coordination has not been demonstrated.

## Present the project

Choose **Workspaces ☰ → Presentation** or the Presentation tab. The twelve-slide deck supports scrolling, Previous/Next, right/left arrow keys, Page Down/Page Up and fullscreen. Its final slide enters City Sandbox. The clearance animation and learning explanations are explanatory diagrams; they do not change live traffic. The engine-status strip and model metrics read local application data.

A compact live demonstration: enter Sandbox, inspect a signal, save two camera angles, start a fixed-hospital Ghost Race, follow the two journeys, then open the debrief. Use Dispatcher and Driver to show the same mission from their workspaces.

## Scope and verification

The city is a Bengaluru-inspired synthetic square-grid network. GPS, E1 point detectors and E2 lane detectors are virtual SUMO sensors. There is no real ambulance booking, physical signal control, clinical monitoring, hospital capacity integration or authentication. Browser voice support is separate from these workspaces and is not a telephone service. A rewindable replay timeline is not implemented.

Backend regression: **15 tests passed** in `results/test-report-sandbox.txt`. This includes actual SUMO road restriction/restore/reset checks and a matched station-to-pickup-to-hospital workflow with independent journey timings and zero reported collisions in that test. Those results do not establish field safety, general performance gains or complete browser coverage. See [VALIDATION.md](VALIDATION.md) for the wider validation record.
