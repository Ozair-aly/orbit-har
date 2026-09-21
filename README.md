# 🚀 ORBIT-HAR (Onboard Real-time Behavioral and  Interactional Tracking for Human Activity Recognition)

## AI Human Activity Recognition for On-Board BAS Experiments

**ORBIT-HAR** is an AI-powered, edge-deployable ,offline Human Activity Recognition and Experiment Monitoring system designed for **on-board biological/physical science experiments in space missions**.

The system allows an astronaut-side computer to locally monitor experimental activities using camera-based AI, recognize predefined actions, validate their sequence, detect incorrect or unexpected actions, and provide real-time feedback through a mission-control-style dashboard.

The core idea is simple:

> **Run the intelligence where the experiment happens — instead of continuously sending raw video to Earth.**

---

## 🛰️ Problem Statement

### Smart India Hackathon — Problem Statement ID: 26174

**AI Human Activity Recognition for On-board BAS Experiments**

Biological and physical science experiments performed during space missions may require astronauts to follow a predefined sequence of actions.

In a conventional setup, large amounts of camera data may need to be transmitted for monitoring and analysis.

However, space missions introduce challenges such as:

* Limited communication bandwidth
* Communication delays
* Limited opportunities for continuous ground monitoring
* Large raw-video data volumes
* Need for autonomous on-board decision making
* Astronauts operating in microgravity where conventional spatial assumptions may not apply

ORBIT-HAR addresses this by performing **local AI-based activity recognition and experiment validation at the edge**.

---

# 🎯 Project Objective

ORBIT-HAR is designed to:

* Detect astronaut actions using an onboard camera
* Track relevant objects and hand interactions
* Recognize predefined experiment activities
* Validate whether actions occur in the correct sequence
* Detect incorrect or unexpected actions
* Provide immediate feedback
* Maintain experiment logs
* Display experiment status through a dashboard
* Run without requiring continuous cloud connectivity
* Support an astronaut-side edge computer
* Provide a mission-control monitoring interface
* Reduce dependence on transmitting raw video for analysis

---

# 🧠 Core Concept

ORBIT-HAR follows an **edge-first architecture**.

```text
                 ┌─────────────────────────┐
                 │       Camera Feed       │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │   Computer Vision       │
                 │                         │
                 │  YOLO Object Detection  │
                 │  MediaPipe Hand Track   │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │   Activity Recognition  │
                 │                         │
                 │ PICK_CONTAINER          │
                 │ TILT_CONTAINER          │
                 │ SHAKE_CONTAINER         │
                 │ OPEN_VALVE              │
                 │ UPRIGHT_CONTAINER       │
                 │ PUTDOWN_CONTAINER       │
                 └────────────┬────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │ Sequence Validation     │
                 │                         │
                 │ Expected Action         │
                 │ Detected Action         │
                 │ Current Step            │
                 │ Experiment State        │
                 └────────────┬────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌─────────────────┐       ┌─────────────────┐
        │ Local Feedback  │       │ Mission Control │
        │                 │       │ Dashboard       │
        │ Voice / Logs    │       │                 │
        └─────────────────┘       └─────────────────┘
```

The AI processing happens locally, while the resulting **events, states, detections and experiment information** can be sent to the monitoring dashboard.

---

# ✨ Key Features

## 🤖 AI-Based Activity Recognition

ORBIT-HAR processes live camera frames and identifies experiment-related activities.

The prototype currently supports actions such as:

* `PICK_CONTAINER`
* `TILT_CONTAINER`
* `SHAKE_CONTAINER`
* `OPEN_VALVE`
* `UPRIGHT_CONTAINER`
* `PUTDOWN_CONTAINER`

The action vocabulary can be extended for additional experiments.

---

## 👋 Hand Tracking

MediaPipe Hands is used to track astronaut hand movement and interaction with experiment objects.

This provides additional information for:

* Hand-object interaction
* Object manipulation
* Action confirmation
* Gesture/activity analysis

---

## 🎯 Object Detection

YOLO is used as part of the computer-vision pipeline to identify relevant objects.

The current prototype uses:

* YOLO
* OpenCV
* MediaPipe

The architecture can later be extended with a custom-trained model specifically for experiment hardware.

---

# 🔄 Experiment Sequence Validation

A major component of ORBIT-HAR is **sequence-aware experiment validation**.

Instead of simply asking:

> "What action is happening?"

the system asks:

> "Is the astronaut performing the correct action at the correct point in the experiment?"

For example:

```text
Expected:
1. PICK_CONTAINER
2. TILT_CONTAINER
3. SHAKE_CONTAINER
4. OPEN_VALVE
5. UPRIGHT_CONTAINER
6. PUTDOWN_CONTAINER
```

If the system detects an unexpected action:

```text
Expected Action : OPEN_VALVE
Detected Action : SHAKE_CONTAINER
Status          : WRONG
```

