from unittest.mock import Mock, patch

from core.providers.zhipu import _get_client, call


@patch("core.providers.zhipu.OpenAI")
def test_zhipu_uses_supported_default_max_tokens(openai_client):
    _get_client.cache_clear()
    client = Mock()
    openai_client.return_value = client
    client.chat.completions.create.return_value.choices = [
        Mock(message=Mock(content="connected"))
    ]

    assert call("test-key", [{"role": "user", "content": "test"}]) == "connected"

    assert client.chat.completions.create.call_args.kwargs["max_tokens"] == 2048
    assert client.chat.completions.create.call_args.kwargs["model"] == "glm-4.7-flash"
    openai_client.assert_called_once_with(
        api_key="test-key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        max_retries=0,
        timeout=30.0,
    )
    _get_client.cache_clear()


@patch("core.providers.zhipu.OpenAI")
def test_zhipu_reuses_client_for_matching_credentials(openai_client):
    _get_client.cache_clear()
    client = Mock()
    openai_client.return_value = client
    client.chat.completions.create.return_value.choices = [
        Mock(message=Mock(content="connected"))
    ]

    call("same-key", [{"role": "user", "content": "one"}])
    call("same-key", [{"role": "user", "content": "two"}])

    openai_client.assert_called_once()
    assert client.chat.completions.create.call_count == 2
    _get_client.cache_clear()
