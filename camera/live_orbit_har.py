import cv2
import mediapipe as mp
from ultralytics import YOLO
import math
import json
import subprocess
from collections import deque
import threading
import queue
import time
from logger import ExperimentLogger
import requests


# ============================================================
# BACKEND
# ============================================================

BACKEND_URL = "http://127.0.0.1:8000/event"
FRAME_URL = "http://127.0.0.1:8000/frame"


def send_event(data):
    try:
        requests.post(
            BACKEND_URL,
            json=data,
            timeout=0.15
        )
    except requests.RequestException:
        pass


def send_frame(frame):
    try:
        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 70]
        )

        if not success:
            return

        requests.post(
            FRAME_URL,
            data=buffer.tobytes(),
            headers={
                "Content-Type": "image/jpeg"
            },
            timeout=0.12
        )

    except requests.RequestException:
        pass
# ============================================================
# ASYNC FRAME SENDER
# ============================================================

frame_lock = threading.Lock()
latest_frame_to_send = None
frame_sender_running = True


def frame_sender_worker():

    global latest_frame_to_send
    global frame_sender_running

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

            success, buffer = cv2.imencode(
                ".jpg",
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, 70]
            )

            if not success:
                continue

            requests.post(
                FRAME_URL,
                data=buffer.tobytes(),
                headers={
                    "Content-Type": "image/jpeg"
                },
                timeout=0.12
            )

        except requests.RequestException:

            pass


frame_sender_thread = threading.Thread(
    target=frame_sender_worker,
    daemon=True
)

frame_sender_thread.start()


def send_frame(frame):

    global latest_frame_to_send

    with frame_lock:

        # Always keep ONLY the newest frame.
        # Never build up a queue of old frames.
        latest_frame_to_send = frame.copy()


# ============================================================
# CONFIG
# ============================================================

EXPERIMENT_FILE = "experiments/liquid_transfer.json"

# Dashboard status
AI_STATUS_INTERVAL = 0.5

# Dashboard video
# 0.10 = about 10 FPS
# This does NOT control AI detection speed.
FRAME_INTERVAL = 0.10

# MUCH shorter than before
ACTION_COOLDOWN = 0.6

# Faster confirmation
PICK_CONFIRM_FRAMES = 4
TILT_CONFIRM_FRAMES = 3
SHAKE_CONFIRM_FRAMES = 6
UPRIGHT_CONFIRM_FRAMES = 5
PUTDOWN_CONFIRM_FRAMES = 6

# Shake
SHAKE_MOVEMENT_THRESHOLD = 4
SHAKE_REQUIRED_MOVING_FRAMES = 4

# Pick
PICK_MOVEMENT_THRESHOLD = 1.5

# Tilt
TILT_DISPLACEMENT_THRESHOLD = 20

# ============================================================
# YOLO SPEED SETTINGS
# ============================================================

# Run YOLO every N frames instead of every frame.
# This is one of the biggest speed improvements.
YOLO_EVERY_N_FRAMES = 2

# Smaller image = faster inference.
YOLO_IMAGE_SIZE = 512

# Slightly lower confidence makes bottle detection
# more tolerant when the container moves.
YOLO_CONFIDENCE = 0.20

# Keep the last detected bottle for this many frames
# when YOLO temporarily misses it.
BOTTLE_HOLD_FRAMES = 12


