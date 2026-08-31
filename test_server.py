"""
Automated unit verification for FB Messenger Server & Engine
"""

import unittest
import json
import time
from fb_engine import parse_cookies, compute_jazoest, bot_runner, FacebookSession
from server import app

class TestFBServer(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_parse_cookies_string(self):
        cookie_str = "c_user=1000889922; xs=294829%3Aabc; datr=xyz;"
        parsed = parse_cookies(cookie_str)
        self.assertEqual(parsed.get("c_user"), "1000889922")
        self.assertEqual(parsed.get("xs"), "294829%3Aabc")
        self.assertEqual(parsed.get("datr"), "xyz")

    def test_parse_cookies_json_appstate(self):
        appstate = json.dumps([
            {"key": "c_user", "value": "1000998877"},
            {"key": "xs", "value": "secret_token_123"}
        ])
        parsed = parse_cookies(appstate)
        self.assertEqual(parsed.get("c_user"), "1000998877")
        self.assertEqual(parsed.get("xs"), "secret_token_123")

    def test_parse_access_token(self):
        token = "EAAAAAY1234567890abcdefghijklmnopqrstuvwxyz_secret_token"
        parsed = parse_cookies(token)
        self.assertEqual(parsed.get("access_token"), token)
        self.assertIn("c_user", parsed)

    def test_compute_jazoest(self):
        dtsg = "NA"
        jazoest = compute_jazoest(dtsg)
        self.assertTrue(jazoest.startswith("2"))
        self.assertEqual(len(jazoest), 5)  # '2' + '78' + '65' = '27865' (len 5)

    def test_health_endpoint(self):
        response = self.app.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("server_uptime", data)

    def test_status_endpoint(self):
        response = self.app.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("is_running", data)
        self.assertIn("status", data)

    def test_speed_update(self):
        response = self.app.post("/api/update_speed", json={
            "typing_delay": 4,
            "message_delay": 12
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(bot_runner.typing_delay, 4)
        self.assertEqual(bot_runner.message_delay, 12)

    def test_bot_runner_controls(self):
        # Test stop on stopped bot
        success, msg = bot_runner.stop()
        self.assertFalse(success)

        # Test speed update method
        bot_runner.update_speed(typing_delay=2, message_delay=8)
        self.assertEqual(bot_runner.typing_delay, 2)
        self.assertEqual(bot_runner.message_delay, 8)

    def test_task_mode_status(self):
        status = bot_runner.get_status()
        self.assertIn("task_mode", status)
        self.assertIn("target_type", status)

    def test_cookie_profiles_storage(self):
        # Save profile
        res = self.app.post("/api/profiles", json={
            "name": "test_account",
            "cookies": "c_user=123; xs=abc;",
            "user_name": "Test User",
            "user_id": "123"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        # List profiles
        res_list = self.app.get("/api/profiles")
        self.assertEqual(res_list.status_code, 200)
        profiles = res_list.get_json().get("profiles", [])
        self.assertTrue(any(p["profile_name"] == "test_account" for p in profiles))

        # Delete profile
        res_del = self.app.delete("/api/profiles/test_account")
        self.assertEqual(res_del.status_code, 200)

    def test_message_files_storage(self):
        # Save file
        res = self.app.post("/api/files", json={
            "filename": "test_msgs.txt",
            "content": "Line 1\nLine 2\nLine 3"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json().get("success"))

        # List files
        res_list = self.app.get("/api/files")
        self.assertEqual(res_list.status_code, 200)
        files = res_list.get_json().get("files", [])
        self.assertTrue(any(f["filename"] == "test_msgs.txt" for f in files))

        # Delete file
        res_del = self.app.delete("/api/files/test_msgs.txt")
        self.assertEqual(res_del.status_code, 200)

    def test_multi_server_endpoints(self):
        # 1. List servers
        res = self.app.get("/api/servers")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("total_servers", 0), 1)

        # 2. Create new server
        res_create = self.app.post("/api/servers/create", json={"task_name": "Server 2 - Group War"})
        self.assertEqual(res_create.status_code, 200)
        c_data = res_create.get_json()
        self.assertTrue(c_data.get("success"))
        task_id = c_data.get("task_id")
        self.assertIsNotNone(task_id)

        # 3. Stop all servers
        res_stop = self.app.post("/api/servers/stop_all")
        self.assertEqual(res_stop.status_code, 200)

        # 4. Delete server
        res_del = self.app.delete(f"/api/servers/{task_id}/delete")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json().get("success"))

    def test_check_ip(self):
        res = self.app.get("/api/check_ip")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIsNotNone(data.get("ip"))

if __name__ == "__main__":
    unittest.main()
