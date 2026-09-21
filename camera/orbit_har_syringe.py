import sys
import os

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import cv2
import mediapipe as mp
import numpy as np
import math
import json
import subprocess
import threading
import queue
import time
from collections import deque
from logger import ExperimentLogger
import requests


# ============================================================
# ORBIT-HAR | SYRINGE LIQUID TRANSFER
# Automatic detection version
#
# No manual ROI.
# No custom YOLO training.
#
# Detection:
#   - Syringe: light-object + geometry + temporal tracking
#   - Containers: HSV color detection
#   - Hand: MediaPipe
#
# Actions:
#   1. PICK_SYRINGE
#   2. INSERT_CONTAINER_A
#   3. DRAW_LIQUID
#   4. INSERT_CONTAINER_B
#   5. RETURN_SYRINGE
# ============================================================


# ============================================================
# BACKEND
# ============================================================

BACKEND_URL = "http://127.0.0.1:8000/event"
FRAME_URL = "http://127.0.0.1:8000/frame"


def send_event(data):
    try:
        requests.post(BACKEND_URL, json=data, timeout=0.15)
    except requests.RequestException:
        pass


frame_lock = threading.Lock()
latest_frame_to_send = None
frame_sender_running = True


def frame_sender_worker():
    global latest_frame_to_send

    while frame_sender_running:
        frame = None

        with frame_lock:
            if latest_frame_to_send is not None:
                frame = latest_frame_to_send
                latest_frame_to_send = None

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
                timeout=0.12,
            )
        except requests.RequestException:
            pass


frame_sender_thread = threading.Thread(
    target=frame_sender_worker,
    daemon=True,
)
frame_sender_thread.start()


def send_frame(frame):
    global latest_frame_to_send

    with frame_lock:
        latest_frame_to_send = frame.copy()


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_FILE = os.path.join(BASE_DIR, "experiments", "syringe_transfer.json")

CAMERA_INDEX = 0

AI_STATUS_INTERVAL = 0.5
FRAME_INTERVAL = 0.10
ACTION_COOLDOWN = 0.8

# ------------------------------------------------------------
# CONTAINER COLORS
# These are the same style of automatic detection used by the
# previous syringe experiment.
# ------------------------------------------------------------

CONTAINER_A_HSV_LOWER = np.array([40, 40, 40])
CONTAINER_A_HSV_UPPER = np.array([80, 255, 255])

CONTAINER_B_HSV_LOWER = np.array([20, 100, 100])
CONTAINER_B_HSV_UPPER = np.array([35, 255, 255])

CONTAINER_MIN_AREA = 800

# ------------------------------------------------------------
# SYRINGE DETECTION
#
# Color-independent geometry detector.  The actual syringe is
# blue/gray and can be partly hidden by the hand, so we detect
# paired long barrel edges and track their position over time.
# ------------------------------------------------------------

SYRINGE_MIN_LINE_LENGTH = 55
SYRINGE_MIN_BODY_LENGTH = 70
SYRINGE_MAX_BODY_LENGTH = 700
SYRINGE_MIN_BODY_WIDTH = 9
SYRINGE_MAX_BODY_WIDTH = 105
SYRINGE_MIN_ASPECT = 2.8
SYRINGE_MAX_ASPECT = 13.5

# Full-syringe box expansion. The paired Hough edges usually describe
# the barrel only; the real syringe also has the plunger and nozzle.
# Keep the detector geometry tight, then expand only along the syringe
# axis so the displayed box covers the complete physical syringe.
SYRINGE_FULL_LENGTH_SCALE = 1.55
SYRINGE_FULL_WIDTH_SCALE = 1.20

SYRINGE_HOUGH_THRESHOLD = 42
SYRINGE_HOUGH_MIN_LINE = 45
SYRINGE_HOUGH_MAX_GAP = 14
SYRINGE_PARALLEL_ANGLE = 12.0
SYRINGE_MIN_PARALLEL_DISTANCE = 7.0
SYRINGE_MAX_PARALLEL_DISTANCE = 105.0
SYRINGE_MIN_OVERLAP = 0.38

SYRINGE_TRACK_MAX_JUMP = 240.0
SYRINGE_TRACK_STRONG_RADIUS = 110.0

# Temporal detection
SYRINGE_DETECT_CONFIRM_FRAMES = 3
SYRINGE_LOST_GRACE_FRAMES = 10

# Hand interaction
HAND_PROXIMITY_MULTIPLIER = 1.25
HAND_INTERACTION_CONFIRM_FRAMES = 3

# Movement
MOVEMENT_STILL_THRESHOLD = 5
PICK_MOVEMENT_THRESHOLD = 8
PICK_CONFIRM_FRAMES = 5

# Container insertion
CONTAINER_PROXIMITY_MULTIPLIER = 0.95
INSERT_CONFIRM_FRAMES = 5

# Drawing
DRAW_CONFIRM_FRAMES = 5
DRAW_MIN_PLUNGER_MOVEMENT = 10

# Return
HOME_DISTANCE_THRESHOLD = 55
RETURN_CONFIRM_FRAMES = 6


# ============================================================
# IMAGE HELPERS
# ============================================================

KERNEL_SMALL = np.ones((3, 3), np.uint8)
KERNEL = np.ones((5, 5), np.uint8)


def largest_contour(mask, min_area):
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if not contours:
        return None

    valid = [
        c for c in contours
        if cv2.contourArea(c) >= min_area
    ]

    if not valid:
        return None

    return max(valid, key=cv2.contourArea)


