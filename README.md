# Controls Engineering Simulation

### Automated Ride Station Control & Fault Diagnostics

**Python · Industrial Automation · SCADA/HMI · PLC-Inspired Monitoring · Fault Diagnostics**

An independent controls-engineering work sample demonstrating a Python-based automated ride station simulator. It combines a shared controller state machine, local HTTP/JSON API, interactive browser HMI, automatic scan cycles, read-only ladder and instruction visualization, and latched fault diagnostics.

**[View the complete technical portfolio (PDF)](Controls%20Engineering%20Technical%20Work%20Sample%20%E2%80%94%20Automated%20Ride%20Station%20Control%20%26%20Fault%20Diagnostics.pdf)**

> **Scope:** Educational simulation only. No physical PLC or ride hardware is connected. The system is not safety-rated; ladder logic is visualized, not executed.

## Key features

- **Controller states:** IDLE, READY, DISPATCHED, AWAY, and FAULT.
- **Interactive HMI:** Digital inputs, operator controls, controller state, alarms, and scan events.
- **Automatic scanning:** Optional 500 ms controller scan cycle, with manual scanning available.
- **PLC-inspired monitoring:** Read-only ladder power flow and XIC, XIO, OTE, OTL, OTU, and TON instruction indications.
- **Diagnostics:** Simulated communications, sensor, drive, and E-stop faults with latched alarms and reset logic.
- **Verification:** Python unit tests, recorded scenario traces, and a documented acceptance walkthrough.

## Technology stack

| Area | Implementation |
| --- | --- |
| Controller and CLI | Python (`ride_sim.py`) |
| API and automatic scan worker | Python standard library (`api_server.py`) |
| Browser HMI | HTML, CSS, JavaScript (`dashboard.html`) |
| Communications | Local HTTP/JSON |
| Logic visualization | Read-only PLC-inspired ladder and instruction monitor |
| Tests | Python `unittest` |
| Development | VS Code, Git, GitHub |

## Project screenshots

### HMI dashboard — READY state

Operator interface showing controller state, digital inputs, dispatch controls, and scan activity.

![HMI dashboard READY state](screenshots/HMI%20Dashboard%20%E2%80%94%20READY%20State.png)

### Ladder logic visualization

Read-only ladder monitor showing instruction status and animated power flow based on Python controller state.

![Ladder logic visualization](screenshots/Ladder%20Logic%20Visualization.png)

### Fault diagnostics — latched alarm

Simulated equipment fault detection, alarm register, and operator reset behavior.

![Fault diagnostics latched alarm](screenshots/Fault%20Diagnostics%20%E2%80%94%20Latched%20Alarm.png)

## Architecture

`dashboard.html` communicates over localhost HTTP/JSON with `api_server.py`. The API owns one shared Python `RideStation` from `ride_sim.py`. A background worker can scan every 500 ms; the browser refreshes status approximately every 250 ms. Phase 3/4 ladder displays derive their indications from controller state and **do not execute ladder logic**.

## Development phases

### Phase 1 — Core controller and connected HMI

Eight digital inputs; IDLE/READY/DISPATCHED/AWAY/FAULT states; dispatch permissives; diagnostic fault latching; reset, arrival, and scan event history. The dashboard uses API endpoints rather than an independent JavaScript controller.

### Phase 2 — Automatic scans

Start or stop automatic 500 ms scans; manual scan remains available. Live dashboard refresh, scan counter, recent scan log, active faults, and latched alarm register.

### Phase 3 — Visual ladder monitor

Read-only, RSLogix-inspired rung visualization for diagnostic health, dispatch permissives, dispatch enable, fault, and train-away indications. TRUE/FALSE contact status and animated power flow reflect the current Python state; this is not executable PLC logic.

### Phase 4 — Instruction monitor

Instruction indications include XIC (examine TRUE), XIO (examine FALSE), OTE (non-retentive coil-style indication), OTL (latch indication), OTU (unlatch indication), and TON (on-delay timer monitor). A separate instruction-status panel accompanies live visual rung flow.

`AWAY_DWELL` has a 2,000 ms preset: EN is enabled while AWAY, TT indicates timing, and DN becomes true when accumulated time reaches the preset. The monitoring timer uses elapsed time between scans and resets outside AWAY. Its DN bit does not command ride motion.

## Inputs and dispatch permissives

The eight modeled digital inputs are:

| Input | Meaning |
| --- | --- |
| `train_present` | Train detected at station |
| `gate_closed` | Station gate closed |
| `restraints_locked` | Restraints locked |
| `block_clear` | Downstream block available |
| `drive_ready` | Drive ready |
| `estop_healthy` | E-stop circuit healthy |
| `plc_comms_ok` | Simulated PLC communications healthy |
| `sensor_consistent` | Sensor readings consistent |

