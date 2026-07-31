from unittest.mock import patch

from core.api_client import get_provider_config


@patch("core.api_client._get_config")
def test_removed_model_provider_falls_back_to_zhipu(get_config):
    get_config.side_effect = lambda key, default="": {
        "model_provider": "deepseek",
        "model_api_key": "test-key",
        "model_api_base": "",
        "model_name": "",
    }.get(key, default)

    config = get_provider_config()

    assert config["provider"] == "zhipu"
    assert config["model_mode"] == "separate"


@patch("core.api_client._get_config")
def test_legacy_custom_model_migrates_to_unified_mode(get_config):
    get_config.side_effect = lambda key, default="": {
        "model_provider": "zhipu",
        "model_name": "legacy-vision-model",
        "model_mode": "",
    }.get(key, default)

    config = get_provider_config()

    assert config["model_mode"] == "unified"
    assert config["unified_model"] == "legacy-vision-model"
