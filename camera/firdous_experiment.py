import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import mediapipe as mp
import numpy as np
import subprocess
import threading
import queue
import time
import json
import requests
from pathlib import Path

# ============================================================
# ORBIT-HAR | SEED SORTING EXPERIMENT
# Dashboard-compatible version
#
# - Uses the existing ORBIT-HAR camera -> /frame pipeline
# - Uses MediaPipe for hand tracking
# - Uses HSV geometry for RED / BLUE seed detection
# - Uses the experiment JSON for the ordered sequence
# - NO wrong-action / error detection
# - If the astronaut performs something else, the system simply
#   waits until the expected action is completed.
# ============================================================

BACKEND_URL = "http://127.0.0.1:8000/event"
FRAME_URL = "http://127.0.0.1:8000/frame"

BASE_DIR = Path(__file__).resolve().parent
EXPERIMENT_FILE = BASE_DIR/ "experiments" / "seed_sorting.json"

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

AI_STATUS_INTERVAL = 0.5
FRAME_INTERVAL = 0.10
ACTION_COOLDOWN = 0.8

MIN_SEED_AREA = 300
HAND_SEED_DISTANCE = 110
HAND_OBJECT_MARGIN = 45
INTERACTION_FRAMES_REQUIRED = 3
PICK_CONFIRM_FRAMES = 4
PLACEMENT_CONFIRM_FRAMES = 5

# ============================================================
# BACKEND / FRAME SENDER
# ============================================================

frame_lock = threading.Lock()
latest_frame = None
frame_sender_running = True


def send_event(data):
    try:
        requests.post(BACKEND_URL, json=data, timeout=0.2)
    except requests.RequestException:
        pass


def frame_sender_worker():
    global latest_frame

    while frame_sender_running:
        frame = None

        with frame_lock:
            if latest_frame is not None:
                frame = latest_frame
                latest_frame = None

        if frame is None:
            time.sleep(0.01)
            continue

        try:
            ok, buffer = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 70],
            )

            if not ok:
                continue

            requests.post(
                FRAME_URL,
                data=buffer.tobytes(),
                headers={"Content-Type": "image/jpeg"},
                timeout=0.15,
            )
        except requests.RequestException:
            pass


frame_sender_thread = threading.Thread(
    target=frame_sender_worker,
    daemon=True,
)
frame_sender_thread.start()


def send_frame(frame):
    global latest_frame

    with frame_lock:
        latest_frame = frame.copy()


# ============================================================
# VOICE
# ============================================================

voice_queue = queue.Queue()
voice_process = None
voice_lock = threading.Lock()


def speak(message):
    print(f"🔊 {message}")

    while not voice_queue.empty():
        try:
            voice_queue.get_nowait()
            voice_queue.task_done()
        except queue.Empty:
            break

    voice_queue.put(message)


def voice_worker():
    global voice_process

    while True:
        message = voice_queue.get()

        with voice_lock:
            try:
                if voice_process is not None:
                    try:
                        voice_process.terminate()
                    except Exception:
                        pass

                voice_process = subprocess.Popen(["say", message])
                voice_process.wait()
            except Exception as exc:
                print("Voice error:", exc)
            finally:
                voice_process = None

        voice_queue.task_done()


threading.Thread(target=voice_worker, daemon=True).start()


# ============================================================
# EXPERIMENT STATE
# ============================================================

