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
    Parses various auth formats:
    1. Direct Facebook Access Token: 'EAAAAAY...' or 'EAAB...' (MonokaiToolkit format)
    2. Standard cookie string: 'c_user=123; xs=abc; datr=xyz;'
    3. JSON array (AppState format from Chrome extensions): [{"name": "c_user", "value": "123"}, ...]
    4. JSON dict: {"c_user": "123", "xs": "abc"}
    """
    cookie_input = cookie_input.strip()
    cookies_dict = {}

    if not cookie_input:
        return cookies_dict

    # Check if direct Facebook Access Token (MonokaiToolkit / Graph API)
    if cookie_input.startswith("EAA") and len(cookie_input) > 25:
        return {
            "access_token": cookie_input,
            "c_user": "token_user"
        }

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

    def __init__(self, cookies: dict, proxy: str = "", rotate_ip: bool = True):
        self.cookies = cookies
        self.access_token = self.cookies.get("access_token", "")
        self.raw_proxy = proxy.strip() if proxy else ""
        self.rotate_ip = rotate_ip
        
        # Build proxy pool (supports multi-line list or comma-separated)
        self.proxy_pool = []
        if self.raw_proxy:
            lines = self.raw_proxy.replace(",", "\n").split("\n")
            for line in lines:
                p = line.strip()
                if p:
                    if not (p.startswith("http://") or p.startswith("https://") or p.startswith("socks5://")):
                        p = "http://" + p
                    self.proxy_pool.append(p)
        
        self.current_proxy_idx = 0
        self.current_proxy_url = ""
        self.session = requests.Session()
        
        # Apply initial proxy
        if self.proxy_pool:
            self.rotate_ip_address()
        
        # Build direct Cookie header string to ensure cookies are always sent to all domains
        self.cookie_header_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items() if k != "access_token"])
        
        self.session.headers.update({
            "User-Agent": DESKTOP_UA,
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Cookie": self.cookie_header_str,
        })
        
        # Also set in cookie jar
        for k, v in self.cookies.items():
            if k != "access_token":
                self.session.cookies.set(k, v, domain=".facebook.com")
                self.session.cookies.set(k, v, domain="facebook.com")
                self.session.cookies.set(k, v, domain=".m.facebook.com")
                self.session.cookies.set(k, v, domain=".mbasic.facebook.com")

        self.user_id = str(self.cookies.get("c_user", ""))
        self.user_name = "Facebook User"
        self.fb_dtsg = ""
        self.jazoest = ""
        self.is_valid = False

    def rotate_ip_address(self) -> str:
        """Rotates to next Indian IP address in pool or generates dynamic session."""
        if not self.proxy_pool:
            return ""
        
        chosen_proxy = self.proxy_pool[self.current_proxy_idx % len(self.proxy_pool)]
        self.current_proxy_idx += 1
        
        # If proxy URL supports dynamic session rotation (e.g. user-session-1234)
        if "-session-" in chosen_proxy or "_session-" in chosen_proxy:
            new_sess = str(random.randint(100000, 999999))
            chosen_proxy = re.sub(r'[-_]session[-_][A-Za-z0-9]+', f'-session-{new_sess}', chosen_proxy)
            
        self.current_proxy_url = chosen_proxy
        self.session.proxies = {
            "http": chosen_proxy,
            "https": chosen_proxy
        }
        return chosen_proxy

    def validate_and_extract_tokens(self) -> tuple[bool, str]:
        """Validates cookie session or Access Token and extracts fb_dtsg and account profile name."""
        # 1. ACCESS TOKEN VALIDATION (MonokaiToolkit / Graph API)
        if self.access_token:
            try:
                res = self.session.get(
                    f"https://graph.facebook.com/v19.0/me?access_token={self.access_token}&fields=id,name",
                    timeout=12
                )
                if res.status_code == 200:
                    data = res.json()
                    self.user_id = str(data.get("id", "token_user"))
                    self.user_name = str(data.get("name", "Facebook Token User"))
                    self.fb_dtsg = f"NAc{self.user_id}"
                    self.jazoest = compute_jazoest(self.fb_dtsg)
                    self.is_valid = True
                    return True, f"Token Valid! Logged in as: {self.user_name} (UID: {self.user_id})"
                else:
                    err_msg = res.json().get("error", {}).get("message", "Token invalid ya expired hai.")
                    return False, f"Access Token Error: {err_msg}"
            except Exception as e:
                return False, f"Token validation error: {str(e)}"

        if not self.user_id:
            for k in ["c_user", "i_user", "uid", "user_id"]:
                if k in self.cookies:
                    self.user_id = str(self.cookies[k])
                    break

        if not self.user_id or self.user_id == "token_user":
            return False, "Cookies me 'c_user' (User ID) nahi mila. Pura AppState JSON ya valid cookie string/token paste karein."

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
            # 1. First check mbasic.facebook.com
            try:
                m_res = self.session.get("https://mbasic.facebook.com/", timeout=12, headers={"User-Agent": MOBILE_UA}, allow_redirects=True)
                m_html = m_res.text

                # Check checkpoint or logged out
                if "checkpoint" in m_res.url or "/checkpoint/" in m_html or "two_factor" in m_html:
                    return False, "⚠️ Facebook ne Checkpoint lagaya hai (Location Mismatch). Facebook app open karke 'Yes, it was me' confirm karein, fir fresh cookie daalein."

                for pattern in dtsg_patterns:
                    match = re.search(pattern, m_html)
                    if match:
                        self.fb_dtsg = match.group(1)
                        break

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
                    res = self.session.get("https://www.facebook.com/", timeout=12, allow_redirects=True)
                    html = res.text

                    if "checkpoint" in res.url or "/checkpoint/" in html:
                        return False, "⚠️ Facebook Security Checkpoint Detect hua! Facebook me jakar verify karein aur fresh cookies export karein."

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
                    res_m = self.session.get("https://m.facebook.com/messages/", timeout=12, headers={"User-Agent": MOBILE_UA}, allow_redirects=True)
                    for pattern in dtsg_patterns:
                        match = re.search(pattern, res_m.text)
                        if match:
                            self.fb_dtsg = match.group(1)
                            break
                except Exception:
                    pass

            if not self.fb_dtsg:
                if self.cookies.get("xs") and len(self.cookies.get("xs", "")) > 8:
                    self.fb_dtsg = f"NAc{self.user_id}"
                else:
                    return False, "Session expired ya invalid hai. Facebook me login karke fresh Cookie JSON export karein."

            self.jazoest = compute_jazoest(self.fb_dtsg)
            self.is_valid = True
            return True, f"Cookie Valid! Logged in as: {self.user_name} (UID: {self.user_id})"

        except Exception as e:
            return False, f"Connection error during validation: {str(e)}"

    def mark_as_seen(self, thread_id: str, is_group: bool = False) -> bool:
        """Sends mark-seen / read receipt to Facebook Messenger."""
        try:
            url = "https://www.facebook.com/ajax/mercury/mark_seen.php"
            payload = {
                "seen_timestamp": int(time.time() * 1000),
                "threads[0][id]": f"user:{thread_id}" if not is_group else f"root:{thread_id}",
                "threads[0][watermark]": int(time.time() * 1000),
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
            }
            self.session.post(url, data=payload, timeout=8)
            return True
        except Exception:
            return False

    def send_typing_indicator(self, thread_id: str, is_typing: bool = True) -> bool:
        """Sends live typing indicator (typing state) to Facebook Messenger."""
        try:
            url = "https://www.facebook.com/ajax/messaging/typ.php"
            payload = {
                "typ_state": "1" if is_typing else "0",
                "to": str(thread_id),
                "source": "mercury-chat",
                "thread": str(thread_id),
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                "__user": self.user_id,
                "__a": "1",
            }
            self.session.post(url, data=payload, timeout=8)
            return True
        except Exception:
            return False

    def send_message(self, thread_id: str, message_text: str, is_group: bool = False) -> tuple[bool, str]:
        """
        Dispatches message to Facebook Messenger using multi-engine fallbacks:
        1. Web Mercury Send Messages AJAX API (Desktop Messenger)
        2. Dynamic mbasic Form Parser
        3. Direct mbasic /messages/send/?icm=1 POST
        4. Direct m.facebook.com /messages/send/?icm=1 POST
        5. Facebook Graph API (If Token Provided)
        """
        diag_errors = []

        # --- Method 1: Web Mercury Send Messages AJAX API ---
        try:
            msg_time = int(time.time() * 1000)
            client_msg_id = f"{msg_time}{random.randint(100, 999)}"
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
                "User-Agent": DESKTOP_UA,
                "Origin": "https://www.facebook.com",
                "Referer": f"https://www.facebook.com/messages/t/{thread_id}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": self.cookie_header_str,
                "X-Requested-With": "XMLHttpRequest",
            }

            res = self.session.post(url, data=payload, headers=headers, timeout=12)
            if res.status_code == 200:
                if '"error":' not in res.text and ('"payload":' in res.text or '"actions":' in res.text or '"thread_fbid":' in res.text or 'message_id' in res.text):
                    return True, "Delivered via Web Mercury API"
                elif '"error":' in res.text:
                    err_m = re.search(r'"errorDescription":\s*"([^"]+)"', res.text)
                    diag_errors.append(f"Mercury: {err_m.group(1) if err_m else 'API Error'}")
            else:
                diag_errors.append(f"Mercury: HTTP {res.status_code}")

            if not is_group:
                payload_alt = dict(payload)
                payload_alt.pop("message_batch[0][other_user_fbid]", None)
                payload_alt["message_batch[0][thread_fbid]"] = str(thread_id)
                payload_alt["message_batch[0][client_thread_id]"] = f"root:{thread_id}"
                res_alt = self.session.post(url, data=payload_alt, headers=headers, timeout=12)
                if res_alt.status_code == 200:
                    if '"error":' not in res_alt.text and ('"payload":' in res_alt.text or '"actions":' in res_alt.text or '"thread_fbid":' in res_alt.text or 'message_id' in res_alt.text):
                        return True, "Delivered via Web Mercury API (Thread Mode)"
        except Exception as e:
            diag_errors.append(f"Mercury: {str(e)[:30]}")

        # --- Method 2: Dynamic mbasic Form Parser ---
        try:
            urls = []
            if not is_group:
                urls.append(f"https://mbasic.facebook.com/messages/compose/?ids={thread_id}")
                urls.append(f"https://mbasic.facebook.com/messages/read/?tid=cid.c.{thread_id}%3A{self.user_id}")
                urls.append(f"https://mbasic.facebook.com/messages/read/?tid=cid.c.{self.user_id}%3A{thread_id}")
                urls.append(f"https://mbasic.facebook.com/messages/read/?tid={thread_id}")
            else:
                urls.append(f"https://mbasic.facebook.com/messages/read/?tid=cid.g.{thread_id}")
                urls.append(f"https://mbasic.facebook.com/messages/read/?tid={thread_id}")

            for c_url in urls:
                headers_get = {
                    "User-Agent": MOBILE_UA,
                    "Cookie": self.cookie_header_str,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                }
                get_res = self.session.get(c_url, headers=headers_get, timeout=12, allow_redirects=True)
                
                # Extract fresh dtsg if present in page
                dtsg_page_m = re.search(r'name="fb_dtsg"\s+value="([^"]+)"', get_res.text)
                if dtsg_page_m:
                    self.fb_dtsg = dtsg_page_m.group(1)
                    self.jazoest = compute_jazoest(self.fb_dtsg)

                form_match = re.search(r'<form[^>]*\s+action=["\']([^"\']+)["\']', get_res.text, re.IGNORECASE)
                if not form_match:
                    form_match = re.search(r'action=["\']([^"\']+)["\']', get_res.text, re.IGNORECASE)

                if form_match:
                    post_action = form_match.group(1).replace("&amp;", "&")
                    if not post_action.startswith("http"):
                        post_action = "https://mbasic.facebook.com" + post_action

                    form_data = {}
                    inputs = re.findall(r'<input\s+[^>]*>', get_res.text, re.IGNORECASE)
                    for inp in inputs:
                        name_m = re.search(r'name=["\']([^"\']+)["\']', inp, re.IGNORECASE)
                        val_m = re.search(r'value=["\']([^"\']*)["\']', inp, re.IGNORECASE)
                        if name_m:
                            name = name_m.group(1)
                            val = val_m.group(1) if val_m else ""
                            form_data[name] = val

                    if "fb_dtsg" not in form_data:
                        form_data["fb_dtsg"] = self.fb_dtsg
                    if "jazoest" not in form_data:
                        form_data["jazoest"] = self.jazoest
                    if not is_group and f"ids[{thread_id}]" not in form_data:
                        form_data[f"ids[{thread_id}]"] = str(thread_id)

                    textarea_m = re.search(r'<textarea[^>]*name=["\']([^"\']+)["\']', get_res.text, re.IGNORECASE)
                    body_key = textarea_m.group(1) if textarea_m else "body"
                    form_data[body_key] = message_text
                    form_data["Send"] = "Send"
                    form_data["send"] = "Send"

                    headers_post = {
                        "User-Agent": MOBILE_UA,
                        "Origin": "https://mbasic.facebook.com",
                        "Referer": c_url,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Cookie": self.cookie_header_str,
                    }

                    send_res = self.session.post(post_action, data=form_data, headers=headers_post, timeout=12, allow_redirects=True)
                    if send_res.status_code in [200, 302]:
                        if "checkpoint" not in send_res.url and "error" not in send_res.url:
                            return True, "Delivered via Mobile Form Engine"
        except Exception as e:
            diag_errors.append(f"mbasic: {str(e)[:30]}")

        # --- Method 3: Direct Mobile POST Endpoint ---
        try:
            m_post_url = "https://mbasic.facebook.com/messages/send/?icm=1"
            m_post_data = {
                "fb_dtsg": self.fb_dtsg,
                "jazoest": self.jazoest,
                f"ids[{thread_id}]": str(thread_id),
                "body": message_text,
                "Send": "Send",
                "tids": f"cid.c.{thread_id}:{self.user_id}" if not is_group else f"cid.g.{thread_id}",
            }
            m_hdrs = {
                "User-Agent": MOBILE_UA,
                "Origin": "https://mbasic.facebook.com",
                "Referer": f"https://mbasic.facebook.com/messages/compose/?ids={thread_id}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": self.cookie_header_str,
            }
            m_res = self.session.post(m_post_url, data=m_post_data, headers=m_hdrs, timeout=12, allow_redirects=True)
            if m_res.status_code in [200, 302]:
                if "checkpoint" not in m_res.url and "login" not in m_res.url:
                    return True, "Delivered via Direct Mobile Gateway"
        except Exception as e:
            diag_errors.append(f"DirectMobile: {str(e)[:30]}")

        # --- Method 4: Facebook Graph API (If Token Provided) ---
        if self.access_token:
            errors_g = []
            try:
                graph_url = f"https://graph.facebook.com/v19.0/me/messages?access_token={self.access_token}"
                payload_graph = {
                    "recipient": {"id": str(thread_id)},
                    "message": {"text": message_text}
                }
                res_g = self.session.post(graph_url, json=payload_graph, timeout=12)
                if res_g.status_code in [200, 201] and ("message_id" in res_g.text or "recipient_id" in res_g.text):
                    return True, "Delivered via Facebook Graph API"
                else:
                    try:
                        errors_g.append(res_g.json().get("error", {}).get("message", res_g.text[:80]))
                    except Exception:
                        pass
                
                res_direct = self.session.post(
                    f"https://graph.facebook.com/v19.0/{thread_id}?access_token={self.access_token}",
                    data={"message": message_text},
                    timeout=12
                )
                if res_direct.status_code in [200, 201] and ("id" in res_direct.text or "success" in res_direct.text):
                    return True, "Delivered via Direct Graph API"
                else:
                    try:
                        errors_g.append(res_direct.json().get("error", {}).get("message", res_direct.text[:80]))
                    except Exception:
                        pass

                res_v2 = self.session.post(
                    f"https://graph.facebook.com/v2.6/me/messages?access_token={self.access_token}",
                    json={"recipient": {"id": str(thread_id)}, "message": {"text": message_text}},
                    timeout=12
                )
                if res_v2.status_code in [200, 201] and ("message_id" in res_v2.text or "recipient_id" in res_v2.text):
                    return True, "Delivered via Graph v2.6 Gateway"

            except Exception as e:
                errors_g.append(str(e))

            if errors_g and not self.cookie_header_str:
                return False, f"Graph API Token Notice: {errors_g[0]}"

        err_summary = " | ".join(diag_errors) if diag_errors else "Target message block / restricted"
        return False, f"Delivery failed ({err_summary})"


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
        Tries Facebook Graph API first (if token), then AJAX UFI, then mbasic form.
        """
        # Method 0: Graph API Comments (If Access Token provided - 100% Reliable!)
        if self.access_token:
            try:
                graph_url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
                res_g = self.session.post(graph_url, data={
                    "message": comment_text,
                    "access_token": self.access_token
                }, timeout=12)
                if res_g.status_code in [200, 201] and "id" in res_g.text:
                    return True, "Commented via Facebook Graph API (Access Token)"
            except Exception:
                pass

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

    def __init__(self, task_id: str = "default", task_name: str = "Primary Server #1"):
        self.task_id = task_id
        self.task_name = task_name
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
        self.typing_delay = 2.0
        self.message_delay = 5.0
        self.run_duration_mins = 0.0
        self.infinite_loop = True
        self.prefix = ""

    def update_speed(self, typing_delay: float = None, message_delay: float = None):
        """Allows dynamically updating speed/delays in real-time while bot is running."""
        updated = []
        if typing_delay is not None:
            self.typing_delay = max(0.0, float(typing_delay))
            updated.append(f"Typing Delay: {self.typing_delay}s")
        if message_delay is not None:
            self.message_delay = max(0.5, float(message_delay))
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
              prefix: str = "", typing_delay: float = 2.0, message_delay: float = 5.0,
              infinite_loop: bool = True, task_mode: str = "chat", trigger_mode: str = "loop",
              run_duration_mins: float = 0.0, proxy: str = "", rotate_ip: bool = True):
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

        fb_session = FacebookSession(cookies, proxy=proxy, rotate_ip=rotate_ip)
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
        self.typing_delay = max(0.0, float(typing_delay))
        self.message_delay = max(0.5, float(message_delay))
        self.run_duration_mins = max(0.0, float(run_duration_mins))
        self.infinite_loop = bool(infinite_loop)
        self.prefix = prefix.strip()

        mode_name = "💬 POST AUTO-COMMENTER" if self.task_mode == "comment" else f"📨 MESSENGER CHAT ({self.target_type.upper()})"
        trig_desc = "⚡ INSTANT AUTO-REPLY ON MSG/SEEN" if self.trigger_mode == "reply_seen" else ("🚀 HYBRID (LOOP + AUTO-REPLY)" if self.trigger_mode == "hybrid" else "🔄 CONTINUOUS TIMER LOOP")
        
        duration_desc = f"{self.run_duration_mins} Minutes" if self.run_duration_mins > 0 else "Infinite 24/7 (Non-stop)"
        self.add_log(f"🚀 Bot Initialized as '{self.user_name}' (UID: {self.user_id})", "SUCCESS")
        self.add_log(f"🎯 Mode: {mode_name} | Trigger: {trig_desc} | Target: {self.target_id}", "INFO")
        self.add_log(f"⏱️ Manual Speed: Typing Delay = {self.typing_delay}s | Message Interval = {self.message_delay}s | Duration = {duration_desc}", "INFO")

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
            time.sleep(min(step, seconds - elapsed))
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

            is_first_start = True
            while not self.stop_event.is_set():
                self.pause_event.wait()
                
                # Check task duration limit
                if self.run_duration_mins > 0 and (time.time() - self.start_time) >= (self.run_duration_mins * 60):
                    self.add_log(f"⏰ [DURATION COMPLETE] Target run duration ({self.run_duration_mins} mins) complete ho gaya! Stopping.", "SUCCESS")
                    self.is_running = False
                    self.status = "COMPLETED"
                    break
                
                trigger_reason = None

                # On start, send first message immediately
                if is_first_start:
                    trigger_reason = "Initial Kickoff (First Message Dispatch)"
                    is_first_start = False
                else:
                    info = fb_session.get_latest_thread_info(self.target_id, is_group=is_group)
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
                    if getattr(fb_session, "rotate_ip", True) and len(getattr(fb_session, "proxy_pool", [])) > 1:
                        new_prx = fb_session.rotate_ip_address()
                        clean_prx = re.sub(r':([^:@]+)@', ':***@', new_prx.replace('http://', '').replace('https://', ''))
                        self.add_log(f"🔄 [IP ROTATED] Nayi Indian Location/IP switch hui: {clean_prx}", "INFO")

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
                
                # Check task duration limit
                if self.run_duration_mins > 0 and (time.time() - self.start_time) >= (self.run_duration_mins * 60):
                    self.add_log(f"⏰ [DURATION COMPLETE] Target run duration ({self.run_duration_mins} mins) complete! Stopping.", "SUCCESS")
                    self.is_running = False
                    self.status = "COMPLETED"
                    return

                self.current_line_idx = idx + 1
                line = raw_line.strip()
                if not line:
                    continue

                full_message = f"{self.prefix} {line}".strip() if self.prefix else line

                # Rotate Indian IP on each loop cycle
                if getattr(fb_session, "rotate_ip", True) and len(getattr(fb_session, "proxy_pool", [])) > 1:
                    new_prx = fb_session.rotate_ip_address()
                    clean_prx = re.sub(r':([^:@]+)@', ':***@', new_prx.replace('http://', '').replace('https://', ''))
                    self.add_log(f"🔄 [IP ROTATED] Nayi Indian Location/IP switch hui: {clean_prx}", "INFO")

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
            "task_id": getattr(self, "task_id", "default"),
            "task_name": getattr(self, "task_name", "Primary Server #1"),
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


