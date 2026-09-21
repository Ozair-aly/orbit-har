import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import cv2
import asyncio
import time
import json
from datetime import datetime
import numpy as np
import subprocess
 
from recording import router as recording_router, recording_manager

CLOUD_MODE = os.environ.get("CLOUD_MODE", "false").lower() in ("true", "1", "yes")

app = FastAPI(title="ORBIT-HAR Backend")
 
# ==========================================
# RECORDING / VIDEOS / LOGS ROUTES
# ==========================================
 
app.include_router(recording_router)
 
 
# ==========================================
# CORS
# ==========================================
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
# ==========================================
# GLOBAL STATE
# ==========================================
 
connected_clients = []
 
latest_frame = None
 
# Time when the last camera frame was received
last_frame_time = 0
 
# Camera considered alive if a frame arrived recently
CAMERA_TIMEOUT = 1.5
 
 
# ==========================================
# LOG PERSISTENCE
#
# This is the single source of truth for the /logs endpoint
# (served from recording.py). We persist here -- in the backend --
# instead of in the camera script, so there's no ambiguity about
# which working directory the log file lives in.
# ==========================================
 
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "experiment_log.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)
 
 
def persist_log_entry(data: dict):
    event_type = data.get("type")
    entry = None
 
    if event_type == "step_verified":
        entry = {
            "experiment": data.get("experiment"),
            "step": data.get("completed_step"),
            "action": data.get("completed_instruction") or data.get("completed_action") or "STEP COMPLETED",
            "status": "SUCCESS",
        }
 
    elif event_type == "experiment_complete":
        entry = {
            "experiment": data.get("experiment"),
            "step": data.get("total_steps"),
            "action": "EXPERIMENT COMPLETED",
            "status": "SUCCESS",
        }
 
    elif event_type == "action_detected" and data.get("status") == "WRONG":
        entry = {
            "experiment": data.get("experiment"),
            "step": data.get("step"),
            "action": data.get("detected_action"),
            "status": "WRONG",
        }
 
    if entry is None:
        # ai_status / camera_status / CHECKING events aren't
        # meaningful history entries, so skip persisting those.
        return
 
    entry["time"] = datetime.now().strftime("%H:%M:%S")
 
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
 
 
# ==========================================
# CAMERA STATUS
# ==========================================
 
def is_camera_active():
 
    global last_frame_time
 
    if last_frame_time == 0:
        return False
 
    return (
        time.time() - last_frame_time
    ) < CAMERA_TIMEOUT
 
 
# ==========================================
# ROOT
# ==========================================
 
@app.get("/")
def root():
 
    return {
        "system": "ORBIT-HAR",
        "status": "ONLINE",
        "camera": "ONLINE" if is_camera_active() else "OFFLINE"
    }
 
 
# ==========================================
# WEBSOCKET
# ==========================================
 
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
 
    await websocket.accept()
 
    connected_clients.append(websocket)
 
    print("🟢 Dashboard connected")
 
    try:
 
        while True:
 
            await websocket.receive_text()
 
    except Exception:
 
        if websocket in connected_clients:
            connected_clients.remove(websocket)
 
        print("🔴 Dashboard disconnected")
 
 
# ==========================================
# BROADCAST EVENTS
# ==========================================
 
async def broadcast(data):
 
    disconnected = []
 
    for client in connected_clients:
 
        try:
 
            await client.send_json(data)
 
        except Exception:
 
            disconnected.append(client)
 
    for client in disconnected:
 
        if client in connected_clients:
            connected_clients.remove(client)
 
 
# ==========================================
# EXPERIMENT EVENTS
# ==========================================
 
@app.post("/event")
async def receive_event(data: dict):

    print("📡 EVENT RECEIVED:", data)

    persist_log_entry(data)

    await broadcast(data)

    # TEST DASHBOARD VOICE
    

    return {
        "status": "received"
    }
# ==========================================
# VOICE BROADCAST
# ==========================================

@app.post("/voice")
async def voice_event(data: dict):

    message = data.get("message", "").strip()

    if not message:
        return {
            "status": "error",
            "message": "Voice message is empty"
        }

    print("🔊 VOICE:", message)

    await broadcast({
        "type": "voice",
        "message": message,
    })

    return {
        "status": "sent",
        "message": message,
    }
 # ==========================================
# ACTIVE EXPERIMENT
# ==========================================
# ==========================================
# EXPERIMENT PYTHON SCRIPTS
# ==========================================

EXPERIMENT_SCRIPTS = {
    "Container Orientation Experiment":
        "live_orbit_har.py",

    "Syringe Liquid Transfer":
        "orbit_har_syringe.py",

    "Seed Sorting Experiment":
        "firdous_experiment.py",
}
active_experiment = None

