
"""
calibrate_hsv.py
 
Standalone helper to find good HSV lower/upper bounds for:
  - the syringe (default: light / low-saturation object)
  - Container A (green)
  - Container B (yellow)
 
Run it, point the camera at the object, and drag the trackbars until
ONLY that object is white in the "mask" window (everything else black).
Print the final numbers into orbit_har_syringe.py's CONFIG section.
 
Usage:
    python calibrate_hsv.py syringe
    python calibrate_hsv.py container_a
    python calibrate_hsv.py container_b
"""
 
import sys
import cv2
import numpy as np
 
TARGET = sys.argv[1] if len(sys.argv) > 1 else "syringe"
 
DEFAULTS = {
    "syringe":     (0, 0, 150, 180, 60, 255),
    "container_a": (40, 40, 40, 80, 255, 255),   # green
    "container_b": (20, 100, 100, 35, 255, 255), # yellow
}
 
h_lo, s_lo, v_lo, h_hi, s_hi, v_hi = DEFAULTS.get(TARGET, DEFAULTS["syringe"])
 
WINDOW = f"Calibrate: {TARGET}"
cv2.namedWindow(WINDOW)
 
 
def nothing(_):
    pass
 
 
cv2.createTrackbar("H min", WINDOW, h_lo, 180, nothing)
cv2.createTrackbar("H max", WINDOW, h_hi, 180, nothing)
cv2.createTrackbar("S min", WINDOW, s_lo, 255, nothing)
cv2.createTrackbar("S max", WINDOW, s_hi, 255, nothing)
cv2.createTrackbar("V min", WINDOW, v_lo, 255, nothing)
cv2.createTrackbar("V max", WINDOW, v_hi, 255, nothing)
 
camera = cv2.VideoCapture(0)
 
if not camera.isOpened():
    print("Camera unavailable")
    sys.exit(1)
 
print(f"Tuning HSV range for: {TARGET}")
print("Adjust sliders until only the target object is white in the mask window.")
print("Press 'p' to print current values, 'q' to quit.")
 
while True:
    ok, frame = camera.read()
    if not ok:
        break
 
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
 
    h_lo = cv2.getTrackbarPos("H min", WINDOW)
    h_hi = cv2.getTrackbarPos("H max", WINDOW)
    s_lo = cv2.getTrackbarPos("S min", WINDOW)
    s_hi = cv2.getTrackbarPos("S max", WINDOW)
    v_lo = cv2.getTrackbarPos("V min", WINDOW)
    v_hi = cv2.getTrackbarPos("V max", WINDOW)
 
    lower = np.array([h_lo, s_lo, v_lo])
    upper = np.array([h_hi, s_hi, v_hi])
 
    mask = cv2.inRange(hsv, lower, upper)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
 
    result = cv2.bitwise_and(frame, frame, mask=mask)
 
    stacked = np.hstack([frame, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR), result])
    cv2.imshow(WINDOW, stacked)
 
    key = cv2.waitKey(1) & 0xFF
 
    if key == ord("q"):
        break
 
    if key == ord("p"):
        print(
            f'"{TARGET}": lower=({h_lo}, {s_lo}, {v_lo}), '
            f'upper=({h_hi}, {s_hi}, {v_hi})'
        )
 
camera.release()
cv2.destroyAllWindows()