All eight must be TRUE to permit dispatch. FALSE values for `estop_healthy`, `plc_comms_ok`, `sensor_consistent`, or `drive_ready` generate diagnostic faults. Gate, restraint, or block loss inhibits dispatch without automatically latching a diagnostic fault in this model.

## Dispatch, departure, and arrival

With all inputs TRUE, SCAN moves IDLE to READY. DISPATCH moves READY to DISPATCHED. The next scan moves to AWAY and sets `train_present=FALSE` and `block_clear=FALSE`.

To simulate return, set `block_clear=TRUE` while AWAY, then request ARRIVE; `train_present` becomes TRUE and the state returns to IDLE. The next scan can restore READY. In AUTO mode, IDLE may be visible only briefly.

## Fault and reset sequence

For example, set `plc_comms_ok=FALSE` and scan. The controller enters FAULT and latches `PLC_COMMUNICATION_LOSS`. Restoring communications alone does not clear the latch. RESET requires no active diagnostic faults and all eight permissives TRUE.

Other modeled diagnostic alarms include `SENSOR_DISAGREEMENT`, `DRIVE_NOT_READY`, and `E_STOP_CIRCUIT_OPEN`.

## Installation and launch (Windows / VS Code)

Open the project folder in VS Code and run the following in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python api_server.py
```

Open **http://127.0.0.1:8000/dashboard.html** in a browser. Use **Ctrl+F5** for a hard refresh and **Ctrl+C** in the terminal to stop the server. The Phase 4 server does not require third-party Python packages.

## Local API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/status` | Read controller and monitor status |
| POST | `/api/scan` | Execute a manual scan |
| POST | `/api/dispatch` | Request dispatch |
| POST | `/api/reset` | Reset eligible latched faults |
| POST | `/api/arrive` | Simulate arrival |
| POST | `/api/input` | Set a simulated input |
| POST | `/api/restart` | Restart simulation |
| POST | `/api/auto/start` | Start automatic scans |
| POST | `/api/auto/stop` | Stop automatic scans |

Example input JSON:

```json
{"name": "plc_comms_ok", "value": false}
```

Controller access is serialized with a Python lock. Commands can trigger scans while AUTO mode is running.

## CLI and verification

Run the interactive controller:

```powershell
python ride_sim.py
```

Available commands include `status`, `scan`, `dispatch`, `arrive`, `reset`, `set <input> <0|1>`, and `quit`.

Run the included original-controller tests and scenarios:

```powershell
python -m unittest -v test_ride_sim.py
python ride_sim.py --scenarios
```

The original work sample reported **10 Python unit tests passed** and **six scenario traces**. These are historical original-controller results, **not evidence of automated Phase 4 browser validation**.

## Suggested acceptance walkthrough

1. Restart, scan to READY, dispatch to DISPATCHED, then scan to AWAY.
2. Observe `AWAY_DWELL` EN, TT, ACC, and DN at approximately 2 seconds.
3. Set `block_clear=TRUE`, request ARRIVE, and scan to READY.
4. Set `plc_comms_ok=FALSE`, scan to FAULT, restore the input, and reset.
5. Start AUTO, confirm the scan counter increases, then stop AUTO and confirm it stops.

## Troubleshooting

- At the `station>` prompt, enter `quit` before starting the API server.
- Do not type the PowerShell prompt itself as part of a command.
- If port 8000 is occupied, stop the prior server using Ctrl+C.
- If the dashboard looks outdated, verify the files and use Ctrl+F5.
- Arrival requires AWAY state and `block_clear=TRUE`.
- Fault reset requires all permissives TRUE and no active diagnostic faults.

## Repository files

| File | Purpose |
| --- | --- |
| `ride_sim.py` | Python `RideStation` state machine and CLI |
| `api_server.py` | Local API, automatic scan worker, instruction monitor |
| `dashboard.html` | Browser HMI and ladder/instruction panels |
| `test_ride_sim.py` | Original Python unit tests |
| `scenario_results.json` | Recorded scenario evidence |
| `test_results.txt` | Recorded test results |
| `screenshots/` | HMI, ladder, and fault diagnostics screenshots |
| `Controls Engineering Technical Work Sample — Automated Ride Station Control & Fault Diagnostics.pdf` | Engineering portfolio report |

## Professional context and limitations

This independent portfolio exercise was prepared for a controls-engineering application. Prior manufacturing experience included Wonderware InTouch SCADA/HMI development, Allen-Bradley PLC integration, and limited online RSLogix 500 ladder monitoring; it **did not include writing or modifying PLC ladder programs**.

The simulator omits real hardware, redundant safety systems, deterministic real-time scheduling, certified block control, braking, and motion dynamics. Phase 5 executable ladder logic is intentionally excluded.