# ============================================================
# ORBIT-HAR
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

        # ----------------------------------------------------
        # STATE
        # ----------------------------------------------------

        self.current_detected_action = "WAITING"
        self.current_ai_status = "READY"

        self.last_ai_status_time = 0
        self.last_warning_time = 0

        self.warning_cooldown = 3

        self.action_cooldown_until = 0

        self.step_changed_at = time.time()

        # ----------------------------------------------------
        # VOICE
        # ----------------------------------------------------

        self.voice_queue = queue.Queue()

        self.voice_thread = threading.Thread(
            target=self.voice_worker,
            daemon=True
        )

        self.voice_thread.start()

        print("\n🚀 ORBIT-HAR LIVE SYSTEM")
        print("=" * 55)

        print(
            f"Experiment: {self.experiment['name']}"
        )

        print("=" * 55)

    # ========================================================
    # ========================================================
    # VOICE
    # ========================================================

    def speak(self, message):

        print(f"🔊 {message}")

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
                    check=False
                )

            except Exception:
                pass

            self.voice_queue.task_done()

    # ========================================================
    # CURRENT STEP
    # ========================================================

    def get_current_step(self):

        if self.current_step >= len(self.steps):
            return None

        return self.steps[self.current_step]

    # ========================================================
    # RESET STEP STATE
    # ========================================================

    def reset_step_state(self):

        self.step_changed_at = time.time()

        self.action_cooldown_until = (
            time.time() + ACTION_COOLDOWN
        )

    # ========================================================
    # PROCESS VERIFIED ACTION
    # ========================================================

    def process_action(self, action):

        if time.time() < self.action_cooldown_until:
            return False

        if self.current_step >= len(self.steps):
            return False

        expected = self.steps[
            self.current_step
        ]["action"]

        print()
        print("=" * 55)
        print(f"EXPECTED : {expected}")
        print(f"DETECTED : {action}")
        print("=" * 55)

        # ----------------------------------------------------
        # WRONG ACTION
        # ----------------------------------------------------

        if action != expected:

            self.current_detected_action = action
            expected_instruction = self.steps[self.current_step]["instruction"]
            self.current_ai_status = "WRONG ACTION"

            self.wrong_action(action)

            return False

        # ====================================================
        # VERIFIED
        # ====================================================

        self.current_detected_action = action
        self.current_ai_status = "VERIFIED"
        

        completed_step = self.current_step + 1

        print(
            f"✅ STEP {completed_step} VERIFIED"
        )

        self.logger.log_step(
            self.steps[self.current_step]["id"],
            action,
            "SUCCESS"
        )
        completed_instruction = self.steps[self.current_step]["instruction"]

        # ----------------------------------------------------
        # MOVE TO NEXT STEP
        # ----------------------------------------------------

        self.current_step += 1

        # ----------------------------------------------------
        # EXPERIMENT COMPLETE
        # ----------------------------------------------------

        if self.current_step >= len(self.steps):

            print()
            print("🎉" * 10)
            print("EXPERIMENT COMPLETE")
            print("🎉" * 10)

            self.current_ai_status = (
                "EXPERIMENT COMPLETE"
            )

            self.current_detected_action = action

            self.logger.complete_experiment()

            send_event({
                "type": "experiment_complete",
                "experiment": self.experiment["name"],
                "step": completed_step,
                "total_steps": len(self.steps),
               
                "expected_action": expected,
                "detected_action": action,
                "status": "COMPLETE"
            })

            self.speak(
                "Experiment completed successfully."
            )

            return True

        # ----------------------------------------------------
        # NEXT STEP
        # ----------------------------------------------------

        next_step = self.steps[
            self.current_step
        ]

        self.current_ai_status = "STEP VERIFIED"

        print(
            f"➡️ NEXT STEP: "
            f"{next_step['instruction']}"
        )

        send_event({
            "type": "step_verified",

            "experiment":
                self.experiment["name"],

            "completed_step":
                completed_step,

            "current_step":
                self.current_step + 1,
            "completed_instruction": completed_instruction,

            "total_steps":
                len(self.steps),

            "expected_action":
                next_step["action"],

            "detected_action":
                "WAITING",

            "status":
                "VERIFIED",

            "next_action":
                next_step["action"],

            "next_instruction":
                next_step["instruction"]
        })

        # ----------------------------------------------------
        # SHORT COOLDOWN
        # ----------------------------------------------------

        self.reset_step_state()

        self.current_detected_action = "WAITING"

        self.current_ai_status = (
            "WAITING FOR NEXT STEP"
        )

        self.speak(
            f"Correct. Next step. "
            f"{next_step['instruction']}"
        )

        return True

    # ========================================================
    # WRONG ACTION
    # ========================================================

    def wrong_action(self, detected_action):

        if self.current_step >= len(self.steps):
            return

        expected = self.steps[
            self.current_step
        ]["action"]

        current_time = time.time()

        send_event({
            "type": "action_detected",

            "experiment":
                self.experiment["name"],

            "step":
                self.current_step + 1,

            "total_steps":
                len(self.steps),

            "expected_action":
                expected,

            "detected_action":
                detected_action,

            "status":
                "WRONG"
        })

        # ----------------------------------------------------
        # VOICE COOLDOWN
        # ----------------------------------------------------

        if (
            current_time -
            self.last_warning_time
            < self.warning_cooldown
        ):
            return

        print()
        print("⚠️ WRONG ACTION")

        print(
            f"Expected: {expected}"
        )

        print(
            f"Detected: {detected_action}"
        )

        self.current_ai_status = "WRONG ACTION"

        self.speak(
            f"Incorrect action. "
            f"Expected {expected}. "
            f"Please perform the correct step."
        )

        self.last_warning_time = current_time


