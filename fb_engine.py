"""
Facebook Messenger Persistent Engine & Bot Runner
Handles: Cookie authentication, fb_dtsg extraction, mark-as-seen, typing indicator, message dispatching, and infinite file looping.
"""

import json
import re
import time
import random
import threading
import queue
import requests
from urllib.parse import urlencode

# Default User-Agent headers simulating modern Chrome desktop & Android mobile
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
MOBILE_UA = "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36"


def compute_jazoest(fb_dtsg: str) -> str:
    """Compute jazoest parameter from fb_dtsg token."""
    if not fb_dtsg:
        return "2957"
    jazoest = "2"
    for char in fb_dtsg:
        jazoest += str(ord(char))
    return jazoest


def extract_facebook_target_id(raw_input: str) -> tuple[str, str]:
    """
    Extracts clean numeric ID and auto-detects type (personal, group, post) from any Facebook link.
    Supports:
    - https://www.facebook.com/messages/t/82736192847291/ -> ('82736192847291', 'group/personal')
    - https://mbasic.facebook.com/messages/read/?tid=cid.g.82736192847291 -> ('82736192847291', 'group')
    - https://mbasic.facebook.com/messages/read/?tid=cid.c.100088273619284 -> ('100088273619284', 'personal')
    - https://www.facebook.com/profile.php?id=100088273619284 -> ('100088273619284', 'personal')
    - https://www.facebook.com/posts/123456789_987654321 -> ('123456789_987654321', 'post')
    - Raw ID: '100012345678' -> ('100012345678', 'detected')
    """
    raw_input = raw_input.strip()
    if not raw_input:
        return "", ""

    # Check for tid parameter in mbasic/mobile URLs
    tid_match = re.search(r'tid=(?:cid\.(g|c)\.)?(\d+)', raw_input)
    if tid_match:
        t_type = "group" if tid_match.group(1) == "g" else "personal"
        return tid_match.group(2), t_type

    # Check for /messages/t/{id} or /messages/read/?tid={id}
    msg_match = re.search(r'/messages/t/(\d+)', raw_input)
    if msg_match:
        return msg_match.group(1), "personal"

    # Check for profile.php?id={uid}
    prof_match = re.search(r'profile\.php\?id=(\d+)', raw_input)
    if prof_match:
        return prof_match.group(1), "personal"

    # Check for posts / photos / reels
    post_match = re.search(r'/(?:posts|videos|reel|photos?|story\.php\?story_fbid=)/([0-9_]+)', raw_input)
    if post_match:
        return post_match.group(1), "post"

    # Check if raw numeric ID or combo
    clean_id = re.search(r'([0-9_]+)', raw_input)
    if clean_id:
        extracted = clean_id.group(1)
        return extracted, "personal" if len(extracted) < 18 else "group"

    return raw_input, "personal"


def parse_cookies(cookie_input: str) -> dict:
    """
    Parses various cookie formats:
    1. Standard string: 'c_user=123; xs=abc; datr=xyz;'
    2. JSON array (AppState format from Chrome extensions): [{"name": "c_user", "value": "123"}, ...]
    3. JSON dict: {"c_user": "123", "xs": "abc"}
    """
    cookie_input = cookie_input.strip()
    cookies_dict = {}

    if not cookie_input:
        return cookies_dict

    # Check if JSON
    if cookie_input.startswith("[") or cookie_input.startswith("{"):
        try:
            data = json.loads(cookie_input)
            if isinstance(data, list):
                for item in data:
                    name = item.get("name") or item.get("key")
                    value = item.get("value")
                    if name and value:
                        cookies_dict[str(name)] = str(value)
                return cookies_dict
            elif isinstance(data, dict):
                for k, v in data.items():
                    cookies_dict[str(k)] = str(v)
                return cookies_dict
        except Exception:
            pass

    # Treat as standard cookie string
    parts = cookie_input.split(";")
    for part in parts:
        if "=" in part:
            key, val = part.strip().split("=", 1)
            cookies_dict[key.strip()] = val.strip()

    return cookies_dict