class OrbitHAR:
    def __init__(self):
        if not EXPERIMENT_FILE.exists():
            raise FileNotFoundError(
                f"Experiment JSON not found: {EXPERIMENT_FILE}"
            )

        with open(EXPERIMENT_FILE, "r") as f:
            self.experiment = json.load(f)

        self.steps = self.experiment.get("steps", [])
        self.current_step = 0
        self.current_detected_action = "WAITING"
        self.current_ai_status = "READY"
        self.action_cooldown_until = time.time() + 1.5

        print("\n🚀 ORBIT-HAR | SEED SORTING")
        print("=" * 60)
        print(f"Experiment: {self.experiment.get('name', 'Seed Sorting Experiment')}")
        print(f"Steps: {len(self.steps)}")
        print("Error detection: OFF")
        print("=" * 60)

    @property
    def name(self):
        return self.experiment.get("name", "Seed Sorting Experiment")

    def get_current_step(self):
        if self.current_step >= len(self.steps):
            return None
        return self.steps[self.current_step]

    def process_action(self, action):
        if time.time() < self.action_cooldown_until:
            return False

        step = self.get_current_step()
        if step is None:
            return False

        expected = step.get("action")
        if action != expected:
            # IMPORTANT: no error detection.
            # Ignore non-current actions and keep waiting.
            return False

        completed_step = self.current_step + 1
        completed_instruction = step.get("instruction", "Step completed")

        self.current_detected_action = action
        self.current_ai_status = "STEP VERIFIED"

        print(f"\n✅ STEP {completed_step} VERIFIED: {action}")

        self.current_step += 1
        self.action_cooldown_until = time.time() + ACTION_COOLDOWN

        if self.current_step >= len(self.steps):
            self.current_ai_status = "EXPERIMENT COMPLETE"
            self.current_detected_action = action

            send_event({
                "type": "step_verified",
                "experiment": self.name,
                "completed_step": completed_step,
                "current_step": len(self.steps) + 1,
                "completed_instruction": completed_instruction,
                "total_steps": len(self.steps),
                "expected_action": action,
                "detected_action": action,
                "status": "VERIFIED",
            })

            send_event({
                "type": "experiment_complete",
                "experiment": self.name,
                "step": completed_step,
                "total_steps": len(self.steps),
                "expected_action": action,
                "detected_action": action,
                "status": "SUCCESS",
            })

            speak("Experiment completed successfully.")
            return True

        next_step = self.steps[self.current_step]

        send_event({
            "type": "step_verified",
            "experiment": self.name,
            "completed_step": completed_step,
            "current_step": self.current_step + 1,
            "completed_instruction": completed_instruction,
            "total_steps": len(self.steps),
            "expected_action": next_step.get("action", "WAITING"),
            "detected_action": "WAITING",
            "status": "VERIFIED",
            "next_action": next_step.get("action", "WAITING"),
            "next_instruction": next_step.get("instruction", ""),
        })

        speak(f"Correct. Next step. {next_step.get('instruction', '')}")
        self.current_detected_action = "WAITING"
        self.current_ai_status = "READY"
        return True


# ============================================================
# CALIBRATION
# ============================================================

WINDOW_NAME = "ORBIT-HAR | Seed Sorting"

regions = {
    "SEED AREA": None,
    "CONTAINER A": None,
    "CONTAINER B": None,
}

calibration_frame = None
drawing = False
start_x = 0
start_y = 0
current_x = 0
current_y = 0
selected_rectangle = None
calibration_step = 0


def mouse_callback(event, x, y, flags, param):
    global drawing, start_x, start_y
    global current_x, current_y, selected_rectangle

    if calibration_frame is None:
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_x, start_y = x, y
        current_x, current_y = x, y

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        current_x, current_y = x, y

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        current_x, current_y = x, y

        x1 = min(start_x, current_x)
        y1 = min(start_y, current_y)
        x2 = max(start_x, current_x)
        y2 = max(start_y, current_y)

        if (x2 - x1) < 30 or (y2 - y1) < 30:
            selected_rectangle = None
            return

        selected_rectangle = (x1, y1, x2, y2)