The system can report the mismatch instead of silently accepting the action.

This allows ORBIT-HAR to function as an **experiment procedure validation system**, rather than only a generic activity-recognition model.

---

# 🧪 Example Experiment

The current prototype includes a liquid-transfer-style experiment.

### Liquid Sample Transfer

Example sequence:

```text
PICK_CONTAINER
       ↓
TILT_CONTAINER
       ↓
SHAKE_CONTAINER
       ↓
OPEN_VALVE
       ↓
UPRIGHT_CONTAINER
       ↓
PUTDOWN_CONTAINER
```

Each experiment can be represented using a configuration file.

Example:

```text
experiments/
└── liquid_transfer.json
```

This makes the system extensible without requiring the complete application logic to be rewritten for every experiment.

---

# 🖥️ ORBIT-HAR Dashboard

ORBIT-HAR includes a web-based mission monitoring dashboard.

The dashboard is designed around the concept of a mission-control interface.

### Dashboard components include:

* Live Camera
* Experiment Status
* Current Step
* Expected Action
* Detected Action
* AI Detection Status
* Sequence Engine Status
* Edge Processing Status
* Mission Log
* Backend/Edge Connectivity
* Voice Assistant Status

Example dashboard state:

```text
┌─────────────────────────────────────────────────────────┐
│                    ORBIT-HAR                            │
│              EDGE EXPERIMENT MONITOR                   │
├───────────────────────────┬─────────────────────────────┤
│                           │                             │
│      LIVE CAMERA          │     EXPERIMENT STATUS       │
│                           │                             │
│      Astronaut Feed       │     Experiment: Liquid     │
│                           │     Sample Transfer         │
│                           │                             │
│                           │     Step: 2 / 6             │
│                           │     Expected: TILT          │
│                           │     Detected: TILT          │
│                           │     Status: VERIFIED        │
│                           │                             │
├───────────────────────────┴─────────────────────────────┤
│                    AI DETECTION                         │
│                                                         │
│  Astronaut        ✓ DETECTED                            │
│  Container        ✓ DETECTED                            │
│  Hand Tracking    ✓ ACTIVE                              │
│  Sequence Engine  ✓ ACTIVE                              │
│  Edge Processing  ✓ LOCAL                               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                    LIVE MISSION LOG                     │
│                                                         │
│  [10:31:02] Container detected                          │
│  [10:31:04] PICK_CONTAINER verified                     │
│  [10:31:08] TILT_CONTAINER detected                     │
│  [10:31:09] Step verified                               │
└─────────────────────────────────────────────────────────┘
```

---

# ⚡ Edge Processing

ORBIT-HAR is designed around **local processing**.

The AI pipeline does not fundamentally depend on a cloud API to recognize experiment actions.

This is important for environments where:

* Internet connectivity is unavailable
* Network latency is high
* Bandwidth is limited
* Data transmission is expensive
* Continuous raw-video transmission is undesirable

The intended deployment model is:

```text
             ASTRONAUT SIDE
        ┌───────────────────────┐
        │       Camera          │
        │          ↓            │
        │    ORBIT-HAR AI       │
        │          ↓            │
        │   Sequence Engine     │
        │          ↓            │
        │   Local Event Log     │
        └───────────┬───────────┘
                    │
                    │ Events / Monitoring
                    │
                    ▼
             MISSION CONTROL
        ┌───────────────────────┐
        │    ORBIT-HAR UI       │
        │                       │
        │ Experiment Status     │
        │ AI Detection          │
        │ Mission Logs          │
        │ Camera Stream*        │
        └───────────────────────┘
```

`*` Live video transmission is an optional monitoring layer and is separate from the core local AI processing.

---

# 📡 Local Camera + Mission Control Streaming

ORBIT-HAR can be structured so that:

### Astronaut-side system

```text
Camera
  ↓
AI Processing
  ↓
Activity Recognition
  ↓
Sequence Validation
  ↓
Event Generation
```

while a separate monitoring channel can provide:

```text
Camera
  ↓
Video Stream
  ↓
Mission-Control Laptop
```

This means video monitoring does not need to determine where the AI runs.

The AI can continue running locally even when mission-control connectivity is unavailable.

---

# 🏗️ System Architecture

```text
                         ORBIT-HAR
                             │
             ┌───────────────┴────────────────┐
             │                                │
       ASTRONAUT SIDE                  MISSION CONTROL
             │                                │
             ▼                                ▼
       Camera Input                    React Dashboard
             │                                ▲
             ▼                                │
       OpenCV Pipeline                        │
             │                                │
      ┌──────┴───────┐                        │
      │              │                        │
      ▼              ▼                        │
    YOLO         MediaPipe                    │
      │              │                        │
      └──────┬───────┘                        │
             ▼                                │
       Action Recognition                     │
             │                                │
             ▼                                │
       Sequence Engine                        │
             │                                │
       ┌─────┴──────┐                         │
       │            │                         │
       ▼            ▼                         │
    Correct       Wrong                       │
       │            │                         │
       └─────┬──────┘                         │
             ▼                                │
       Event / Log ───────► FastAPI ──────────┘
```

