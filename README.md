# 🛡️ CPU Guardian

An automated, self-hosted CPU monitoring dashboard with auto-termination capabilities. Designed to keep your system running smoothly during heavy workloads by intelligently closing unneeded background apps when CPU usage hits critical levels.

Built with Python, Flask, and `psutil`, featuring a sleek, dark-mode glassmorphism UI.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-Web_Dashboard-green?logo=flask)
![Platform](https://img.shields.io/badge/Platform-macOS/Linux-informational)

---

## ✨ Features

*   **Real-time Monitoring:** Live CPU and RAM usage displayed in a beautiful, minimal UI.
*   **Auto-Optimization:** Automatically terminates specific "expendable" or "disposable" apps when CPU usage exceeds 90%.
*   **Priority Kill System:** Kills apps in a smart order (e.g., closes After Effects before closing Zoom).
*   **Click-to-Kill UI:** Click any process in the dashboard to safely kill it via a popup modal.
*   **System Protection:** Built-in protection list prevents accidental termination of critical system processes, IDEs, or terminals.
*   **Manual Override:** "Optimize Now" button to manually sweep and close all target apps.
*   **Native Notifications:** (macOS) Sends native desktop alerts when actions are taken.
*   **Alert History:** In-app scrolling log of all system warnings and terminated processes.

---

## 🛠️ Prerequisites

*   **Python 3.8+**
*   **macOS** (Recommended/Primary target due to specific process names and notification support, but works on Linux with modified config).
*   **pip** (Python package manager)

---

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/cpu-guardian.git
    cd cpu-guardian
    ```

2.  **Create and activate a virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install required dependencies:**
    ```bash
    pip install flask psutil
    ```

4.  **(Optional - macOS Only) Enable Desktop Notifications:**
    ```bash
    pip install pync
    ```

---

## ⚙️ Configuration

Before running, you may want to customize the `CONFIG` dictionary inside `app.py` to match your specific workflow and installed applications.

```python
CONFIG = {
    # Apps that will NEVER be killed
    'protected_apps': ['Google Chrome', 'Code', 'Python', 'System', 'kernel', ...],
    
    # Apps that will be killed FIRST during critical CPU spikes
    'expendable_apps': ['After Effects', 'Spotify', 'Discord'], 
    
    # Apps that will be killed SECOND if expendable apps aren't running
    'disposable_apps': ['Zoom', 'Teams', 'Slack'],
    
    # The CPU percentage that triggers auto-killing
    'cpu_critical_threshold': 90,
    
    # How often the background thread checks CPU (in seconds)
    'check_interval': 2
}
```
*⚠️ **Warning:** Be very careful what you put in `expendable_apps`. If you put your active IDE or unsaved work there, it will be terminated without warning when CPU spikes!*

---

## 🚀 Usage

1.  Run the application:
    ```bash
    python app.py
    ```
2.  Open your web browser and navigate to:
    👉 **http://127.0.0.1:8080**
3.  Leave it running in the background. The guardian thread will monitor your CPU independently of the web dashboard.

---

## 🧠 How It Works (The Logic)

1.  **Background Thread:** A Python `threading.Thread` runs a loop every 2 seconds, checking overall CPU usage.
2.  **Warning State (>70%):** Updates the dashboard banner to yellow and logs a warning.
3.  **Critical State (>90%):** Updates the banner to red and initiates the Kill Sequence:
    *   Scans all running processes, sorted by CPU usage (highest first).
    *   Checks if the process is in the `protected_apps` list. If yes, skips it.
    *   Checks if the process is in `expendable_apps`. If yes, terminates it immediately and stops the loop.
    *   If no expendable apps are found, it checks `disposable_apps` and terminates the highest CPU consumer.
4.  **UI Interaction:** The frontend uses `fetch()` to poll `/api/stats` every 2 seconds. Clicking a process sends a request to `/api/kill/<pid>` after verifying it isn't protected.

---

## 📸 UI Preview

*(You can add a screenshot here by replacing the link below)*
![Dashboard UI](https://via.placeholder.com/400x700?text=CPU+Guardian+UI+Preview)

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change (e.g., porting the protected process list for Windows/Linux).
