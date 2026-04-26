from flask import Flask, request, jsonify, send_from_directory
import json
import os
import threading
import schedule
import time
import requests as req
from datetime import datetime

app = Flask(__name__, static_folder="static")

# ── Paths ──────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATA_FILE    = os.path.join(BASE_DIR, "data", "medicines.json")
VOICES_DIR   = os.path.join(BASE_DIR, "data", "voices")
SETTINGS_FILE= os.path.join(BASE_DIR, "data", "settings.json")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)

# ── Default data ───────────────────────────────────────────
DEFAULT_MEDICINES = [
    {"id": "1", "name": "Metformin",      "quantity": "1 tablet",  "time": "08:00", "note": "After breakfast", "voice": ""},
    {"id": "2", "name": "Aspirin",         "quantity": "1 tablet",  "time": "08:00", "note": "After breakfast", "voice": ""},
    {"id": "3", "name": "Vitamin D",       "quantity": "1 capsule", "time": "13:00", "note": "After lunch",     "voice": ""},
    {"id": "4", "name": "Blood Pressure",  "quantity": "1 tablet",  "time": "21:30", "note": "Before bed",      "voice": ""},
]


DEFAULT_SETTINGS = {
    "bot_token": "8340562347:AAGI60xIhflvaJ8N8OKFfJr7kJZ-uVFAllc",
    "chat_id": "1528050849",
    "bot_active": True
}

# ── Helpers ────────────────────────────────────────────────
def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_medicines():
    return load_json(DATA_FILE, DEFAULT_MEDICINES)

def get_settings():
    return load_json(SETTINGS_FILE, DEFAULT_SETTINGS)

# ── Telegram ───────────────────────────────────────────────
# def send_text(token, chat_id, message):
#     url = f"https://api.telegram.org/bot{token}/sendMessage"
#     try:
#         r = req.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
#         return r.status_code == 200
#     except:
#         return False

def send_text(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = req.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)

        data = r.json()

        print("📩 Telegram Response:", data)   # 👈 IMPORTANT

        return data.get("ok", False)
    except Exception as e:
        print("❌ Error sending message:", e)
        return False
    
def send_voice(token, chat_id, voice_path):
    if not voice_path or not os.path.exists(voice_path):
        return False
    url = f"https://api.telegram.org/bot{token}/sendVoice"
    try:
        with open(voice_path, "rb") as f:
            r = req.post(url, data={"chat_id": chat_id}, files={"voice": f}, timeout=30)
        return r.status_code == 200
    except:
        return False

def build_message(medicines_at_time):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    lines = [
        "💊 <b>Water Reminder</b>",
        f"🕐 <i>{now}</i>",
        "",
        "Please take the following:",
        ""
    ]
    for m in medicines_at_time:
        lines.append(f"  💉 <b>{m['name']}</b> — {m['quantity']}")
        lines.append(f"      📌 {m['note']}")
    lines += ["", "✅ Stay healthy! Love you Appa 🙏"]
    return "\n".join(lines)

def fire_reminder(time_str):
    settings  = get_settings()
    medicines = get_medicines()
    token     = settings.get("bot_token", "")
    chat_id   = settings.get("chat_id", "")

    if not token or not chat_id:
        print(f"[{time_str}] ❌ Bot token or chat ID not set")
        return

    meds = [m for m in medicines if m["time"] == time_str]
    if not meds:
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔔 Firing reminder for {time_str}")

    # Send voice for each unique voice file at this time
    sent_voices = set()
    for m in meds:
        vf = m.get("voice", "")
        if vf and vf not in sent_voices:
            vpath = os.path.join(VOICES_DIR, vf)
            send_voice(token, chat_id, vpath)
            sent_voices.add(vf)

    # Send text
    send_text(token, chat_id, build_message(meds))

# ── Scheduler ──────────────────────────────────────────────
scheduler_lock  = threading.Lock()
scheduler_thread = None
stop_scheduler  = threading.Event()

def rebuild_schedule():
    schedule.clear()
    settings  = get_settings()
    if not settings.get("bot_active"):
        return
    medicines = get_medicines()
    unique_times = set(m["time"] for m in medicines)
    for t in unique_times:
        schedule.every().day.at(t).do(fire_reminder, t)
        print(f"  ⏰ Scheduled {t}")