experiment_process = None
# ==========================================
# HUMAN 3D MESH PROCESS
# ==========================================

human_mesh_process = None

HUMAN_MESH_SCRIPT = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "human_mesh",
    "mediapipe_3d_viewer.py"
)
# ==========================================
# START HUMAN 3D MESH
# ==========================================

@app.post("/human-mesh/start")
async def start_human_mesh():

    global human_mesh_process

    if CLOUD_MODE:
        return {
            "status": "error",
            "message": "3D Human Mesh requires local camera and display hardware and is only available in local/offline mode.",
        }

    # Already running
    if (
        human_mesh_process is not None
        and human_mesh_process.poll() is None
    ):
        return {
            "status": "already_running",
            "message": "Human 3D Mesh is already running",
            "url": "http://127.0.0.1:8010",
        }

    # Check Python file
    if not os.path.exists(HUMAN_MESH_SCRIPT):

        return {
            "status": "error",
            "message": (
                f"Human Mesh script not found: "
                f"{HUMAN_MESH_SCRIPT}"
            )
        }

    print("\n==============================================")
    print("🚀 STARTING ORBIT-HAR HUMAN 3D MESH")
    print("==============================================")
    print("Python:", sys.executable)
    print("Script:", HUMAN_MESH_SCRIPT)

    try:

        human_mesh_process = subprocess.Popen(
            [
                sys.executable,
                HUMAN_MESH_SCRIPT
            ],
            cwd=os.path.dirname(HUMAN_MESH_SCRIPT)
        )
        # ==========================================
        # WAIT FOR HUMAN 3D SERVER
        # ==========================================

        import socket

        server_ready = False

        for _ in range(30):

            try:

                with socket.create_connection(
                    ("127.0.0.1", 8010),
                    timeout=0.5
                ):

                    server_ready = True
                    break

            except OSError:

                await asyncio.sleep(0.5)


        if server_ready:

            print("🟢 Human 3D server is READY on port 8010")

        else:

            print("🔴 Human 3D server did not become ready")

        print(
            "🧍 Human 3D Mesh started | PID:",
            human_mesh_process.pid
        )

        await broadcast({
            "type": "human_mesh_status",
            "status": "STARTING",
            "url": "http://127.0.0.1:8010",
        })

        return {
            "status": "started",
            "message": "Human 3D Mesh started",
            "pid": human_mesh_process.pid,
            "url": "http://127.0.0.1:8010",
        }

    except Exception as e:

        print(
            "❌ Failed to start Human 3D Mesh:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }
# ==========================================
# STOP HUMAN 3D MESH
# ==========================================

@app.post("/human-mesh/stop")
async def stop_human_mesh():

    global human_mesh_process

    if (
        human_mesh_process is None
        or human_mesh_process.poll() is not None
    ):

        human_mesh_process = None

        return {
            "status": "already_stopped",
            "message": "Human 3D Mesh is not running"
        }

    print("\n==============================================")
    print("🛑 STOPPING ORBIT-HAR HUMAN 3D MESH")
    print("==============================================")

    try:

        human_mesh_process.terminate()

        try:

            human_mesh_process.wait(
                timeout=3
            )

        except subprocess.TimeoutExpired:

            print(
                "⚠️ Human Mesh did not stop gracefully."
                " Killing process..."
            )

            human_mesh_process.kill()
            human_mesh_process.wait()

        print("🛑 Human 3D Mesh stopped.")

        human_mesh_process = None

        await broadcast({
            "type": "human_mesh_status",
            "status": "STOPPED",
        })

        return {
            "status": "stopped",
            "message": "Human 3D Mesh stopped"
        }

    except Exception as e:

        print(
            "❌ Failed to stop Human 3D Mesh:",
            e
        )

        return {
            "status": "error",
            "message": str(e)
        }
# ==========================================
# HUMAN 3D MESH STATUS
# ==========================================

@app.get("/human-mesh/status")
def human_mesh_status():

    global human_mesh_process

    running = (
        human_mesh_process is not None
        and human_mesh_process.poll() is None
    )

    return {
        "running": running,
        "status": "ONLINE" if running else "OFFLINE",
        "url": "http://127.0.0.1:8010",
    }
# ==========================================
# START EXPERIMENT
# ==========================================

@app.post("/experiment/start")
async def start_experiment(data: dict):

    global active_experiment
    global experiment_process

    if CLOUD_MODE:
        return {
            "status": "error",
            "message": "Physical experiment AI camera tracking requires a local webcam/hardware and is only available in local/offline mode.",
        }

    experiment_name = data.get(
        "name",
        "Unknown Experiment"
    )

    steps = data.get(
        "steps",
        []
    )

    # ==========================================
    # FIND PYTHON SCRIPT
    # ==========================================

    script_name = EXPERIMENT_SCRIPTS.get(
        experiment_name
    )

    if script_name is None:

        return {
            "status": "error",
            "message": (
                f"No Python script configured "
                f"for {experiment_name}"
            )
        }

    # ==========================================
    # STOP PREVIOUS EXPERIMENT
    # ==========================================

    if (
        experiment_process is not None
        and experiment_process.poll() is None
    ):

        print(
            "🛑 Stopping previous experiment..."
        )

        experiment_process.terminate()

        try:
            experiment_process.wait(
                timeout=3
            )
        except subprocess.TimeoutExpired:
            experiment_process.kill()

    # ==========================================
    # SAVE ACTIVE EXPERIMENT
    # ==========================================

    active_experiment = data

    # ==========================================
    # PYTHON SCRIPT PATH
    # ==========================================

    # ==========================================
    # ==========================================
    # PYTHON SCRIPT PATH
    # ==========================================

    PROJECT_ROOT = os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )

    CAMERA_DIR = os.path.join(
        PROJECT_ROOT,
        "camera"
    )

    script_path = os.path.join(
        CAMERA_DIR,
        script_name
    )

    # ==========================================
    # CHECK SCRIPT EXISTS
    # ==========================================

    if not os.path.exists(script_path):

        return {
            "status": "error",
            "message": (
                f"Python file not found: "
                f"{script_path}"
            )
        }

    # ==========================================
    # START PYTHON EXPERIMENT
    # ==========================================

    print(
        "\n🚀 STARTING PYTHON EXPERIMENT"
    )

    print(
        "Experiment:",
        experiment_name
    )

    print(
        "Python file:",
        script_path
    )

    experiment_process = subprocess.Popen(
        [
            sys.executable,
            script_path
        ],
        cwd=CAMERA_DIR
    )

    # ==========================================
    # INFORM DASHBOARD
    # ==========================================

    await broadcast({

        "type":
            "experiment_started",

        "experiment":
            experiment_name,

        "steps":
            steps,

        "total_steps":
            len(steps),

    })

    return {

        "status":
            "started",

        "experiment":
            experiment_name,

        "script":
            script_name,

        "total_steps":
            len(steps),

    }