def detect_container(hsv_frame, lower, upper):
    mask = cv2.inRange(hsv_frame, lower, upper)

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        KERNEL,
        iterations=1,
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        KERNEL,
        iterations=2,
    )

    contour = largest_contour(mask, CONTAINER_MIN_AREA)

    if contour is None:
        return None, None

    x, y, w, h = cv2.boundingRect(contour)

    if w < 20 or h < 20:
        return None, None

    bbox = (x, y, x + w, y + h)
    center = (x + w // 2, y + h // 2)

    return bbox, center


def point_to_bbox_distance(point, bbox):
    if point is None or bbox is None:
        return float("inf")

    px, py = point
    x1, y1, x2, y2 = bbox

    dx = max(x1 - px, 0, px - x2)
    dy = max(y1 - py, 0, py - y2)

    return math.sqrt(dx * dx + dy * dy)


def near_container(point, bbox, multiplier=CONTAINER_PROXIMITY_MULTIPLIER):
    if point is None or bbox is None:
        return False

    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1

    distance = point_to_bbox_distance(point, bbox)
    threshold = max(25, max(w, h) * (1.0 - multiplier))

    # Also allow the syringe center to be inside/over the container.
    expanded = (
        x1 - int(w * multiplier),
        y1 - int(h * multiplier),
        x2 + int(w * multiplier),
        y2 + int(h * multiplier),
    )

    return (
        expanded[0] <= point[0] <= expanded[2]
        and expanded[1] <= point[1] <= expanded[3]
    ) or distance <= threshold


def distance(a, b):
    if a is None or b is None:
        return float("inf")

    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2
    )


# ============================================================
# SYRINGE DETECTOR
# ============================================================

# Detection implementation lives here; configuration is above.
# No state-machine or MediaPipe code is changed.

HAND_PROXIMITY_MULTIPLIER = 1.25
HAND_INTERACTION_CONFIRM_FRAMES = 3

# Movement
MOVEMENT_STILL_THRESHOLD = 5
PICK_MOVEMENT_THRESHOLD = 8
PICK_CONFIRM_FRAMES = 5

# Container insertion
CONTAINER_PROXIMITY_MULTIPLIER = 0.95
INSERT_CONFIRM_FRAMES = 5

# Drawing
DRAW_CONFIRM_FRAMES = 5
DRAW_MIN_PLUNGER_MOVEMENT = 10

# Return
HOME_DISTANCE_THRESHOLD = 55
RETURN_CONFIRM_FRAMES = 6


def _angle_difference(a, b):
    """Smallest difference between two undirected line angles."""
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _line_angle_and_length(line):
    x1, y1, x2, y2 = [float(v) for v in line]
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx)) % 180.0
    return angle, length


def _line_midpoint(line):
    x1, y1, x2, y2 = [float(v) for v in line]
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)


def _project_segment(line, axis):
    """Return min/max scalar projection of a line segment on axis."""
    x1, y1, x2, y2 = [float(v) for v in line]
    ax, ay = axis
    p1 = x1 * ax + y1 * ay
    p2 = x2 * ax + y2 * ay
    return min(p1, p2), max(p1, p2)


def _rotated_box(center, axis, length, width):
    """Build a 4-point oriented rectangle from its long axis."""
    cx, cy = center
    ax, ay = axis
    px, py = -ay, ax

    hl = length * 0.5
    hw = width * 0.5

    pts = np.array([
        [cx - ax * hl - px * hw, cy - ay * hl - py * hw],
        [cx + ax * hl - px * hw, cy + ay * hl - py * hw],
        [cx + ax * hl + px * hw, cy + ay * hl + py * hw],
        [cx - ax * hl + px * hw, cy - ay * hl + py * hw],
    ], dtype=np.int32)

    return pts


