import cv2
import requests
import base64
import serial
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# ============================================
# 🔧 FILL IN YOUR DETAILS HERE — CHANGE ONLY
#    THESE LINES, NOTHING ELSE
# ============================================

PLANT_API_KEY   = "GEnMtatc1kQwnJWN17FxFyW8FX53v8ieFC5ARMf5bGZUBo6ySY"

SENDER_EMAIL    = "srinivas79206@gmail.com"
SENDER_PASSWORD = "gkotaidrsubxtocu"    # 16-char app password, no spaces
RECEIVER_EMAIL  = "srinivas79206@gmail.com"

COM_PORT        = "COM12"   # your ESP32 port from Step 5

# ============================================

print("=" * 45)
print("   🌿 Plant Disease Detector")
print("   Desktop Cam + Email Alert System")
print("=" * 45)

# ── Connect to ESP32 ──────────────────────
esp = None
try:
    esp = serial.Serial(COM_PORT, 9600, timeout=3)
    time.sleep(2)
    print(f"✅ ESP32 connected → {COM_PORT}")
except Exception as e:
    print(f"⚠️  ESP32 not found: {e}")
    print("    Running without ESP32...")

# ── Connect to Webcam ─────────────────────
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Webcam not found! Check connection.")
    exit()
print("✅ Webcam ready")
print("\n👉  SPACE = Scan leaf   |   Q = Quit\n")

# ── Email Function ────────────────────────
def send_email(plant_name, disease_name,
               confidence, image_path):
    try:
        print("📧 Sending email alert...")

        msg = MIMEMultipart()
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = RECEIVER_EMAIL
        msg["Subject"] = \
            f"🚨 Plant Disease Alert: {plant_name}"

        body = f"""
Hello,

Your Plant Disease Detection Robot has found an issue!

━━━━━━━━━━━━━━━━━━━━━━━━
🌿 Plant Detected  : {plant_name}
🦠 Disease Found   : {disease_name}
📊 Confidence      : {confidence}%
⏰ Time Detected   : {time.strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  ACTION NEEDED:
Please inspect this plant immediately.
Consider isolating it from other plants
to prevent spread of disease.

The leaf image captured is attached
to this email for your reference.

─────────────────────────
🤖 Plant Disease Detection Robot
   Powered by Plant.id AI
        """

        msg.attach(MIMEText(body, "plain"))

        # Attach the captured leaf image
        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                part = MIMEBase("application",
                                "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=diseased_leaf.jpg"
            )
            msg.attach(part)

        # Send via Gmail
        with smtplib.SMTP_SSL(
                "smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL,
                         SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL,
                            RECEIVER_EMAIL,
                            msg.as_string())

        print("✅ Email sent successfully!")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Email failed: Wrong Gmail/password")
        print("   Check SENDER_EMAIL and SENDER_PASSWORD")
        return False
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

# ── Analyze Leaf Function ─────────────────
def analyze_leaf(frame):

    cv2.imwrite("captured_leaf.jpg", frame)

    _, buffer = cv2.imencode('.jpg', frame)

    image_b64 = base64.b64encode(
        buffer
    ).decode('utf-8')

    print("📤 Sending to Plant.id API...")

    headers = {
        "Api-Key": PLANT_API_KEY,
        "Content-Type": "application/json"
    }

    # =========================
    # 1. Plant Identification
    # =========================

    identify_response = requests.post(

        "https://api.plant.id/v2/identify",

        headers=headers,

        json={
            "images": [image_b64],
            "plant_details": [
                "common_names"
            ]
        },

        timeout=20
    )

    identify_data = identify_response.json()

    # =========================
    # 2. Health Assessment
    # =========================

    health_response = requests.post(

        "https://api.plant.id/v2/health_assessment",

        headers=headers,

        json={
            "images": [image_b64]
        },

        timeout=20
    )

    health_data = health_response.json()

    return identify_data, health_data

