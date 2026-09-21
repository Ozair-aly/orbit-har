import cv2
import mediapipe as mp
import numpy as np
import time
import threading

# ============================================================
# ORBIT-HAR HUMAN MESH BRIDGE
# ============================================================
#
# Standalone MediaPipe processing.
#
# DOES NOT TOUCH EXPERIMENT STATE.
# DOES NOT TOUCH YOLO.
# DOES NOT TOUCH EXPERIMENT LOGIC.
#
# ============================================================

mp_pose = mp.solutions.pose

pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

CONNECTIONS = [
    list(pair)
    for pair in mp_pose.POSE_CONNECTIONS
]


# ============================================================
# SAME MESH-STYLE FACES AS YOUR VIEWER
# ============================================================

MESH_FACES = [

    # Head / neck
    (0, 11, 12),
    (0, 12, 24),
    (0, 24, 23),
    (0, 23, 11),

    # Chest / abdomen
    (11, 12, 24),
    (11, 24, 23),

    # Left arm
    (11, 13, 15),
    (13, 15, 19),
    (15, 19, 17),

    # Right arm
    (12, 14, 16),
    (14, 16, 20),
    (16, 20, 18),

    # Left leg
    (23, 25, 27),
    (25, 27, 29),
    (27, 29, 31),

    # Right leg
    (24, 26, 28),
    (26, 28, 30),
    (28, 30, 32),
]


# ============================================================
# STATE
# ============================================================

latest_mesh = {
    "detected": False,
    "fps": 0.0,
    "landmarks": [],
    "connections": CONNECTIONS,
    "faces": MESH_FACES,
}

lock = threading.Lock()

last_time = time.time()
fps = 0.0


# ============================================================
# PROCESS FRAME
# ============================================================

def process_frame(frame):

    global fps
    global last_time
    global latest_mesh

    if frame is None:
        return latest_mesh

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    results = pose.process(rgb)

    detected = (
        results.pose_landmarks is not None
        and results.pose_world_landmarks is not None
    )

    now = time.time()

    dt = now - last_time

    if dt > 0:

        instantaneous_fps = 1.0 / dt

        fps = (
            0.90 * fps
            + 0.10 * instantaneous_fps
        )

    last_time = now


    # ========================================================
    # NO HUMAN
    # ========================================================

    if not detected:

        output = {
            "detected": False,
            "fps": round(fps, 1),
            "landmarks": [],
            "connections": CONNECTIONS,
            "faces": MESH_FACES,
        }

        with lock:
            latest_mesh = output

        return output


    # ========================================================
    # MEDIA PIPE WORLD LANDMARKS
    # ========================================================

    points = np.array(
        [
            [
                p.x,
                -p.z,
                -p.y,
            ]
            for p in results.pose_world_landmarks.landmark
        ],
        dtype=np.float32,
    )


    # ========================================================
    # CENTER AROUND TORSO
    # ========================================================

    torso = points[
        [11, 12, 23, 24]
    ]

    center = np.mean(
        torso,
        axis=0
    )

    points -= center


    # ========================================================
    # JSON FRIENDLY
    # ========================================================

    landmarks = [
        [
            round(float(p[0]), 5),
            round(float(p[1]), 5),
            round(float(p[2]), 5),
        ]
        for p in points
    ]


    output = {
        "detected": True,
        "fps": round(fps, 1),
        "landmarks": landmarks,
        "connections": CONNECTIONS,
        "faces": MESH_FACES,
    }


    with lock:
        latest_mesh = output


    return output


# ============================================================
# GET LATEST
# ============================================================

def get_latest_mesh():

    with lock:
        return latest_mesh.copy()