# ============================================================
# LOAD YOLO
# ============================================================

print("🤖 Loading ORBIT-HAR AI...")

yolo = YOLO("yolo11n.pt")


# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


# ============================================================
# CAMERA
# ============================================================

# KEEP THIS EXACTLY AS YOUR WORKING VERSION
camera = cv2.VideoCapture(0)

if not camera.isOpened():

    print("❌ Camera unavailable")

    send_event({
        "type":
            "camera_status",

        "active":
            False,

        "status":
            "OFFLINE"
    })

    exit()


# ============================================================
# ORBIT
# ============================================================

orbit = OrbitHAR()


# ============================================================
# CAMERA ONLINE
# ============================================================

send_event({
    "type":
        "camera_status",

    "active":
        True,

    "status":
        "LIVE"
})


# ============================================================
# TRACKING
# ============================================================

bottle_history = deque(maxlen=30)


interaction_history = deque(maxlen=20)

shake_movements = deque(maxlen=12)


interaction_frames = 0

last_bottle_center = None

last_ai_status_time = 0

last_frame_time = 0


# ============================================================
# YOLO TRACKING CACHE
# ============================================================

cached_bottle_box = None

cached_bottle_center = None

bottle_hold_counter = 0

frame_counter = 0


# ============================================================
# EVIDENCE COUNTERS
# ============================================================

pick_evidence = 0

tilt_evidence = 0

shake_evidence = 0

upright_evidence = 0

putdown_evidence = 0

# ============================================================
# STEP 2 — TILT TRACKING
# ============================================================

tilt_ratio_history = deque(maxlen=12)
tilt_baseline_ratio = None
tilt_evidence = 0
tilt_missing_frames = 0
# ============================================================
# STEP FLAGS
# ============================================================

pick_sent = False
tilt_sent = False
shake_sent = False
upright_sent = False
putdown_sent = False


# ============================================================
# START
# ============================================================

print()

print("🎥 LIVE ORBIT-HAR STARTED")

print("=" * 55)

print("Perform the experiment in order.")

print("Press Q to quit.")

