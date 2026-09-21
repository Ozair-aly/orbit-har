"""
recording.py

Recording + video/log listing support for the ORBIT-HAR backend.

This is written as a standalone, mergeable module. It assumes your
existing backend is FastAPI (matching the /event, /frame, /ws,
/camera/status, /video endpoints the frontend already calls).

------------------------------------------------------------------
HOW TO WIRE THIS IN
------------------------------------------------------------------

1. Drop this file next to your existing backend main file.

2. In your main FastAPI app file:

       from recording import router as recording_router, recording_manager

       app.include_router(recording_router)

3. Find your existing "/frame" endpoint (the one that receives JPEG
   bytes posted from orbit_har_syringe.py's send_frame()). Add a
   single call so recorded frames actually get written:

       import cv2
       import numpy as np

       @app.post("/frame")
       async def receive_frame(request: Request):
           body = await request.body()

           # ... your existing logic that stores/streams `body` ...

           if recording_manager.is_recording():
               arr = np.frombuffer(body, dtype=np.uint8)
               img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
               if img is not None:
                   recording_manager.write_frame(img)

4. (Optional) If you want /logs to return real experiment history,
   point LOGS_FILE below at wherever your ExperimentLogger writes to,
   or replace read_logs() with your own implementation.
------------------------------------------------------------------
"""

import os
import time
import json
import threading
from datetime import datetime

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

VIDEOS_DIR = "recordings"
LOGS_FILE = "logs/experiment_log.jsonl"  # adjust to match your ExperimentLogger

os.makedirs(VIDEOS_DIR, exist_ok=True)


# ============================================================
# RECORDING MANAGER
# ============================================================

class RecordingManager:
    """
    Thread-safe recording state machine: idle -> recording -> paused -> ...

    Frames are written via write_frame() whenever status == "recording".
    While "paused", frames are simply dropped (the writer stays open so
    resuming doesn't require re-opening the file).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.status = "idle"  # idle | recording | paused
        self.writer = None
        self.filepath = None
        self.start_time = None
        self.fps = 15
        self.frame_size = None  # (width, height), set on first frame

    def is_recording(self):
        return self.status == "recording"

    def start(self):
        with self._lock:
            if self.status != "idle":
                raise RuntimeError("Recording already in progress")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
            self.filepath = os.path.join(VIDEOS_DIR, filename)

            # Writer is created lazily on the first frame, once we know
            # the actual frame size coming from the camera.
            self.writer = None
            self.frame_size = None
            self.start_time = time.time()
            self.status = "recording"

            return filename

    def pause(self):
        with self._lock:
            if self.status != "recording":
                raise RuntimeError("Not currently recording")
            self.status = "paused"

    def resume(self):
        with self._lock:
            if self.status != "paused":
                raise RuntimeError("Not currently paused")
            self.status = "recording"

    def stop(self):
        with self._lock:
            if self.status == "idle":
                raise RuntimeError("Nothing to stop")

            if self.writer is not None:
                self.writer.release()

            filepath = self.filepath

            self.status = "idle"
            self.writer = None
            self.filepath = None
            self.frame_size = None
            self.start_time = None

            return filepath

    def write_frame(self, frame):
        with self._lock:
            if self.status != "recording":
                return

            height, width = frame.shape[:2]

            if self.writer is None:
                self.frame_size = (width, height)
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                self.writer = cv2.VideoWriter(
                    self.filepath, fourcc, self.fps, self.frame_size
                )

            # Guard against a mid-recording resolution change
            if (width, height) != self.frame_size:
                frame = cv2.resize(frame, self.frame_size)

            self.writer.write(frame)


recording_manager = RecordingManager()


# ============================================================
# RECORDING ENDPOINTS
# ============================================================

@router.post("/recording/start")
def start_recording():
    try:
        filename = recording_manager.start()
        return {"status": "recording", "filename": filename}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/recording/pause")
def pause_recording():
    try:
        recording_manager.pause()
        return {"status": "paused"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/recording/resume")
def resume_recording():
    try:
        recording_manager.resume()
        return {"status": "recording"}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/recording/stop")
def stop_recording():
    try:
        filepath = recording_manager.stop()
        return {"status": "idle", "saved": filepath}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/recording/status")
def recording_status():
    return {"status": recording_manager.status}


# ============================================================
# VIDEOS
# ============================================================

@router.get("/videos")
def list_videos():
    videos = []

    for filename in sorted(os.listdir(VIDEOS_DIR), reverse=True):
        if not filename.lower().endswith(".mp4"):
            continue

        full_path = os.path.join(VIDEOS_DIR, filename)
        stat = os.stat(full_path)

        videos.append({
            "filename": filename,
            "size": stat.st_size,
            "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return videos


@router.get("/videos/{filename}")
def get_video(filename: str):
    full_path = os.path.join(VIDEOS_DIR, filename)

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(full_path, media_type="video/mp4")


# ============================================================
# LOGS
# ============================================================

@router.get("/logs")
def get_logs():
    """
    Reads a JSON-lines log file (one JSON object per line), newest first.
    Adjust this to match whatever your ExperimentLogger actually writes.
    """
    if not os.path.isfile(LOGS_FILE):
        return []

    entries = []

    with open(LOGS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    entries.reverse()
    return entries
