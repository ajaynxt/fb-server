"""
Server-side Secure Data & File Manager
Handles persistent storage of cookies, message files, and configurations in a protected data directory.
"""

import os
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIES_DIR = os.path.join(DATA_DIR, "cookies")
MESSAGES_DIR = os.path.join(DATA_DIR, "messages")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# Ensure secure storage directories exist
os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(MESSAGES_DIR, exist_ok=True)


def init_storage():
    """Initializes storage directories and default config."""
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "admin_pin": "1234",
            "last_target_id": "",
            "last_target_type": "personal",
            "last_task_mode": "chat",
            "last_trigger_mode": "reply_seen",
            "last_typing_delay": 2,
            "last_message_delay": 5,
            "last_prefix": "",
        }
        save_config(default_config)


def get_config() -> dict:
    """Reads persistent server configuration."""
    init_storage()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config_data: dict) -> bool:
    """Saves updated server configuration."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def save_cookie_profile(name: str, cookies: str, user_name: str = "", user_id: str = "") -> bool:
    """Saves a cookie session profile securely on the server."""
    if not name:
        name = f"profile_{int(time.time())}"
    clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
    file_path = os.path.join(COOKIES_DIR, f"{clean_name}.json")
    
    data = {
        "profile_name": clean_name,
        "user_name": user_name,
        "user_id": user_id,
        "cookies": cookies,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def list_cookie_profiles() -> list:
    """Lists all saved cookie profiles on the server."""
    profiles = []
    if not os.path.exists(COOKIES_DIR):
        return profiles

    for fname in os.listdir(COOKIES_DIR):
        if fname.endswith(".json"):
            fpath = os.path.join(COOKIES_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    profiles.append({
                        "profile_name": data.get("profile_name", fname.replace(".json", "")),
                        "user_name": data.get("user_name", "FB Account"),
                        "user_id": data.get("user_id", ""),
                        "saved_at": data.get("saved_at", ""),
                    })
            except Exception:
                pass
    return profiles


def get_cookie_profile(name: str) -> dict:
    """Retrieves full cookie profile data."""
    clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
    file_path = os.path.join(COOKIES_DIR, f"{clean_name}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def delete_cookie_profile(name: str) -> bool:
    """Deletes a saved cookie profile."""
    clean_name = "".join(c for c in name if c.isalnum() or c in ("-", "_")).strip()
    file_path = os.path.join(COOKIES_DIR, f"{clean_name}.json")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception:
            pass
    return False


def save_message_file(filename: str, content: str) -> bool:
    """Saves a message text file permanently to server storage."""
    clean_filename = "".join(c for c in filename if c.isalnum() or c in ("-", "_", ".")).strip()
    if not clean_filename.endswith(".txt"):
        clean_filename += ".txt"
        
    file_path = os.path.join(MESSAGES_DIR, clean_filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False


def list_message_files() -> list:
    """Lists saved message files on the server."""
    files = []
    if not os.path.exists(MESSAGES_DIR):
        return files

    for fname in os.listdir(MESSAGES_DIR):
        if fname.endswith(".txt"):
            fpath = os.path.join(MESSAGES_DIR, fname)
            try:
                size = os.path.getsize(fpath)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                files.append({
                    "filename": fname,
                    "total_lines": len(lines),
                    "size_bytes": size,
                    "preview": lines[:3],
                })
            except Exception:
                pass
    return files


def get_message_file_content(filename: str) -> str:
    """Reads saved message file content."""
    clean_filename = "".join(c for c in filename if c.isalnum() or c in ("-", "_", ".")).strip()
    file_path = os.path.join(MESSAGES_DIR, clean_filename)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            pass
    return ""


def delete_message_file(filename: str) -> bool:
    """Deletes a saved message file."""
    clean_filename = "".join(c for c in filename if c.isalnum() or c in ("-", "_", ".")).strip()
    file_path = os.path.join(MESSAGES_DIR, clean_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return True
        except Exception:
            pass
    return False

init_storage()
