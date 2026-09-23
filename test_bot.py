import os
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from bot import reply_for


class BotTests(unittest.TestCase):
    def setUp(self):
        self.update = {
            "business_message": {
                "business_connection_id": "connection",
                "chat": {"id": 123, "type": "private"},
                "from": {"id": 123, "is_bot": False},
                "text": "Которое время?",
            }
        }
        self.calls = []
        os.environ["TIME_ZONE"] = "Europe/Istanbul"

    def api(self, method, payload):
        self.calls.append((method, payload))
        if method == "getBusinessConnection":
            return {"is_enabled": True, "rights": {"can_reply": True}}
        return {"message_id": 1}

    def test_replies_in_business_chat(self):
        instant = datetime(2026, 9, 23, 18, 45, tzinfo=ZoneInfo("Europe/Istanbul"))
        self.assertTrue(reply_for(self.update, self.api, instant))
        self.assertEqual(self.calls[-1], ("sendMessage", {
            "business_connection_id": "connection", "chat_id": 123,
            "text": "Сейчас 18:45 (Europe/Istanbul).",
        }))

    def test_ignores_outgoing_and_other_words(self):
        self.update["business_message"]["from"]["id"] = 999
        self.assertFalse(reply_for(self.update, self.api))
        self.update["business_message"]["from"]["id"] = 123
        self.update["business_message"]["text"] = "времени"
        self.assertFalse(reply_for(self.update, self.api))
        self.assertEqual(self.calls, [])

    def test_ignores_connection_without_reply_right(self):
        def no_rights(method, payload):
            self.calls.append((method, payload))
            return {"is_enabled": True, "rights": {"can_reply": False}}

        self.assertFalse(reply_for(self.update, no_rights))
        self.assertEqual(len(self.calls), 1)


if __name__ == "__main__":
    unittest.main()