---

# 🧩 Technology Stack

## AI / Computer Vision

* Python
* OpenCV
* YOLO / Ultralytics
* MediaPipe
* NumPy

## Backend

* Python
* FastAPI
* Uvicorn
* WebSockets

## Frontend

* React
* JavaScript
* WebSocket communication
* HTML/CSS

## Configuration

* JSON-based experiment definitions

## Local Feedback

* System voice output
* Local event logging

---

# 📁 Project Structure

The project is organized approximately as follows:

```text
ORBIT-HAR/
│
├── backend/
│   ├── main.py
│   └── ...
│
├── dashboard/
│   ├── src/
│   │   ├── App.jsx
│   │   └── ...
│   ├── package.json
│   └── ...
│
├── experiments/
│   └── liquid_transfer.json
│
├── models/
│   └── yolo11n.pt
│
├── logs/
│   └── ...
│
├── live_orbit_har.py
├── camera.py
├── yolo_test.py
├── requirements.txt
├── README.md
└── ...
```

The exact contents may evolve as the project is expanded.

---

# 📋 Experiment Configuration

Experiments are represented separately from the main recognition pipeline.

Example:

```json
{
  "experiment_name": "Liquid Sample Transfer",
  "steps": [
    {
      "action": "PICK_CONTAINER"
    },
    {
      "action": "TILT_CONTAINER"
    },
    {
      "action": "SHAKE_CONTAINER"
    },
    {
      "action": "OPEN_VALVE"
    },
    {
      "action": "UPRIGHT_CONTAINER"
    },
    {
      "action": "PUTDOWN_CONTAINER"
    }
  ]
}
```

This allows new experiments to be added by defining their sequence instead of rebuilding the entire application.

---

# 🔌 Backend API

The ORBIT-HAR backend is built using FastAPI.

The backend currently provides:

### Health endpoint

```text
GET /
```

Example response:

```json
{
  "system": "ORBIT-HAR",
  "status": "ONLINE"
}
```

---

### Event endpoint

```text
POST /event
```

Used by the AI pipeline to send experiment events to the backend.

Example event:

```json
{
  "experiment": "Liquid Sample Transfer",
  "step": 1,
  "total_steps": 6,
  "expected_action": "PICK_CONTAINER",
  "detected_action": "PICK_CONTAINER",
  "status": "VERIFIED"
}
```

---

### WebSocket

```text
/ws
```

The WebSocket connection allows the dashboard to receive live experiment updates.

Example flow:

```text
AI Pipeline
     │
     │ event
     ▼
 FastAPI
     │
     │ WebSocket broadcast
     ▼
 React Dashboard
```

---

# 🔄 Real-Time Event Flow

When the astronaut performs an action:

```text
Camera Frame
     ↓
Vision Processing
     ↓
Object / Hand Detection
     ↓
Action Recognition
     ↓
Sequence Validation
     ↓
Event Generated
     ↓
FastAPI Backend
     ↓
WebSocket
     ↓
Dashboard
```

The dashboard can then immediately update:

```text
Current Step
Expected Action
Detected Action
Status
Mission Log
```

---

# 🗣️ Voice Feedback

ORBIT-HAR can provide local voice feedback to the astronaut.

Possible feedback includes:

```text
"Step verified."

"Wrong action detected."

"Expected open valve."

"Experiment complete."
```

The voice layer is designed as an additional feedback channel and does not replace visual mission monitoring.

---

# 📝 Logging

ORBIT-HAR maintains experiment events that can be used for:

* Debugging
* Experiment replay
* Performance analysis
* Error analysis
* Mission logs
* Demonstration purposes

Example:

```text
[10:31:02] Experiment started
[10:31:05] PICK_CONTAINER detected
[10:31:06] Step 1 verified
[10:31:10] TILT_CONTAINER detected
[10:31:11] Step 2 verified
[10:31:16] SHAKE_CONTAINER detected
[10:31:17] Step 3 verified
```

---

# ❌ Wrong Action Detection

A key capability of ORBIT-HAR is detecting when the astronaut performs an action that does not match the expected experimental sequence.

Example:

```text
EXPECTED:
OPEN_VALVE

DETECTED:
SHAKE_CONTAINER

RESULT:
WRONG ACTION
```

The system can then:

1. Mark the current step as incorrect
2. Log the event
3. Notify the dashboard
4. Provide voice feedback
5. Continue monitoring for the expected action

This enables the system to act as an **AI-assisted procedural safety and verification layer**.

---