def detect_syringe(hsv_frame, previous_center=None):
    """
    Detect the physical syringe without relying on syringe color.

    The important change from the old detector is that a single
    bright contour can no longer become "the syringe".  A candidate
    is built from paired long edges with syringe-like geometry.

    previous_center is used as a tracking prior, so once the real
    syringe is found we strongly prefer the same object in subsequent
    frames, even when the hand partially occludes it.
    """

    if hsv_frame is None or hsv_frame.size == 0:
        return None

    # Use brightness rather than HSV color.  This works for the
    # blue/gray syringe seen in the actual camera feed.
    value = hsv_frame[:, :, 2]

    # Mild local contrast enhancement makes the barrel edges survive
    # changes in room lighting without assuming a syringe color.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(value)
    blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)

    edges = cv2.Canny(blurred, 35, 105)

    # The ORBIT-HAR status text is drawn on top of the same camera
    # frame.  During initial acquisition, ignore that UI band so
    # Hough does not mistake two text strokes for the syringe.
    if previous_center is None:
        ui_h = min(240, max(0, edges.shape[0] // 3))
        edges[:ui_h, :min(600, edges.shape[1])] = 0

    # Suppress strong skin-colored edges. This is deliberately only
    # an edge suppression aid; it is NOT the syringe detector.
    # It reduces finger/hand lines while leaving the blue/gray syringe
    # edges available for Hough detection.
    hue = hsv_frame[:, :, 0]
    sat = hsv_frame[:, :, 1]
    val = hsv_frame[:, :, 2]
    skin = (
        (((hue <= 25) | (hue >= 170)) &
         (sat >= 35) &
         (sat <= 210) &
         (val >= 55))
    ).astype(np.uint8) * 255
    skin = cv2.dilate(skin, np.ones((5, 5), np.uint8), iterations=1)
    edges[skin > 0] = 0

    # Close tiny breaks in the long barrel edges.
    edges = cv2.morphologyEx(
        edges,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), np.uint8),
        iterations=1,
    )

    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180.0,
        threshold=SYRINGE_HOUGH_THRESHOLD,
        minLineLength=SYRINGE_HOUGH_MIN_LINE,
        maxLineGap=SYRINGE_HOUGH_MAX_GAP,
    )

    if lines is None:
        return None

    raw_lines = [
        tuple(int(v) for v in line[0])
        for line in lines
    ]

    # Ignore very short/weak lines before the O(n^2) pairing step.
    usable = []
    for line in raw_lines:
        angle, length = _line_angle_and_length(line)
        if length >= SYRINGE_MIN_LINE_LENGTH:
            usable.append((line, angle, length))

    if len(usable) < 2:
        return None

    candidates = []

    # Pair two roughly parallel edges. A syringe barrel normally has
    # two long boundaries even when the hand hides part of the body.
    for i in range(len(usable)):
        line_a, angle_a, len_a = usable[i]
        mid_a = _line_midpoint(line_a)

        for j in range(i + 1, len(usable)):
            line_b, angle_b, len_b = usable[j]

            if _angle_difference(angle_a, angle_b) > SYRINGE_PARALLEL_ANGLE:
                continue

            mid_b = _line_midpoint(line_b)

            # Common undirected axis.
            theta = math.radians((angle_a + angle_b) * 0.5)
            axis = (math.cos(theta), math.sin(theta))
            normal = (-axis[1], axis[0])

            # Separation of the two lines measured perpendicular to
            # their shared long axis.
            dx = mid_b[0] - mid_a[0]
            dy = mid_b[1] - mid_a[1]
            separation = abs(dx * normal[0] + dy * normal[1])

            if (
                separation < SYRINGE_MIN_PARALLEL_DISTANCE
                or separation > SYRINGE_MAX_PARALLEL_DISTANCE
            ):
                continue

            # How much do the two segments overlap along the long axis?
            amin, amax = _project_segment(line_a, axis)
            bmin, bmax = _project_segment(line_b, axis)
            overlap = max(0.0, min(amax, bmax) - max(amin, bmin))
            shorter = max(min(len_a, len_b), 1.0)
            overlap_ratio = overlap / shorter

            if overlap_ratio < SYRINGE_MIN_OVERLAP:
                continue

            # Estimate the whole visible barrel span from both lines.
            span_min = min(amin, bmin)
            span_max = max(amax, bmax)
            body_length = span_max - span_min

            # Add a small margin for the barrel's end caps/nozzle.
            body_length = min(
                SYRINGE_MAX_BODY_LENGTH,
                body_length + min(24.0, separation * 0.35),
            )

            if (
                body_length < SYRINGE_MIN_BODY_LENGTH
                or body_length > SYRINGE_MAX_BODY_LENGTH
            ):
                continue

            # The two detected edges describe the barrel width. Add a
            # conservative margin so partial edges still produce a box
            # around the physical syringe.
            body_width = separation + 10.0

            if (
                body_width < SYRINGE_MIN_BODY_WIDTH
                or body_width > SYRINGE_MAX_BODY_WIDTH
            ):
                continue

            aspect = body_length / max(body_width, 1.0)

            if aspect < SYRINGE_MIN_ASPECT or aspect > SYRINGE_MAX_ASPECT:
                continue

            # Center from the midpoint of the combined projection span.
            center_scalar = (span_min + span_max) * 0.5
            center = (
                center_scalar * axis[0],
                center_scalar * axis[1],
            )

            # Shift from the global origin into image coordinates by
            # using the midpoint of the two segment centers.
            origin_x = (mid_a[0] + mid_b[0]) * 0.5
            origin_y = (mid_a[1] + mid_b[1]) * 0.5
            origin_projection = (
                origin_x * axis[0] + origin_y * axis[1]
            )
            center_shift = center_scalar - origin_projection
            center = (
                int(round(origin_x + axis[0] * center_shift)),
                int(round(origin_y + axis[1] * center_shift)),
            )

            # Keep a tight barrel box for image-support scoring.
            barrel_box_points = _rotated_box(
                center,
                axis,
                body_length,
                body_width,
            )

            # The Hough pair normally sees the barrel, while the physical
            # syringe extends beyond it with the plunger on one side and
            # nozzle/tip on the other. Build the DISPLAY/TRACKING box from
            # the same axis, but expand it along the long direction. This
            # gives one bounding box around the whole syringe without using
            # the hand as part of the detector.
            full_length = min(
                SYRINGE_MAX_BODY_LENGTH * 1.25,
                body_length * SYRINGE_FULL_LENGTH_SCALE,
            )
            full_width = min(
                SYRINGE_MAX_BODY_WIDTH * 1.10,
                body_width * SYRINGE_FULL_WIDTH_SCALE,
            )

            box_points = _rotated_box(
                center,
                axis,
                full_length,
                full_width,
            )

            x1 = max(0, int(box_points[:, 0].min()))
            y1 = max(0, int(box_points[:, 1].min()))
            x2 = min(hsv_frame.shape[1] - 1, int(box_points[:, 0].max()))
            y2 = min(hsv_frame.shape[0] - 1, int(box_points[:, 1].max()))

            if x2 <= x1 or y2 <= y1:
                continue

            # --------------------------------------------------------
            # Candidate score
            # --------------------------------------------------------
            score = 0.0

            # Longer paired edges are more syringe-like than fingers.
            line_score = min(
                ((len_a + len_b) * 0.5) / 180.0,
                1.5,
            )
            score += 3.0 * line_score

            # Parallelism.
            angle_error = _angle_difference(angle_a, angle_b)
            score += 2.0 * (1.0 - angle_error / SYRINGE_PARALLEL_ANGLE)

            # Strong overlap means both edges describe the same object.
            score += 3.0 * min(overlap_ratio, 1.0)

            # Syringe barrel aspect is elongated but not infinitely thin.
            aspect_target = 5.0
            aspect_score = 1.0 - min(
                abs(aspect - aspect_target) / 7.0,
                1.0,
            )
            score += 2.5 * aspect_score

            # Prefer plausible barrel width.
            width_score = 1.0 - min(
                abs(body_width - 34.0) / 70.0,
                1.0,
            )
            score += 1.5 * width_score

            # --------------------------------------------------------
            # Image support inside the proposed box.
            # A real barrel should contain edge pixels near both sides.
            # --------------------------------------------------------
            mask_box = np.zeros_like(edges)
            cv2.fillConvexPoly(mask_box, barrel_box_points, 255)
            roi_edges = cv2.bitwise_and(edges, mask_box)
            roi_area = max(cv2.countNonZero(mask_box), 1)
            edge_density = cv2.countNonZero(roi_edges) / roi_area

            if edge_density < 0.012:
                continue

            score += 2.0 * min(edge_density / 0.10, 1.0)

            # A blue/gray syringe usually has more chroma than white
            # overlay text.  This is only a weak anti-UI signal, not
            # the object detector itself, so gray syringes still work.
            mean_saturation = cv2.mean(
                hsv_frame[:, :, 1],
                mask=mask_box,
            )[0]
            if mean_saturation >= 25.0:
                score += 2.0
            elif mean_saturation < 8.0:
                score -= 1.5

            # Temporal continuity is the strongest discriminator once
            # the syringe has been seen. It prevents jumping to fingers.
            if previous_center is not None:
                d = distance(center, previous_center)

                if d <= SYRINGE_TRACK_STRONG_RADIUS:
                    score += 7.0
                elif d <= SYRINGE_TRACK_MAX_JUMP:
                    score += 3.0 * (
                        1.0 -
                        (d - SYRINGE_TRACK_STRONG_RADIUS) /
                        max(
                            SYRINGE_TRACK_MAX_JUMP -
                            SYRINGE_TRACK_STRONG_RADIUS,
                            1.0,
                        )
                    )
                else:
                    score -= 6.0

            candidates.append({
                "bbox": (x1, y1, x2, y2),
                "center": center,
                "box_points": box_points,
                "length": float(full_length),
                "width": float(full_width),
                "barrel_length": float(body_length),
                "barrel_width": float(body_width),
                "angle": float(math.degrees(theta)),
                "area": float(body_length * body_width),
                "aspect": float(aspect),
                "solidity": 1.0,
                "rectangularity": float(min(edge_density * 8.0, 1.0)),
                "score": float(score),
                "line_support": float((len_a + len_b) * 0.5),
                "parallel_distance": float(separation),
                "edge_density": float(edge_density),
                "mean_saturation": float(mean_saturation),
            })

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    best = candidates[0]

    # Absolute gate. A random pair of room/hand edges should not be
    # reported as a syringe just because it is the best available pair.
    # The score threshold is deliberately moderate because the syringe
    # can be partly hidden by the hand.
    if best["score"] < 7.0:
        return None

    return best