@app.post("/experiment/stop")
async def stop_experiment():

    global experiment_process
    global active_experiment

    print()
    print("🛑 STOP REQUEST RECEIVED FROM DASHBOARD")
    print("==========================================")

    print(
        "Process:",
        experiment_process
    )

    # No process
    if experiment_process is None:

        print("⚠️ experiment_process is None")

        return {
            "status": "already_stopped",
            "message": "No experiment process exists"
        }

    # Process already dead
    if experiment_process.poll() is not None:

        print(
            "⚠️ Experiment already stopped.",
            "Return code:",
            experiment_process.returncode
        )

        experiment_process = None
        active_experiment = None

        return {
            "status": "already_stopped",
            "message": "Experiment was already stopped"
        }

    # Process is alive
    print(
        "🔴 TERMINATING EXPERIMENT PID:",
        experiment_process.pid
    )

    try:

        experiment_process.terminate()

        print("⏳ Waiting for experiment to stop...")

        try:

            experiment_process.wait(timeout=3)

        except subprocess.TimeoutExpired:

            print(
                "⚠️ Did not stop within 3 seconds."
            )

            print(
                "🔪 FORCE KILLING PID:",
                experiment_process.pid
            )

            experiment_process.kill()
            experiment_process.wait()

        print("✅ EXPERIMENT PROCESS STOPPED")

        experiment_process = None
        active_experiment = None

        await broadcast({
            "type": "experiment_stopped",
            "status": "STOPPED"
        })

        return {
            "status": "stopped",
            "message": "Experiment stopped successfully"
        }

    except Exception as e:

        print(
            "❌ STOP ERROR:",
            repr(e)
        )

        return {
            "status": "error",
            "message": str(e)
        }
# ==========================================
# CAMERA FRAME
# ==========================================
 
