"""
What j4ne sends OpenCode: the endpoint and models opencode_settings picks
from the environment, and tool names the API accepts (card #985). Nothing
here calls OpenCode.
"""

import re

import pytest

from tools.direct_client import (GO_BASE_URL, ZEN_BASE_URL, DirectClient, api_tool_name, api_tools,
                                 opencode_settings)


@pytest.fixture
def env(monkeypatch):
    """An environment with only an API key, plus whatever the test sets"""
    for name in ("OPENCODE_USE_GO", "OPENCODE_ZEN_MODEL", "OPENCODE_ZEN_FOLLOWUP_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENCODE_ZEN_API_KEY", "test-key")

    def set_env(**values):
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        return opencode_settings()

    return set_env


def test_go_is_the_default(env):
    settings = env()
    assert settings["base_url"] == GO_BASE_URL
    assert settings["default_model"] == settings["followup_model"] == "glm-5.3"


def test_go_takes_its_models_from_the_zen_names(env):
    # How production's .env names them
    settings = env(OPENCODE_USE_GO="true", OPENCODE_ZEN_MODEL="kimi-k2.6",
                   OPENCODE_ZEN_FOLLOWUP_MODEL="glm-5.3-flash")
    assert settings["base_url"] == GO_BASE_URL
    assert (settings["default_model"], settings["followup_model"]) == ("kimi-k2.6", "glm-5.3-flash")


def test_followup_defaults_to_the_model(env):
    assert env(OPENCODE_ZEN_MODEL="deepseek-v4-pro")["followup_model"] == "deepseek-v4-pro"


def test_opencode_prefix_is_dropped(env):
    settings = env(OPENCODE_ZEN_MODEL="opencode-go/glm-5.3", OPENCODE_ZEN_FOLLOWUP_MODEL="opencode-go/glm-5.3-flash")
    assert (settings["default_model"], settings["followup_model"]) == ("glm-5.3", "glm-5.3-flash")


def test_zen_when_go_is_off(env):
    settings = env(OPENCODE_USE_GO="false", OPENCODE_ZEN_MODEL="gpt-5.1-codex")
    assert settings["base_url"] == ZEN_BASE_URL
    assert settings["default_model"] == "gpt-5.1-codex"


def test_missing_key(env, monkeypatch):
    monkeypatch.delenv("OPENCODE_ZEN_API_KEY")
    with pytest.raises(ValueError, match="OPENCODE_ZEN_API_KEY"):
        opencode_settings()


@pytest.mark.parametrize("context", ["cli", "slack"])
def test_every_tool_name_is_one_the_api_accepts(env, tmp_path, monkeypatch, context):
    import tools.direct_client as direct_client
    monkeypatch.setattr(direct_client, "MEMORY_AVAILABLE", False)
    client = DirectClient(root_path=str(tmp_path), db_path=str(tmp_path / "test.db"), context=context)
    renamed, names = api_tools(client.get_available_tools())
    assert renamed
    for tool in renamed:
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", tool["function"]["name"])
    # and each maps back to the tool it came from
    assert sorted(names.values()) == sorted(t["function"]["name"] for t in client.get_available_tools())


def test_api_names(env):
    assert api_tool_name("filesystem.read-file") == "filesystem_read-file"
    assert api_tool_name("web.search") == "web_search"
