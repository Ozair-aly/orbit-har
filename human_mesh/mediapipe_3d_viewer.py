import cv2
import mediapipe as mp
import numpy as np
import time
import threading
from io import BytesIO

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn


# ============================================================
# ORBIT-HAR | STANDALONE HUMAN 3D VIEWER
# ============================================================

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

WEB_HOST = "127.0.0.1"
WEB_PORT = 8010


# ============================================================
# FASTAPI
# ============================================================

web_app = FastAPI(title="ORBIT-HAR Human 3D Viewer")

latest_camera_jpeg = None
latest_mesh_jpeg = None

frame_lock = threading.Lock()


# ============================================================
# MEDIAPIPE
# ============================================================

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

CONNECTIONS = list(mp_pose.POSE_CONNECTIONS)

MESH_FACES = [
    (11, 12, 23),
    (12, 24, 23),
    (11, 23, 24),
    (11, 12, 24),

    (11, 13, 15),
    (12, 14, 16),

    (13, 15, 17),
    (14, 16, 18),

    (23, 25, 27),
    (24, 26, 28),

    (25, 27, 29),
    (26, 28, 30),
]


pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)


# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(
    CAMERA_INDEX,
    cv2.CAP_AVFOUNDATION
)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

if not cap.isOpened():
    raise RuntimeError("Camera could not be opened.")

print("📷 Camera opened successfully")


# ============================================================
# IMAGE ENCODING
# ============================================================

def encode_jpeg(frame, quality=85):

    ok, encoded = cv2.imencode(
        ".jpg",
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, quality]
    )

    if not ok:
        return None

    return encoded.tobytes()


def update_camera_frame(frame):

    global latest_camera_jpeg

    data = encode_jpeg(frame)

    if data is None:
        return

    with frame_lock:
        latest_camera_jpeg = data


# ============================================================
# 3D LANDMARK EXTRACTION
# ============================================================

def world_points(results):

    if not results.pose_world_landmarks:
        return None

    points = np.array(
        [
            [
                landmark.x,
                -landmark.z,
                -landmark.y
            ]
            for landmark in results.pose_world_landmarks.landmark
        ],
        dtype=np.float32
    )

    # Center body around torso
    center = np.mean(
        points[[11, 12, 23, 24]],
        axis=0
    )

    points = points - center

    return points


# ============================================================
# CREATE 3D MESH IMAGE
# ============================================================

def create_mesh_image(points):

    fig = plt.figure(
        figsize=(7, 6),
        dpi=100
    )

    ax = fig.add_subplot(
        111,
        projection="3d"
    )

    # --------------------------------------------------------
    # DARK BACKGROUND
    # --------------------------------------------------------

    fig.patch.set_facecolor("#05080c")
    ax.set_facecolor("#05080c")

    # --------------------------------------------------------
    # NO HUMAN
    # --------------------------------------------------------

    if points is None:

        ax.text2D(
            0.5,
            0.52,
            "NO HUMAN DETECTED",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=18,
            color="white",
        )

        ax.text2D(
            0.5,
            0.45,
            "MediaPipe Pose",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            color="#9aa7b5",
        )

    else:

        # ----------------------------------------------------
        # BODY TRIANGLES
        # ----------------------------------------------------

        triangles = []

        for a, b, c in MESH_FACES:

            if (
                a < len(points)
                and b < len(points)
                and c < len(points)
            ):
                triangles.append(
                    [
                        points[a],
                        points[b],
                        points[c]
                    ]
                )

        if triangles:

            mesh = Poly3DCollection(
                triangles,
                alpha=0.35,
                facecolor="#22a6f2",
                edgecolor="#8ed8ff",
                linewidths=0.7,
            )

            ax.add_collection3d(mesh)

        # ----------------------------------------------------
        # SKELETON
        # ----------------------------------------------------

        for a, b in CONNECTIONS:

            if (
                a >= len(points)
                or b >= len(points)
            ):
                continue

            p1 = points[a]
            p2 = points[b]

            ax.plot(
                [p1[0], p2[0]],
                [p1[1], p2[1]],
                [p1[2], p2[2]],
                color="#ffffff",
                linewidth=1.8,
            )

        # ----------------------------------------------------
        # JOINTS
        # ----------------------------------------------------

        ax.scatter(
            points[:, 0],
            points[:, 1],
            points[:, 2],
            s=22,
            color="#ffcc33",
            depthshade=True,
        )

        # ----------------------------------------------------
        # VIEW
        # ----------------------------------------------------

        ax.set_xlim(-1.0, 1.0)
        ax.set_ylim(-1.0, 1.0)
        ax.set_zlim(-1.2, 1.2)

        ax.view_init(
            elev=12,
            azim=-75
        )

        ax.text2D(
            0.03,
            0.95,
            "3D POSE: ACTIVE",
            transform=ax.transAxes,
            fontsize=10,
            color="#00ff88",
        )

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    ax.set_title(
        "ORBIT-HAR | HUMAN 3D MESH",
        color="white",
        fontsize=15,
        pad=10,
    )

    # --------------------------------------------------------
    # REMOVE AXIS
    # --------------------------------------------------------

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_zlabel("")

    # --------------------------------------------------------
    # SAVE DIRECTLY TO MEMORY
    # --------------------------------------------------------

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="jpg",
        dpi=90,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
    )

    plt.close(fig)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# UPDATE WEB MESH