@app.post("/frame")
async def receive_frame(request: Request):
 
    global latest_frame
    global last_frame_time
 
    try:
 
        frame_bytes = await request.body()
 
        if frame_bytes:
 
            array = np.frombuffer(
                frame_bytes,
                dtype=np.uint8
            )
 
            frame = cv2.imdecode(
                array,
                cv2.IMREAD_COLOR
            )
 
            if frame is not None:
 
                latest_frame = frame
 
                # Mark camera as alive
                last_frame_time = time.time()
 
                # Feed the frame to the recorder (no-op unless
                # a recording is currently in progress)
                recording_manager.write_frame(frame)
 
        return {
            "status": "received"
        }
 
    except Exception as e:
 
        print("❌ FRAME ERROR:", e)
 
        return {
            "status": "error"
        }
 
 
# ==========================================
# CAMERA STATUS API
# ==========================================
 
@app.get("/camera/status")
def camera_status():
 
    active = is_camera_active()
 
    return {
        "active": active,
        "status": "ONLINE" if active else "OFFLINE"
    }
 
 
# ==========================================
# OFFLINE CAMERA FRAME
# ==========================================
 
def create_offline_frame():
 
    frame = np.zeros(
        (480, 640, 3),
        dtype=np.uint8
    )
 
    cv2.putText(
        frame,
        "ORBIT-HAR",
        (220, 210),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (150, 150, 150),
        2
    )
 
    cv2.putText(
        frame,
        "CAMERA OFFLINE",
        (190, 260),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (80, 80, 80),
        2
    )
 
    cv2.putText(
        frame,
        "Start live_orbit_har.py",
        (175, 310),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (80, 80, 80),
        2
    )
 
    return frame
 
 
# ==========================================
# VIDEO STREAM
# ==========================================
 
def generate_frames():
 
    global latest_frame
 
    while True:
 
        # ==================================
        # CAMERA OFFLINE
        # ==================================
 
        if not is_camera_active():
 
            offline_frame = create_offline_frame()
 
            success, buffer = cv2.imencode(
                ".jpg",
                offline_frame
            )
 
            if success:
 
                frame = buffer.tobytes()
 
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
 
            time.sleep(0.5)
 
            continue
 
 
        # ==================================
        # CAMERA ONLINE
        # ==================================
 
        if latest_frame is None:
 
            time.sleep(0.05)
 
            continue
 
 
        success, buffer = cv2.imencode(
            ".jpg",
            latest_frame
        )
 
        if not success:
 
            time.sleep(0.01)
 
            continue
 
 
        frame = buffer.tobytes()
 
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame
            + b"\r\n"
        )
 
        time.sleep(0.01)
 
 
# ==========================================
# VIDEO ENDPOINT
# ==========================================
 
@app.get("/video")
def video_feed():
 
    return StreamingResponse(
        generate_frames(),
        media_type=(
            "multipart/x-mixed-replace;"
            "boundary=frame"
        )
    )
# ==========================================
# TEXT FILE LOGS
# ==========================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

CAMERA_LOG_DIR = os.path.join(
    PROJECT_ROOT,
    "camera",
    "logs"
)


# ------------------------------------------
# LIST TEXT FILES
# ------------------------------------------

@app.get("/text-files")
def get_text_files():

    if not os.path.exists(CAMERA_LOG_DIR):
        return {
            "status": "error",
            "message": "Camera logs directory not found",
            "files": []
        }

    files = []

    for filename in os.listdir(CAMERA_LOG_DIR):

        file_path = os.path.join(
            CAMERA_LOG_DIR,
            filename
        )

        if (
            os.path.isfile(file_path)
            and filename.lower().endswith(
                (".txt", ".log")
            )
        ):

            stat = os.stat(file_path)

            files.append({
                "name": filename,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(
                    stat.st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
            })

    files.sort(
        key=lambda x: x["modified"],
        reverse=True
    )

    return {
        "status": "success",
        "directory": CAMERA_LOG_DIR,
        "files": files
    }


# ------------------------------------------
# READ ONE TEXT FILE
# ------------------------------------------

@app.get("/text-files/{filename}")
def read_text_file(filename: str):

    # Prevent paths such as ../../something
    safe_name = os.path.basename(filename)

    file_path = os.path.join(
        CAMERA_LOG_DIR,
        safe_name
    )

    if not os.path.isfile(file_path):
        return {
            "status": "error",
            "message": "Text file not found"
        }

    if not safe_name.lower().endswith(
        (".txt", ".log")
    ):
        return {
            "status": "error",
            "message": "Only text log files are allowed"
        }

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="replace"
        ) as f:

            content = f.read()

        return {
            "status": "success",
            "name": safe_name,
            "content": content
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ==========================================
# ENTRYPOINT (RENDER & DIRECT EXECUTION)
# ==========================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0" if CLOUD_MODE else "127.0.0.1")
    uvicorn.run("main:app", host=host, port=port, reload=False)