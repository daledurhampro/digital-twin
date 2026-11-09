import io
import json
import os
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException


def bedrock_reply(text):
    return {"output": {"message": {"content": [{"text": text}]}}}


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "Operation")


@pytest.fixture
def bedrock(monkeypatch, server_module):
    mock = MagicMock()
    mock.converse.return_value = bedrock_reply("Hi, I'm the twin.")
    monkeypatch.setattr(server_module, "bedrock_client", mock)
    return mock


@pytest.fixture
def s3(monkeypatch, server_module):
    mock = MagicMock()
    monkeypatch.setattr(server_module, "USE_S3", True)
    monkeypatch.setattr(server_module, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(server_module, "s3_client", mock, raising=False)
    return mock


# --- memory helpers -------------------------------------------------------

def test_get_memory_path(server_module):
    assert server_module.get_memory_path("abc") == "abc.json"


def test_load_conversation_local_missing_returns_empty(server_module):
    assert server_module.load_conversation("nope") == []


def test_save_then_load_conversation_local(server_module):
    msgs = [{"role": "user", "content": "hi", "timestamp": "t"}]
    server_module.save_conversation("s1", msgs)
    path = os.path.join(server_module.MEMORY_DIR, "s1.json")
    assert os.path.exists(path)
    assert server_module.load_conversation("s1") == msgs


def test_load_conversation_s3(server_module, s3):
    msgs = [{"role": "user", "content": "hi"}]
    s3.get_object.return_value = {"Body": io.BytesIO(json.dumps(msgs).encode())}
    assert server_module.load_conversation("s1") == msgs
    s3.get_object.assert_called_once_with(Bucket="test-bucket", Key="s1.json")


def test_load_conversation_s3_no_such_key_returns_empty(server_module, s3):
    s3.get_object.side_effect = client_error("NoSuchKey")
    assert server_module.load_conversation("s1") == []


def test_load_conversation_s3_other_error_raises(server_module, s3):
    s3.get_object.side_effect = client_error("AccessDenied")
    with pytest.raises(ClientError):
        server_module.load_conversation("s1")


def test_save_conversation_s3(server_module, s3):
    msgs = [{"role": "user", "content": "hi"}]
    server_module.save_conversation("s1", msgs)
    s3.put_object.assert_called_once()
    kwargs = s3.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "test-bucket"
    assert kwargs["Key"] == "s1.json"
    assert kwargs["ContentType"] == "application/json"
    assert json.loads(kwargs["Body"]) == msgs


# --- call_bedrock ---------------------------------------------------------

def test_call_bedrock_builds_messages(server_module, bedrock):
    history = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]
    result = server_module.call_bedrock(history, "q2")

    assert result == "Hi, I'm the twin."
    kwargs = bedrock.converse.call_args.kwargs
    assert kwargs["modelId"] == server_module.BEDROCK_MODEL_ID
    messages = kwargs["messages"]
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"].startswith("System: ")
    assert messages[1] == {"role": "user", "content": [{"text": "q1"}]}
    assert messages[2] == {"role": "assistant", "content": [{"text": "a1"}]}
    assert messages[-1] == {"role": "user", "content": [{"text": "q2"}]}
    assert kwargs["inferenceConfig"]["maxTokens"] == 2000


def test_call_bedrock_truncates_history_to_last_50(server_module, bedrock):
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"}
        for i in range(60)
    ]
    server_module.call_bedrock(history, "latest")
    messages = bedrock.converse.call_args.kwargs["messages"]
    # system prompt + 50 history + current message
    assert len(messages) == 52
    assert messages[1]["content"][0]["text"] == "m10"


@pytest.mark.parametrize(
    "code,status",
    [("ValidationException", 400), ("AccessDeniedException", 403), ("ThrottlingException", 500)],
)
def test_call_bedrock_maps_client_errors(server_module, bedrock, code, status):
    bedrock.converse.side_effect = client_error(code)
    with pytest.raises(HTTPException) as exc:
        server_module.call_bedrock([], "hi")
    assert exc.value.status_code == status


# --- endpoints ------------------------------------------------------------

def test_root(client, server_module):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["storage"] == "local"
    assert body["ai_model"] == server_module.BEDROCK_MODEL_ID
    assert body["memory_enabled"] is True


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert resp.json()["use_s3"] is False


def test_chat_new_session(client, server_module, bedrock):
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "Hi, I'm the twin."
    session_id = body["session_id"]
    assert session_id

    saved = server_module.load_conversation(session_id)
    assert [m["role"] for m in saved] == ["user", "assistant"]
    assert saved[0]["content"] == "Hello"
    assert saved[1]["content"] == "Hi, I'm the twin."
    assert all("timestamp" in m for m in saved)


def test_chat_existing_session_passes_history(client, server_module, bedrock):
    server_module.save_conversation(
        "sess", [{"role": "user", "content": "earlier", "timestamp": "t"},
                 {"role": "assistant", "content": "reply", "timestamp": "t"}]
    )
    resp = client.post("/chat", json={"message": "again", "session_id": "sess"})
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "sess"

    messages = bedrock.converse.call_args.kwargs["messages"]
    texts = [m["content"][0]["text"] for m in messages[1:]]
    assert texts == ["earlier", "reply", "again"]
    assert len(server_module.load_conversation("sess")) == 4


def test_chat_propagates_bedrock_http_errors(client, bedrock):
    bedrock.converse.side_effect = client_error("AccessDeniedException")
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 403


def test_chat_unexpected_error_returns_500(client, bedrock):
    bedrock.converse.side_effect = RuntimeError("kaboom")
    resp = client.post("/chat", json={"message": "Hello"})
    assert resp.status_code == 500
    assert "kaboom" in resp.json()["detail"]


def test_chat_requires_message(client):
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_get_conversation(client, server_module):
    msgs = [{"role": "user", "content": "hi", "timestamp": "t"}]
    server_module.save_conversation("abc", msgs)
    resp = client.get("/conversation/abc")
    assert resp.status_code == 200
    assert resp.json() == {"session_id": "abc", "messages": msgs}


def test_get_conversation_unknown_session(client):
    resp = client.get("/conversation/missing")
    assert resp.status_code == 200
    assert resp.json()["messages"] == []


def test_get_conversation_storage_error_returns_500(client, server_module, s3):
    s3.get_object.side_effect = client_error("AccessDenied")
    resp = client.get("/conversation/abc")
    assert resp.status_code == 500


def test_cors_allows_configured_origin(client):
    resp = client.options(
        "/chat",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_lambda_handler_wraps_app():
    import lambda_handler
    from mangum import Mangum

    assert isinstance(lambda_handler.handler, Mangum)