# ============================================================
# PLUNGER / SYRINGE AXIS ESTIMATION
# ============================================================

def syringe_axis_endpoints(syringe):
    """
    Return the two endpoints of the long axis.

    This is used for tracking changes along the syringe axis.
    It is deliberately geometry-based rather than a trained
    plunger detector.
    """

    if syringe is None:
        return None, None

    points = syringe["box_points"].astype(np.float32)

    max_distance = 0
    best_a = None
    best_b = None

    for i in range(4):
        for j in range(i + 1, 4):
            d = np.linalg.norm(points[i] - points[j])

            if d > max_distance:
                max_distance = d
                best_a = points[i]
                best_b = points[j]

    if best_a is None:
        return None, None

    return (
        (int(best_a[0]), int(best_a[1])),
        (int(best_b[0]), int(best_b[1])),
    )


def estimate_axis_projection(point, axis_a, axis_b):
    if point is None or axis_a is None or axis_b is None:
        return None

    ax, ay = axis_a
    bx, by = axis_b

    vx = bx - ax
    vy = by - ay

    denom = vx * vx + vy * vy

    if denom <= 1e-6:
        return None

    px, py = point

    return (
        ((px - ax) * vx + (py - ay) * vy)
        / math.sqrt(denom)
    )


# ============================================================
# ORBIT-HAR STATE MACHINE
# ============================================================

