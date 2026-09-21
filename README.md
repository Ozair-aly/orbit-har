# 🚀 ORBIT-HAR

## AI Human Activity Recognition for On-Board BAS Experiments

ORBIT-HAR is an edge-AI based Human Activity Recognition and Experiment Monitoring system designed for astronaut-assisted experiments in space environments.

The system uses computer vision and AI to monitor predefined experimental procedures, detect objects and hand interactions, recognize experiment actions, validate the correct sequence, identify wrong or out-of-sequence actions, and provide real-time feedback through a mission-control dashboard.

The core AI processing runs locally on the astronaut-side system, while the mission-control dashboard receives experiment status, AI events, logs, and live camera monitoring through the ORBIT-HAR backend.

---

## ✨ Key Features

- 🎥 Live astronaut-side camera monitoring
- 🤖 YOLO-based object detection
- ✋ MediaPipe hand tracking
- 🧠 AI-based activity/action recognition
- 🔄 Predefined experiment sequence validation
- ⚠️ Wrong-action and out-of-sequence detection
- 📊 Real-time mission-control dashboard
- 🌐 Live camera streaming to the dashboard
- 📡 FastAPI backend communication
- 🔌 WebSocket-based live dashboard updates
- 📝 Experiment logging
- 🔊 Voice feedback
- 🛑 Dashboard-based experiment stopping
- 🛰️ Local edge processing
- 🧩 Configurable experiment definitions
- 🧍 Human/pose experimentation support
- 💻 Browser-based monitoring interface

---

# 🛰️ System Architecture

```text
                    ASTRONAUT-SIDE SYSTEM
                    =====================

                         Camera
                           │
                           ▼
                    ┌───────────────┐
                    │   OpenCV      │
                    │ Camera Capture │
                    └───────┬───────┘
                            │
                            ▼
                ┌───────────────────────┐
                │     ORBIT-HAR AI      │
                │                       │
                │ YOLO Object Detection │
                │ MediaPipe Hand Track  │
                │ Motion Analysis       │
                │ Action Recognition    │
                │ Sequence Validation   │
                └───────────┬───────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        AI Events       Live Frames     Logs
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                    ┌───────────────┐
                    │ FastAPI       │
                    │ Backend       │
                    └───────┬───────┘
                            │
                  WebSocket / HTTP
                            │
                            ▼
                 ┌────────────────────┐
                 │ Mission-Control    │
                 │ React Dashboard    │
                 └────────────────────┘
💻 Requirements

Before running ORBIT-HAR, make sure the system has:

Python 3.9+
Node.js 18+
npm
Git
A working camera
macOS / Linux / Windows

Camera permissions must be enabled for the application/Python process.

📥 Clone the Repository

Open a terminal and run:

git clone https://github.com/h1e2l3l4o5/ORBIT-HAR.git

Then enter the project:

cd ORBIT-HAR
🐍 Backend / AI Environment Setup

Create a Python virtual environment:

python3 -m venv venv

Activate it.

macOS / Linux
source venv/bin/activate
Windows
venv\Scripts\activate
📦 Install Python Dependencies

Install all Python dependencies using:

pip install -r requirements.txt

The requirements file contains the dependencies required by the ORBIT-HAR Python components, including:

OpenCV
MediaPipe
Ultralytics
Requests
FastAPI
Uvicorn
WebSockets
🤖 YOLO Model

ORBIT-HAR uses an Ultralytics YOLO model for object detection.

The model file is intentionally not included in the Git repository because ML model files can be large.

Download the required model before running the AI pipeline.

For the current prototype, the expected model is:

yolo11n.pt

Place it where live_orbit_har.py expects it.

For example:

ORBIT-HAR/
│
├── yolo11n.pt
├── camera/
├── backend/
└── orbit-har-dashboard/
🌐 Dashboard Setup

Open another terminal.

Go to the dashboard:

cd orbit-har-dashboard

Install Node dependencies:

npm install

Start the development server:

npm run dev

The terminal will display a local address similar to:

http://localhost:5173

Open that address in your browser.

⚙️ Start the ORBIT-HAR Backend

Open another terminal.

From the project root:

cd ORBIT-HAR

Activate the Python environment:

source venv/bin/activate

Then start FastAPI:

uvicorn backend.main:app --host 127.0.0.1 --port 8000

The backend should become available at:

http://127.0.0.1:8000

You can check it by opening:

http://127.0.0.1:8000

The backend should report that ORBIT-HAR is online.

🎥 Start the AI Camera System

Open another terminal.

From the project root:

source venv/bin/activate

Then:

python camera/live_orbit_har.py

The ORBIT-HAR AI pipeline will:

Open the camera
Capture live frames
Run YOLO object detection
Track hands using MediaPipe
Detect hand-container interaction
Analyze movement
Determine the current experiment action
Verify the action against the expected experiment step
Send experiment events to the backend
Send the live camera feed to the dashboard
Update the monitoring dashboard in real time
🖥️ Running the Complete System

ORBIT-HAR currently uses three processes.

You should have three terminals open.

Terminal 1 — Backend
cd ORBIT-HAR
source venv/bin/activate

uvicorn backend.main:app --host 127.0.0.1 --port 8000
Terminal 2 — Dashboard
cd ORBIT-HAR/orbit-har-dashboard

npm install
npm run dev
Terminal 3 — AI / Camera
cd ORBIT-HAR
source venv/bin/activate

python camera/live_orbit_har.py

Then open the dashboard URL shown by Vite.
