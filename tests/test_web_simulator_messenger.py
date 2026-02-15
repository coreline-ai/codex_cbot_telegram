import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import core
import simulator_messenger_server as webmock


def _write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _setup_webmock_paths(monkeypatch, tmp_path: Path):
    messages = tmp_path / "messages.json"
    outbox = tmp_path / "web_outbox.json"
    history = tmp_path / "web_chat_history.json"
    working = tmp_path / "working.json"
    log = tmp_path / "execution.log"

    _write_json(messages, {"messages": [], "last_update_id": 0})
    _write_json(outbox, {"messages": []})
    _write_json(history, {"messages": []})
    _write_json(working, {"active": False, "message_id": None, "time": ""})
    log.write_text("", encoding="utf-8")

    monkeypatch.setattr(webmock, "ROOT", tmp_path)
    monkeypatch.setattr(webmock, "MESSAGES_FILE", messages)
    monkeypatch.setattr(webmock, "OUTBOX_FILE", outbox)
    monkeypatch.setattr(webmock, "HISTORY_FILE", history)
    monkeypatch.setattr(webmock, "WORKING_FILE", working)
    monkeypatch.setattr(webmock, "EXEC_LOG", log)
    monkeypatch.setattr(webmock, "_ACTIVE_PROCESS", None)

    return {
        "messages": messages,
        "outbox": outbox,
        "history": history,
        "working": working,
        "log": log,
    }


def test_core_webmock_channel_writes_outbox(monkeypatch, tmp_path):
    outbox = tmp_path / "web_outbox.json"
    _write_json(outbox, {"messages": []})

    img = tmp_path / "sample.png"
    doc = tmp_path / "sample.txt"
    img.write_bytes(b"\x89PNG\r\n")
    doc.write_text("demo", encoding="utf-8")

    monkeypatch.setattr(core, "MESSAGE_CHANNEL", "webmock")
    monkeypatch.setattr(core, "_DIR", str(tmp_path))
    monkeypatch.setattr(core, "WEB_OUTBOX_FILE", str(outbox))

    assert asyncio.run(core.send_message(10001, "hello webmock")) is True
    assert asyncio.run(core.send_photo(10001, str(img), caption="photo cap")) is True
    assert asyncio.run(core.send_document(10001, str(doc), caption="doc cap")) is True

    data = _read_json(outbox)
    msgs = data["messages"]
    assert [m["type"] for m in msgs] == ["message", "photo", "document"]
    assert msgs[0]["text"] == "hello webmock"
    assert msgs[1]["photo_path"] == "sample.png"
    assert msgs[2]["file_path"] == "sample.txt"


def test_webmock_api_endpoints(monkeypatch, tmp_path):
    paths = _setup_webmock_paths(monkeypatch, tmp_path)

    def fake_trigger():
        return {"ok": True, "triggered": True, "pid": 12345}

    monkeypatch.setattr(webmock, "_trigger_executor", fake_trigger)
    client = TestClient(webmock.app)

    post_res = client.post("/api/messages", json={"text": "first task", "chat_id": 10001, "user": "Tester"})
    assert post_res.status_code == 200
    payload = post_res.json()
    assert payload["ok"] is True
    assert payload["trigger"]["triggered"] is True

    saved = _read_json(paths["messages"])
    assert len(saved["messages"]) == 1
    assert saved["messages"][0]["text"] == "first task"
    assert saved["messages"][0]["processed"] is False

    get_res = client.get("/api/messages")
    assert get_res.status_code == 200
    messages = get_res.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["direction"] == "in"

    (tmp_path / "artifact.txt").write_text("artifact", encoding="utf-8")
    _write_json(
        paths["outbox"],
        {
            "messages": [
                {
                    "type": "document",
                    "chat_id": 10001,
                    "file_path": "artifact.txt",
                    "caption": "result file",
                    "timestamp": "2026-01-01 00:00:01",
                }
            ]
        },
    )

    get_res_2 = client.get("/api/messages")
    assert get_res_2.status_code == 200
    timeline = get_res_2.json()["messages"]
    assert any(m["direction"] == "out" and m["kind"] == "document" for m in timeline)

    file_res = client.get("/api/files/artifact.txt")
    assert file_res.status_code == 200
    assert file_res.content == b"artifact"

    with pytest.raises(Exception) as exc:
        webmock._safe_file_path("../outside.txt")
    assert getattr(exc.value, "status_code", None) == 403


