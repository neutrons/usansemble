"""Shared fixtures: point pyoncatng's config loader at a bundled test INI and
inject a scriptable fake ONCat agent.

usansemble reuses pyoncatng's ``OncatLogin``/``IPTSTable``, so the ONCat wiring
under test lives in the ``pyoncatng`` package; the fixtures patch it there.
"""

import os

import pytest
from fakes import FakeAgent

import pyoncatng.configuration as configuration

TEST_CONFIG = os.path.join(os.path.dirname(__file__), "data", "configuration.ini")


@pytest.fixture(autouse=True)
def _config_path(monkeypatch):
    """Point pyoncatng's configuration loader at the bundled test INI."""
    monkeypatch.setattr(configuration, "CONFIG_PATH_FILE", TEST_CONFIG)


@pytest.fixture
def fake_agent(monkeypatch):
    """Patch pyoncatng's ``build_agent`` so widgets use a scriptable fake agent.

    ``OncatLogin`` builds its agent through ``pyoncatng.core.service.build_agent``;
    patching it makes ``RunsSelector``'s login (and the ``IPTSTable`` it feeds)
    use the returned :class:`FakeAgent`.
    """
    agent = FakeAgent()

    def _build(oncat_url, client_id, *, token_getter, token_setter, verification_handler, scopes=None, timeout=10.0):
        agent.built = {
            "oncat_url": oncat_url,
            "client_id": client_id,
            "scopes": scopes,
            "timeout": timeout,
        }
        agent.token_getter = token_getter
        agent.token_setter = token_setter
        agent.verification_handler = verification_handler
        return agent

    monkeypatch.setattr("pyoncatng.core.service.build_agent", _build)
    return agent