print("=" * 55)


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    success, frame = camera.read()

    if not success:

        print("❌ CAMERA READ FAILED")

        send_event({
            "type":
                "camera_status",

            "active":
                False,

            "status":
                "FRAME ERROR"
        })

        break

    height, width, _ = frame.shape

    current_time = time.time()

    frame_counter += 1
    yolo_updated = False

    # ========================================================
    # YOLO
    # FAST CACHED INFERENCE
    # ========================================================

    bottle_box = cached_bottle_box
    bottle_center = cached_bottle_center

    # Only run YOLO every N frames.
    if frame_counter % YOLO_EVERY_N_FRAMES == 0:

        results = yolo(
            frame,
            verbose=False,
            conf=YOLO_CONFIDENCE,
            imgsz=YOLO_IMAGE_SIZE
        )

        detected_box = None
        detected_center = None

        for result in results:

            for box in result.boxes:

                class_id = int(
                    box.cls[0]
                )

                confidence = float(
                    box.conf[0]
                )

                name = yolo.names[
                    class_id
                ]

                if (
                    name == "bottle"
                    and confidence >= YOLO_CONFIDENCE
                ):

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0]
                    )

                    detected_box = (
                        x1,
                        y1,
                        x2,
                        y2
                    )

                    detected_center = (
                        (x1 + x2) // 2,
                        (y1 + y2) // 2
                    )

                    break

        # ----------------------------------------------------
        # YOLO FOUND BOTTLE
        # ----------------------------------------------------

        if detected_center:
            yolo_updated = True
            cached_bottle_box = detected_box
            cached_bottle_center = detected_center

            bottle_hold_counter = (
                BOTTLE_HOLD_FRAMES
            )

        # ----------------------------------------------------
        # YOLO MISSED IT
        # ----------------------------------------------------

        else:

            bottle_hold_counter -= 1

            if bottle_hold_counter <= 0:

                cached_bottle_box = None
                cached_bottle_center = None

            else:

                # Keep previous detection temporarily.
                pass

        bottle_box = cached_bottle_box
        bottle_center = cached_bottle_center

    # ========================================================
    # DRAW CACHED YOLO BOX
    # ========================================================

    if bottle_box:

        x1, y1, x2, y2 = bottle_box

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            "SAMPLE CONTAINER",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )


    # ========================================================
    # HAND TRACKING
    # ========================================================

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    hand_result = hands.process(rgb)

    hand_detected = bool(
        hand_result.multi_hand_landmarks
    )

    closest_distance = float("inf")

    closest_hand = None


    if hand_result.multi_hand_landmarks:

        for hand in (
            hand_result.multi_hand_landmarks
        ):

            mp_draw.draw_landmarks(
                frame,
                hand,
                mp_hands.HAND_CONNECTIONS
            )

            fingertip = hand.landmark[
                mp_hands.HandLandmark.INDEX_FINGER_TIP
            ]

            hx = int(
                fingertip.x * width
            )

            hy = int(
                fingertip.y * height
            )

            if bottle_center:

                distance = math.sqrt(
                    (hx - bottle_center[0]) ** 2
                    +
                    (hy - bottle_center[1]) ** 2
                )

                if distance < closest_distance:

                    closest_distance = distance

                    closest_hand = (
                        hx,
                        hy
                    )


    # ========================================================
    # HAND ↔ CONTAINER
    # ========================================================

    interacting = False

    if bottle_box and closest_hand:

        x1, y1, x2, y2 = bottle_box

        box_size = max(
            x2 - x1,
            y2 - y1
        )

        threshold = box_size * 1.05

        if closest_distance < threshold:

            interacting = True

            interaction_frames += 1

        else:

            interaction_frames = max(
                0,
                interaction_frames - 1
            )

    else:

        interaction_frames = max(
            0,
            interaction_frames - 1
        )


    interaction_history.append(
        interacting
    )


    # ========================================================
    # BOTTLE HISTORY
    # ========================================================

    if bottle_center:

        bottle_history.append(
            bottle_center
        )


    # ========================================================
    # MOVEMENT
    # ========================================================

    current_movement = 0

    if (
        bottle_center
        and last_bottle_center
    ):

        current_movement = math.sqrt(

            (
                bottle_center[0]
                -
                last_bottle_center[0]
            ) ** 2

            +

            (
                bottle_center[1]
                -
                last_bottle_center[1]
            ) ** 2
        )


    if bottle_center:

        last_bottle_center = (
            bottle_center
        )


    # ========================================================
    # RESET EVIDENCE AFTER STEP CHANGE
    # ========================================================

    if (
        current_time -
        orbit.step_changed_at
        < ACTION_COOLDOWN
    ):

        pick_evidence = 0
        tilt_evidence = 0
        shake_evidence = 0
        upright_evidence = 0
        putdown_evidence = 0

        shake_movements.clear()


    # ========================================================
    # LIVE AI ACTIVITY
    # ========================================================

    if bottle_box and hand_detected:

        if interacting:

            live_ai_activity = (
                "HAND + CONTAINER INTERACTION"
            )

        else:

            live_ai_activity = (
                "HAND TRACKING"
            )

    elif bottle_box:

        live_ai_activity = (
            "CONTAINER DETECTED"
        )

    elif hand_detected:

        live_ai_activity = (
            "HAND DETECTED"
        )

    else:

        live_ai_activity = (
            "SEARCHING"
        )


    # ========================================================
    # CURRENT EXPECTED ACTION
    # ========================================================

    current_step_data = (
        orbit.get_current_step()
    )

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


    # ========================================================
    # SEND LIVE AI STATUS
    # ========================================================

    if (
        current_time -
        last_ai_status_time
        >= AI_STATUS_INTERVAL
    ):

        send_event({

            "type":
                "ai_status",

            "experiment":
                orbit.experiment["name"],

            "step":
                orbit.current_step + 1,

            "total_steps":
                len(orbit.steps),

            "expected_action":
                expected_action,

            "detected_action":
                orbit.current_detected_action,

            "ai_activity":
                live_ai_activity,

            "ai_status":
                orbit.current_ai_status,

            "bottle_detected":
                bottle_box is not None,

            "hand_detected":
                hand_detected,

            "hand_container_interaction":
                interacting,

            "interaction_frames":
                interaction_frames,

            "movement":
                round(
                    current_movement,
                    2
                ),

            "instruction":
                instruction
        })

        last_ai_status_time = (
            current_time
        )


    # ========================================================
    # ACTION COOLDOWN
    # ========================================================

    if current_time < orbit.action_cooldown_until:

        pass


    # ========================================================
    # STEP 1 — PICK CONTAINER
    # ========================================================

    #elif (
     #   orbit.current_step == 0
      #  and not pick_sent
    #):

     #   if (
      #      interacting
       #     and interaction_frames >= 2
        #    and current_movement >= PICK_MOVEMENT_THRESHOLD
        #):

         #   pick_evidence += 1

        #else:

         #   pick_evidence = max(
          #      0,
           #     pick_evidence - 1
            #)


        #if pick_evidence >= PICK_CONFIRM_FRAMES:

         #   print(
          #      "\n🧠 CONFIRMED: PICK_CONTAINER"
           # )

           # if orbit.process_action(
            #    "PICK_CONTAINER"
            #):

             #   pick_sent = True

              #  bottle_history.clear()

               # shake_movements.clear()

                #last_bottle_center = None
    # ========================================================
    # STEP 1 — PICK CONTAINER
    # ========================================================

    elif (
        orbit.current_step == 0
        and not pick_sent
    ):

        # Picking is primarily:
        # 1. Hand is interacting with container
        # 2. Container starts moving
        #
        # We don't require large frame-to-frame movement because
        # YOLO is intentionally not running every frame anymore.

        if (
            interacting
            and interaction_frames >= 3
        ):
            pick_evidence += 1

        else:
            pick_evidence = max(
                0,
                pick_evidence - 1
            )

        if pick_evidence >= PICK_CONFIRM_FRAMES:

            print(
                "\n🧠 CONFIRMED: PICK_CONTAINER"
            )

            if orbit.process_action(
                "PICK_CONTAINER"
            ):

                pick_sent = True

                pick_evidence = 0

                bottle_history.clear()

                shake_movements.clear()

                last_bottle_center = None

                print(
                    "✅ PICK CONTAINER VERIFIED"
                )


    # ========================================================
    # STEP 2 — TILT CONTAINER
    # ========================================================

    if (
        orbit.current_step == 1
        and not tilt_sent
    ):

        # ----------------------------------------------------
        # INITIALIZE TILT STATE
        # ----------------------------------------------------

        if not hasattr(orbit, "tilt_baseline_ratio"):

            orbit.tilt_baseline_ratio = None
            orbit.tilt_evidence = 0
            orbit.tilt_missing_frames = 0
            orbit.tilt_last_ratio = None


        # ----------------------------------------------------
        # CONTAINER DETECTED
        # ----------------------------------------------------

        if bottle_box:

            x1, y1, x2, y2 = bottle_box

            box_width = max(
                x2 - x1,
                1
            )

            box_height = max(
                y2 - y1,
                1
            )

            current_ratio = (
                box_width /
                box_height
            )


            # ------------------------------------------------
            # KEEP RATIO HISTORY
            # ------------------------------------------------

            tilt_ratio_history.append(
                current_ratio
            )

            orbit.tilt_missing_frames = 0


            # ------------------------------------------------
            # ESTABLISH UPRIGHT BASELINE
            # ------------------------------------------------

            if orbit.tilt_baseline_ratio is None:

                orbit.tilt_baseline_ratio = (
                    current_ratio
                )

                orbit.tilt_last_ratio = (
                    current_ratio
                )

                orbit.tilt_evidence = 0


            baseline = (
                orbit.tilt_baseline_ratio
            )


            # ------------------------------------------------
            # SMOOTH CURRENT RATIO
            # ------------------------------------------------

            if len(tilt_ratio_history) >= 3:

                sorted_ratios = sorted(
                    tilt_ratio_history
                )

                middle = len(
                    sorted_ratios
                ) // 2

                smoothed_ratio = (
                    sorted_ratios[middle]
                )

            else:

                smoothed_ratio = (
                    current_ratio
                )


            # ------------------------------------------------
            # TILT CHANGE
            # ------------------------------------------------

            ratio_change = (
                smoothed_ratio -
                baseline
            )


            # ------------------------------------------------
            # TILT EVIDENCE
            #
            # A tilted container becomes wider relative
            # to its height in the camera view.
            # ------------------------------------------------

            if ratio_change > 0.10:

                orbit.tilt_evidence += 1

            else:

                orbit.tilt_evidence = max(
                    0,
                    orbit.tilt_evidence - 1
                )


            # ------------------------------------------------
            # ALSO ACCEPT STRONG MOVEMENT
            #
            # This helps when the bbox geometry changes
            # only slightly but the container is clearly
            # being moved by the astronaut.
            # ------------------------------------------------

            strong_motion = (
                current_movement > 12
            )


            if (
                interacting
                and strong_motion
                and ratio_change > 0.06
            ):

                orbit.tilt_evidence += 1


            # ------------------------------------------------
            # CONFIRM TILT
            # ------------------------------------------------

            if (
                interacting
                and orbit.tilt_evidence
                >= TILT_CONFIRM_FRAMES
            ):

                print()
                print(
                    "🧠 CONFIRMED: "
                    "TILT_CONTAINER"
                )

                print(
                    f"Baseline ratio: "
                    f"{baseline:.2f}"
                )

                print(
                    f"Current ratio: "
                    f"{smoothed_ratio:.2f}"
                )

                print(
                    f"Ratio change: "
                    f"{ratio_change:.2f}"
                )

                if orbit.process_action(
                    "TILT_CONTAINER"
                ):

                    tilt_sent = True

                    orbit.tilt_evidence = 0

                    tilt_ratio_history.clear()

                    print(
                        "✅ TILT CONTAINER VERIFIED"
                    )


            orbit.tilt_last_ratio = (
                current_ratio
            )


        # ----------------------------------------------------
        # YOLO TEMPORARILY LOST CONTAINER
        # ----------------------------------------------------

        else:

            orbit.tilt_missing_frames += 1

            # Do NOT immediately reset the tilt baseline.
            #
            # YOLO can miss the container for a few frames
            # while it is rotating.
            #
            # Keep the accumulated evidence alive.

            if (
                orbit.tilt_missing_frames
                <= BOTTLE_HOLD_FRAMES
            ):

                orbit.tilt_evidence = max(
                    0,
                    orbit.tilt_evidence - 0
                )

            else:

                # Only after a genuinely long loss do
                # we reset the baseline.

                orbit.tilt_baseline_ratio = None

                orbit.tilt_last_ratio = None

                orbit.tilt_evidence = 0

                tilt_ratio_history.clear()
    # ============================================================
    # STEP 3 — SHAKE CONTAINER
    # ============================================================

    elif (
        orbit.current_step == 2
        and not shake_sent
    ):

        # Only record movement when YOLO produced
        # a genuinely new bottle position.
        if (
            yolo_updated
            and bottle_center
            and interacting
        ):

            shake_movements.append(
                current_movement
            )


        moving_frames = sum(
            1
            for movement in shake_movements
            if movement > SHAKE_MOVEMENT_THRESHOLD
        )


        if (
            len(shake_movements) >= SHAKE_CONFIRM_FRAMES
            and moving_frames >= SHAKE_REQUIRED_MOVING_FRAMES
        ):

            print(
                "\n🧠 CONFIRMED: "
                "SHAKE_CONTAINER"
            )

            if orbit.process_action(
                "SHAKE_CONTAINER"
            ):

                shake_sent = True

                shake_movements.clear()

                bottle_history.clear()

                last_bottle_center = None
    # ========================================================
    # STEP 4 — RETURN UPRIGHT
    # ========================================================

    elif (
        orbit.current_step == 3

        and bottle_box

        and not upright_sent
    ):

        x1, y1, x2, y2 = bottle_box

        box_width = x2 - x1

        box_height = y2 - y1

        ratio = (
            box_width /
            max(box_height, 1)
        )


        if ratio < 0.70:

            upright_evidence += 1

        else:

            upright_evidence = max(
                0,
                upright_evidence - 1
            )


        if (
            upright_evidence
            >= UPRIGHT_CONFIRM_FRAMES
        ):

            print(
                "\n🧠 CONFIRMED: RETURN_UPRIGHT"
            )

            if orbit.process_action(
                "RETURN_UPRIGHT"
            ):

                upright_sent = True

                bottle_history.clear()

                shake_movements.clear()

                last_bottle_center = None


    # ========================================================
    # STEP 5 — PUT CONTAINER DOWN
    # ========================================================

    elif (
        orbit.current_step == 4

        and bottle_center

        and not putdown_sent
    ):

        recent_movements = list(
            bottle_history
        )


        if len(recent_movements) >= 10:

            old_x, old_y = (
                recent_movements[0]
            )

            new_x, new_y = (
                recent_movements[-1]
            )


            total_movement = math.sqrt(

                (new_x - old_x) ** 2
                +
                (new_y - old_y) ** 2
            )


            recent_no_hand = (
                sum(
                    interaction_history
                )
                <= 3
            )


            if (
                total_movement < 15

                and recent_no_hand
            ):

                putdown_evidence += 1

            else:

                putdown_evidence = max(
                    0,
                    putdown_evidence - 1
                )


        if (
            putdown_evidence
            >= PUTDOWN_CONFIRM_FRAMES
        ):

            print(
                "\n🧠 CONFIRMED: "
                "PUT_CONTAINER_DOWN"
            )

            if orbit.process_action(
                "PUT_CONTAINER_DOWN"
            ):

                putdown_sent = True

    # ============================================================
    # WRONG ACTION MONITOR
    # ============================================================

    elif (
        orbit.current_step >= 2
        and orbit.current_step != 2
        and bottle_center
        and interacting
    ):

        shake_movements.append(
            current_movement
        )

        moving_frames = sum(
            1
            for movement in shake_movements
            if movement > SHAKE_MOVEMENT_THRESHOLD
        )

        if (
            len(shake_movements)
            >= SHAKE_CONFIRM_FRAMES

            and moving_frames
            >= SHAKE_REQUIRED_MOVING_FRAMES
        ):

            print(
                "\n⚠️ CONFIRMED "
                "OUT-OF-SEQUENCE SHAKE"
            )

            orbit.wrong_action(
                "SHAKE_CONTAINER"
            )

            shake_movements.clear()
    # ========================================================
    # STATUS TEXT
    # ========================================================

    if orbit.current_step >= len(orbit.steps):

        status = (
            "🎉 EXPERIMENT COMPLETE"
        )

    else:

        step = orbit.steps[
            orbit.current_step
        ]

        status = (
            f"STEP {step['id']}: "
            f"{step['instruction']}"
        )


    # ========================================================
    # OPENCV UI
    # ========================================================

    cv2.putText(
        frame,
        "ORBIT-HAR",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        status,
        (30, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"Movement: "
        f"{int(current_movement)}",
        (30, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    cv2.putText(
        frame,
        f"AI: {live_ai_activity}",
        (30, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    # ========================================================
    # SEND FRAME TO BROWSER
    # ========================================================

    if (
        current_time -
        last_frame_time
        >= FRAME_INTERVAL
    ):

        send_frame(frame)

        last_frame_time = (
            current_time
        )


    # ========================================================
    # LOCAL OPENCV PREVIEW
    # ========================================================

    cv2.imshow(
        "ORBIT-HAR | LIVE EXPERIMENT",
        frame
    )


    # ========================================================
    # QUIT
    # ========================================================

    if (
        cv2.waitKey(1) & 0xFF
        == ord("q")
    ):

        break


# ============================================================
# CLEANUP
# ============================================================
frame_sender_running = False
camera.release()

try:
    hands.close()

except ValueError:
    pass

cv2.destroyAllWindows()


# ============================================================
# CAMERA OFFLINE
# ============================================================

send_event({
    "type":
        "camera_status",

    "active":
        False,

    "status":
        "OFFLINE"
})


print()

print("🔴 ORBIT-HAR STOPPED")