# ── Parse API Result ──────────────────────
def parse_result(
        identify_data,
        health_data):

    plant_name   = "Unknown plant"
    disease_name = "Unknown disease"
    confidence   = 0
    command      = "UNKNOWN"

    # =========================
    # Plant Identification
    # =========================

    if identify_data.get("suggestions"):

        top = identify_data[
            "suggestions"
        ][0]

        common = top.get(
            "plant_details",
            {}
        ).get(
            "common_names",
            []
        )

        plant_name = (
            common[0]
            if common
            else top.get(
                "plant_name",
                "Unknown plant"
            )
        )

        confidence = int(
            top.get(
                "probability",
                0
            ) * 100
        )

    # =========================
    # Health Assessment
    # =========================

    health = health_data.get(
        "health_assessment",
        {}
    )

    if health:

        healthy_prob = health.get(
            "is_healthy_probability",
            1.0
        )

        if healthy_prob > 0.5:

            command = "HEALTHY"

        else:

            command = "DISEASED"

            diseases = health.get(
                "diseases",
                []
            )

            if diseases:

                disease = diseases[0]

                disease_name = disease.get(
                    "common_name",
                    disease.get(
                        "name",
                        "Unknown disease"
                    )
                )

    return (
        plant_name,
        disease_name,
        confidence,
        command
    )
# ── Draw UI on Frame ──────────────────────
def draw_ui(frame, status, result_text, color):
    h, w   = frame.shape[:2]
    display = frame.copy()

    cv2.rectangle(display,
                  (0, 0), (w, 135),
                  (20, 20, 20), -1)

    cv2.putText(display, status,
                (15, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 255), 2)

    cv2.putText(display, result_text,
                (15, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72, color, 2)

    cv2.putText(display,
                "SPACE = Scan Leaf  |  Q = Quit",
                (15, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (120, 120, 120), 1)
    return display

# ── Main Loop ─────────────────────────────
status      = "Hold leaf in front of camera"
result_text = "Press SPACE to scan"
color       = (200, 200, 200)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    display = draw_ui(frame, status,
                      result_text, color)
    cv2.imshow("Plant Disease Detector", display)
    key = cv2.waitKey(1) & 0xFF

    # ── SPACE → Scan ──────────────────────
    if key == ord(' '):
        status      = "Analyzing... please wait"
        result_text = ""
        cv2.imshow("Plant Disease Detector",
                   draw_ui(frame, status,
                           result_text, color))
        cv2.waitKey(100)

        try:

            identify_data, health_data = \
                analyze_leaf(frame)

            plant_name, disease_name, \
            confidence, command = \
            parse_result(
                identify_data,
                health_data
            )

            print(f"\n{'='*40}")

            print(f"  Plant   : {plant_name}")
            print(f"  Status  : {command}")
            print(f"  Disease : {disease_name}")
            print(f"  Match   : {confidence}%")

            print(f"{'='*40}\n")
            # Update display
            if command == "HEALTHY":
                result_text = \
                    f"{plant_name}  ->  HEALTHY"
                color  = (0, 220, 0)
                status = \
                    "Plant is healthy! Press SPACE again"

            elif command == "DISEASED":
                result_text = \
                    f"{plant_name}  ->  {disease_name}"
                color  = (0, 0, 255)
                status = \
                    "Disease found! Email sent. Press SPACE again"

                # Send email alert
                send_email(
                    plant_name,
                    disease_name,
                    confidence,
                    "captured_leaf.jpg"
                )

            else:
                result_text = "Could not identify"
                color  = (200, 200, 0)
                status = \
                    "Try again with better lighting"

            # Send to ESP32
            if esp:
                esp.write(
                    (command + '\n').encode())
                print(f"📡 ESP32 notified: {command}")

        except requests.exceptions.Timeout:
            status      = "Timeout - check internet!"
            result_text = "Try again"
            color       = (0, 165, 255)
            print("❌ Request timed out")

        except requests.exceptions.ConnectionError:
            status      = "No internet connection!"
            result_text = "Connect to WiFi and retry"
            color       = (0, 0, 255)
            print("❌ No internet")

        except Exception as e:
            status      = "Error occurred"
            result_text = str(e)[:50]
            color       = (0, 0, 255)
            print(f"❌ Error: {e}")

    # ── Q → Quit ──────────────────────────
    elif key == ord('q'):
        print("👋 Closing...")
        break

# ── Cleanup ───────────────────────────────
cap.release()
cv2.destroyAllWindows()
if esp:
    esp.close()
if os.path.exists("captured_leaf.jpg"):
    os.remove("captured_leaf.jpg")
print("✅ Program closed cleanly.")