def run_scheduler():
    while not stop_scheduler.is_set():
        schedule.run_pending()
        time.sleep(20)

def start_scheduler_thread():
    global scheduler_thread
    stop_scheduler.clear()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

# ── API Routes ─────────────────────────────────────────────

# Serve frontend
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# --- Medicines ---
@app.route("/api/medicines", methods=["GET"])
def api_get_medicines():
    return jsonify(get_medicines())

@app.route("/api/medicines", methods=["POST"])
def api_add_medicine():
    data = request.json
    medicines = get_medicines()
    new_id = str(int(max((int(m["id"]) for m in medicines), default=0)) + 1)
    medicine = {
        "id":       new_id,
        "name":     data.get("name", ""),
        "quantity": data.get("quantity", "1 tablet"),
        "time":     data.get("time", "08:00"),
        "note":     data.get("note", ""),
        "voice":    data.get("voice", "")
    }
    medicines.append(medicine)
    save_json(DATA_FILE, medicines)
    rebuild_schedule()
    return jsonify(medicine), 201

@app.route("/api/medicines/<med_id>", methods=["PUT"])
def api_update_medicine(med_id):
    data = request.json
    medicines = get_medicines()
    for m in medicines:
        if m["id"] == med_id:
            m.update({k: data[k] for k in data if k != "id"})
            break
    save_json(DATA_FILE, medicines)
    rebuild_schedule()
    return jsonify({"ok": True})

@app.route("/api/medicines/<med_id>", methods=["DELETE"])
def api_delete_medicine(med_id):
    medicines = [m for m in get_medicines() if m["id"] != med_id]
    save_json(DATA_FILE, medicines)
    rebuild_schedule()
    return jsonify({"ok": True})

# --- Settings ---
@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    s = get_settings()
    # Don't expose full token
    safe = dict(s)
    if safe.get("bot_token"):
        safe["bot_token_set"] = True
        safe["bot_token"] = safe["bot_token"][:8] + "..." if len(safe["bot_token"]) > 8 else "set"
    return jsonify(safe)

@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data     = request.json
    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if "bot_token" in data and data["bot_token"] and "..." not in data["bot_token"]:
        settings["bot_token"] = data["bot_token"]
    if "chat_id" in data:
        settings["chat_id"] = data["chat_id"]
    if "bot_active" in data:
        settings["bot_active"] = data["bot_active"]
    save_json(SETTINGS_FILE, settings)
    rebuild_schedule()
    return jsonify({"ok": True})

# --- Voice upload ---
@app.route("/api/voice/upload", methods=["POST"])
def api_upload_voice():
    if "voice" not in request.files:
        return jsonify({"error": "No file"}), 400
    f        = request.files["voice"]
    label    = request.form.get("label", "recording")
    filename = f"{label}_{int(time.time())}.ogg"
    path     = os.path.join(VOICES_DIR, filename)
    f.save(path)
    return jsonify({"filename": filename})

@app.route("/api/voice/list", methods=["GET"])
def api_list_voices():
    files = [f for f in os.listdir(VOICES_DIR) if f.endswith((".ogg", ".mp3", ".wav"))]
    return jsonify(files)

@app.route("/api/voice/<filename>", methods=["GET"])
def api_get_voice(filename):
    return send_from_directory(VOICES_DIR, filename)

@app.route("/api/voice/<filename>", methods=["DELETE"])
def api_delete_voice(filename):
    path = os.path.join(VOICES_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"ok": True})

# --- Test reminder ---
@app.route("/api/test", methods=["POST"])
def api_test():
    print("🔥 TEST TRIGGERED")   # 👈 debug

    settings  = get_settings()
    token     = settings.get("bot_token", "")
    chat_id   = settings.get("chat_id", "")

    print("TOKEN:", token[:10])
    print("CHAT ID:", chat_id)

    if not token or not chat_id:
        return jsonify({"ok": False, "error": "Bot token or chat ID not configured"}), 400

    ok = send_text(token, chat_id,
        "🤖 <b>Test Message!</b>\nBot is working ✅")

    print("RESULT:", ok)

    return jsonify({"ok": ok})

# ── Start ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  💊 Medicine Reminder Web App")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    rebuild_schedule()
    start_scheduler_thread()
    # app.run(debug=False, port=5000)
    app.run(host="0.0.0.0", port=10000)
