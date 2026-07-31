from unittest.mock import patch

from core.api_client import test_connection as check_connection


@patch("core.api_client.call_model")
@patch("core.api_client.get_provider_config")
def test_unified_connection_check_uses_an_image_request(get_config, call_model):
    get_config.return_value = {"model_mode": "unified"}
    call_model.return_value = "ok"

    ok, message = check_connection()

    assert ok
    assert "多模态" in message
    assert call_model.call_count == 1
    assert call_model.call_args.kwargs["task_type"] == "image"


@patch("core.api_client.call_model")
@patch("core.api_client.get_provider_config")
def test_separate_connection_check_tests_both_models(get_config, call_model):
    get_config.return_value = {"model_mode": "separate"}
    call_model.return_value = "ok"

    ok, message = check_connection()

    assert ok
    assert "均连接成功" in message
    assert [call.kwargs["task_type"] for call in call_model.call_args_list] == [
        "text",
        "image",
    ]