# ============================================================

def update_web_mesh(points):

    global latest_mesh_jpeg

    data = create_mesh_image(points)

    if data is None:
        return

    with frame_lock:
        latest_mesh_jpeg = data


# ============================================================
# MJPEG STREAM
# ============================================================

def mjpeg_stream(name):

    while True:

        with frame_lock:

            if name == "camera":
                frame = latest_camera_jpeg
            else:
                frame = latest_mesh_jpeg

        if frame is not None:

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: "
                + str(len(frame)).encode()
                + b"\r\n\r\n"
                + frame
                + b"\r\n"
            )

        time.sleep(0.04)


# ============================================================
# API ROUTES
# ============================================================

@web_app.get("/")
def root():

    return {
        "system": "ORBIT-HAR",
        "viewer": "Human 3D Mesh",
        "status": "ONLINE",
        "port": WEB_PORT,
    }


@web_app.get("/status")
def status():

    with frame_lock:

        camera_ready = (
            latest_camera_jpeg is not None
        )

        mesh_ready = (
            latest_mesh_jpeg is not None
        )

    return {
        "status": "ONLINE",
        "camera": camera_ready,
        "mesh": mesh_ready,
    }


@web_app.get("/video")
def video():

    return StreamingResponse(
        mjpeg_stream("camera"),
        media_type=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        ),
    )


@web_app.get("/mesh")
def mesh():

    return StreamingResponse(
        mjpeg_stream("mesh"),
        media_type=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        ),
    )


# ============================================================
# WEB SERVER THREAD
# ============================================================

def start_web_server():

    uvicorn.run(
        web_app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="warning",
    )


# ============================================================
# START SERVER
# ============================================================

server_thread = threading.Thread(
    target=start_web_server,
    daemon=True,
)

server_thread.start()


# ============================================================
# STARTUP
# ============================================================

print()
print("==============================================")
print("🚀 ORBIT-HAR HUMAN 3D WEB SERVER")
print("🧍 ORBIT-HAR HUMAN 3D VIEWER")
print("==============================================")
print()
print(f"🌐 http://{WEB_HOST}:{WEB_PORT}")
print("MediaPipe: ACTIVE")
print("Camera: ACTIVE")
print(
    f"Web server: http://{WEB_HOST}:{WEB_PORT}"
)
print()
print("📷 Camera stream:")
print(
    f"http://{WEB_HOST}:{WEB_PORT}/video"
)
print()
print("🧍 3D mesh stream:")
print(
    f"http://{WEB_HOST}:{WEB_PORT}/mesh"
)
print()
print("Open the ORBIT-HAR Human 3D page.")
print("Press Q in the camera window to stop.")
print("==============================================")
print()


# ============================================================
# MAIN LOOP
# ============================================================

last_time = time.time()
fps = 0.0

mesh_counter = 0

try:

    while True:

        ok, frame = cap.read()

        if not ok:

            print("Camera frame not received.")

            time.sleep(0.1)

            continue

        # ----------------------------------------------------
        # MEDIAPIPE
        # ----------------------------------------------------

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        results = pose.process(rgb)

        # ----------------------------------------------------
        # CAMERA POSE DRAWING
        # ----------------------------------------------------

        if results.pose_landmarks:

            mp_draw.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
            )

        # ----------------------------------------------------
        # FPS
        # ----------------------------------------------------

        now = time.time()

        dt = now - last_time

        if dt > 0:

            fps = (
                0.9 * fps
                + 0.1 * (1.0 / dt)
            )

        last_time = now

        # ----------------------------------------------------
        # CAMERA STATUS
        # ----------------------------------------------------

        if results.pose_world_landmarks:

            status_text = "3D POSE ACTIVE"

        else:

            status_text = "SEARCHING FOR HUMAN"

        # ----------------------------------------------------
        # CAMERA OVERLAY
        # ----------------------------------------------------

        cv2.rectangle(
            frame,
            (0, 0),
            (frame.shape[1], 75),
            (0, 0, 0),
            -1,
        )

        cv2.putText(
            frame,
            "ORBIT-HAR | HUMAN 3D VIEWER",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"{status_text}   FPS: {fps:.1f}",
            (20, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (0, 255, 255),
            1,
        )

        # ----------------------------------------------------
        # UPDATE CAMERA WEB STREAM
        # ----------------------------------------------------

        update_camera_frame(frame)

        # ----------------------------------------------------
        # UPDATE 3D WEB STREAM
        #
        # IMPORTANT:
        # Do NOT render Matplotlib every camera frame.
        # It is expensive.
        # ----------------------------------------------------

        mesh_counter += 1

        if mesh_counter >= 5:

            mesh_counter = 0

            points = world_points(results)

            update_web_mesh(points)

        # ----------------------------------------------------
        # OPTIONAL LOCAL CAMERA WINDOW
        # ----------------------------------------------------

        cv2.imshow(
            "ORBIT-HAR Camera",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):

            break


finally:

    cap.release()

    pose.close()

    cv2.destroyAllWindows()

    print()
    print("🛑 ORBIT-HAR Human 3D Viewer stopped.")