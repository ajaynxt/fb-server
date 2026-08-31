"""
Flask Web Server & Dashboard Controller for Facebook Messenger Persistent Bot
Provides: Modern Web UI, REST APIs, SSE Live Log Streaming, and Keep-Alive Monitoring.
"""

import os
import time
import json
from io import BytesIO
import requests
from flask import Flask, render_template, request, jsonify, Response, send_file
from fb_engine import bot_runner, multi_manager, parse_cookies, FacebookSession
import data_manager

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload size
SERVER_START_TIME = time.time()


@app.route("/")
def index():
    """Renders the main control dashboard."""
    return render_template("index.html")


@app.route("/health")
@app.route("/ping")
def health():
    """Keep-alive health endpoint for 24/7 uptime monitors (e.g. UptimeRobot, cron)."""
    server_uptime = int(time.time() - SERVER_START_TIME)
    h, rem = divmod(server_uptime, 3600)
    m, s = divmod(rem, 60)
    return jsonify({
        "status": "healthy",
        "server_uptime": f"{h:02d}:{m:02d}:{s:02d}",
        "bot_status": bot_runner.status,
        "bot_running": bot_runner.is_running,
        "timestamp": int(time.time()),
    }), 200


@app.route("/api/check_ip", methods=["GET", "POST"])
def check_ip():
    """Checks outgoing IP and geo-location for Cloud Server or Custom Indian Proxy."""
    data = request.get_json(silent=True) or request.args or request.form or {}
    proxy = data.get("proxy", "").strip() if isinstance(data, dict) else ""
    session = requests.Session()
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    try:
        res = session.get("https://ipapi.co/json/", timeout=4)
        if res.status_code == 200:
            ip_info = res.json()
            return jsonify({
                "success": True,
                "ip": ip_info.get("ip"),
                "country": ip_info.get("country_name", "India"),
                "country_code": ip_info.get("country_code", "IN"),
                "city": ip_info.get("city", ""),
                "org": ip_info.get("org", "")
            })
    except Exception:
        try:
            res = session.get("https://api.ipify.org?format=json", timeout=3)
            if res.status_code == 200:
                return jsonify({
                    "success": True,
                    "ip": res.json().get("ip"),
                    "country": "Cloud Host",
                    "country_code": "US",
                    "city": "",
                    "org": ""
                })
        except Exception:
            pass

    return jsonify({
        "success": True,
        "ip": "Local/Proxy Gateway",
        "country": "India (Gateway)",
        "country_code": "IN",
        "city": "",
        "org": ""
    }), 200


@app.route("/api/validate_cookie", methods=["POST"])
def validate_cookie():
    """Validates FB cookie and returns account info."""
    data = request.get_json(silent=True) or {}
    cookie_str = data.get("cookies", "").strip()

    if not cookie_str:
        return jsonify({"success": False, "message": "Cookie khali hai."}), 400

    parsed = parse_cookies(cookie_str)
    if not parsed:
        return jsonify({"success": False, "message": "Cookie format invalid hai."}), 400

    session = FacebookSession(parsed)
    valid, msg = session.validate_and_extract_tokens()

    return jsonify({
        "success": valid,
        "message": msg,
        "user_name": session.user_name if valid else None,
        "user_id": session.user_id if valid else None,
    })


