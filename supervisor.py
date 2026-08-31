"""
24/7 Watchdog Supervisor for FB Messenger Server
Monitors the server process and automatically restarts it if it crashes or terminates.
"""

import sys
import os
import time
import subprocess
import signal

SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
PYTHON_EXEC = sys.executable

def log(msg):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [SUPERVISOR] {msg}", flush=True)

def run_supervisor():
    log(f"🛡️ 24/7 Supervisor started! Monitoring: {SERVER_SCRIPT}")
    log(f"🐍 Python Runtime: {PYTHON_EXEC}")

    process = None

    def handle_signal(sig, frame):
        log("Received termination signal. Shutting down gracefully...")
        if process:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                process.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    restart_count = 0

    while True:
        try:
            log(f"🚀 Launching server (Instance #{restart_count + 1})...")
            start_time = time.time()
            
            process = subprocess.Popen(
                [PYTHON_EXEC, SERVER_SCRIPT],
                stdout=sys.stdout,
                stderr=sys.stderr,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )

            # Wait for process to exit
            ret_code = process.wait()
            duration = time.time() - start_time
            restart_count += 1

            log(f"⚠️ Server exited with code {ret_code} after running for {duration:.1f} seconds.")

            # If it crashed too quickly (< 2s), back off slightly to prevent CPU spin
            if duration < 2:
                log("Server exited immediately. Waiting 3 seconds before restart...")
                time.sleep(3)
            else:
                time.sleep(1)

            log("🔄 Auto-restarting server now...")

        except KeyboardInterrupt:
            handle_signal(None, None)
            break
        except Exception as e:
            log(f"Supervisor error: {e}. Retrying in 2 seconds...")
            time.sleep(2)

if __name__ == "__main__":
    run_supervisor()