class OrbitHAR:

    def __init__(self):
        with open(EXPERIMENT_FILE, "r") as f:
            self.experiment = json.load(f)

        self.steps = self.experiment["steps"]
        self.current_step = 0

        self.logger = ExperimentLogger(
            self.experiment["name"]
        )

        self.current_detected_action = "WAITING"
        self.current_ai_status = "READY"

        self.last_warning_time = 0
        self.warning_cooldown = 3

        self.action_cooldown_until = 0
        self.step_changed_at = time.time()

        self.voice_queue = queue.Queue()

        self.voice_thread = threading.Thread(
            target=self.voice_worker,
            daemon=True,
        )
        self.voice_thread.start()

        print()
        print("=" * 60)
        print("🚀 ORBIT-HAR | SYRINGE LIQUID TRANSFER")
        print("=" * 60)
        print(f"Experiment: {self.experiment['name']}")
        print("=" * 60)

    def speak(self, message):
        print(f"🔊 {message}")

        # Keep voice from stacking old messages.
        while not self.voice_queue.empty():
            try:
                self.voice_queue.get_nowait()
                self.voice_queue.task_done()
            except queue.Empty:
                break

        self.voice_queue.put(message)

    def voice_worker(self):
        while True:
            message = self.voice_queue.get()

            try:
                subprocess.run(
                    ["say", message],
                    check=False,
                )
            except Exception:
                pass

            self.voice_queue.task_done()

    def get_current_step(self):
        if self.current_step >= len(self.steps):
            return None

        return self.steps[self.current_step]

    def reset_step_state(self):
        self.step_changed_at = time.time()
        self.action_cooldown_until = (
            time.time() + ACTION_COOLDOWN
        )

    def process_action(self, action):
        if time.time() < self.action_cooldown_until:
            return False

        if self.current_step >= len(self.steps):
            return False

        expected = self.steps[self.current_step]["action"]

        print()
        print("-" * 60)
        print(f"EXPECTED : {expected}")
        print(f"DETECTED : {action}")
        print("-" * 60)

        if action != expected:
            self.current_detected_action = action
            self.current_ai_status = "WRONG ACTION"

            self.wrong_action(action)
            return False

        self.current_detected_action = action
        self.current_ai_status = "VERIFIED"

        completed_step = self.current_step + 1
        completed_instruction = self.steps[
            self.current_step
        ]["instruction"]

        print(f"✅ STEP {completed_step} VERIFIED")

        self.logger.log_step(
            self.steps[self.current_step]["id"],
            action,
            "SUCCESS",
        )

        self.current_step += 1

        if self.current_step >= len(self.steps):
            print()
            print("🎉" * 10)
            print("EXPERIMENT COMPLETE")
            print("🎉" * 10)

            self.current_ai_status = "EXPERIMENT COMPLETE"
            self.current_detected_action = action

            self.logger.complete_experiment()

            send_event({
                "type": "experiment_complete",
                "experiment": self.experiment["name"],
                "step": completed_step,
                "total_steps": len(self.steps),
                "expected_action": expected,
                "detected_action": action,
                "status": "COMPLETE",
            })

            self.speak(
                "Experiment completed successfully."
            )

            return True

        next_step = self.steps[self.current_step]

        self.current_ai_status = "STEP VERIFIED"

        send_event({
            "type": "step_verified",
            "experiment": self.experiment["name"],
            "completed_step": completed_step,
            "completed_action": action,
            "completed_instruction": completed_instruction,
            "current_step": self.current_step + 1,
            "total_steps": len(self.steps),
            "expected_action": next_step["action"],
            "detected_action": "WAITING",
            "status": "VERIFIED",
            "next_action": next_step["action"],
            "next_instruction": next_step["instruction"],
        })

        self.reset_step_state()

        self.current_detected_action = "WAITING"
        self.current_ai_status = "WAITING FOR NEXT STEP"

        self.speak(
            f"Correct. Next step. "
            f"{next_step['instruction']}"
        )

        return True

    def wrong_action(self, detected_action):
        if self.current_step >= len(self.steps):
            return

        expected = self.steps[self.current_step]["action"]

        now = time.time()

        send_event({
            "type": "action_detected",
            "experiment": self.experiment["name"],
            "step": self.current_step + 1,
            "total_steps": len(self.steps),
            "expected_action": expected,
            "detected_action": detected_action,
            "status": "WRONG",
        })

        if now - self.last_warning_time < self.warning_cooldown:
            return

        print()
        print("⚠️ WRONG ACTION")
        print(f"Expected: {expected}")
        print(f"Detected: {detected_action}")

        self.current_ai_status = "WRONG ACTION"

        self.speak(
            f"Incorrect action. Expected {expected}. "
            f"Please perform the correct step."
        )

        self.last_warning_time = now


# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)


# ============================================================
# CAMERA
# ============================================================

camera = cv2.VideoCapture(CAMERA_INDEX)
if not camera.isOpened():
    camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not camera.isOpened():
    print("❌ Camera unavailable")

    send_event({
        "type": "camera_status",
        "active": False,
        "status": "OFFLINE",
    })

    raise SystemExit(1)


# ============================================================
# ORBIT
# ============================================================

orbit = OrbitHAR()

send_event({
    "type": "camera_status",
    "active": True,
    "status": "LIVE",
})


# ============================================================
# TRACKING STATE
# ============================================================

last_syringe_center = None
last_syringe = None

syringe_detect_streak = 0
syringe_lost_streak = 0

interaction_frames = 0

last_frame_time = 0
last_ai_status_time = 0

movement_history = deque(maxlen=20)
syringe_center_history = deque(maxlen=20)

# Home position is learned automatically while the syringe
# is stationary before step 1.
syringe_home_position = None
home_samples = deque(maxlen=20)

# Drawing state
draw_axis_projection_history = deque(maxlen=20)
draw_started_projection = None
draw_baseline_length = None

# Evidence
pick_evidence = 0
insert_a_evidence = 0
draw_evidence = 0
insert_b_evidence = 0
return_evidence = 0

# Step flags
pick_sent = False
insert_a_sent = False
draw_sent = False
insert_b_sent = False
return_sent = False


# ============================================================
# START
# ============================================================