@app.route("/api/start", methods=["POST"])
def start_bot():
    """Starts the bot loop with supplied cookies, target, and messages."""
    # Check if form-data or JSON
    if request.is_json:
        data = request.get_json()
        cookies_input = data.get("cookies", "")
        target_id = data.get("target_id", "")
        target_type = data.get("target_type", "personal")
        messages_raw = data.get("messages", "")
        prefix = data.get("prefix", "")
        proxy = data.get("proxy", "")
        task_mode = data.get("task_mode", "chat")
        trigger_mode = data.get("trigger_mode", "loop")
        typing_delay = data.get("typing_delay", 3)
        message_delay = data.get("message_delay", 5)
        infinite_loop = data.get("infinite_loop", True)

        if isinstance(messages_raw, list):
            messages = [m for m in messages_raw if str(m).strip()]
        else:
            messages = [line.strip() for line in str(messages_raw).split("\n") if line.strip()]

    else:
        cookies_input = request.form.get("cookies", "")
        target_id = request.form.get("target_id", "")
        target_type = request.form.get("target_type", "personal")
        task_mode = request.form.get("task_mode", "chat")
        trigger_mode = request.form.get("trigger_mode", "loop")
        messages_text = request.form.get("messages", "")
        prefix = request.form.get("prefix", "")
        proxy = request.form.get("proxy", "")
        typing_delay = float(request.form.get("typing_delay", 2.0) or 2.0)
        message_delay = float(request.form.get("message_delay", 5.0) or 5.0)
        run_duration_mins = float(request.form.get("run_duration", 0.0) or 0.0)
        infinite_loop = request.form.get("infinite_loop", "true").lower() in ["true", "1", "on", "yes"]

        # Check for uploaded cookie file
        if "cookie_file" in request.files:
            file = request.files["cookie_file"]
            if file and file.filename != "":
                cookies_input = file.read().decode("utf-8", errors="ignore")

        # Check for uploaded messages file
        messages = []
        if "messages_file" in request.files:
            file = request.files["messages_file"]
            if file and file.filename != "":
                content = file.read().decode("utf-8", errors="ignore")
                messages = [line.strip() for line in content.split("\n") if line.strip()]

        if not messages and messages_text:
            messages = [line.strip() for line in messages_text.split("\n") if line.strip()]

    success, message = bot_runner.start(
        cookies_input=cookies_input,
        target_id=target_id,
        target_type=target_type,
        messages=messages,
        prefix=prefix,
        typing_delay=typing_delay,
        message_delay=message_delay,
        infinite_loop=infinite_loop,
        task_mode=task_mode,
        trigger_mode=trigger_mode,
        run_duration_mins=run_duration_mins,
        proxy=proxy
    )

    return jsonify({"success": success, "message": message}), (200 if success else 400)


@app.route("/api/stop", methods=["POST"])
def stop_bot():
    """Stops the bot immediately (like PythonAnywhere Stop)."""
    success, message = bot_runner.stop()
    return jsonify({"success": success, "message": message})


@app.route("/api/pause", methods=["POST"])
def pause_bot():
    """Pauses the running bot."""
    success, message = bot_runner.pause()
    return jsonify({"success": success, "message": message})


@app.route("/api/resume", methods=["POST"])
def resume_bot():
    """Resumes the paused bot."""
    success, message = bot_runner.resume()
    return jsonify({"success": success, "message": message})


@app.route("/api/update_speed", methods=["POST"])
def update_speed():
    """Updates speed (message delay and typing delay) on the fly without stopping."""
    data = request.get_json(silent=True) or request.form or {}
    typing_delay = data.get("typing_delay")
    message_delay = data.get("message_delay")

    success, msg = bot_runner.update_speed(
        typing_delay=int(typing_delay) if typing_delay is not None else None,
        message_delay=int(message_delay) if message_delay is not None else None
    )
    return jsonify({"success": success, "message": msg})


@app.route("/api/status", methods=["GET"])
def get_status():
    """Returns current live statistics."""
    task_id = request.args.get("task_id", "default")
    srv = multi_manager.get_server(task_id)
    status_data = srv.get_status()
    status_data["all_servers"] = multi_manager.list_servers()
    status_data["total_running"] = sum(1 for s in multi_manager.servers.values() if s.is_running)
    return jsonify(status_data)


@app.route("/api/servers", methods=["GET"])
def get_servers():
    """Returns list of all configured server instances."""
    return jsonify({
        "success": True,
        "servers": multi_manager.list_servers(),
        "total_servers": len(multi_manager.servers),
        "running_servers": sum(1 for s in multi_manager.servers.values() if s.is_running)
    })


@app.route("/api/servers/create", methods=["POST"])
def create_server():
    """Creates a new parallel server instance."""
    data = request.get_json(silent=True) or request.form or {}
    task_name = data.get("task_name", "").strip()
    srv = multi_manager.create_server(task_name=task_name)
    return jsonify({
        "success": True,
        "task_id": srv.task_id,
        "task_name": srv.task_name,
        "message": f"New server '{srv.task_name}' created!"
    })