# 🧠 Why Sequence Validation Matters

Generic activity recognition answers:

> "What is the astronaut doing?"

ORBIT-HAR additionally asks:

> "Is this what the astronaut is supposed to be doing right now?"

That distinction is important for structured experiments.

For example:

```text
Activity Recognition:

Astronaut → shaking container
```

versus:

```text
Experiment Validation:

Expected → OPEN_VALVE
Detected → SHAKE_CONTAINER
Result   → WRONG
```

The second provides significantly more useful information for experiment monitoring.

---

# 🌌 Microgravity Considerations

Space environments introduce unique challenges compared with conventional laboratory environments.

ORBIT-HAR is designed with the following considerations in mind:

* Astronaut orientation may change
* Objects can be manipulated in non-traditional orientations
* Traditional "up/down" assumptions may not always hold
* Camera viewpoints can change
* Hand-object interaction is important
* Experiment sequence matters more than absolute scene orientation

Future versions can extend the system with orientation-agnostic 3D human pose or human mesh reconstruction.

---

# 🔒 Privacy & Data Handling

The system is designed around local processing.

Instead of requiring raw video to be continuously uploaded to an external server, the edge computer can process the camera stream locally and transmit only required information such as:

```text
Detected Action
Current Step
Experiment Status
Error Events
System Health
Timestamp
```

This can significantly reduce the amount of information that needs to leave the local processing environment.

---

# 📴 Offline Deployment

One of the major design goals of ORBIT-HAR is the ability to operate without an active Internet connection.

An offline deployment can package:

```text
ORBIT-HAR
│
├── Python Runtime
├── Python Dependencies
├── YOLO Model
├── MediaPipe
├── OpenCV
├── Backend
├── React Build
├── Experiment Configurations
├── Logs
└── Startup Scripts
```

The deployed system can then run entirely on the local machine.

---

# 📦 Installation

## 1. Clone the repository

```bash
git clone https://github.com/h1e2l3l4o5/ORBIT-HAR.git
cd ORBIT-HAR
```

Replace the repository URL with the actual GitHub repository.

---

# 🐍 2. Create a Python virtual environment

On macOS/Linux:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

On Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

---

# 📚 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

If a requirements file is not yet included:

```bash
pip install opencv-python
pip install mediapipe
pip install ultralytics
pip install fastapi
pip install uvicorn
```

---

# 🤖 4. Model Setup

The prototype uses a YOLO model such as:

```text
models/yolo11n.pt
```

The model should be available locally for offline operation.

Do not depend on automatic model downloading when deploying to a disconnected environment.

Recommended deployment structure:

```text
models/
└── yolo11n.pt
```

---

# 📷 5. Camera Test

Before starting the complete system, verify camera access.

Run:

```bash
python live_orbit_har.py
```

A successful startup should display:

```text
🚀 ORBIT-HAR camera is running
Press Q to quit
```

If the camera does not open:

* Check OS camera permissions
* Check whether another application is using the camera
* Verify the camera index
* Test the camera independently

---

# 🖥️ Running the Complete System

ORBIT-HAR consists of multiple components.

The typical development setup uses:

```text
Terminal 1 → Backend
Terminal 2 → Dashboard
Terminal 3 → AI / Camera Pipeline
```

---

# 1️⃣ Start the Backend

Open Terminal 1:

```bash
cd ORBIT-HAR
source venv/bin/activate
```

Then:

```bash
cd backend
python3 -m uvicorn main:app
```

The backend should be available locally at:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/
```

Expected response:

```json
{
  "system": "ORBIT-HAR",
  "status": "ONLINE"
}
```

---

# 2️⃣ Start the Dashboard

Open Terminal 2:

```bash
cd ORBIT-HAR/orbit-har-dashboard
npm install
npm run dev
```

The terminal will display the local dashboard URL.

Open that address in your browser.

The dashboard communicates with the backend through WebSockets.

---

# 3️⃣ Start the AI Pipeline
Not really necessary (already embedded)
Open Terminal 3:

```bash
cd ORBIT-HAR
source venv/bin/activate
```

Run:

```bash
python3 live_orbit_har.py
```

The application will:

```text
Open Camera
     ↓
Process Frames
     ↓
Detect Objects
     ↓
Track Hands
     ↓
Recognize Activity
     ↓
Validate Sequence
     ↓
Generate Event
     ↓
Send Event to Backend
```

---

# 🔧 Configuration

The recognition pipeline contains configurable parameters for controlling detection and confirmation behavior.

Typical parameters include:

```text
AI_STATUS_INTERVAL
FRAME_INTERVAL
ACTION_COOLDOWN
YOLO_EVERY_N_FRAMES
YOLO_IMAGE_SIZE
YOLO_CONFIDENCE
BOTTLE_HOLD_FRAMES
```

Action confirmation thresholds can also be configured.

These parameters help balance:

* Detection speed
* Stability
* False positives
* CPU/GPU usage
* Responsiveness

---

# ⚙️ Performance Strategy

The prototype uses several optimizations to reduce unnecessary computation.

For example:

```text
Camera
  ↓
