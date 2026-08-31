"""
Flask Web Server & Dashboard Controller for Facebook Messenger Persistent Bot
Provides: Modern Web UI, REST APIs, SSE Live Log Streaming, and Keep-Alive Monitoring.
"""

import os
import time
import json
from flask import Flask, render_template, request, jsonify, Response, send_file
from io import BytesIO
from fb_engine import bot_runner, parse_cookies, FacebookSession

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
        task_mode = data.get("task_mode", "chat")
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
        messages_text = request.form.get("messages", "")
        prefix = request.form.get("prefix", "")
        typing_delay = int(request.form.get("typing_delay", 3))
        message_delay = int(request.form.get("message_delay", 5))
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
        task_mode=task_mode
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
    return jsonify(bot_runner.get_status())


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🔥 Starting FB Messenger Persistent Server on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