@app.route("/api/servers/<task_id>/start", methods=["POST"])
def start_server_instance(task_id):
    """Starts a specific server instance, automatically inheriting master token if needed."""
    srv = multi_manager.get_server(task_id)
    if request.is_json:
        data = request.get_json()
        cookies_input = data.get("cookies", "") or multi_manager.master_token
        target_id = data.get("target_id", "")
        target_type = data.get("target_type", "personal")
        messages_raw = data.get("messages", "")
        prefix = data.get("prefix", "")
        proxy = data.get("proxy", "")
        task_mode = data.get("task_mode", "chat")
        trigger_mode = data.get("trigger_mode", "loop")
        typing_delay = float(data.get("typing_delay", 2.0) or 2.0)
        message_delay = float(data.get("message_delay", 5.0) or 5.0)
        run_duration_mins = float(data.get("run_duration", 0.0) or 0.0)
        infinite_loop = data.get("infinite_loop", True)
        if isinstance(messages_raw, list):
            messages = [m for m in messages_raw if str(m).strip()]
        else:
            messages = [line.strip() for line in str(messages_raw).split("\n") if line.strip()]
    else:
        cookies_input = request.form.get("cookies", "") or multi_manager.master_token
        target_id = request.form.get("target_id", "")
        target_type = request.form.get("target_type", "personal")
        task_mode = request.form.get("task_mode", "chat")
        trigger_mode = request.form.get("trigger_mode", "loop")
        messages_text = request.form.get("messages", "")
        prefix = request.form.get("prefix", "")
        proxy = request.form.get("proxy", "")
        typing_delay = float(request.form.get("typing_delay", 2.0) or 2.0)
        message_delay = float(request.form.get("message_delay", 5.0) or 5.0)
        run_duration_mins = float(request.form.get("run_duration", 0.0) or 0.0)
        infinite_loop = request.form.get("infinite_loop", "true").lower() in ["true", "1", "on", "yes"]
        messages = [line.strip() for line in messages_text.split("\n") if line.strip()]

    if cookies_input:
        multi_manager.set_master_token(cookies_input)

    success, message = srv.start(
        cookies_input=cookies_input,
        target_id=target_id,
        target_type=target_type,
        messages=messages,
        prefix=prefix,
        typing_delay=typing_delay,
        message_delay=message_delay,
        infinite_loop=infinite_loop,
        task_mode=task_mode,
        trigger_mode=trigger_mode,
        run_duration_mins=run_duration_mins,
        proxy=proxy
    )
    return jsonify({"success": success, "message": message, "task_id": task_id})


@app.route("/api/servers/<task_id>/stop", methods=["POST"])
def stop_server_instance(task_id):
    srv = multi_manager.get_server(task_id)
    success, message = srv.stop()
    return jsonify({"success": success, "message": message, "task_id": task_id})


@app.route("/api/servers/<task_id>/delete", methods=["DELETE", "POST"])
def delete_server_instance(task_id):
    success = multi_manager.delete_server(task_id)
    return jsonify({"success": success, "message": f"Server {task_id} deleted." if success else "Failed to delete server."})


@app.route("/api/servers/stop_all", methods=["POST"])
def stop_all_servers():
    count = multi_manager.stop_all()
    return jsonify({"success": True, "message": f"All {count} running servers stopped!"})


@app.route("/api/logs", methods=["GET"])
def stream_logs():
    """
    Server-Sent Events (SSE) live streaming logs to client web interface.
    """
    def event_stream():
        # First send existing history
        for entry in bot_runner.logs_history[-30:]:
            yield f"data: {json.dumps(entry)}\n\n"

        # Stream new events as they arrive
        while True:
            try:
                log_entry = bot_runner.log_queue.get(timeout=25)
                yield f"data: {json.dumps(log_entry)}\n\n"
            except Exception:
                # Send heartbeat comment to keep connection alive
                yield ": heartbeat\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