Every frame
  ↓
Lightweight processing
  ↓
YOLO every N frames
  ↓
Action confirmation
  ↓
Event only after stable detection
```

This prevents every single frame from immediately changing the experiment state.

Temporal confirmation is especially useful because computer-vision predictions can fluctuate between frames.

---

# 🧪 Adding a New Experiment

To add another experiment:

### 1. Create a new JSON configuration

```text
experiments/
└── new_experiment.json
```

### 2. Define the experiment sequence

For example:

```json
{
  "experiment_name": "Example Experiment",
  "steps": [
    {
      "action": "PICK_OBJECT"
    },
    {
      "action": "OPEN_CONTAINER"
    },
    {
      "action": "TRANSFER_SAMPLE"
    },
    {
      "action": "CLOSE_CONTAINER"
    }
  ]
}
```

### 3. Add/extend the corresponding recognition logic

The computer-vision pipeline must be capable of identifying the actions used by the new experiment.

---

# 🧑‍🚀 Dataset Generation

A future/custom-model version of ORBIT-HAR can use experiment-specific datasets containing:

### Object Detection

Examples:

* Containers
* Valves
* Tools
* Samples
* Experimental hardware

### Pose Estimation

Human body landmarks can be used to understand:

* Arm position
* Hand position
* Body orientation
* Interaction with equipment

### Hand-Object Interaction

Interaction labels can capture:

```text
Hand → Container
Hand → Valve
Hand → Tool
Hand → Sample
```

This can improve activity recognition beyond simple object detection.

---

# 🧠 Future AI Pipeline

A more advanced version can use:

```text
Object Detection
       +
Human Pose
       +
Hand Tracking
       +
Object Tracking
       +
Temporal Modeling
       ↓
Activity Recognition
       ↓
Experiment State Machine
```

A temporal model could learn patterns across multiple frames rather than classifying actions independently.

Potential future approaches include:

* LSTM
* GRU
* Temporal Transformer
* Temporal CNN
* Video Transformer
* 3D pose-based recognition

---

# 🛰️ Future Mission Architecture

The long-term architecture can support:

```text
                 SPACECRAFT
                     │
          ┌──────────┴──────────┐
          │                     │
     Astronaut AI          Mission Control
          │                     │
       Camera                Dashboard
          │                     │
          ▼                     │
    ORBIT-HAR Edge              │
          │                     │
    ┌─────┴─────┐               │
    │           │               │
   AI       Experiment          │
Processing   Engine             │
    │           │               │
    └─────┬─────┘               │
          │                     │
       Events ──────────────────┘