print()
print("🎥 LIVE ORBIT-HAR STARTED")
print("=" * 60)
print("SYRINGE LIQUID TRANSFER")
print("=" * 60)
print("Automatic syringe detection: ON")
print("Automatic container detection: ON")
print("MediaPipe hand tracking: ON")
print("Manual ROI calibration: OFF")
print()
print("Perform the experiment in order.")
print("Press Q to quit.")
print("=" * 60)


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        success, frame = camera.read()

        if not success:
            print("❌ CAMERA READ FAILED")

            send_event({
                "type": "camera_status",
                "active": False,
                "status": "FRAME ERROR",
            })

            break

        height, width, _ = frame.shape
        current_time = time.time()

        hsv = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2HSV,
        )

        # ====================================================
        # DETECT OBJECTS
        # ====================================================

        previous_for_detector = last_syringe_center

        syringe_candidate = detect_syringe(
            hsv,
            previous_for_detector,
        )

        # Temporal confirmation / loss handling.
        if syringe_candidate is not None:
            syringe_detect_streak += 1
            syringe_lost_streak = 0
        else:
            syringe_detect_streak = max(
                0,
                syringe_detect_streak - 1,
            )
            syringe_lost_streak += 1

        syringe = None

        if syringe_candidate is not None:
            if (
                syringe_detect_streak >=
                SYRINGE_DETECT_CONFIRM_FRAMES
            ):
                syringe = syringe_candidate
                last_syringe = syringe_candidate

        elif (
            last_syringe is not None
            and syringe_lost_streak <= SYRINGE_LOST_GRACE_FRAMES
        ):
            # Short detector dropout:
            # keep the last position for action stability.
            syringe = last_syringe

        else:
            last_syringe = None

        syringe_bbox = (
            syringe["bbox"]
            if syringe is not None
            else None
        )

        syringe_center = (
            syringe["center"]
            if syringe is not None
            else None
        )

        syringe_length = (
            syringe["length"]
            if syringe is not None
            else None
        )

        # Containers remain automatic.
        container_a_bbox, container_a_center = detect_container(
            hsv,
            CONTAINER_A_HSV_LOWER,
            CONTAINER_A_HSV_UPPER,
        )

        container_b_bbox, container_b_center = detect_container(
            hsv,
            CONTAINER_B_HSV_LOWER,
            CONTAINER_B_HSV_UPPER,
        )

        # ====================================================
        # MOVEMENT
        # ====================================================

        current_movement = 0.0

        if (
            syringe_center is not None
            and last_syringe_center is not None
        ):
            current_movement = distance(
                syringe_center,
                last_syringe_center,
            )

        if syringe_center is not None:
            last_syringe_center = syringe_center
            syringe_center_history.append(
                syringe_center
            )

        movement_history.append(
            current_movement
        )

        # ====================================================
        # HAND TRACKING
        # ====================================================

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB,
        )

        hand_result = hands.process(rgb)

        hand_detected = bool(
            hand_result.multi_hand_landmarks
        )

        closest_distance = float("inf")
        closest_hand = None

        if hand_result.multi_hand_landmarks:

            for hand in hand_result.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                    frame,
                    hand,
                    mp_hands.HAND_CONNECTIONS,
                )

                # Use several hand landmarks rather than only
                # the index fingertip. This is much more robust
                # when the hand is actually gripping the syringe.
                candidate_points = [
                    hand.landmark[
                        mp_hands.HandLandmark.WRIST
                    ],
                    hand.landmark[
                        mp_hands.HandLandmark.THUMB_TIP
                    ],
                    hand.landmark[
                        mp_hands.HandLandmark.INDEX_FINGER_TIP
                    ],
                    hand.landmark[
                        mp_hands.HandLandmark.MIDDLE_FINGER_TIP
                    ],
                    hand.landmark[
                        mp_hands.HandLandmark.INDEX_FINGER_MCP
                    ],
                    hand.landmark[
                        mp_hands.HandLandmark.MIDDLE_FINGER_MCP
                    ],
                ]

                for landmark in candidate_points:

                    hx = int(
                        landmark.x * width
                    )
                    hy = int(
                        landmark.y * height
                    )

                    if syringe_center is not None:

                        d = distance(
                            (hx, hy),
                            syringe_center,
                        )

                        if d < closest_distance:
                            closest_distance = d
                            closest_hand = (
                                hx,
                                hy,
                            )

        # ====================================================
        # HAND <-> SYRINGE INTERACTION
        # ====================================================

        interacting = False

        if (
            syringe_bbox is not None
            and closest_hand is not None
        ):

            x1, y1, x2, y2 = syringe_bbox

            box_size = max(
                x2 - x1,
                y2 - y1,
            )

            interaction_threshold = max(
                45,
                box_size * HAND_PROXIMITY_MULTIPLIER,
            )

            if closest_distance <= interaction_threshold:
                interacting = True
                interaction_frames += 1
            else:
                interaction_frames = max(
                    0,
                    interaction_frames - 1,
                )

        else:
            interaction_frames = max(
                0,
                interaction_frames - 1,
            )

        interaction_confirmed = (
            interaction_frames >=
            HAND_INTERACTION_CONFIRM_FRAMES
        )

        # ====================================================
        # HOME POSITION
        # ====================================================

        if (
            orbit.current_step == 0
            and not pick_sent
            and syringe_center is not None
            and not interaction_confirmed
            and current_movement <=
                MOVEMENT_STILL_THRESHOLD
        ):

            home_samples.append(
                syringe_center
            )

            if len(home_samples) >= 10:

                xs = [
                    p[0]
                    for p in home_samples
                ]

                ys = [
                    p[1]
                    for p in home_samples
                ]

                syringe_home_position = (
                    int(sum(xs) / len(xs)),
                    int(sum(ys) / len(ys)),
                )

        # ====================================================
        # LIVE ACTIVITY
        # ====================================================

        if syringe_bbox is not None and hand_detected:

            if interaction_confirmed:
                live_ai_activity = (
                    "HAND + SYRINGE INTERACTION"
                )
            else:
                live_ai_activity = (
                    "HAND TRACKING"
                )

        elif syringe_bbox is not None:
            live_ai_activity = (
                "SYRINGE DETECTED"
            )

        elif hand_detected:
            live_ai_activity = (
                "HAND DETECTED"
            )

        else:
            live_ai_activity = (
                "SEARCHING"
            )

        # ====================================================
        # CURRENT STEP
        # ====================================================

        current_step_data = orbit.get_current_step()

        if current_step_data:

            expected_action = (
                current_step_data["action"]
            )

            instruction = (
                current_step_data["instruction"]
            )

        else:

            expected_action = "COMPLETE"
            instruction = (
                "Experiment completed"
            )

        # ====================================================
        # AI STATUS TO DASHBOARD
        # ====================================================

        if (
            current_time - last_ai_status_time
            >= AI_STATUS_INTERVAL
        ):

            send_event({
                "type": "ai_status",
                "experiment": orbit.experiment["name"],
                "step": orbit.current_step + 1,
                "total_steps": len(orbit.steps),
                "expected_action": expected_action,
                "detected_action": orbit.current_detected_action,
                "ai_activity": live_ai_activity,
                "ai_status": orbit.current_ai_status,
                "syringe_detected": syringe_bbox is not None,
                "container_a_detected": (
                    container_a_bbox is not None
                ),
                "container_b_detected": (
                    container_b_bbox is not None
                ),
                "hand_detected": hand_detected,
                "hand_syringe_interaction": interacting,
                "interaction_frames": interaction_frames,
                "movement": round(
                    current_movement,
                    2,
                ),
                "syringe_score": round(
                    syringe["score"],
                    2,
                ) if syringe is not None else 0,
                "syringe_aspect": round(
                    syringe["aspect"],
                    2,
                ) if syringe is not None else 0,
                "instruction": instruction,
            })

            last_ai_status_time = current_time

        # ====================================================
        # STEP COOLDOWN
        # ====================================================

        in_cooldown = (
            current_time <
            orbit.action_cooldown_until
        )

        # ====================================================
        # STEP 1 -- PICK SYRINGE
        #
        # Requires:
        #   - syringe detected
        #   - hand interacting
        #   - syringe movement
        #   - repeated evidence
        #
        # Merely putting a hand near the syringe is not enough.
        # ====================================================

        if (
            not in_cooldown
            and orbit.current_step == 0
            and not pick_sent
        ):

            pick_condition = (
                syringe_center is not None
                and interaction_confirmed
                and current_movement >=
                    PICK_MOVEMENT_THRESHOLD
            )

            if pick_condition:
                pick_evidence += 1
            else:
                pick_evidence = max(
                    0,
                    pick_evidence - 1,
                )

            if (
                pick_evidence >=
                PICK_CONFIRM_FRAMES
            ):

                print(
                    "\n🧠 CONFIRMED: PICK_SYRINGE"
                )

                if orbit.process_action(
                    "PICK_SYRINGE"
                ):

                    pick_sent = True
                    pick_evidence = 0
                    interaction_frames = 0

        # ====================================================
        # STEP 2 -- INSERT CONTAINER A
        # ====================================================

        elif (
            not in_cooldown
            and orbit.current_step == 1
            and not insert_a_sent
        ):

            insert_condition = (
                syringe_center is not None
                and container_a_bbox is not None
                and near_container(
                    syringe_center,
                    container_a_bbox,
                )
                and interaction_confirmed
            )

            if insert_condition:
                insert_a_evidence += 1
            else:
                insert_a_evidence = max(
                    0,
                    insert_a_evidence - 1,
                )

            if (
                insert_a_evidence >=
                INSERT_CONFIRM_FRAMES
            ):

                print(
                    "\n🧠 CONFIRMED: "
                    "INSERT_CONTAINER_A"
                )

                if orbit.process_action(
                    "INSERT_CONTAINER_A"
                ):

                    insert_a_sent = True
                    insert_a_evidence = 0

                    draw_axis_projection_history.clear()
                    draw_started_projection = None

                    if syringe_length is not None:
                        draw_baseline_length = (
                            syringe_length
                        )

        # ====================================================
        # STEP 3 -- DRAW LIQUID
        #
        # We deliberately do NOT assume that a bigger bounding
        # box means liquid was drawn.
        #
        # We watch the syringe's long-axis geometry and require
        # sustained change while the syringe is interacting with
        # Container A.
        # ====================================================

        elif (
            not in_cooldown
            and orbit.current_step == 2
            and not draw_sent
        ):

            still_in_a = (
                syringe_center is not None
                and container_a_bbox is not None
                and near_container(
                    syringe_center,
                    container_a_bbox,
                    multiplier=1.15,
                )
            )

            axis_a, axis_b = syringe_axis_endpoints(
                syringe
            )

            axis_projection = None

            if (
                still_in_a
                and syringe_center is not None
                and axis_a is not None
                and axis_b is not None
            ):

                # Use the midpoint as a stable reference for
                # the syringe's long-axis position.
                axis_projection = estimate_axis_projection(
                    syringe_center,
                    axis_a,
                    axis_b,
                )

                if axis_projection is not None:
                    draw_axis_projection_history.append(
                        axis_projection
                    )

            if (
                still_in_a
                and interaction_confirmed
                and syringe_length is not None
            ):

                if draw_baseline_length is None:
                    draw_baseline_length = (
                        syringe_length
                    )

                length_change = abs(
                    syringe_length -
                    draw_baseline_length
                )

                projection_change = 0

                if (
                    axis_projection is not None
                    and draw_axis_projection_history
                ):

                    recent = list(
                        draw_axis_projection_history
                    )

                    projection_change = (
                        max(recent) -
                        min(recent)
                    )

                draw_condition = (
                    length_change >=
                    DRAW_MIN_PLUNGER_MOVEMENT
                    or
                    projection_change >=
                    DRAW_MIN_PLUNGER_MOVEMENT
                )

                if draw_condition:
                    draw_evidence += 1
                else:
                    draw_evidence = max(
                        0,
                        draw_evidence - 1,
                    )

            else:
                draw_evidence = max(
                    0,
                    draw_evidence - 1,
                )

            if (
                draw_evidence >=
                DRAW_CONFIRM_FRAMES
            ):

                print(
                    "\n🧠 CONFIRMED: DRAW_LIQUID"
                )

                if orbit.process_action(
                    "DRAW_LIQUID"
                ):

                    draw_sent = True
                    draw_evidence = 0

        # ====================================================
        # STEP 4 -- INSERT CONTAINER B
        # ====================================================

        elif (
            not in_cooldown
            and orbit.current_step == 3
            and not insert_b_sent
        ):

            insert_condition = (
                syringe_center is not None
                and container_b_bbox is not None
                and near_container(
                    syringe_center,
                    container_b_bbox,
                )
                and interaction_confirmed
            )

            if insert_condition:
                insert_b_evidence += 1
            else:
                insert_b_evidence = max(
                    0,
                    insert_b_evidence - 1,
                )

            if (
                insert_b_evidence >=
                INSERT_CONFIRM_FRAMES
            ):

                print(
                    "\n🧠 CONFIRMED: "
                    "INSERT_CONTAINER_B"
                )

                if orbit.process_action(
                    "INSERT_CONTAINER_B"
                ):

                    insert_b_sent = True
                    insert_b_evidence = 0

        # ====================================================
        # STEP 5 -- RETURN SYRINGE
        # ====================================================

        elif (
            not in_cooldown
            and orbit.current_step == 4
            and not return_sent
        ):

            # Step 5 is complete when the syringe
            # leaves the camera frame.
            syringe_removed = (
                syringe_center is None
            )

            if syringe_removed:

                return_evidence += 1

            else:

                return_evidence = max(
                    0,
                    return_evidence - 1
                )

            if (
                return_evidence >=
                RETURN_CONFIRM_FRAMES
            ):

                print(
                    "\n🧠 CONFIRMED: "
                    "RETURN_SYRINGE"
                )

                if orbit.process_action(
                    "RETURN_SYRINGE"
                ):

                    return_sent = True
                    return_evidence = 0

        # ====================================================
        # OVERLAYS
        # ====================================================

        # Syringe
        if syringe is not None:

            cv2.drawContours(
                frame,
                [syringe["box_points"]],
                0,
                (255, 255, 255),
                2,
            )

            sx, sy = syringe["center"]

            cv2.circle(
                frame,
                (sx, sy),
                5,
                (255, 255, 255),
                -1,
            )

            cv2.putText(
                frame,
                "SYRINGE",
                (
                    syringe["bbox"][0],
                    max(20, syringe["bbox"][1] - 10),
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

        # Container A
        if container_a_bbox is not None:

            x1, y1, x2, y2 = (
                container_a_bbox
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2,
            )

            cv2.putText(
                frame,
                "CONTAINER A",
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

        # Container B
        if container_b_bbox is not None:

            x1, y1, x2, y2 = (
                container_b_bbox
            )

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 255),
                2,
            )

            cv2.putText(
                frame,
                "CONTAINER B",
                (x1, max(20, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

        # Home position
        if syringe_home_position is not None:

            cv2.circle(
                frame,
                syringe_home_position,
                8,
                (255, 0, 255),
                2,
            )

            cv2.putText(
                frame,
                "HOME",
                (
                    syringe_home_position[0] + 10,
                    syringe_home_position[1],
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 255),
                2,
            )

        # ====================================================
        # STATUS PANEL
        # ====================================================

        if orbit.current_step >= len(orbit.steps):

            status = "EXPERIMENT COMPLETE"

        else:

            step = orbit.steps[
                orbit.current_step
            ]

            status = (
                f"STEP {step['id']}: "
                f"{step['instruction']}"
            )

        cv2.putText(
            frame,
            "ORBIT-HAR",
            (25, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            status[:90],
            (25, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"AI: {live_ai_activity}",
            (25, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"Movement: {int(current_movement)}",
            (25, 128),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"Interaction: {interaction_frames}",
            (25, 154),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"Syringe: "
            f"{'YES' if syringe_bbox else 'NO'}",
            (25, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"A: "
            f"{'YES' if container_a_bbox else 'NO'}   "
            f"B: "
            f"{'YES' if container_b_bbox else 'NO'}",
            (25, 206),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            2,
        )

        # Debug evidence
        cv2.putText(
            frame,
            f"P:{pick_evidence} "
            f"A:{insert_a_evidence} "
            f"D:{draw_evidence} "
            f"B:{insert_b_evidence} "
            f"R:{return_evidence}",
            (25, 232),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            2,
        )

        # ====================================================
        # SEND FRAME
        # ====================================================

        if (
            current_time - last_frame_time
            >= FRAME_INTERVAL
        ):

            send_frame(frame)
            last_frame_time = current_time

        # ====================================================
        # LOCAL PREVIEW
        # ====================================================

        cv2.imshow(
            "ORBIT-HAR | SYRINGE LIQUID TRANSFER",
            frame,
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break


finally:

    frame_sender_running = False

    camera.release()

    try:
        hands.close()
    except ValueError:
        pass

    cv2.destroyAllWindows()

    send_event({
        "type": "camera_status",
        "active": False,
        "status": "OFFLINE",
    })

    print()
    print("🔴 ORBIT-HAR STOPPED")
