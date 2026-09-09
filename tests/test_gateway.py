from openai.types.chat import ChatCompletion

from relay.gateway import GatewayModel


def test_tool_call_history_has_explicit_content_without_losing_tool_id():
    messages = [
        {
            "role": "assistant",
            "content": [{"toolUse": {"toolUseId": "call_123", "name": "inspect_workspace", "input": {}}}],
        }
    ]
    result = GatewayModel.format_request_messages(messages)
    assert "inspect_workspace" in result[0]["content"]
    assert "call_123" in result[0]["content"]
    assert "tool_calls" not in result[0]


def test_tool_result_history_preserves_result_and_reference():
    messages = [
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "abc123", "status": "success", "content": [{"text": "pong"}]}}
            ],
        }
    ]
    result = GatewayModel.format_request_messages(messages)
    assert result[0]["role"] == "user"
    assert "abc123" in result[0]["content"]
    assert "pong" in result[0]["content"]


def test_explicit_model_action_becomes_real_strands_tool_use():
    model = GatewayModel(client_args={"api_key": "synthetic-test"}, model_id="test", stream=False)
    response = ChatCompletion.model_validate(
        {
            "id": "test",
            "created": 0,
            "object": "chat.completion",
            "model": "observed-model",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": '{"tool_calls":[{"name":"inspect_workspace","arguments":{}}]}',
                    },
                }
            ],
        }
    )
    chunks = model._format_non_streaming_response(response)
    assert model.observed_models == {"observed-model"}
    assert any(
        c.get("contentBlockStart", {}).get("start", {}).get("toolUse", {}).get("name") == "inspect_workspace"
        for c in chunks
    )
    assert not any("pong" in str(c) for c in chunks)
