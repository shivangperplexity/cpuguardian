import time
import os
import psutil
import threading
from flask import Flask, render_template_string, jsonify
from datetime import datetime
# shivanghehe
# Try to import macOS notifications
try:
    from pync import Notifier
    MACOS_NOTIFS = True
except ImportError:
    MACOS_NOTIFS = False
    print("pync not installed or not on macOS. Desktop notifications disabled.")

app = Flask(__name__)

# --- Configuration & State ---
MY_PID = os.getpid()

CONFIG = {
    'protected_apps': [
        'Google Chrome', 'Code', 'Python', 'System', 'kernel', 
        'WindowServer', 'Terminal', 'iTerm', 'bash', 'zsh'
    ],
    'expendable_apps': ['After Effects', 'Spotify', 'Discord'], # Kill these FIRST
    'disposable_apps': ['Zoom', 'Teams', 'Slack'],
    'cpu_critical_threshold': 90,
    'check_interval': 2
}

alert_history = []
current_status = {"level": "stable", "message": "System Normal"}

# --- HTML Template (Your Requested UI with Click-to-Kill Logic Added) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CPU Guardian Dashboard</title>
    <style>
        :root {
            --bg-color: #1c1c1e;
            --card-bg: #2c2c2e;
            --text-color: #ffffff;
            --text-secondary: #8e8e93;
            --green: #30d158;
            --yellow: #ffd60a;
            --red: #ff453a;
            --blue: #0a84ff;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .container {
            width: 400px;
            background-color: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            position: relative; /* For modal positioning context */
        }

        h2 {
            margin-top: 0;
            text-align: center;
            font-weight: 600;
            margin-bottom: 20px;
        }

        /* Status Header */
        .status-header {
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 15px;
            font-weight: bold;
            font-size: 18px;
            transition: background-color 0.3s;
        }

        .status-stable { background-color: var(--green); color: black; }
        .status-warning { background-color: var(--yellow); color: black; }
        .status-critical { background-color: var(--red); animation: pulse 1s infinite; }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 15px;
        }

        .card {
            background-color: var(--card-bg);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
        }

        .card-title {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        .card-value {
            font-size: 32px;
            font-weight: 700;
        }

        /* Process List */
        .process-list {
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 10px;
            margin-bottom: 15px;
        }

        .process-item {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 14px;
            cursor: pointer; /* Indicates clickable */
            transition: background 0.2s;
        }
        .process-item:hover { background: rgba(255,255,255,0.05); }
        .process-item:last-child { border-bottom: none; }

        /* Buttons */
        .btn {
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 12px;
            background-color: var(--blue);
            color: white;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            margin-bottom: 15px;
        }
        .btn:hover { opacity: 0.9; }

        /* Alerts Log */
        .log-container {
            max-height: 150px;
            overflow-y: auto;
            font-size: 12px;
            color: var(--text-secondary);
        }
        .log-entry {
            margin-bottom: 5px;
            padding: 5px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
        }
        .log-time { color: var(--blue); margin-right: 5px; }
        .log-level-warning { color: var(--yellow); }
        .log-level-critical { color: var(--red); }
        .log-level-action { color: #bf5af2; } /* Purple for action */
        .log-level-success { color: var(--green); }

        /* Modal (Popup) Styles - Hidden by default */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            display: none; /* Hidden initially */
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-content {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 20px;
            width: 300px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
        .modal-title { font-size: 20px; font-weight: bold; margin-bottom: 15px; }
        .modal-btn-group { display: flex; gap: 10px; margin-top: 20px; }
        .modal-btn {
            flex: 1;
            padding: 10px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-cancel { background: #3a3a3c; color: white; }
        .btn-kill { background: var(--red); color: white; }
    </style>
</head>
<body>

<div class="container">
    <h2>🛡️ CPU Guardian</h2>

    <!-- Top Status Banner -->
    <div id="status-banner" class="status-header status-stable">
        System Normal
    </div>

    <!-- Stats Grid -->
    <div class="grid">
        <div class="card">
            <div class="card-title">CPU Usage</div>
            <div class="card-value" id="cpu-val">0%</div>
        </div>
        <div class="card">
            <div class="card-title">RAM Usage</div>
            <div class="card-value" id="ram-val">0%</div>
        </div>
    </div>

    <!-- Process Table -->
    <div class="process-list">
        <div class="card-title" style="padding-left:5px;">Top Processes (Click to Manage)</div>
        <div id="process-container">
            <!-- Filled by JS -->
        </div>
    </div>

    <!-- Emergency Button -->
    <button class="btn" onclick="triggerOptimize()">⚡ Optimize Now</button>

    <!-- Alert History -->
    <div class="process-list" style="background: transparent; padding: 0;">
        <div class="card-title">ALERT HISTORY</div>
        <div class="log-container" id="log-container">
            <div class="log-entry">System initialized...</div>
        </div>
    </div>
</div>

<!-- The Popup Modal (Hidden) -->
<div id="kill-modal" class="modal-overlay">
    <div class="modal-content">
        <div class="modal-title" id="modal-title">Process Name</div>
        <div style="color:var(--text-secondary);">
            PID: <span id="modal-pid"></span><br>
            CPU: <span id="modal-cpu"></span>%
        </div>
        <div class="modal-btn-group">
            <button class="modal-btn btn-cancel" onclick="closeModal()">Cancel</button>
            <button class="modal-btn btn-kill" onclick="confirmKill()">Force Kill</button>
        </div>
    </div>
</div>

<script>
    let selectedPid = null;

    // Request permission for browser notifications
    if (Notification.permission !== "granted") {
        Notification.requestPermission();
    }

    function fetchData() {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                updateDashboard(data);
            });
    }

    function updateDashboard(data) {
        // 1. Update Text Values
        document.getElementById('cpu-val').innerText = data.stats.cpu + '%';
        document.getElementById('ram-val').innerText = data.stats.ram + '%';

        // 2. Update Status Banner
        const banner = document.getElementById('status-banner');
        banner.className = 'status-header status-' + data.status.level;
        banner.innerText = data.status.message;

        // Color logic for text
        if(data.status.level === 'critical') {
            document.getElementById('cpu-val').style.color = 'var(--red)';
        } else if (data.status.level === 'warning') {
            document.getElementById('cpu-val').style.color = 'var(--yellow)';
        } else {
            document.getElementById('cpu-val').style.color = 'var(--green)';
        }

        // 3. Update Process List (Added Click Logic)
        const procContainer = document.getElementById('process-container');
        procContainer.innerHTML = '';
        data.stats.processes.forEach(p => {
            const div = document.createElement('div');
            div.className = 'process-item';
            div.innerHTML = `<span>${p.name}</span><span>${p.cpu_percent.toFixed(1)}%</span>`;
            
            // Add click listener to open modal
            div.onclick = () => openModal(p.name, p.pid, p.cpu_percent.toFixed(1));
            
            procContainer.appendChild(div);
        });

        // 4. Update Logs
        const logContainer = document.getElementById('log-container');
        logContainer.innerHTML = '';
        data.alerts.forEach(a => {
            const div = document.createElement('div');
            div.className = 'log-entry';
            div.innerHTML = `<span class="log-time">${a.time}</span> <span class="log-level-${a.level.toLowerCase()}">[${a.level}]</span> ${a.message}`;
            logContainer.appendChild(div);
        });
    }

    function triggerOptimize() {
        fetch('/api/optimize')
            .then(response => response.json())
            .then(data => {
                alert("Optimization Complete: " + data.message);
            });
    }

    // --- Modal Logic ---
    function openModal(name, pid, cpu) {
        selectedPid = pid;
        document.getElementById('modal-title').innerText = name;
        document.getElementById('modal-pid').innerText = pid;
        document.getElementById('modal-cpu').innerText = cpu;
        document.getElementById('kill-modal').style.display = 'flex';
    }

    function closeModal() {
        document.getElementById('kill-modal').style.display = 'none';
        selectedPid = null;
    }

    function confirmKill() {
        if(selectedPid) {
            fetch('/api/kill/' + selectedPid)
                .then(res => res.json())
                .then(data => {
                    alert(data.message);
                    closeModal();
                    fetchData(); // Refresh immediately
                });
        }
    }

    // Poll every 2 seconds
    setInterval(fetchData, 2000);
    fetchData();
</script>

</body>
</html>
"""

# --- Logic Functions ---

def log_alert(level, message, details=""):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
        "details": details
    }
    alert_history.insert(0, entry)
    if len(alert_history) > 20:
        alert_history.pop()
    
    if MACOS_NOTIFS:
        try:
            Notifier.notify(message, title=f"CPU Guardian - {level}", sound='default')
        except Exception as e:
            print(f"Notification error: {e}")

def get_system_stats():
    cpu_percent = psutil.cpu_percent(interval=1)
    ram_percent = psutil.virtual_memory().percent
    
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            p_info = proc.info
            if p_info['cpu_percent'] is None:
                p_info['cpu_percent'] = 0.0
            processes.append(p_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    processes = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:10]
    
    return {"cpu": cpu_percent, "ram": ram_percent, "processes": processes}

def is_protected(proc_name, pid):
    if pid == MY_PID:
        return True
    p_name = proc_name.lower()
    for p in CONFIG['protected_apps']:
        if p.lower() in p_name:
            return True
    return False

def guardian_loop():
    while True:
        stats = get_system_stats()
        cpu = stats['cpu']
        
        if cpu > CONFIG['cpu_critical_threshold']:
            current_status['level'] = "critical"
            current_status['message'] = f"Critical CPU Load: {cpu}%"
            
            killed = False
            
            # Priority 1: Expendable Apps (After Effects, etc)
            for proc in stats['processes']:
                p_name = proc['name']
                pid = proc['pid']
                
                if is_protected(p_name, pid):
                    continue
                    
                is_expendable = any(d.lower() in p_name.lower() for d in CONFIG['expendable_apps'])
                
                if is_expendable and proc['cpu_percent'] > 0:
                    try:
                        p = psutil.Process(pid)
                        p.terminate()
                        msg = f"Auto-closed {p_name} (Priority Target) to save CPU."
                        log_alert("ACTION", msg, f"PID {pid} terminated")
                        current_status['message'] = msg
                        killed = True
                        break 
                    except Exception as e:
                        print(f"Failed to kill {p_name}: {e}")

            # Priority 2: Disposable Apps
            if not killed:
                for proc in stats['processes']:
                    p_name = proc['name']
                    pid = proc['pid']
                    
                    if is_protected(p_name, pid):
                        continue
                        
                    is_disposable = any(d.lower() in p_name.lower() for d in CONFIG['disposable_apps'])
                    
                    if is_disposable and proc['cpu_percent'] > 0:
                        try:
                            p = psutil.Process(pid)
                            p.terminate()
                            msg = f"Auto-closed {p_name} to save CPU."
                            log_alert("ACTION", msg, f"PID {pid} terminated")
                            current_status['message'] = msg
                            killed = True
                            break
                        except Exception as e:
                            print(f"Failed to kill {p_name}: {e}")
            
            if not killed:
                log_alert("CRITICAL", f"CPU at {cpu}%", "No disposable apps found to close.")

        elif cpu > 70:
            current_status['level'] = "warning"
            current_status['message'] = f"High CPU Usage: {cpu}%"
            if len(alert_history) == 0 or alert_history[0]['level'] != 'WARNING':
                 log_alert("WARNING", "High CPU Detected", "Monitoring closely")

        else:
            current_status['level'] = "stable"
            current_status['message'] = "System Normal"

        time.sleep(CONFIG['check_interval'])

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    stats = get_system_stats()
    return jsonify({
        "stats": stats,
        "status": current_status,
        "alerts": alert_history
    })

@app.route('/api/kill/<int:pid>')
def api_kill(pid):
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        
        if is_protected(name, pid):
            return jsonify({"success": False, "message": "Cannot kill protected system process."})
            
        proc.terminate()
        log_alert("ACTION", f"Manually killed {name}", f"PID {pid}")
        return jsonify({"success": True, "message": f"Process {name} terminated."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/optimize')
def optimize():
    stats = get_system_stats()
    killed_list = []
    
    targets = CONFIG['expendable_apps'] + CONFIG['disposable_apps']
    
    for proc in stats['processes']:
        p_name = proc['name']
        pid = proc['pid']
        
        if is_protected(p_name, pid):
            continue
        
        for target in targets:
            if target.lower() in p_name.lower():
                try:
                    p = psutil.Process(pid)
                    p.terminate()
                    killed_list.append(p_name)
                except:
                    pass
    
    msg = f"Optimized: Closed {', '.join(killed_list)}"
    log_alert("SUCCESS", "Manual Optimization Triggered", msg)
    return jsonify({"result": "success", "message": msg})

if __name__ == '__main__':
    t = threading.Thread(target=guardian_loop)
    t.daemon = True
    t.start()
    
    print("CPU Guardian Running... Open http://127.0.0.1:8080")
    app.run(debug=True, port=8080)