```

The system can therefore separate:

### Critical processing

Runs locally:

* Camera processing
* AI inference
* Activity recognition
* Sequence validation
* Error detection

### Monitoring

Can be transmitted:

* Experiment state
* Step number
* Detected activity
* Errors
* Logs
* System health
* Optional video stream

---

# 🚀 Offline Deployment Architecture

For a fully disconnected deployment:

```text
┌───────────────────────────────────────┐
│         ORBIT-HAR EDGE COMPUTER      │
│                                       │
│  Python Runtime                       │
│  OpenCV                               │
│  MediaPipe                            │
│  YOLO Model                           │
│  FastAPI                              │
│  Experiment Config                    │
│  React Dashboard                      │
│  Local Logs                           │
│                                       │
│            ↓                          │
│          CAMERA                       │
└───────────────────────────────────────┘
```

No external API is required for the core recognition pipeline.

This makes ORBIT-HAR suitable for environments where Internet access cannot be assumed.

---

# 🔐 Security Considerations

For a production deployment, additional security mechanisms should be added.

Recommended future improvements include:

* Authentication
* Role-based access
* Encrypted communication
* Signed model files
* Secure WebSocket connections
* Audit logs
* Configuration integrity checks
* Device authentication
* Secure software updates

The current prototype focuses primarily on demonstrating the AI and experiment-monitoring architecture.

---

# 📊 Current Prototype Status

| Component                        | Status                     |
| -------------------------------- | -------------------------- |
| Camera input                     | ✅ Implemented              |
| OpenCV pipeline                  | ✅ Implemented              |
| Hand tracking                    | ✅ Implemented              |
| YOLO integration                 | ✅ Implemented              |
| Activity recognition             | ✅ Implemented              |
| Experiment sequence              | ✅ Implemented              |
| Wrong-action detection           | ✅ Implemented              |
| Experiment configuration         | ✅ Implemented              |
| Voice feedback                   | ✅ Implemented              |
| Local event logging              | ✅ Implemented              |
| FastAPI backend                  | ✅ Implemented              |
| WebSocket communication          | ✅ Implemented              |
| React dashboard                  | ✅ Implemented              |
| Edge/local processing            | ✅ Implemented              |
| Offline architecture             | 🟡 Deployment-ready design |
| Custom experiment datasets       | 🔄 Extensible              |
| Custom-trained experiment model  | 🔄 Future enhancement      |
| Advanced 3D orientation handling | 🔄 Future enhancement      |
| Production-grade security        | 🔄 Future enhancement      |

---

# 🛠️ Troubleshooting

## Camera does not open

Check camera permissions in the operating system.

On macOS:

```text
System Settings
→ Privacy & Security
→ Camera
```

Make sure the terminal/application running Python has permission.

---

## Backend shows "Address already in use"

Check which process is using port `8000`.

On macOS/Linux:

```bash
lsof -i :8000
```

Terminate the process if necessary:

```bash
kill <PID>
```

Then restart:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## Dashboard says Backend Offline

First verify:

```bash
curl http://127.0.0.1:8000/
```

If the backend is running, check that the dashboard WebSocket is configured for:

```text
ws://127.0.0.1:8000/ws
```

---

## YOLO model cannot be found

Verify that the model exists locally:

```text
models/
└── yolo11n.pt
```

If deploying offline, ensure the model is copied with the application.

---

## Detection is unstable

Possible improvements:

* Increase confidence threshold
* Increase temporal confirmation frames
* Adjust frame sampling
* Improve camera positioning
* Improve lighting
* Add object tracking
* Train an experiment-specific model

---

# 🧪 Testing

Before a demonstration, test the system in this order:

### Test 1 — Camera

```bash
python camera.py
```

### Test 2 — Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Test 3 — Backend health

```bash
curl http://127.0.0.1:8000/
```

### Test 4 — Dashboard

```bash
cd dashboard
npm run dev
```

### Test 5 — AI pipeline

```bash
python live_orbit_har.py
```

### Test 6 — Complete experiment

Perform the experiment in the correct sequence.

### Test 7 — Wrong-action detection

Intentionally perform an incorrect action and verify:

```text
Detected Action ≠ Expected Action
             ↓
          WRONG
             ↓
        Dashboard
             +
          Log
             +
      Voice Feedback
```

---

# 🎬 Demonstration Flow

A recommended ORBIT-HAR demonstration is:

```text
1. Start the edge computer

2. Start ORBIT-HAR

3. Camera becomes active

4. Dashboard shows:
   EDGE SYSTEM ONLINE

5. Start Liquid Sample Transfer

6. Astronaut picks up container

7. ORBIT-HAR detects:
   PICK_CONTAINER

8. Dashboard updates:
   Step 1 VERIFIED

9. Astronaut tilts container

10. ORBIT-HAR detects:
    TILT_CONTAINER

11. Dashboard updates:
    Step 2 VERIFIED

12. Perform an incorrect action

13. ORBIT-HAR detects mismatch

14. Dashboard shows:
    WRONG ACTION

15. Voice feedback is generated

16. Continue with the correct action

17. Experiment proceeds

18. Final step completes

19. Experiment status:
    COMPLETE