@app.route("/api/clear_logs", methods=["POST"])
def clear_logs():
    """Clears logs history."""
    bot_runner.logs_history.clear()
    bot_runner.add_log("🧹 Logs history cleared.", "INFO")
    return jsonify({"success": True})


@app.route("/api/download_logs", methods=["GET"])
def download_logs():
    """Downloads log history as a text file."""
    lines = []
    for log in bot_runner.logs_history:
        lines.append(f"[{log['timestamp']}] [{log['level']}] {log['message']}")
    content = "\n".join(lines)
    mem_file = BytesIO(content.encode("utf-8"))
    mem_file.seek(0)
    return send_file(
        mem_file,
        as_attachment=True,
        download_name=f"fb_bot_logs_{int(time.time())}.txt",
        mimetype="text/plain"
    )


# ==============================================================================
# SECURE BACKEND STORAGE APIs (Cookie Profiles, Message Files, Config)
# ==============================================================================

@app.route("/api/profiles", methods=["GET", "POST"])
def handle_cookie_profiles():
    """Lists saved cookie profiles (GET) or saves a new one (POST)."""
    if request.method == "GET":
        return jsonify({"success": True, "profiles": data_manager.list_cookie_profiles()})

    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    cookies = data.get("cookies", "").strip()
    user_name = data.get("user_name", "")
    user_id = data.get("user_id", "")

    if not cookies:
        return jsonify({"success": False, "message": "Cookies khali hain."}), 400

    success = data_manager.save_cookie_profile(name, cookies, user_name, user_id)
    return jsonify({
        "success": success,
        "message": "Cookie profile server storage me successfully save ho gaya!" if success else "Save failed."
    })


@app.route("/api/profiles/<name>", methods=["GET", "DELETE"])
def handle_single_profile(name):
    """Retrieves (GET) or deletes (DELETE) a saved cookie profile."""
    if request.method == "DELETE":
        success = data_manager.delete_cookie_profile(name)
        return jsonify({"success": success, "message": "Profile deleted."})

    profile = data_manager.get_cookie_profile(name)
    if profile:
        return jsonify({"success": True, "profile": profile})
    return jsonify({"success": False, "message": "Profile not found."}), 404


@app.route("/api/files", methods=["GET", "POST"])
def handle_message_files():
    """Lists saved message files (GET) or saves a new text file (POST)."""
    if request.method == "GET":
        return jsonify({"success": True, "files": data_manager.list_message_files()})

    if "file" in request.files:
        uploaded_file = request.files["file"]
        if uploaded_file and uploaded_file.filename != "":
            content = uploaded_file.read().decode("utf-8", errors="ignore")
            success = data_manager.save_message_file(uploaded_file.filename, content)
            return jsonify({"success": success, "message": f"File '{uploaded_file.filename}' save ho gayi!"})

    data = request.get_json(silent=True) or {}
    filename = data.get("filename", "").strip()
    content = data.get("content", "").strip()

    if not filename or not content:
        return jsonify({"success": False, "message": "Filename aur content dono zaroori hain."}), 400

    success = data_manager.save_message_file(filename, content)
    return jsonify({"success": success, "message": f"Message file '{filename}' save ho gayi!"})


@app.route("/api/files/<filename>", methods=["GET", "DELETE"])
def handle_single_file(filename):
    """Retrieves (GET) content or deletes (DELETE) a message file."""
    if request.method == "DELETE":
        success = data_manager.delete_message_file(filename)
        return jsonify({"success": success, "message": "File deleted."})

    content = data_manager.get_message_file_content(filename)
    if content:
        return jsonify({"success": True, "filename": filename, "content": content})
    return jsonify({"success": False, "message": "File not found."}), 404


@app.route("/api/config", methods=["GET", "POST"])
def handle_config():
    """Retrieves or saves default form preferences on server."""
    if request.method == "GET":
        return jsonify({"success": True, "config": data_manager.get_config()})

    data = request.get_json(silent=True) or {}
    success = data_manager.save_config(data)
    return jsonify({"success": success})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🔥 Starting FB Messenger Persistent Server on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
