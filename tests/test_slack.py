"""
Slack delivery (card #986): mrkdwn conversion, signature checks on every
route, acknowledging events before answering them, and slack_send_message
reporting what actually happened.
"""

import asyncio
import hashlib
import hmac
import threading
import time
import warnings

import pytest
from starlette.applications import Starlette
from starlette.testclient import TestClient

import networks.slack_http as slack_http
from networks.slack import SlackClient, markdown_to_mrkdwn
from tools.direct_tools import SlackToolProvider


class TestMrkdwn:
    @pytest.mark.parametrize("markdown,mrkdwn", [
        ("this is **important** ok", "this is *important* ok"),
        ("an *aside* here", "an _aside_ here"),
        ("**bold** and *italic*", "*bold* and _italic_"),
        ("Items:\n* apple\n* banana", "Items:\n• apple\n• banana"),
        ("- one\n  - two", "• one\n  • two"),
        ("## Results\nfine", "*Results*\nfine"),
        ("2 * 3 * 4", "2 * 3 * 4"),
        ("~~old~~ new", "~old~ new"),
        ("see [the docs](https://example.com/a)", "see <https://example.com/a|the docs>"),
        ("> quoted\nnot > this", "> quoted\nnot &gt; this"),
        ("a < b & c", "a &lt; b &amp; c"),
    ])
    def test_prose(self, markdown, mrkdwn):
        assert markdown_to_mrkdwn(markdown) == mrkdwn

    def test_inline_code_is_left_alone(self):
        assert markdown_to_mrkdwn("use `a*b*c` and `**x**`") == "use `a*b*c` and `**x**`"

    def test_code_block_is_left_alone_minus_its_language(self):
        text = "```python\ndef f(*args, **kw):\n    return a < b\n```"
        assert markdown_to_mrkdwn(text) == "```\ndef f(*args, **kw):\n    return a &lt; b\n```"

    def test_slack_tokens_pass_through(self):
        text = "hey <@U123ABC>, see <#C42|general> and <https://x.io|this>"
        assert markdown_to_mrkdwn(text) == text


def sign(secret, body, timestamp=None):
    timestamp = str(int(timestamp or time.time()))
    digest = hmac.new(secret.encode(), f"v0:{timestamp}:{body}".encode(), hashlib.sha256).hexdigest()
    return {"X-Slack-Request-Timestamp": timestamp, "X-Slack-Signature": f"v0={digest}"}


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "s3cret")
    return TestClient(Starlette(routes=slack_http.get_slack_routes()))


class TestSignatures:
    @pytest.mark.parametrize("route", ["/slack/events", "/slack/commands", "/slack/interactive"])
    def test_unsigned_requests_are_refused(self, http, route):
        with warnings.catch_warnings():
            # An un-awaited check would warn here as well as letting the request in
            warnings.simplefilter("error", RuntimeWarning)
            response = http.post(route, content="payload=%7B%7D",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert response.status_code == 403

    @pytest.mark.parametrize("route", ["/slack/commands", "/slack/interactive"])
    def test_signed_requests_are_accepted(self, http, route):
        body = "command=%2Fj4ne&text=hi&payload=%7B%7D"
        headers = {"Content-Type": "application/x-www-form-urlencoded", **sign("s3cret", body)}
        assert http.post(route, content=body, headers=headers).status_code == 200

    def test_old_timestamps_are_refused(self, http):
        body = "payload=%7B%7D"
        headers = {"Content-Type": "application/x-www-form-urlencoded",
                   **sign("s3cret", body, timestamp=time.time() - 3600)}
        assert http.post("/slack/commands", content=body, headers=headers).status_code == 403


class SlowSlackClient:
    """Stands in for SlackClient; its answer takes as long as the test says"""

    def __init__(self):
        self.app = type("App", (), {"client": object()})()
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.finished = False

    async def _handle_message_event(self, event, client, is_mention=False):
        self.started.set()
        await self.release.wait()
        self.finished = True


class TestEventsAck:
    def test_events_are_acknowledged_before_the_answer(self, monkeypatch):
        monkeypatch.setenv("SLACK_SIGNING_SECRET", "s3cret")
        slow = SlowSlackClient()
        monkeypatch.setattr(SlackClient, "_global_instance", slow)
        app = Starlette(routes=slack_http.get_slack_routes())

        async def scenario():
            import httpx
            body = '{"type":"event_callback","event":{"type":"app_mention","user":"U1","channel":"C1","ts":"1.0","text":"hi"}}'
            headers = {"Content-Type": "application/json", **sign("s3cret", body)}
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await asyncio.wait_for(client.post("/slack/events", content=body, headers=headers), 2)
            assert response.status_code == 200
            assert not slow.finished
            await asyncio.wait_for(slow.started.wait(), 2)
            slow.release.set()
            await asyncio.sleep(0)
            for _ in range(10):
                if slow.finished:
                    break
                await asyncio.sleep(0.01)
            assert slow.finished

        slack_http.processed_events.clear()
        asyncio.run(scenario())


class FakeSlack:
    """A connected SlackClient whose loop runs in a thread of its own"""

    def __init__(self, accept=True):
        self.connected = True
        self.accept = accept
        self.sent = []
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    async def send_message(self, channel, message, thread_ts=None):
        self.sent.append((channel, message, thread_ts))
        return self.accept

    def close(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(2)
        self.loop.close()


class TestSendMessageTool:
    @pytest.fixture
    def tool(self):
        return SlackToolProvider().tools["slack_send_message"]

    def test_reports_success_once_slack_accepts(self, tool, monkeypatch):
        slack = FakeSlack(accept=True)
        monkeypatch.setattr(SlackClient, "_global_instance", slack)
        try:
            result = tool.execute(channel="#general", message="hello")
        finally:
            slack.close()
        assert result["success"] is True
        assert slack.sent == [("#general", "hello", None)]

    def test_reports_failure_when_slack_refuses(self, tool, monkeypatch):
        slack = FakeSlack(accept=False)
        monkeypatch.setattr(SlackClient, "_global_instance", slack)
        try:
            result = tool.execute(channel="#nowhere", message="hello")
        finally:
            slack.close()
        assert "error" in result

    def test_without_slack(self, tool, monkeypatch):
        monkeypatch.setattr(SlackClient, "_global_instance", None)
        assert "not available" in tool.execute(channel="#general", message="hello")["error"]
