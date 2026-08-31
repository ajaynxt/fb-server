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

if __name__ == "__main__":
    unittest.main()
