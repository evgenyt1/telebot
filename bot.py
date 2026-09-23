"""Tiny Telegram Business bot: answer 'время' in incoming private chats."""

import argparse
import hmac
import json
import logging
import os
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
WORD = re.compile(r"(?<!\w)время(?!\w)", re.IGNORECASE)
LOG = logging.getLogger("telebot")


def load_env():
    """Read simple KEY=VALUE lines from the local, ignored .env file."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"\''))


def api(method, payload):
    token = os.environ["BOT_TOKEN"]
    request = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Telegram {method} request failed: {exc}") from exc
    if not result.get("ok"):
        raise RuntimeError(f"Telegram {method}: {result.get('description', 'unknown error')}")
    return result["result"]


def reply_for(update, call_api=api, now=None):
    """Handle only a new, incoming Business message in a private chat."""
    message = update.get("business_message")
    if not isinstance(message, dict):
        return False
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    text = message.get("text")
    connection_id = message.get("business_connection_id")
    if (
        chat.get("type") != "private"
        or not isinstance(text, str)
        or not WORD.search(text)
        or not connection_id
        or sender.get("id") != chat.get("id")
        or sender.get("is_bot")
    ):
        return False

    connection = call_api("getBusinessConnection", {"business_connection_id": connection_id})
    if not connection.get("is_enabled") or not (connection.get("rights") or {}).get("can_reply"):
        LOG.info("Business connection cannot reply; skipping")
        return False

    zone = ZoneInfo(os.environ.get("TIME_ZONE", "Europe/Istanbul"))
    current = now or datetime.now(zone)
    answer = f"Сейчас {current.astimezone(zone):%H:%M} ({zone.key})."
    call_api("sendMessage", {
        "business_connection_id": connection_id,
        "chat_id": chat["id"],
        "text": answer,
    })
    return True


class Handler(BaseHTTPRequestHandler):
    seen_updates = set()

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok\n")

    def do_POST(self):
        if self.path != "/webhook":
            self.send_error(404)
            return
        expected = os.environ["WEBHOOK_SECRET"]
        actual = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(actual, expected):
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 1024 * 1024:
                self.send_error(413)
                return
            update = json.loads(self.rfile.read(length))
            if not isinstance(update, dict):
                raise ValueError("update must be an object")
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return

        update_id = update.get("update_id")
        if update_id not in self.seen_updates:
            try:
                reply_for(update)
            except Exception:
                LOG.exception("Could not process Telegram update")
                self.send_error(502)
                return
            if isinstance(update_id, int):
                self.seen_updates.add(update_id)
                if len(self.seen_updates) > 1000:
                    self.seen_updates.clear()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok\n")


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="run local webhook server")
    webhook = commands.add_parser("set-webhook", help="register current tunnel URL")
    webhook.add_argument("url", help="https://...trycloudflare.com")
    commands.add_parser("webhook-info", help="check Telegram webhook status")
    commands.add_parser("delete-webhook", help="stop webhook delivery")
    args = parser.parse_args()

    if not os.environ.get("BOT_TOKEN") or not os.environ.get("WEBHOOK_SECRET"):
        parser.error("set BOT_TOKEN and WEBHOOK_SECRET in .env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "serve":
        port = int(os.environ.get("PORT", "8080"))
        LOG.info("Listening at http://127.0.0.1:%s", port)
        HTTPServer(("127.0.0.1", port), Handler).serve_forever()
    elif args.command == "set-webhook":
        parsed = urlparse(args.url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            parser.error("provide an HTTPS tunnel URL")
        target = args.url.rstrip("/") + "/webhook"
        api("setWebhook", {
            "url": target,
            "secret_token": os.environ["WEBHOOK_SECRET"],
            "allowed_updates": ["business_connection", "business_message"],
            "max_connections": 1,
        })
        print(f"Webhook set: {target}")
    elif args.command == "webhook-info":
        print(json.dumps(api("getWebhookInfo", {}), ensure_ascii=False, indent=2))
    else:
        api("deleteWebhook", {})
        print("Webhook removed")


if __name__ == "__main__":
    main()
