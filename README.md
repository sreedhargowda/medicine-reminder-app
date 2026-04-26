# 💊 MedRemind Web App — Quick Start

## Folder Structure
```
medicine_webapp/
├── app.py              ← Flask backend
├── requirements.txt    ← Python dependencies
├── static/
│   └── index.html      ← Web UI
└── data/               ← Auto-created on first run
    ├── medicines.json
    ├── settings.json
    └── voices/         ← Your recorded .ogg files
```

## Setup (One Time)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## Using the Web App

### ⚙️ Settings Tab (do this first)
1. Get Bot Token from @BotFather on Telegram
2. Get Chat ID (see SETUP_GUIDE.md for steps)
3. Paste both → Save Settings
4. Click "Send Test Message" to verify
5. Toggle "Enable Reminders" ON

### 💊 Medicines Tab
- Click **+ Add Medicine** to add a tablet
- Set name, quantity, time, note, and optionally a voice recording
- Edit ✏️ or Delete 🗑️ any time

### 🎙️ Voice Tab
- Click the mic button → speak → stop
- Label your recording (e.g. "morning", "night")
- Save it
- Now assign it to a medicine in the Medicines tab

---

## Run 24/7 on Windows
Create `start.bat`:
```bat
cd C:\path\to\medicine_webapp
pythonw app.py
```
Add to startup folder: Win+R → shell:startup

## Run 24/7 on Linux/Mac
```bash
nohup python app.py &
```