def draw_calibration_screen(frame):
    display = frame.copy()

    colors = {
        "SEED AREA": (0, 255, 255),
        "CONTAINER A": (0, 255, 0),
        "CONTAINER B": (255, 0, 0),
    }

    for name, rect in regions.items():
        if rect is None:
            continue

        x1, y1, x2, y2 = rect
        color = colors[name]
        cv2.rectangle(display, (x1, y1), (x2, y2), color, 3)
        cv2.putText(
            display,
            name,
            (x1 + 10, y1 + 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

    if drawing:
        cv2.rectangle(
            display,
            (start_x, start_y),
            (current_x, current_y),
            (255, 255, 255),
            2,
        )

    if calibration_step == 0:
        title = "STEP 1: SELECT SEED AREA"
        instruction = "Drag a rectangle around where the red/blue seeds start"
    elif calibration_step == 1:
        title = "STEP 2: SELECT CONTAINER A"
        instruction = "Drag a rectangle around Container A"
    elif calibration_step == 2:
        title = "STEP 3: SELECT CONTAINER B"
        instruction = "Drag a rectangle around Container B"
    else:
        title = "CALIBRATION COMPLETE"
        instruction = "Press ENTER to start the experiment"

    cv2.rectangle(
        display,
        (0, 0),
        (display.shape[1], 100),
        (0, 0, 0),
        -1,
    )

    cv2.putText(
        display,
        title,
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (0, 255, 255),
        2,
    )

    cv2.putText(
        display,
        instruction,
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )

    cv2.putText(
        display,
        "ENTER: Confirm   C: Clear   R: Reset   Q: Quit",
        (20, display.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )

    return display


def calibrate(cap):
    global calibration_frame, calibration_step, selected_rectangle

    calibration_step = 0
    selected_rectangle = None

    for key in regions:
        regions[key] = None

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    region_names = ["SEED AREA", "CONTAINER A", "CONTAINER B"]

    print("\n======================================")
    print("             CALIBRATION")
    print("======================================")
    print("Select SEED AREA, CONTAINER A, CONTAINER B")
    print("Press ENTER after each selection.")

    while True:
        ret, frame = cap.read()
        if not ret:
            return False

        calibration_frame = frame.copy()
        display = draw_calibration_screen(frame)
        send_frame(display)
        cv2.imshow(WINDOW_NAME, display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            return False

        if key == ord("r"):
            return calibrate(cap)

        if key == ord("c"):
            selected_rectangle = None
            continue

        if key == 13:
            if selected_rectangle is None:
                print("Please draw a rectangle first.")
                continue

            if calibration_step >= 3:
                return True

            region_name = region_names[calibration_step]
            regions[region_name] = selected_rectangle
            print(f"{region_name}: {selected_rectangle}")
            selected_rectangle = None
            calibration_step += 1

            if calibration_step >= 3:
                print("Calibration complete. Press ENTER again to start.")


# ============================================================
# DETECTION HELPERS
# ============================================================

def point_inside_region(x, y, rect):
    if rect is None:
        return False

    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def determine_location(center_x, center_y):
    if point_inside_region(center_x, center_y, regions["CONTAINER A"]):
        return "CONTAINER A"

    if point_inside_region(center_x, center_y, regions["CONTAINER B"]):
        return "CONTAINER B"

    if point_inside_region(center_x, center_y, regions["SEED AREA"]):
        return "SEED AREA"

    return "UNKNOWN"


def distance_between(p1, p2):
    if p1 is None or p2 is None:
        return 999999.0

    return float(np.hypot(p1[0] - p2[0], p1[1] - p2[1]))


def is_hand_near_object(hand_x, hand_y, object_x, object_y, bbox):
    x1, y1, x2, y2 = bbox

    center_distance = distance_between(
        (hand_x, hand_y),
        (object_x, object_y),
    )

    inside_expanded_box = (
        x1 - HAND_OBJECT_MARGIN <= hand_x <= x2 + HAND_OBJECT_MARGIN
        and y1 - HAND_OBJECT_MARGIN <= hand_y <= y2 + HAND_OBJECT_MARGIN
    )

    return (
        center_distance <= HAND_SEED_DISTANCE
        or inside_expanded_box
    )


def hand_is_near_object(hand_landmark_points, object_x, object_y, bbox):
    for hx, hy in hand_landmark_points:
        if is_hand_near_object(
            hx,
            hy,
            object_x,
            object_y,
            bbox,
        ):
            return True

    return False


def find_colored_seed(mask):
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    best = None
    best_area = 0

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_SEED_AREA:
            continue

        if area > best_area:
            best_area = area
            best = contour

    if best is None:
        return None

    x, y, w, h = cv2.boundingRect(best)

    return {
        "bbox": (x, y, x + w, y + h),
        "center": (x + w // 2, y + h // 2),
        "area": best_area,
    }


def draw_regions(frame):
    colors = {
        "SEED AREA": (0, 255, 255),
        "CONTAINER A": (0, 255, 0),
        "CONTAINER B": (255, 0, 0),
    }

    for name, rect in regions.items():
        if rect is None:
            continue

        x1, y1, x2, y2 = rect
        color = colors[name]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            name,
            (x1 + 8, y1 + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )


# ============================================================
# MAIN
# ============================================================

cap = cv2.VideoCapture(CAMERA_INDEX)
if not cap.isOpened():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("❌ Camera could not be opened")
    send_event({
        "type": "camera_status",
        "active": False,
        "status": "OFFLINE",
    })
    raise SystemExit(1)

send_event({
    "type": "camera_status",
    "active": True,
    "status": "LIVE",
})

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

if not calibrate(cap):
    cap.release()
    hands.close()
    cv2.destroyAllWindows()
    frame_sender_running = False
    raise SystemExit(0)

orbit = OrbitHAR()

# Seed tracking state.
last_centers = {"RED": None, "BLUE": None}
interaction_frames = {"RED": 0, "BLUE": 0}
pick_evidence = {"RED": 0, "BLUE": 0}
place_evidence = {"RED": 0, "BLUE": 0}

last_ai_status_time = 0

print("\n🎥 LIVE ORBIT-HAR STARTED")
print("Error detection: OFF")
print("Perform the experiment in order.")
print("Press Q to quit.")

speak("Seed sorting experiment started.")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Camera frame not received.")
            send_event({
                "type": "camera_status",
                "active": False,
                "status": "FRAME ERROR",
            })
            break

        current_time = time.time()
        height, width = frame.shape[:2]

        # --------------------------------------------------------
        # HAND TRACKING
        # --------------------------------------------------------
        hand_landmark_points = []
        hand_detected = False

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        hand_results = hands.process(rgb)

        if hand_results.multi_hand_landmarks:
            hand_detected = True

            for hand_landmarks in hand_results.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                )

                for landmark in hand_landmarks.landmark:
                    px = int(landmark.x * width)
                    py = int(landmark.y * height)
                    hand_landmark_points.append((px, py))

        # --------------------------------------------------------
        # HSV SEED DETECTION
        # --------------------------------------------------------
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        red_mask_1 = cv2.inRange(
            hsv,
            np.array([0, 100, 80]),
            np.array([10, 255, 255]),
        )
        red_mask_2 = cv2.inRange(
            hsv,
            np.array([170, 100, 80]),
            np.array([180, 255, 255]),
        )
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)

        blue_mask = cv2.inRange(
            hsv,
            np.array([90, 80, 50]),
            np.array([140, 255, 255]),
        )

        kernel = np.ones((5, 5), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
        blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)

        detections = {}

        for color_name, mask, draw_color in [
            ("RED", red_mask, (0, 0, 255)),
            ("BLUE", blue_mask, (255, 0, 0)),
        ]:
            detection = find_colored_seed(mask)
            detections[color_name] = detection

            if detection is None:
                continue

            x1, y1, x2, y2 = detection["bbox"]
            cx, cy = detection["center"]
            location = determine_location(cx, cy)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                draw_color,
                3,
            )
            cv2.circle(
                frame,
                (cx, cy),
                5,
                (0, 255, 255),
                -1,
            )
            cv2.putText(
                frame,
                f"{color_name} SEED",
                (x1, max(y1 - 10, 125)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                draw_color,
                2,
            )
            cv2.putText(
                frame,
                location,
                (x1, y2 + 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                2,
            )

        # --------------------------------------------------------
        # CURRENT STEP
        # --------------------------------------------------------
        step = orbit.get_current_step()

        if step is None:
            expected_action = "COMPLETE"
            instruction = "Experiment completed"
        else:
            expected_action = step.get("action", "WAITING")
            instruction = step.get("instruction", "")

        expected_color = step.get("object") if step else None
        target_location = step.get("target") if step else None

        # --------------------------------------------------------
        # ACTION DETECTION — ONLY CURRENT EXPECTED ACTIONS
        # --------------------------------------------------------
        candidate_action = None
        interaction = False

        if step is not None and expected_color in detections:
            detection = detections.get(expected_color)

            if detection is not None:
                cx, cy = detection["center"]
                bbox = detection["bbox"]
                location = determine_location(cx, cy)

                interaction = hand_is_near_object(
                    hand_landmark_points,
                    cx,
                    cy,
                    bbox,
                )

                if interaction:
                    interaction_frames[expected_color] += 1
                else:
                    interaction_frames[expected_color] = max(
                        0,
                        interaction_frames[expected_color] - 1,
                    )

                previous_center = last_centers[expected_color]
                movement = distance_between(previous_center, (cx, cy))
                last_centers[expected_color] = (cx, cy)

                if expected_action.startswith("PICK_"):
                    if (
                        location == "SEED AREA"
                        and interaction_frames[expected_color] >= INTERACTION_FRAMES_REQUIRED
                        and movement > 2
                    ):
                        pick_evidence[expected_color] += 1
                    else:
                        pick_evidence[expected_color] = max(
                            0,
                            pick_evidence[expected_color] - 1,
                        )

                    if pick_evidence[expected_color] >= PICK_CONFIRM_FRAMES:
                        candidate_action = expected_action
                        pick_evidence[expected_color] = 0

                elif expected_action.startswith("PLACE_"):
                    if location == target_location:
                        place_evidence[expected_color] += 1
                    else:
                        place_evidence[expected_color] = 0

                    if place_evidence[expected_color] >= PLACEMENT_CONFIRM_FRAMES:
                        candidate_action = expected_action
                        place_evidence[expected_color] = 0

        # --------------------------------------------------------
        # VERIFY CURRENT EXPECTED ACTION
        # --------------------------------------------------------
        if candidate_action is not None:
            orbit.process_action(candidate_action)

        # --------------------------------------------------------
        # LIVE AI ACTIVITY
        # --------------------------------------------------------
        detected_any = any(value is not None for value in detections.values())

        if interaction:
            live_ai_activity = "HAND + SEED INTERACTION"
        elif detected_any:
            live_ai_activity = "SEED DETECTED"
        elif hand_detected:
            live_ai_activity = "HAND DETECTED"
        else:
            live_ai_activity = "SEARCHING"

        # --------------------------------------------------------
        # DASHBOARD AI STATUS
        # --------------------------------------------------------
        if current_time - last_ai_status_time >= AI_STATUS_INTERVAL:
            send_event({
                "type": "ai_status",
                "experiment": orbit.name,
                "step": orbit.current_step + 1,
                "total_steps": len(orbit.steps),
                "expected_action": expected_action,
                "detected_action": orbit.current_detected_action,
                "ai_activity": live_ai_activity,
                "ai_status": orbit.current_ai_status,
                "hand_detected": hand_detected,
                "hand_tracking": hand_detected,
                "interaction": interaction,
                "interaction_frames": max(interaction_frames.values()),
                "objects": {
                    "red_seed": detections["RED"] is not None,
                    "blue_seed": detections["BLUE"] is not None,
                },
                "red_seed_detected": detections["RED"] is not None,
                "blue_seed_detected": detections["BLUE"] is not None,
                "instruction": instruction,
                "status": "VERIFIED" if orbit.current_ai_status == "STEP VERIFIED" else "CHECKING",
            })
            last_ai_status_time = current_time

        # --------------------------------------------------------
        # ON-CAMERA STATUS
        # --------------------------------------------------------
        cv2.rectangle(
            frame,
            (0, 0),
            (width, 120),
            (0, 0, 0),
            -1,
        )

        cv2.putText(
            frame,
            "ORBIT-HAR",
            (20, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"STEP {min(orbit.current_step + 1, len(orbit.steps))}/{len(orbit.steps)}: {instruction}",
            (20, 62),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"AI: {live_ai_activity}",
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            "ERROR DETECTION: OFF",
            (width - 250, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (180, 180, 180),
            1,
        )

        draw_regions(frame)
        send_frame(frame)

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        time.sleep(FRAME_INTERVAL)

finally:
    frame_sender_running = False

    cap.release()
    hands.close()
    cv2.destroyAllWindows()

    send_event({
        "type": "camera_status",
        "active": False,
        "status": "OFFLINE",
    })

    print("\n📷 CAMERA RELEASED")
    print("ORBIT-HAR SEED SORTING ENDED")