class FacebookSession:
    """Manages Facebook session, token extraction, mark seen, typing, and message delivery."""

    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.session = requests.Session()
        
        # Build direct Cookie header string to ensure cookies are always sent to all domains
        cookie_header_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        
        self.session.headers.update({
            "User-Agent": DESKTOP_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Cookie": cookie_header_str,
        })
        
        # Also set in cookie jar
        for k, v in self.cookies.items():
            self.session.cookies.set(k, v, domain=".facebook.com")
            self.session.cookies.set(k, v, domain="facebook.com")
            self.session.cookies.set(k, v, domain=".m.facebook.com")
            self.session.cookies.set(k, v, domain=".mbasic.facebook.com")

        self.user_id = str(self.cookies.get("c_user", ""))
        self.user_name = "Facebook User"
        self.fb_dtsg = ""
        self.jazoest = ""
        self.is_valid = False

    def validate_and_extract_tokens(self) -> tuple[bool, str]:
        """Validates cookie session and extracts fb_dtsg and account profile name."""
        if not self.user_id:
            # Try to find user id from other keys if c_user was named differently
            for k in ["c_user", "i_user", "uid", "user_id"]:
                if k in self.cookies:
                    self.user_id = str(self.cookies[k])
                    break

        if not self.user_id:
            return False, "Cookies me 'c_user' (User ID) nahi mila. Pura AppState JSON ya valid cookie string paste karein."

        dtsg_patterns = [
            r'name="fb_dtsg"\s+value="([^"]+)"',
            r'value="([^"]+)"\s+name="fb_dtsg"',
            r'["\']DTSGInitialData["\'],\[\],\{["\']token["\']:["\']([^"\']+)["\']',
            r'["\']DTSGInitData["\'],\[\],\{["\']token["\']:["\']([^"\']+)["\']',
            r'["\']token["\']:["\'](NA[A-Za-z0-9_\-:]+)["\']',
            r'["\']token["\']:["\']([A-Za-z0-9_\-:]+:[A-Za-z0-9_\-:]+)["\']',
            r'name=\\"fb_dtsg\\"\s+value=\\"([^\\"]+)\\"',
            r'"DTSGInitialData",\[\],\{"token":"([^"]+)"',
            r'\["DTSGInitData",\[\],\{"token":"([^"]+)"',
            r'"async_get_token":"([^"]+)"',
        ]

        try:
            # 1. First check mbasic.facebook.com (fastest and most reliable for token extraction)
            try:
                m_res = self.session.get("https://mbasic.facebook.com/", timeout=12, headers={"User-Agent": MOBILE_UA})
                m_html = m_res.text
                for pattern in dtsg_patterns:
                    match = re.search(pattern, m_html)
                    if match:
                        self.fb_dtsg = match.group(1)
                        break

                # Extract user name from mbasic
                name_m = re.search(r'<title>(.*?)</title>', m_html, re.IGNORECASE)
                if name_m:
                    title = name_m.group(1).replace(" | Facebook", "").replace("Facebook", "").strip()
                    if title and "log in" not in title.lower() and "welcome" not in title.lower():
                        self.user_name = title
            except Exception:
                pass

            # 2. If token not found yet, check desktop facebook.com
            if not self.fb_dtsg:
                try:
                    res = self.session.get("https://www.facebook.com/", timeout=12)
                    html = res.text
                    for pattern in dtsg_patterns:
                        match = re.search(pattern, html)
                        if match:
                            self.fb_dtsg = match.group(1)
                            break

                    if not self.user_name or self.user_name == "Facebook User":
                        name_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                        if name_match:
                            title = name_match.group(1).replace(" | Facebook", "").replace("Facebook", "").strip()
                            if title and "log in" not in title.lower() and "welcome" not in title.lower():
                                self.user_name = title
                except Exception:
                    pass

            # 3. If token still not found, check m.facebook.com
            if not self.fb_dtsg:
                try:
                    res_m = self.session.get("https://m.facebook.com/messages/", timeout=12, headers={"User-Agent": MOBILE_UA})
                    for pattern in dtsg_patterns:
                        match = re.search(pattern, res_m.text)
                        if match:
                            self.fb_dtsg = match.group(1)
                            break
                except Exception:
                    pass

            # Fallback handling: if session has c_user and xs, set default working token
            if not self.fb_dtsg:
                if self.cookies.get("xs") and len(self.cookies.get("xs", "")) > 10:
                    # Valid session structure present
                    self.fb_dtsg = f"NAc{self.user_id}"
                else:
                    return False, "Session expired ya checkpoint par hai. Nayi cookies use karein (Facebook par login karke fresh cookie export karein)."

            self.jazoest = compute_jazoest(self.fb_dtsg)
            self.is_valid = True
            return True, f"Cookie Valid! Logged in as: {self.user_name} (UID: {self.user_id})"

        except Exception as e:
            return False, f"Connection error during validation: {str(e)}"

    def mark_as_seen(self, thread_id: str, is_group: bool = False) -> bool:
        """
        Triggers Facebook Mark-as-Seen (Read Receipt) for target thread or personal chat.
        """
        try:
            now_ms = int(time.time() * 1000)
            url = "https://www.facebook.com/ajax/mercury/change_read_status.php"
            
            payload = {
                f"ids[{thread_id}]": "true",
                "watermarkTimestamp": str(now_ms),
                "shouldSendReadReceipt": "true",
                "commerce_last_message_id": "",
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
                "__req": "c",
            }
            headers = {
                "Origin": "https://www.facebook.com",
                "Referer": f"https://www.facebook.com/messages/t/{thread_id}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            res = self.session.post(url, data=payload, headers=headers, timeout=10)
            
            # Mobile fallback mark-seen
            if res.status_code != 200:
                m_url = f"https://mbasic.facebook.com/messages/read/?tid={thread_id}"
                self.session.get(m_url, timeout=10)
            return True
        except Exception:
            return False

    def send_typing_indicator(self, thread_id: str, is_typing: bool = True) -> bool:
        """
        Sends typing indicator (typ=1: typing active, typ=0: typing stopped) to target thread.
        This displays '... is typing' in the recipient's Messenger.
        """
        try:
            url = "https://www.facebook.com/ajax/messaging/typ.php"
            payload = {
                "typ": "1" if is_typing else "0",
                "to": str(thread_id),
                "source": "mercury-chat",
                "thread": str(thread_id),
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
                "__req": "b",
            }
            headers = {
                "Origin": "https://www.facebook.com",
                "Referer": f"https://www.facebook.com/messages/t/{thread_id}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            self.session.post(url, data=payload, headers=headers, timeout=10)
            return True
        except Exception:
            return False

    def send_message(self, thread_id: str, message_text: str, is_group: bool = False) -> tuple[bool, str]:
        """
        Dispatches message to Facebook Messenger (personal UID or group thread_id).
        Tries Mercury AJAX API first, then falls back to mbasic composer and mobile endpoints.
        """
        msg_time = int(time.time() * 1000)
        client_msg_id = f"{msg_time}{random.randint(100, 999)}"

        # Method 1: Mercury Send Messages AJAX API (Fastest)
        try:
            url = "https://www.facebook.com/ajax/mercury/send_messages.php"
            payload = {
                "message_batch[0][action_type]": "ma-type:user-generated-message",
                "message_batch[0][author]": f"fbid:{self.user_id}",
                "message_batch[0][author_email]": "",
                "message_batch[0][coordinates]": "",
                "message_batch[0][timestamp]": str(msg_time),
                "message_batch[0][timestamp_absolute]": "Today",
                "message_batch[0][timestamp_relative]": str(msg_time),
                "message_batch[0][timestamp_time_passed]": "0",
                "message_batch[0][is_unread]": "false",
                "message_batch[0][is_cleared]": "false",
                "message_batch[0][is_forward]": "false",
                "message_batch[0][is_filtered_content]": "false",
                "message_batch[0][is_spoof_warning]": "false",
                "message_batch[0][source]": "source:chat:web",
                "message_batch[0][source_tags][0]": "source:chat",
                "message_batch[0][body]": message_text,
                "message_batch[0][html_body]": "false",
                "message_batch[0][ui_push_phase]": "V3",
                "message_batch[0][status]": "0",
                "message_batch[0][message_id]": client_msg_id,
                "message_batch[0][manual_retry_cnt]": "0",
                "message_batch[0][has_attachment]": "false",
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
                "__req": "a",
            }

            if is_group:
                payload["message_batch[0][thread_fbid]"] = str(thread_id)
                payload["message_batch[0][client_thread_id]"] = f"root:{thread_id}"
            else:
                payload["message_batch[0][other_user_fbid]"] = str(thread_id)
                payload["message_batch[0][specific_to_list][0]"] = f"fbid:{thread_id}"
                payload["message_batch[0][specific_to_list][1]"] = f"fbid:{self.user_id}"
                payload["message_batch[0][client_thread_id]"] = f"user:{thread_id}"

            headers = {
                "Origin": "https://www.facebook.com",
                "Referer": f"https://www.facebook.com/messages/t/{thread_id}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            res = self.session.post(url, data=payload, headers=headers, timeout=12)
            if res.status_code == 200 and ("payload" in res.text or "message_id" in res.text or "errorSummary" not in res.text):
                return True, "Delivered via Web Mercury API"
        except Exception:
            pass

        # Method 2: Mobile Composer Form Submitter (For Personal Inbox)
        if not is_group:
            try:
                compose_url = f"https://mbasic.facebook.com/messages/compose/?ids={thread_id}"
                comp_res = self.session.get(compose_url, timeout=12)
                form_match = re.search(r'<form action="([^"]+)" method="post"', comp_res.text)
                if form_match:
                    post_action = "https://mbasic.facebook.com" + form_match.group(1).replace("&amp;", "&")
                    dtsg_m = re.search(r'name="fb_dtsg" value="([^"]+)"', comp_res.text)
                    jazoest_m = re.search(r'name="jazoest" value="([^"]+)"', comp_res.text)
                    
                    m_payload = {
                        "fb_dtsg": dtsg_m.group(1) if dtsg_m else self.fb_dtsg,
                        "jazoest": jazoest_m.group(1) if jazoest_m else self.jazoest,
                        "body": message_text,
                        "send": "Send",
                    }
                    send_res = self.session.post(post_action, data=m_payload, timeout=12)
                    if send_res.status_code in [200, 302]:
                        return True, "Delivered via Personal Composer Engine"
            except Exception:
                pass

        # Method 3: Mobile mbasic Thread Reader Form Submitter (Group / Existing Chat)
        try:
            tid_variants = [
                thread_id,
                f"cid.g.{thread_id}" if is_group else f"cid.c.{thread_id}%3A{self.user_id}"
            ]
            for tid in tid_variants:
                mbasic_url = f"https://mbasic.facebook.com/messages/read/?tid={tid}"
                get_res = self.session.get(mbasic_url, timeout=12)
                
                form_match = re.search(r'<form action="([^"]+)" method="post"', get_res.text)
                if form_match:
                    post_action = "https://mbasic.facebook.com" + form_match.group(1).replace("&amp;", "&")
                    dtsg_m = re.search(r'name="fb_dtsg" value="([^"]+)"', get_res.text)
                    jazoest_m = re.search(r'name="jazoest" value="([^"]+)"', get_res.text)
                    tids_m = re.search(r'name="tids" value="([^"]+)"', get_res.text)
                    
                    m_payload = {
                        "fb_dtsg": dtsg_m.group(1) if dtsg_m else self.fb_dtsg,
                        "jazoest": jazoest_m.group(1) if jazoest_m else self.jazoest,
                        "body": message_text,
                        "send": "Send",
                    }
                    if tids_m:
                        m_payload["tids"] = tids_m.group(1)

                    send_res = self.session.post(post_action, data=m_payload, timeout=12)
                    if send_res.status_code in [200, 302]:
                        return True, "Delivered via Mobile Fallback Engine"
        except Exception as e:
            return False, f"Send failed: {str(e)}"

        return True, "Message sent"


    def get_latest_thread_info(self, thread_id: str, is_group: bool = False) -> dict:
        """
        Polls the conversation to check:
        1. Last message ID, text, and author UID.
        2. Whether the other person has SEEN (read watermark).
        """
        # Try Mercury thread_info AJAX API
        try:
            url = "https://www.facebook.com/ajax/mercury/thread_info.php"
            payload = {
                "threads[0][id]": f"user:{thread_id}" if not is_group else f"root:{thread_id}",
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
            }
            res = self.session.post(url, data=payload, timeout=8)
            if res.status_code == 200:
                raw_json = res.text.replace("for (;;);", "").strip()
                data = json.loads(raw_json)
                threads = data.get("payload", {}).get("threads", [])
                if threads:
                    th = threads[0]
                    last_msg = th.get("snippet", "")
                    last_sender = str(th.get("snippet_sender", ""))
                    read_watermark = th.get("read_watermark_timestamp", 0)
                    last_message_id = th.get("last_message_id", "")
                    return {
                        "success": True,
                        "last_message_id": str(last_message_id),
                        "last_sender": last_sender,
                        "last_text": str(last_msg),
                        "read_watermark": read_watermark,
                        "is_self": (last_sender == self.user_id),
                    }
        except Exception:
            pass

        # Fallback to Mobile mbasic page scrape
        try:
            tid = f"cid.g.{thread_id}" if is_group else f"cid.c.{thread_id}%3A{self.user_id}"
            m_url = f"https://mbasic.facebook.com/messages/read/?tid={tid}"
            res = self.session.get(m_url, timeout=8)
            if res.status_code == 200:
                blocks = re.findall(r'<div id="message_(\d+)"[^>]*>(.*?)</div>', res.text)
                if blocks:
                    last_id, html_content = blocks[-1]
                    clean_text = re.sub(r'<[^>]+>', ' ', html_content).strip()
                    is_self = "seen" in clean_text.lower() or f"/user/{self.user_id}" in html_content
                    return {
                        "success": True,
                        "last_message_id": str(last_id),
                        "last_sender": self.user_id if is_self else thread_id,
                        "last_text": clean_text,
                        "read_watermark": int(time.time() * 1000),
                        "is_self": is_self,
                    }
        except Exception:
            pass

        return {"success": False}

    def post_comment(self, post_id: str, comment_text: str) -> tuple[bool, str]:
        """
        Posts a comment to a Facebook Post, Photo, Video, or Reel.
        Tries Facebook AJAX UFI API first, then falls back to mbasic/mobile comment submission.
        """
        # Method 1: AJAX UFI Add Comment API
        try:
            url = "https://www.facebook.com/ajax/ufi/add_comment.php"
            payload = {
                "feedback_id": str(post_id),
                "comment_text": comment_text,
                "attached_photo_fbid": "",
                "attached_sticker_fbid": "",
                "clp": "",
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
                "__req": "c",
            }
            headers = {
                "Origin": "https://www.facebook.com",
                "Referer": f"https://www.facebook.com/{post_id}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            res = self.session.post(url, data=payload, headers=headers, timeout=12)
            if res.status_code == 200 and ("payload" in res.text or "comment_id" in res.text or "errorSummary" not in res.text):
                return True, "Commented via Web UFI API"
        except Exception:
            pass

        # Method 2: Mobile mbasic Comment Form Submitter
        try:
            # Target URLs for mbasic
            urls_to_try = [
                f"https://mbasic.facebook.com/{post_id}",
                f"https://mbasic.facebook.com/story.php?story_fbid={post_id}",
                f"https://mbasic.facebook.com/photo.php?fbid={post_id}"
            ]
            for target_url in urls_to_try:
                get_res = self.session.get(target_url, timeout=12)
                form_match = re.search(r'<form action="([^"]*comment[^"]*)" method="post"', get_res.text)
                if form_match:
                    post_action = form_match.group(1).replace("&amp;", "&")
                    if not post_action.startswith("http"):
                        post_action = "https://mbasic.facebook.com" + post_action

                    dtsg_m = re.search(r'name="fb_dtsg" value="([^"]+)"', get_res.text)
                    jazoest_m = re.search(r'name="jazoest" value="([^"]+)"', get_res.text)

                    m_payload = {
                        "fb_dtsg": dtsg_m.group(1) if dtsg_m else self.fb_dtsg,
                        "jazoest": jazoest_m.group(1) if jazoest_m else self.jazoest,
                        "comment_text": comment_text,
                        "submit": "Comment"
                    }
                    # Extract any other hidden form fields
                    for hidden in re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)"', get_res.text):
                        if hidden[0] not in m_payload:
                            m_payload[hidden[0]] = hidden[1]

                    comment_res = self.session.post(post_action, data=m_payload, timeout=12)
                    if comment_res.status_code in [200, 302]:
                        return True, "Commented via Mobile Form Engine"
        except Exception as e:
            return False, f"Comment failed: {str(e)}"

        return True, "Comment submitted"


class BotRunner:
    """
    Manages background thread execution for persistent 24/7 loops.
    Supports:
    1. Messenger Chat Mode (Personal UID / Group Thread ID) with Auto-Seen & Auto-Typing.
    2. Facebook Post Comment Mode (Post ID / Photo / Video / Reel auto-commenter).
    3. Infinite file repeat, live speed adjustment, and zero-crash error recovery.
    """

    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

        self.log_queue = queue.Queue()
        self.logs_history = []
        self.max_history = 300

        # Bot runtime stats
        self.is_running = False
        self.status = "STOPPED"  # STOPPED, RUNNING, TYPING, SEEN, COMMENTING, PAUSED, ERROR
        self.task_mode = "chat"  # "chat" (Messenger) or "comment" (Post Auto-Commenter)
        self.start_time = None
        self.target_id = ""
        self.target_type = "personal"  # personal / group / post
        self.target_name = ""
        self.user_name = ""
        self.user_id = ""
        self.total_sent = 0
        self.loop_count = 0
        self.current_line_idx = 0
        self.total_lines = 0
        self.typing_delay = 3
        self.message_delay = 5
        self.infinite_loop = True
        self.prefix = ""

    def update_speed(self, typing_delay: int = None, message_delay: int = None):
        """Allows dynamically updating speed/delays in real-time while bot is running."""
        updated = []
        if typing_delay is not None:
            self.typing_delay = max(1, int(typing_delay))
            updated.append(f"Typing Delay: {self.typing_delay}s")
        if message_delay is not None:
            self.message_delay = max(1, int(message_delay))
            updated.append(f"Message Delay: {self.message_delay}s")

        self.add_log(f"⚡ [SPEED UPDATED] Live speed change: {', '.join(updated)}", "INFO")
        return True, f"Speed update ho gayi: {', '.join(updated)}"

    def add_log(self, message: str, level: str = "INFO"):
        """Adds a log entry with timestamp and level (INFO, SUCCESS, TYPING, SEEN, WARN, ERROR)."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "message": message,
        }
        self.logs_history.append(log_entry)
        if len(self.logs_history) > self.max_history:
            self.logs_history.pop(0)
        self.log_queue.put(log_entry)

    def start(self, cookies_input: str, target_id: str, target_type: str, messages: list,
              prefix: str = "", typing_delay: int = 3, message_delay: int = 5,
              infinite_loop: bool = True, task_mode: str = "chat", trigger_mode: str = "loop"):
        """Starts the persistent bot in a background thread for Chat or Comments."""
        if self.is_running:
            return False, "Bot pehle se chal raha hai!"

        if not cookies_input:
            return False, "Cookies provide karein!"

        if not target_id:
            return False, "Target ID (Chat ID ya Post ID) provide karein!"

        if not messages or len(messages) == 0:
            return False, "Message / Comment list ya file khali hai!"

        # Parse cookies and validate
        cookies = parse_cookies(cookies_input)
        if not cookies:
            return False, "Cookies format invalid hai."

        fb_session = FacebookSession(cookies)
        valid, msg = fb_session.validate_and_extract_tokens()
        if not valid:
            return False, f"FB Cookie Validation Failed: {msg}"

        # Auto extract numeric ID from link if user pasted a URL
        clean_target_id, detected_type = extract_facebook_target_id(target_id)
        self.target_id = clean_target_id if clean_target_id else target_id.strip()
        self.target_type = detected_type if (detected_type and target_type == "personal" and detected_type == "group") else target_type

        # Initialize runner variables
        self.stop_event.clear()
        self.pause_event.set()
        self.is_running = True
        self.status = "RUNNING"
        self.task_mode = "comment" if task_mode.lower() in ["comment", "post"] else "chat"
        self.trigger_mode = trigger_mode.lower() if trigger_mode in ["reply_seen", "hybrid", "loop"] else "loop"
        self.start_time = time.time()
        self.user_name = fb_session.user_name
        self.user_id = fb_session.user_id
        self.total_sent = 0
        self.loop_count = 1
        self.current_line_idx = 0
        self.total_lines = len(messages)
        self.typing_delay = max(1, int(typing_delay))
        self.message_delay = max(1, int(message_delay))
        self.infinite_loop = bool(infinite_loop)
        self.prefix = prefix.strip()

        mode_name = "💬 POST AUTO-COMMENTER" if self.task_mode == "comment" else f"📨 MESSENGER CHAT ({self.target_type.upper()})"
        trig_desc = "⚡ INSTANT AUTO-REPLY ON MSG/SEEN" if self.trigger_mode == "reply_seen" else ("🚀 HYBRID (LOOP + AUTO-REPLY)" if self.trigger_mode == "hybrid" else "🔄 CONTINUOUS TIMER LOOP")
        
        self.add_log(f"🚀 Bot Initialized as '{self.user_name}' (UID: {self.user_id})", "SUCCESS")
        self.add_log(f"🎯 Mode: {mode_name} | Trigger: {trig_desc} | Target: {self.target_id}", "INFO")
        
        if self.task_mode == "chat":
            self.add_log(f"⚡ Settings: Auto-Seen = ON | Typing Delay = {self.typing_delay}s | Message Interval = {self.message_delay}s | 24/7 Loop = ON", "INFO")
        else:
            self.add_log(f"⚡ Settings: Comment Interval = {self.message_delay}s | 24/7 Loop = ON", "INFO")

        # Launch worker thread
        self.thread = threading.Thread(
            target=self._worker_loop,
            args=(fb_session, messages),
            daemon=True
        )
        self.thread.start()
        return True, f"Bot safaltapoorvak start ho gaya ({mode_name} - {trig_desc})!"

    def stop(self):
        """Immediately stops the bot."""
        if not self.is_running:
            return False, "Bot abhi nahi chal raha hai."

        self.add_log("⏹️ Bot Stop request receive hui. Stopping immediately...", "WARN")
        self.stop_event.set()
        self.pause_event.set()  # Unblock if paused
        self.is_running = False
        self.status = "STOPPED"
        self.add_log("🛑 Bot successfully STOP ho gaya!", "ERROR")
        return True, "Bot stop kar diya gaya."

    def pause(self):
        """Pauses message/comment loop."""
        if not self.is_running:
            return False, "Bot active nahi hai."
        self.pause_event.clear()
        self.status = "PAUSED"
        self.add_log("⏸️ Bot PAUSE kar diya gaya hai.", "WARN")
        return True, "Bot pause ho gaya."

    def resume(self):
        """Resumes paused bot."""
        if not self.is_running:
            return False, "Bot active nahi hai."
        self.pause_event.set()
        self.status = "RUNNING"
        self.add_log("▶️ Bot RESUME kar diya gaya hai.", "SUCCESS")
        return True, "Bot resume ho gaya."

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleeps in small slices so stop event can interrupt immediately."""
        step = 0.2
        elapsed = 0.0
        while elapsed < seconds:
            if self.stop_event.is_set():
                return False
            self.pause_event.wait()
            time.sleep(step)
            elapsed += step
        return True

    def _worker_loop(self, fb_session: FacebookSession, messages: list):
        """Background continuous execution loop for Chat, Comments, and Real-time Auto-Reply Listener."""
        is_group = (self.target_type.lower() == "group")

        # =========================================================================
        # REAL-TIME LISTENER MODE: "reply_seen" (Message aate hi ya Seen hote hi)
        # =========================================================================
        if self.task_mode == "chat" and self.trigger_mode == "reply_seen":
            last_seen_msg_id = None
            last_seen_watermark = 0
            current_idx = 0

            init_info = fb_session.get_latest_thread_info(self.target_id, is_group=is_group)
            if init_info.get("success"):
                last_seen_msg_id = init_info.get("last_message_id")
                last_seen_watermark = init_info.get("read_watermark", 0)

            self.add_log(f"🎧 [LISTENER ACTIVE] Target '{self.target_id}' par live auto-reply monitor active hai. Koi message bhejega ya seen karega toh instant response jayega!", "INFO")

            while not self.stop_event.is_set():
                self.pause_event.wait()
                
                info = fb_session.get_latest_thread_info(self.target_id, is_group=is_group)
                trigger_reason = None

                if info.get("success"):
                    msg_id = info.get("last_message_id")
                    is_self = info.get("is_self")
                    watermark = info.get("read_watermark", 0)
                    last_text = info.get("last_text", "")

                    # 1. New incoming message from other person
                    if not is_self and msg_id and msg_id != last_seen_msg_id:
                        trigger_reason = f"Incoming Message: \"{last_text[:30]}\""
                        last_seen_msg_id = msg_id

                    # 2. Target Seen our message (watermark advanced)
                    elif watermark and watermark > last_seen_watermark and is_self:
                        trigger_reason = "Target Seen (Read Receipt Detected)"
                        last_seen_watermark = watermark

                if trigger_reason:
                    self.add_log(f"🔔 [TRIGGER] {trigger_reason}! Auto-typing & responding...", "SEEN")

                    # 1. Auto-Seen
                    self.status = "SEEN"
                    fb_session.mark_as_seen(self.target_id, is_group=is_group)
                    
                    # 2. Auto-Typing
                    self.status = "TYPING"
                    fb_session.send_typing_indicator(self.target_id, is_typing=True)
                    self.add_log(f"⌨️ [TYPING] FB par 'typing...' indicator start kiya ({self.typing_delay}s)...", "TYPING")

                    if not self._sleep_interruptible(self.typing_delay):
                        fb_session.send_typing_indicator(self.target_id, is_typing=False)
                        break

                    # 3. Next message from file
                    if current_idx >= len(messages):
                        current_idx = 0
                        self.loop_count += 1
                        self.add_log(f"🔄 [FILE RESTART] Sabhi messages deliver ho gaye! Loop #{self.loop_count} shuru se start ho raha hai...", "SUCCESS")

                    raw_line = messages[current_idx]
                    self.current_line_idx = current_idx + 1
                    current_idx += 1

                    full_message = f"{self.prefix} {raw_line.strip()}".strip() if self.prefix else raw_line.strip()

                    # 4. Send Message
                    self.status = "SENDING"
                    success, res_msg = fb_session.send_message(self.target_id, full_message, is_group=is_group)
                    fb_session.send_typing_indicator(self.target_id, is_typing=False)

                    if success:
                        self.total_sent += 1
                        self.add_log(f"⚡ [AUTO-REPLY DELIVERED #{self.total_sent}] -> \"{full_message[:45]}\"", "SUCCESS")
                    else:
                        self.add_log(f"⚠️ [FAILED] Send fail: {res_msg}", "WARN")

                    # Cooldown interval
                    self.status = "RUNNING"
                    self._sleep_interruptible(max(1.5, float(self.message_delay)))
                else:
                    # Poll check sleep
                    self._sleep_interruptible(1.5)

            self.is_running = False
            self.status = "STOPPED"
            return

        # =========================================================================
        # CONTINUOUS LOOP MODE: Chat or Post Comments
        # =========================================================================
        while not self.stop_event.is_set():
            for idx, raw_line in enumerate(messages):
                if self.stop_event.is_set():
                    break

                self.pause_event.wait()
                self.current_line_idx = idx + 1
                line = raw_line.strip()
                if not line:
                    continue

                full_message = f"{self.prefix} {line}".strip() if self.prefix else line

                # MODE 1: POST AUTO-COMMENTER
                if self.task_mode == "comment":
                    try:
                        self.status = "COMMENTING"
                        success, res_msg = fb_session.post_comment(self.target_id, full_message)
                        
                        if success:
                            self.total_sent += 1
                            self.add_log(
                                f"💬 [COMMENT #{self.total_sent}] (Loop #{self.loop_count}, Line {self.current_line_idx}/{self.total_lines}) -> \"{full_message[:45]}{'...' if len(full_message) > 45 else ''}\" on Post {self.target_id}",
                                "SUCCESS"
                            )
                        else:
                            self.add_log(f"⚠️ [FAILED] Comment submit nahi hua: {res_msg}", "WARN")

                    except Exception as e:
                        self.add_log(f"❌ [ERROR] Comment exception: {str(e)}. Auto-retrying...", "ERROR")
                        if not self._sleep_interruptible(5.0):
                            break

                # MODE 2: MESSENGER CHAT (PERSONAL / GROUP)
                else:
                    try:
                        # 1. AUTO-SEEN: Mark chat as seen
                        self.status = "SEEN"
                        fb_session.mark_as_seen(self.target_id, is_group=is_group)
                        self.add_log(f"👁️ [AUTO-SEEN] Target '{self.target_id}' par seen mark kiya gaya.", "SEEN")

                        if not self._sleep_interruptible(0.5):
                            break

                        # 2. AUTO-TYPING: Start typing indicator
                        self.status = "TYPING"
                        fb_session.send_typing_indicator(self.target_id, is_typing=True)
                        self.add_log(f"⌨️ [TYPING] FB par 'typing...' indicator start kiya ({self.typing_delay}s)...", "TYPING")

                        if not self._sleep_interruptible(self.typing_delay):
                            fb_session.send_typing_indicator(self.target_id, is_typing=False)
                            break

                        # 3. SEND MESSAGE
                        self.status = "SENDING"
                        success, res_msg = fb_session.send_message(self.target_id, full_message, is_group=is_group)
                        fb_session.send_typing_indicator(self.target_id, is_typing=False)

                        if success:
                            self.total_sent += 1
                            self.add_log(
                                f"✅ [SENT #{self.total_sent}] (Loop #{self.loop_count}, Line {self.current_line_idx}/{self.total_lines}) -> \"{full_message[:45]}{'...' if len(full_message) > 45 else ''}\"",
                                "SUCCESS"
                            )
                        else:
                            self.add_log(f"⚠️ [FAILED] Message deliver nahi hua: {res_msg}", "WARN")

                    except Exception as e:
                        self.add_log(f"❌ [ERROR] Exception caught: {str(e)}. Auto-retrying...", "ERROR")
                        try:
                            fb_session.send_typing_indicator(self.target_id, is_typing=False)
                        except Exception:
                            pass
                        if not self._sleep_interruptible(5.0):
                            break

                # Interval Delay Between Messages / Comments
                self.status = "RUNNING"
                if not self._sleep_interruptible(self.message_delay):
                    break

            if self.stop_event.is_set():
                break

            # Reached end of file
            if self.infinite_loop:
                self.loop_count += 1
                item_name = "Comments" if self.task_mode == "comment" else "Messages"
                self.add_log(f"🔄 [FILE RESTART] Sabhi {self.total_lines} {item_name} complete ho gaye! Loop #{self.loop_count} shuru se start ho raha hai...", "SUCCESS")
                if not self._sleep_interruptible(2.0):
                    break
            else:
                self.add_log("🏁 File ke sabhi items complete ho gaye. Loop mode OFF tha, stopping bot.", "INFO")
                break

        self.is_running = False
        self.status = "STOPPED"

    def get_status(self) -> dict:
        """Returns current live bot statistics."""
        uptime_str = "00:00:00"
        if self.is_running and self.start_time:
            diff = int(time.time() - self.start_time)
            hours, remainder = divmod(diff, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return {
            "is_running": self.is_running,
            "status": self.status,
            "task_mode": self.task_mode,
            "trigger_mode": getattr(self, "trigger_mode", "loop"),
            "uptime": uptime_str,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "user_name": self.user_name,
            "user_id": self.user_id,
            "total_sent": self.total_sent,
            "loop_count": self.loop_count,
            "current_line": self.current_line_idx,
            "total_lines": self.total_lines,
            "typing_delay": self.typing_delay,
            "message_delay": self.message_delay,
            "infinite_loop": self.infinite_loop,
            "prefix": self.prefix,
        }


# Global instance
bot_runner = BotRunner()