```

This demonstrates that ORBIT-HAR is not simply detecting objects — it is **understanding and validating an experiment workflow**.

---

# 🌍 Applications

Although initially designed for on-board space experiments, the architecture can be adapted to other environments.

Potential applications include:

* Space missions
* Laboratory automation
* Remote experiments
* Industrial procedure monitoring
* Manufacturing
* Medical procedure assistance
* Hazardous environments
* Remote maintenance
* Training systems
* Autonomous robotic operations

---

# 🔭 Future Roadmap

## Phase 1 — Prototype

* [x] Camera pipeline
* [x] YOLO integration
* [x] Hand tracking
* [x] Activity recognition
* [x] Sequence validation
* [x] Wrong-action detection
* [x] Backend
* [x] Dashboard
* [x] Logging
* [x] Voice feedback

## Phase 2 — Robust AI

* [x] Custom experiment dataset
* [x] Custom YOLO training
* [x] Improved object tracking
* [x] Temporal activity recognition
* [x] Better hand-object interaction
* [x] Robust orientation handling

## Phase 3 — Edge Deployment

* [x] Complete offline packaging
* [x] Automated installation
* [x] One-command startup
* [x] Hardware optimization
* [x] GPU/accelerator support
* [x] Resource monitoring

## Phase 4 — Mission Control

* [x] Remote mission-control client
* [x] Live camera stream
* [x] Remote experiment monitoring
* [x] Event synchronization
* [ ] Network interruption recovery
* [ ] Secure communication

## Phase 5 — Advanced Space AI

* [x] Orientation-agnostic 3D human pose
* [x] Human mesh reconstruction
* [x] Multi-camera support
* [ ] Autonomous experiment recovery
* [x] Long-duration autonomous monitoring
* [ ] Multi-experiment management

---

# 🏆 What Makes ORBIT-HAR Different?

Traditional computer vision systems may answer:

```text
"What objects are visible?"
```

Activity recognition systems may answer:

```text
"What is the astronaut doing?"
```

ORBIT-HAR goes one step further:

```text
"What is the astronaut doing,
and is that action correct for the
current stage of the experiment?"
```

This enables ORBIT-HAR to function as an **AI experiment-monitoring and procedural-validation system** rather than simply an object detector.

---

# 💡 Design Philosophy

ORBIT-HAR follows three main principles:

### 1. Edge First

AI processing should happen as close to the experiment as possible.

### 2. Sequence Aware

Actions should be interpreted in the context of the experiment.

### 3. Human Assistive

The system should assist the astronaut and mission-control team rather than replace human oversight.

---

# 👨‍💻 Development

Clone the repository:

```bash
git clone https://github.com/h1e2l3l4o5/ORBIT-HAR.git
cd ORBIT-HAR
```

Create the environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Start the dashboard:

```bash
cd dashboard
npm install
npm run dev
```

Start the AI pipeline:

```bash
python live_orbit_har.py
```

---

# 🤝 Contributing

Contributions are welcome.

A typical contribution workflow:

```bash
git checkout -b feature/new-feature
```

Make your changes, test them, then:

```bash
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
```

Open a Pull Request on GitHub.

---

# 📜 License

Add the project's chosen license here.

For example:

```text
MIT License
```

If this project is being submitted under a competition or institutional program, ensure that the selected license is compatible with the applicable rules before publishing.

---

# 👩‍🚀 Project

## ORBIT-HAR

**AI Human Activity Recognition for On-Board BAS Experiments**

Designed as an edge-AI experiment monitoring system for structured experiments in space environments.

```text
             🚀 ORBIT-HAR

     Observe → Understand → Validate

          CAMERA
             ↓
       COMPUTER VISION
             ↓
      ACTIVITY RECOGNITION
             ↓
       SEQUENCE ENGINE
             ↓
     EXPERIMENT VALIDATION
             ↓
       MISSION MONITOR
