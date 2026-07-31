from unittest.mock import patch

from core.api_client import call_model


@patch("core.providers.zhipu.call")
@patch("core.api_client.get_provider_config")
def test_text_and_image_use_separate_default_models(get_config, provider_call):
    get_config.return_value = {
        "provider": "zhipu",
        "api_key": "key",
        "api_base": "",
        "model_mode": "separate",
        "unified_model": "",
        "text_model": "",
        "image_model": "",
    }
    provider_call.return_value = "ok"

    call_model([], task_type="text")
    assert provider_call.call_args.kwargs["model"] == "glm-4.7-flash"

    call_model([], task_type="image")
    assert provider_call.call_args.kwargs["model"] == "glm-4.6v-flash"


@patch("core.providers.zhipu.call")
@patch("core.api_client.get_provider_config")
def test_explicit_custom_model_still_overrides_task_defaults(get_config, provider_call):
    get_config.return_value = {
        "provider": "zhipu",
        "api_key": "key",
        "api_base": "",
        "model_mode": "unified",
        "unified_model": "custom-multimodal-model",
        "text_model": "",
        "image_model": "",
    }
    provider_call.return_value = "ok"

    call_model([], task_type="image")

    assert provider_call.call_args.kwargs["model"] == "custom-multimodal-model"


@patch("core.providers.zhipu.call")
@patch("core.api_client.get_provider_config")
def test_separate_mode_honors_each_custom_model(get_config, provider_call):
    get_config.return_value = {
        "provider": "zhipu",
        "api_key": "key",
        "api_base": "",
        "model_mode": "separate",
        "unified_model": "",
        "text_model": "text-only-model",
        "image_model": "vision-model",
    }
    provider_call.return_value = "ok"

    call_model([], task_type="text")
    assert provider_call.call_args.kwargs["model"] == "text-only-model"
    call_model([], task_type="image")
    assert provider_call.call_args.kwargs["model"] == "vision-model"