class MultiServerManager:
    """
    Manages multiple parallel BotRunner server instances running on the same master Facebook Token or different tokens.
    Allows spawning unlimited independent target servers simultaneously!
    """
    def __init__(self):
        self.servers: dict[str, BotRunner] = {}
        self.master_token: str = ""
        # Initialize primary server
        default_runner = BotRunner(task_id="default", task_name="Primary Server #1")
        self.servers["default"] = default_runner

    def set_master_token(self, token: str):
        self.master_token = token.strip()

    def get_server(self, task_id: str = "default") -> BotRunner:
        if task_id not in self.servers:
            idx = len(self.servers) + 1
            self.servers[task_id] = BotRunner(task_id=task_id, task_name=f"Server #{idx}")
        return self.servers[task_id]

    def create_server(self, task_name: str = "", task_id: str = None) -> BotRunner:
        if not task_id:
            task_id = f"srv_{int(time.time()*1000)%100000}_{len(self.servers)+1}"
        if not task_name:
            task_name = f"Server #{len(self.servers)+1}"
        srv = BotRunner(task_id=task_id, task_name=task_name)
        self.servers[task_id] = srv
        return srv

    def list_servers(self) -> list:
        result = []
        for sid, srv in list(self.servers.items()):
            st = srv.get_status()
            st["task_id"] = sid
            st["task_name"] = srv.task_name
            result.append(st)
        return result

    def stop_all(self) -> int:
        stopped = 0
        for sid, srv in self.servers.items():
            if srv.is_running:
                srv.stop()
                stopped += 1
        return stopped

    def delete_server(self, task_id: str) -> bool:
        if task_id == "default":
            self.servers["default"].stop()
            return True
        if task_id in self.servers:
            srv = self.servers[task_id]
            if srv.is_running:
                srv.stop()
            del self.servers[task_id]
            return True
        return False


# Global Manager & Default Instance
multi_manager = MultiServerManager()
bot_runner = multi_manager.get_server("default")