```

---

# 💻 OFFLINE WINDOWS DEPLOYMENT (SIH DEMONSTRATION)

This guide explains how to prepare, verify, and run the complete **ORBIT-HAR** system offline on a Windows laptop for live demonstrations with **zero internet connection**.

---

## 📋 A. One-Time Setup (While Internet is Available)

Before arriving at the demonstration venue, complete these steps once:

1. Clone or copy the ORBIT-HAR repository to your laptop.
2. Double-click **`setup.bat`** (or run `.\setup.bat` in Command Prompt).
3. The setup script will automatically:
   - Check your Python and Node.js installations.
   - Create a Python virtual environment (`.venv`).
   - Install all required Python packages (`opencv-python`, `mediapipe==0.10.14`, `ultralytics`, `fastapi`, `uvicorn`, `websockets`, `matplotlib`, `numpy`).
   - Download the YOLO11n weights (`yolo11n.pt`) and place them in `camera/` and `models/`.
   - Install npm packages in `orbit-har-dashboard/`.
   - Build the production React frontend bundle in `orbit-har-dashboard/dist/`.
   - Populate the offline wheel cache in `wheels/` for offline portability.

---

## 🛠️ B. Required Software

* **Operating System**: Windows 10 or Windows 11 (64-bit)
* **Python**: Python 3.10 or 3.11 ([python.org](https://www.python.org/downloads/)) — *Must check "Add Python to PATH" during installation*
* **Node.js**: Node.js v18, v20, or v22 LTS ([nodejs.org](https://nodejs.org/))
* **Webcam**: Built-in laptop webcam or external USB webcam

---

## 📦 C. Required Downloads & Offline Files

All of these are automatically downloaded and cached by `setup.bat`:

| File / Folder | Purpose | Local Path |
|---|---|---|
| `models/yolo11n.pt` & `camera/yolo11n.pt` | YOLO11 Object Detection Weights (~5.4 MB) | `camera/yolo11n.pt` |
| `wheels/*.whl` | Pre-downloaded Python wheels cache | `wheels/` |
| `orbit-har-dashboard/node_modules/` | Installed frontend npm packages | `orbit-har-dashboard/node_modules` |
| `orbit-har-dashboard/dist/` | Compiled production dashboard bundle | `orbit-har-dashboard/dist` |

---

## ⌨️ D. Installation Commands (Manual Alternative)

If you prefer running commands manually instead of `setup.bat`:

```powershell
# 1. Create and activate Python virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies (from offline wheels if available, or online)
pip install -r requirements.txt matplotlib

# 3. Setup YOLO weights
python -c "import os, shutil; from ultralytics import YOLO; model = YOLO('yolo11n.pt'); os.makedirs('models', exist_ok=True); shutil.copy('yolo11n.pt', 'models/yolo11n.pt'); shutil.copy('yolo11n.pt', 'camera/yolo11n.pt')"

# 4. Install and build frontend
cd orbit-har-dashboard
npm install
npm run build
cd ..
```

---

## ✅ E. How to Verify Installation

Run the offline verification test:

```powershell
.\.venv\Scripts\python.exe -c "from ultralytics import YOLO; import mediapipe as mp, cv2, fastapi, uvicorn, websockets; print('All ML/CV/Web libraries verified!')"
```

Expected output:
```text
All ML/CV/Web libraries verified!
```

---

## ✈️ F. How to Disconnect from Internet (SIH Simulation)

1. Turn off Wi-Fi on your laptop (or enable Airplane Mode).
2. Unplug any Ethernet cable.
3. Verify that your browser cannot reach google.com.

---

## 🚀 G. How to Start the Application (Offline)

Simply **double-click `start.bat`**.

This launches:
1. **FastAPI Backend**: `http://127.0.0.1:8000`
2. **React Dashboard**: `http://localhost:5173`
3. Automatically opens your default web browser to the Mission Control dashboard.

### During the Live Presentation:
1. **Monitoring Page (`/`)**: Displays the live camera feed, AI object detection states, hand-tracking indicators, and step validation status.
2. **Experiments Page (`/experiments`)**:
   - **Container Orientation Experiment**: YOLO11n + MediaPipe hand tracking for bottle manipulation sequence.
   - **Syringe Liquid Transfer**: Color + Hough geometry + hand tracking for liquid transfer.
   - **Seed Sorting Experiment**: Real-time red/blue seed placement validation.
3. **3D Human Mesh (`/human-mesh`)**: Click `START HUMAN 3D` to stream real-time 3D pose landmarks on port 8010.
4. **Logs & Videos (`/logs`, `/videos`, `/text-files`)**: View real-time experiment logs, recordings, and raw text outputs.

---

## 🛑 H. How to Stop the Application

Double-click **`stop.bat`** (or run `.\stop.bat`).

This cleanly terminates all background processes on ports 8000, 8010, and 5173.

---

## 🔌 J. Ports Used by Components

| Port | Service | Protocol | Description |
|---|---|---|---|
| `8000` | FastAPI Backend | HTTP & WS | REST API (`/event`, `/frame`, `/video`, `/logs`), WebSocket (`/ws`) |
| `5173` | Frontend Dashboard | HTTP | React / Vite UI |
| `8010` | 3D Human Mesh Server | HTTP | MediaPipe 3D projection & video streams (`/mesh`, `/video`) |

---

## 📁 K. Folder Structure

```text
orbit-har/
├── setup.bat                 # One-time preparation script
├── start.bat                 # 1-click offline launcher
├── stop.bat                  # 1-click process cleanup
├── requirements.txt          # Python dependency specifications
├── .env.example              # Environment defaults
├── backend/
│   ├── main.py               # FastAPI backend entrypoint & router
│   ├── recording.py          # Video recorder and log manager
│   └── logs/                 # Experiment history jsonl files
├── camera/
│   ├── live_orbit_har.py     # Container Orientation AI engine
│   ├── orbit_har_syringe.py  # Syringe Liquid Transfer AI engine
│   ├── firdous_experiment.py # Seed Sorting AI engine
│   ├── calibrate.py          # HSV color calibration tool
│   ├── logger.py             # File logging helper
│   ├── yolo11n.pt            # Pre-downloaded YOLO11 weights
│   └── experiments/          # JSON sequence configuration files
├── human_mesh/
│   └── mediapipe_3d_viewer.py# 3D Human Pose Mesh server (Port 8010)
├── models/
│   └── yolo11n.pt            # Local weights archive
├── wheels/                   # Offline Python wheels cache
└── orbit-har-dashboard/      # React 19 frontend
    ├── package.json
    ├── vite.config.js
    ├── dist/                 # Production compiled assets
    └── src/
        ├── pages/            # Monitoring, Experiments, Logs, etc.
        └── hooks/            # useOrbitSocket (WebSocket connection)
```

---

## ❓ I. Troubleshooting

* **"Camera OFFLINE" shown on dashboard**:
  - Make sure you clicked "Start Experiment" on the **Experiments** tab. The camera subprocess starts dynamically for the selected experiment.
  - If using an external USB webcam, ensure camera index 0 is available or adjust `CAMERA_INDEX = 0` in the experiment file.
* **"Port already in use" error**:
  - Run `stop.bat` to terminate any previous background instances, then run `start.bat` again.
* **Voice assistant audio silent**:
  - Ensure laptop volume is turned up; browser speech synthesis (`window.speechSynthesis`) is fully offline and does not require internet.



