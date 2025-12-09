import cv2
import mediapipe as mp
import time
import platform
import ctypes

# --------------- OS MEDIA KEYS (Windows) ----------------
SYSTEM = platform.system()

# Virtual-key codes for media keys
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_UP = 0xAF
VK_VOLUME_DOWN = 0xAE

def send_vk(vk_code, label=""):
    """Send a media key on Windows and print label."""
    if SYSTEM == "Windows":
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.02)
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
    if label:
        print(label)

def play_pause():   send_vk(VK_MEDIA_PLAY_PAUSE, "Play/Pause")
def next_track():   send_vk(VK_MEDIA_NEXT,       "Next track")
def prev_track():   send_vk(VK_MEDIA_PREV,       "Previous track")
def vol_up():       send_vk(VK_VOLUME_UP,        "Volume up")
def vol_down():     send_vk(VK_VOLUME_DOWN,      "Volume down")

# --------------- MEDIAPIPE HANDS SETUP ----------------
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# fingertip indices (MediaPipe)
TIP_IDS = [4, 8, 12, 16, 20]   # thumb, index, middle, ring, pinky

# Cooldown so gestures don't spam
ACTION_COOLDOWN = 1.0
last_action_time = 0.0

# --------------- HELPER: WHICH FINGERS ARE UP ----------------
def fingers_up(landmarks):
    """
    Return list [thumb, index, middle, ring, pinky] as 1 (up) / 0 (down)
    using simple geometric rules.
    """
    fingers = []

    # Thumb: compare x of tip (4) and joint before it (3).
    # Works reasonably on mirrored webcam for right hand.
    if landmarks[TIP_IDS[0]].x < landmarks[TIP_IDS[0] - 1].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # Other fingers: tip.y < pip.y (higher on image) => finger up
    for i in range(1, 5):
        tip = landmarks[TIP_IDS[i]]
        pip = landmarks[TIP_IDS[i] - 2]
        if tip.y < pip.y:
            fingers.append(1)
        else:
            fingers.append(0)

    return fingers

# --------------- MAIN LOOP ----------------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Could not open camera.")
    raise SystemExit

print("Gesture music control started. Press ESC in the video window to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera read failed.")
        break

    frame = cv2.flip(frame, 1)  # mirror view
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, _ = frame.shape
    now = time.time()
    gesture_text = ""

    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        lm = hand_landmarks.landmark

        # Draw landmarks
        mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Which fingers are up?
        f = fingers_up(lm)  # [thumb, index, middle, ring, pinky]
        total_up = sum(f)

        # ---------- INDEX DIRECTION–BASED GESTURES (prev/next/vol down) ----------
        index_tip = lm[8]   # fingertip
        index_base = lm[5]  # base joint

        dx = index_tip.x - index_base.x   # horizontal direction
        dy = index_tip.y - index_base.y   # vertical direction (negative = up)

        index_only = (f[1] == 1 and total_up == 1)

        if index_only:
            # Pointing RIGHT -> Next
            if dx > 0.07 and now - last_action_time > ACTION_COOLDOWN:
                next_track()
                last_action_time = now
                gesture_text = "Next (index RIGHT)"

            # Pointing LEFT -> Previous
            elif dx < -0.07 and now - last_action_time > ACTION_COOLDOWN:
                prev_track()
                last_action_time = now
                gesture_text = "Previous (index LEFT)"

            # Pointing UP (mostly vertical, little horizontal) -> Volume down
            elif dy < -0.07 and abs(dx) < 0.05 and now - last_action_time > ACTION_COOLDOWN:
                vol_down()
                last_action_time = now
                gesture_text = "Volume Down (index UP)"

        # ---------- OTHER STATIC GESTURES ----------
        elif total_up == 5:
            # ✋ Open palm -> Play/Pause
            if now - last_action_time > ACTION_COOLDOWN:
                play_pause()
                last_action_time = now
                gesture_text = "Play/Pause (open palm)"

        elif f[0] == 1 and sum(f[1:]) == 0:
            # 👍 Thumb only -> Like
            if now - last_action_time > ACTION_COOLDOWN:
                print("Liked song (thumbs up)")
                last_action_time = now
                gesture_text = "Like (thumbs up)"

        elif f[1] == 1 and f[2] == 1 and f[0] == 0 and f[3] == 0 and f[4] == 0:
            # ✌ Index + middle -> Volume Up
            if now - last_action_time > ACTION_COOLDOWN:
                vol_up()
                last_action_time = now
                gesture_text = "Volume Up (two fingers)"

    # Show current gesture on screen
    if gesture_text:
        cv2.putText(frame, gesture_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    cv2.imshow("Gesture Music Control", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == 27:   # ESC
        break

cap.release()
cv2.destroyAllWindows()
print("Gesture control stopped.")
