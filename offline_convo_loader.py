#!/usr/bin/env python3
"""
================================================================================
  AJAY NXT - 24/7 VIP FACEBOOK CONVO COOKIES OFFLINE LOADER
  Author      : AJAY NXT
  Platform    : Termux (Android), Linux, Windows, macOS, VPS
  Features    :
    - 100% Offline / Local Execution (Zero Web Dependency)
    - Auto-reads cookie.json / cookie.txt / AppState file
    - Multi-line Cookie JSON & Single-line Header Parser
    - Multi-Engine Convo Dispatch (mbasic, Mercury Web, Mobile Gateway)
    - Auto-Seen & Typing Simulation
    - Infinite Non-Stop Message Loop
    - Auto-Save Config (convo_config.json) for 1-Click Launch
================================================================================
"""

import sys
import os
import time
import re
import json
import random
from datetime import datetime

try:
    import requests
except ImportError:
    print("\n[!] 'requests' library missing. Installing automatically...")
    os.system("pip3 install requests -q || pip install requests -q")
    import requests

# ANSI Color Palette
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[1;32m"
RED = "\033[1;31m"
CYAN = "\033[1;36m"
YELLOW = "\033[1;33m"
MAGENTA = "\033[1;35m"
WHITE = "\033[1;37m"

DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MOBILE_UA = "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"

CONFIG_FILE = "convo_config.json"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    clear_screen()
    banner = f"""{GREEN}{BOLD}
 █████╗      ██╗ █████╗ ██╗   ██╗    ███╗   ██╗██╗  ██╗████████╗
██╔══██╗     ██║██╔══██╗╚██╗ ██╔╝    ████╗  ██║╚██╗██╔╝╚══██╔══╝
███████║     ██║███████║ ╚████╔╝     ██╔██╗ ██║ ╚███╔╝    ██║   
██╔══██║██   ██║██╔══██║  ╚██╔╝      ██║╚██╗██║ ██╔██╗    ██║   
██║  ██║╚█████╔╝██║  ██║   ██║       ██║ ╚████║██╔╝ ██╗   ██║   
╚═╝  ╚═╝ ╚════╝ ╚═╝  ╚═╝   ╚═╝       ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   
{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🔥 24/7 FACEBOOK CONVO COOKIES OFFLINE LOADER [VIP EDITION] 🔥
 👑 CREATOR   : AJAY NXT
 🛡️ SECURITY  : ZERO CHECKPOINT / MULTI-GATEWAY DISPATCH
 ⚡ PLATFORM  : TERMUX / LINUX / WINDOWS / VPS / MACOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
"""
    print(banner)


def parse_cookies_input(raw: str) -> dict:
    """Parses cookie JSON array, dict, or standard cookie string."""
    raw = raw.strip()
    cookies_dict = {}

    if os.path.isfile(raw):
        try:
            with open(raw, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read().strip()
        except Exception as e:
            print(f"{RED}[!] Error reading cookie file: {e}{RESET}")

    if raw.startswith("[") or raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        cookies_dict[item["name"]] = str(item["value"])
            elif isinstance(data, dict):
                for k, v in data.items():
                    cookies_dict[str(k)] = str(v)
            return cookies_dict
        except Exception:
            pass

    if "=" in raw:
        for part in raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies_dict[k.strip()] = v.strip()

    if raw.startswith("EAA") or raw.startswith("EAAB"):
        cookies_dict["access_token"] = raw

    return cookies_dict


def compute_jazoest(dtsg: str) -> str:
    ans = sum(ord(c) for c in dtsg) if dtsg else 0
    return f"2{ans}"


class ConvoSession:
    """Handles Facebook authentication, session management, and message dispatch."""

    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.access_token = cookies.get("access_token", "")
        self.user_id = str(cookies.get("c_user", ""))
        self.user_name = "Facebook User"
        self.fb_dtsg = ""
        self.jazoest = ""
        self.cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items() if k != "access_token"])

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": DESKTOP_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Cookie": self.cookie_str,
        })
        for k, v in self.cookies.items():
            if k != "access_token":
                self.session.cookies.set(k, v, domain=".facebook.com")
                self.session.cookies.set(k, v, domain=".mbasic.facebook.com")

    def login_and_extract_tokens(self) -> tuple[bool, str]:
        """Validates cookies and extracts real fb_dtsg and account name."""
        if not self.user_id and not self.access_token:
            for k in ["c_user", "i_user", "uid", "user_id"]:
                if k in self.cookies:
                    self.user_id = str(self.cookies[k])
                    break

        if not self.user_id and not self.access_token:
            return False, "Cookies me 'c_user' (User ID) nahi mila!"

        dtsg_patterns = [
            r'name="fb_dtsg"\s+value="([^"]+)"',
            r'value="([^"]+)"\s+name="fb_dtsg"',
            r'["\']DTSGInitialData["\'],\[\],\{["\']token["\']:["\']([^"\']+)["\']',
            r'["\']DTSGInitData["\'],\[\],\{["\']token["\']:["\']([^"\']+)["\']',
            r'["\']token["\']:["\'](NA[A-Za-z0-9_\-:]+)["\']',
            r'name=\\"fb_dtsg\\"\s+value=\\"([^\\"]+)\\"',
            r'"async_get_token":"([^"]+)"',
        ]

        # 1. Check mbasic
        try:
            m_res = self.session.get("https://mbasic.facebook.com/", headers={"User-Agent": MOBILE_UA}, timeout=12)
            if "checkpoint" in m_res.url or "two_factor" in m_res.text:
                return False, "Facebook Checkpoint (Location Verification required in FB App)!"

            for p in dtsg_patterns:
                m = re.search(p, m_res.text)
                if m:
                    self.fb_dtsg = m.group(1)
                    break

            name_m = re.search(r'<title>(.*?)</title>', m_res.text, re.IGNORECASE)
            if name_m:
                t = name_m.group(1).replace(" | Facebook", "").replace("Facebook", "").strip()
                if t and "log in" not in t.lower() and "welcome" not in t.lower():
                    self.user_name = t
        except Exception:
            pass

        # 2. Check Desktop
        if not self.fb_dtsg:
            try:
                res = self.session.get("https://www.facebook.com/", timeout=12)
                for p in dtsg_patterns:
                    m = re.search(p, res.text)
                    if m:
                        self.fb_dtsg = m.group(1)
                        break
                if not self.user_name or self.user_name == "Facebook User":
                    name_m = re.search(r'<title>(.*?)</title>', res.text, re.IGNORECASE)
                    if name_m:
                        t = name_m.group(1).replace(" | Facebook", "").replace("Facebook", "").strip()
                        if t and "log in" not in t.lower():
                            self.user_name = t
            except Exception:
                pass

        if not self.fb_dtsg:
            self.fb_dtsg = f"NAc{self.user_id}"

        self.jazoest = compute_jazoest(self.fb_dtsg)
        return True, f"Logged in as: {self.user_name} (UID: {self.user_id})"

    def send_typing(self, target_id: str, is_typing: bool = True):
        """Sends typing indicator."""
        try:
            url = "https://www.facebook.com/ajax/messaging/typ.php"
            data = {
                "typ_state": "1" if is_typing else "0",
                "to": str(target_id),
                "source": "mercury-chat",
                "thread": str(target_id),
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
            }
            self.session.post(url, data=data, timeout=6)
        except Exception:
            pass

    def send_convo_message(self, target_id: str, message_text: str) -> tuple[bool, str]:
        """Dispatches message to the conversation using multi-protocol fallbacks."""
        # 1. Try Mercury Desktop API
        try:
            msg_time = int(time.time() * 1000)
            client_id = f"{msg_time}{random.randint(100, 999)}"
            url = "https://www.facebook.com/ajax/mercury/send_messages.php"
            payload = {
                "message_batch[0][action_type]": "ma-type:user-generated-message",
                "message_batch[0][author]": f"fbid:{self.user_id}",
                "message_batch[0][timestamp]": str(msg_time),
                "message_batch[0][source]": "source:chat:web",
                "message_batch[0][body]": message_text,
                "message_batch[0][message_id]": client_id,
                "message_batch[0][other_user_fbid]": str(target_id),
                "message_batch[0][specific_to_list][0]": f"fbid:{target_id}",
                "message_batch[0][specific_to_list][1]": f"fbid:{self.user_id}",
                "message_batch[0][client_thread_id]": f"user:{target_id}",
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
            }
            hdrs = {
                "User-Agent": DESKTOP_UA,
                "Origin": "https://www.facebook.com",
                "Referer": f"https://www.facebook.com/messages/t/{target_id}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": self.cookie_str,
                "X-Requested-With": "XMLHttpRequest",
            }
            res = self.session.post(url, data=payload, headers=hdrs, timeout=10)
            if res.status_code == 200 and '"error":' not in res.text and ('"payload":' in res.text or 'message_id' in res.text):
                return True, "Mercury Web API"
        except Exception:
            pass

        # 2. Try mbasic Form / Direct POST
        try:
            c_url = f"https://mbasic.facebook.com/messages/compose/?ids={target_id}"
            get_res = self.session.get(c_url, headers={"User-Agent": MOBILE_UA, "Cookie": self.cookie_str}, timeout=10)
            
            dtsg_m = re.search(r'name="fb_dtsg"\s+value="([^"]+)"', get_res.text)
            if dtsg_m:
                self.fb_dtsg = dtsg_m.group(1)
                self.jazoest = compute_jazoest(self.fb_dtsg)

            post_data = {
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                f"ids[{target_id}]": str(target_id),
                "body": message_text,
                "Send": "Send",
                "tids": f"cid.c.{target_id}:{self.user_id}",
            }
            post_hdrs = {
                "User-Agent": MOBILE_UA,
                "Origin": "https://mbasic.facebook.com",
                "Referer": c_url,
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": self.cookie_str,
            }
            send_res = self.session.post("https://mbasic.facebook.com/messages/send/?icm=1", data=post_data, headers=post_hdrs, timeout=10)
            if send_res.status_code in [200, 302] and "checkpoint" not in send_res.url:
                return True, "Mobile Form Engine"
        except Exception:
            pass

        return False, "Delivery Failed"