def test_webmock_message_to_result_integration(monkeypatch, tmp_path):
    paths = _setup_webmock_paths(monkeypatch, tmp_path)

    def fake_trigger_and_process():
        data = _read_json(paths["messages"])
        pending = next((m for m in data["messages"] if not m.get("processed")), None)
        if pending is None:
            return {"ok": True, "triggered": False, "reason": "no_pending"}

        pending["processed"] = True
        _write_json(paths["messages"], data)

        out = _read_json(paths["outbox"])
        out["messages"].append(
            {
                "type": "message",
                "chat_id": pending["chat_id"],
                "text": f"Processed: {pending['text']}",
                "timestamp": pending["timestamp"],
            }
        )
        _write_json(paths["outbox"], out)
        return {"ok": True, "triggered": True}

    monkeypatch.setattr(webmock, "_trigger_executor", fake_trigger_and_process)
    client = TestClient(webmock.app)

    res = client.post("/api/messages", json={"text": "build demo page", "chat_id": 10001, "user": "Tester"})
    assert res.status_code == 200

    timeline = client.get("/api/messages").json()["messages"]
    inbound = [m for m in timeline if m["direction"] == "in"]
    outbound = [m for m in timeline if m["direction"] == "out"]

    assert len(inbound) == 1
    assert inbound[0]["processed"] is True
    assert len(outbound) == 1
    assert outbound[0]["text"].startswith("Processed: build demo page")


def test_webmock_clear_debug_log(monkeypatch, tmp_path):
    paths = _setup_webmock_paths(monkeypatch, tmp_path)
    paths["log"].write_text("line1\nline2\n", encoding="utf-8")

    client = TestClient(webmock.app)
    res = client.post("/api/debug/clear")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert paths["log"].read_text(encoding="utf-8") == ""


def test_webmock_history_persists_when_source_files_reset(monkeypatch, tmp_path):
    paths = _setup_webmock_paths(monkeypatch, tmp_path)

    def fake_trigger():
        return {"ok": True, "triggered": True}

    monkeypatch.setattr(webmock, "_trigger_executor", fake_trigger)
    client = TestClient(webmock.app)

    client.post("/api/messages", json={"text": "remember this message", "chat_id": 10001, "user": "Tester"})
    _write_json(
        paths["outbox"],
        {
            "messages": [
                {
                    "type": "message",
                    "chat_id": 10001,
                    "text": "remembered response",
                    "timestamp": "2026-01-01 00:00:02",
                }
            ]
        },
    )

    first = client.get("/api/messages")
    assert first.status_code == 200
    first_timeline = first.json()["messages"]
    assert any(m.get("direction") == "in" and m.get("text") == "remember this message" for m in first_timeline)
    assert any(m.get("direction") == "out" and m.get("text") == "remembered response" for m in first_timeline)

    _write_json(paths["messages"], {"messages": [], "last_update_id": 0})
    _write_json(paths["outbox"], {"messages": []})

    second = client.get("/api/messages")
    assert second.status_code == 200
    second_timeline = second.json()["messages"]
    assert any(m.get("direction") == "in" and m.get("text") == "remember this message" for m in second_timeline)
    assert any(m.get("direction") == "out" and m.get("text") == "remembered response" for m in second_timeline)


def test_webmock_control_retrigger(monkeypatch, tmp_path):
    _setup_webmock_paths(monkeypatch, tmp_path)

    def fake_trigger():
        return {"ok": True, "triggered": True, "pid": 54321}

    monkeypatch.setattr(webmock, "_trigger_executor", fake_trigger)
    client = TestClient(webmock.app)

    res = client.post("/api/control/retrigger")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["trigger"]["triggered"] is True


def test_webmock_control_test_message(monkeypatch, tmp_path):
    paths = _setup_webmock_paths(monkeypatch, tmp_path)

    def fake_trigger():
        return {"ok": True, "triggered": True, "pid": 11111}

    monkeypatch.setattr(webmock, "_trigger_executor", fake_trigger)
    client = TestClient(webmock.app)

    res = client.post("/api/control/test-message", json={"text": "control ping", "chat_id": 10001, "user": "Tester"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["message"]["text"] == "control ping"

    saved = _read_json(paths["messages"])
    assert any(m.get("text") == "control ping" for m in saved["messages"])


def test_webmock_control_stop_worker(monkeypatch, tmp_path):
    _setup_webmock_paths(monkeypatch, tmp_path)

    class DummyProc:
        def __init__(self):
            self.pid = 99999
            self._alive = True

        def poll(self):
            return None if self._alive else 0

        def terminate(self):
            self._alive = False

        def wait(self, timeout=None):
            self._alive = False
            return 0

        def kill(self):
            self._alive = False

    monkeypatch.setattr(webmock, "_ACTIVE_PROCESS", DummyProc())
    client = TestClient(webmock.app)

    res = client.post("/api/control/stop-worker")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["result"]["stopped"] is True
