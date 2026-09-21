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