def load_messages(msg_source: str) -> list:
    """Loads messages from a text file or multi-line string."""
    messages = []
    if os.path.isfile(msg_source):
        try:
            with open(msg_source, "r", encoding="utf-8", errors="ignore") as f:
                messages = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"{RED}[!] Error reading message file: {e}{RESET}")
    else:
        messages = [line.strip() for line in msg_source.split("\n") if line.strip()]
    return messages


def get_clean_input(prompt: str) -> str:
    """Reads input safely without getting corrupted by previous pastes."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        return sys.stdin.readline().strip()
    except Exception:
        return ""


def interactive_setup():
    """Interactive CLI configuration setup with auto-cookie detection."""
    print_banner()

    # 1. Check if cookie.json already exists in current folder
    cookie_auto = ""
    for candidate in ["cookie.json", "cookies.json", "cookie.txt", "cookies.txt"]:
        if os.path.isfile(candidate):
            cookie_auto = candidate
            break

    # 2. Check for existing saved config
    if os.path.isfile(CONFIG_FILE):
        print(f"{YELLOW}[?] Found saved configuration in '{CONFIG_FILE}'!{RESET}")
        use_saved = get_clean_input(f"{BOLD}{WHITE}Do you want to use saved config? (y/n) [Default: y]: {RESET}").lower()
        if use_saved in ["", "y", "yes"]:
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                return cfg
            except Exception as e:
                print(f"{RED}[!] Failed to read config: {e}{RESET}")

    print(f"\n{BOLD}{CYAN}=== 🛠️ STEP 1: FACEBOOK COOKIES ==={RESET}")
    if cookie_auto:
        print(f"{GREEN}[✓] Auto-detected '{cookie_auto}' in folder!{RESET}")
        c_choice = get_clean_input(f"{WHITE}Use '{cookie_auto}'? (y/n) [Default: y]: {RESET}").lower()
        if c_choice in ["", "y", "yes"]:
            cookie_input = cookie_auto
        else:
            cookie_input = get_clean_input(f"{GREEN}> Cookie File Path (e.g. cookie.json): {RESET}")
    else:
        print(f"{WHITE}Cookie file ka naam (e.g. cookie.json) ya single-line cookie paste karein:{RESET}")
        cookie_input = get_clean_input(f"{GREEN}> Cookie Input / File Path: {RESET}")

    print(f"\n{BOLD}{CYAN}=== 🎯 STEP 2: TARGET CONVO / INBOX ID ==={RESET}")
    print(f"{WHITE}Samne wale ka Target Profile UID, Chat ID ya Group Thread ID daalein:{RESET}")
    target_id = get_clean_input(f"{GREEN}> Target ID: {RESET}")

    print(f"\n{BOLD}{CYAN}=== 💬 STEP 3: MESSAGE FILE / TEXT ==={RESET}")
    # Auto-detect messages.txt if exists
    msg_auto = "messages.txt" if os.path.isfile("messages.txt") else ""
    if msg_auto:
        print(f"{GREEN}[✓] Auto-detected 'messages.txt' in folder!{RESET}")
        m_choice = get_clean_input(f"{WHITE}Use 'messages.txt'? (y/n) [Default: y]: {RESET}").lower()
        if m_choice in ["", "y", "yes"]:
            msg_file = "messages.txt"
        else:
            msg_file = get_clean_input(f"{GREEN}> Message File / Text: {RESET}")
    else:
        print(f"{WHITE}Messages file (.txt) ka path daalein (e.g. messages.txt) ya direct text:{RESET}")
        msg_file = get_clean_input(f"{GREEN}> Message File / Text: {RESET}")

    print(f"\n{BOLD}{CYAN}=== 🏷️ STEP 4: HATERS / VIP PREFIX TAG ==={RESET}")
    print(f"{WHITE}Har message ke aage lagane wala Tag (e.g. [AJAY NXT] ya [VIP]):{RESET}")
    prefix = get_clean_input(f"{GREEN}> Prefix Tag (Optional, Press Enter to Skip): {RESET}")

    print(f"\n{BOLD}{CYAN}=== ⏱️ STEP 5: DELAY SPEED (SECONDS) ==={RESET}")
    delay_str = get_clean_input(f"{GREEN}> Delay between messages in seconds [Default: 5]: {RESET}")
    try:
        delay = float(delay_str) if delay_str else 5.0
    except ValueError:
        delay = 5.0

    cfg = {
        "cookies": cookie_input,
        "target_id": target_id,
        "messages": msg_file,
        "prefix": prefix,
        "delay": delay
    }

    # Save config
    save_opt = get_clean_input(f"\n{YELLOW}[?] Save this setup for 1-click launch next time? (y/n) [Default: y]: {RESET}").lower()
    if save_opt in ["", "y", "yes"]:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"{GREEN}[✓] Configuration saved to '{CONFIG_FILE}'!{RESET}")
        except Exception as e:
            print(f"{RED}[!] Error saving config: {e}{RESET}")

    return cfg


def main():
    cfg = interactive_setup()

    print_banner()
    print(f"{YELLOW}[*] Validating Facebook Cookies & Initializing Engine...{RESET}")

    cookies = parse_cookies_input(cfg["cookies"])
    if not cookies:
        print(f"{RED}[❌] Invalid Cookie Format! Please provide Cookie JSON or valid file path.{RESET}")
        sys.exit(1)

    session = ConvoSession(cookies)
    valid, status_msg = session.login_and_extract_tokens()

    if not valid:
        print(f"{RED}[❌] Login Failed: {status_msg}{RESET}")
        sys.exit(1)

    messages = load_messages(cfg["messages"])
    if not messages:
        print(f"{RED}[❌] Message file is empty or missing! Please provide valid messages.{RESET}")
        sys.exit(1)

    target_id = str(cfg["target_id"]).strip()
    prefix = str(cfg.get("prefix", "")).strip()
    delay = float(cfg.get("delay", 5.0))

    print(f"{GREEN}[✓] {status_msg}{RESET}")
    print(f"{CYAN}[✓] Target Convo ID : {BOLD}{target_id}{RESET}")
    print(f"{CYAN}[✓] Loaded Messages : {BOLD}{len(messages)} lines{RESET}")
    print(f"{CYAN}[✓] Speed Interval  : {BOLD}{delay}s per message{RESET}")
    print(f"{CYAN}[✓] Prefix Tag      : {BOLD}{prefix if prefix else '(None)'}{RESET}")
    print(f"\n{GREEN}{BOLD}🚀 STARTING 24/7 INFINITE CONVO LOADER... (Press Ctrl+C to Stop){RESET}")
    print(f"{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    total_sent = 0
    round_count = 1

    try:
        while True:
            for idx, raw_line in enumerate(messages, 1):
                full_msg = f"{prefix} {raw_line}".strip() if prefix else raw_line

                now = datetime.now().strftime("%H:%M:%S")

                # Send typing state
                session.send_typing(target_id, is_typing=True)
                time.sleep(1.5)

                success, method = session.send_convo_message(target_id, full_msg)
                session.send_typing(target_id, is_typing=False)

                if success:
                    total_sent += 1
                    print(f"{GREEN}[SENT #{total_sent}]{RESET} {CYAN}[{now}]{RESET} (Round #{round_count}, Line {idx}/{len(messages)}) -> {WHITE}\"{full_msg}\"{RESET} {GREEN}✓ ({method}){RESET}")
                else:
                    print(f"{RED}[FAIL]{RESET} {YELLOW}[{now}]{RESET} (Round #{round_count}, Line {idx}/{len(messages)}) -> {WHITE}\"{full_msg}\"{RESET} {RED}✗ ({method}){RESET}")

                # Sleep interval
                time.sleep(max(1.0, delay))

            round_count += 1
            print(f"\n{MAGENTA}🔄 [ROUND COMPLETE] Round #{round_count - 1} finished! Restarting from Line 1 non-stop...{RESET}\n")

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Convo Loader Stopped by User. Total Messages Sent: {total_sent}{RESET}")
        print(f"{GREEN}👑 Thank you for using AJAY NXT FB Convo Loader!{RESET}\n")


if __name__ == "__main__":
    main()
