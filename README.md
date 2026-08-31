# ⚡ Facebook Messenger 24/7 Persistent Server & Bot

Ek powerful, crash-proof aur fully automated Facebook Messenger bot server jo **Cookies (AppState / Cookie String)** ke sath kaam karta hai. Ye 24/7 non-stop chalne ke liye design kiya gaya hai.

---

## 🌟 Key Features

1. **🔄 Infinite File Loop (Non-Stop)**:
   - Message file (.txt) ki sabhi lines complete hote hi automatically **Line 1 se dobara shuru** ho jata hai bina ruke.
2. **👁️ Real-time Auto-Seen**:
   - Har message send karne se pehle chat par **Mark-as-Seen (Read Receipt)** trigger hota hai.
3. **⌨️ Facebook Real-Time Typing Indicator**:
   - Message send karne se pehle recipient ko live **"Typing..."** dikhta hai.
4. **⚡ Live Speed & Delay Controls**:
   - Message delay aur typing duration ko web interface se **Live (running state me bhi) adjust** kiya ja sakta hai.
   - Quick Presets: Ultra Fast (1s/2s), Fast (2s/5s), Normal (3s/10s), Safe (5s/20s).
5. **⏹️ PythonAnywhere Style Instant Controls**:
   - One-click **START**, **STOP**, **PAUSE**, aur **RESUME** buttons.
6. **🛡️ 24/7 Watchdog Supervisor**:
   - Agar internet disconnect ya network error aaye toh server crash nahi hota, balki auto-retry aur auto-restart hota hai.
7. **🖥️ Modern Cyberpunk Dark Web Dashboard**:
   - Real-time Server-Sent Events (SSE) Live colored terminal logs, active counters, FB account validator, aur file uploaders.

---

## 🚀 How to Run Locally (Mac / Linux / Windows)

### Step 1: Start the Server
Terminal me command chalayein:
```bash
./run.sh
```
Ya direct:
```bash
source venv/bin/activate
python3 supervisor.py
```

### Step 2: Open Dashboard in Browser
Browser me open karein:
👉 **`http://localhost:8080`** ya **`http://127.0.0.1:8080`**

---

## 🌐 24/7 Free Cloud Hosting (PythonAnywhere / Render / VPS)

### Option 1: PythonAnywhere (24/7 Web App)
1. [PythonAnywhere.com](https://www.pythonanywhere.com) par free account banayein.
2. **Files** tab me jakar project files upload karein ya Bash Console me clone/copy karein.
3. **Web** tab me **Add a new web app** -> **Manual configuration** -> **Python 3.9/3.10** choose karein.
4. WSGI configuration file me ye add karein:
   ```python
   import sys
   path = '/home/yourusername/server'
   if path not in sys.path:
       sys.path.append(path)

   from server import app as application
   ```
5. **Reload** button dabayein. Aapka server 24/7 chalega!

### Option 2: Render.com / VPS / Replit
1. Web Service create karein:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python3 server.py`
2. 24/7 active rakhne ke liye [UptimeRobot.com](https://uptimerobot.com) par free HTTP monitor lagayein URL par:
   `https://your-app-name.onrender.com/health`

---

## 📁 File Structure

```
├── fb_engine.py          # Core FB auth, mark-seen, typing, and message loop engine
├── server.py             # Flask Web API, SSE streaming, and route controller
├── supervisor.py         # 24/7 watchdog supervisor that auto-restarts on crashes
├── run.sh                # 1-click startup bash script
├── requirements.txt      # Python dependencies (Flask, requests, urllib3)
├── messages_sample.txt   # Sample message text file
├── cookies_guide.txt     # Guide on how to export FB cookies
├── templates/
│   └── index.html        # Web dashboard UI
├── static/
│   ├── css/style.css     # Dark theme styles & terminal design
│   └── js/app.js         # Frontend controller, live SSE, and slider handlers
└── README.md             # Complete user guide
```

---

## 🔒 Security & Privacy
- Aapki cookies keval aapke local/server memory me process hoti hain aur kisi third-party server par share nahi hoti.
