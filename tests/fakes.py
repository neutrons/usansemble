"""A scriptable fake ONCat agent shared across the test suite.

Borrowed from pyoncatng's test suite: usansemble's widgets consume pyoncatng's
``OncatLogin``/``IPTSTable``, so the tests script the same ``pyoncat.ONCat``
surface (``Facility.list``/``Run.list``/``login``/``logout``) without a live
session. Injected by patching ``pyoncatng.core.service.build_agent`` (see the
``fake_agent`` fixture in ``conftest.py``).
"""

import types

import pyoncat


class _Facility:
    """Stand-in for ``agent.Facility`` exposing a scriptable ``list()``."""

    def __init__(self, agent: "FakeAgent") -> None:
        self._agent = agent

    def list(self):  # noqa: A003 - mirrors the pyoncat resource API
        self._agent.facility_calls += 1
        if self._agent.facility_error is not None:
            raise self._agent.facility_error
        return []


class _Run:
    """Stand-in for ``agent.Run`` exposing a scriptable ``list()``."""

    def __init__(self, agent: "FakeAgent") -> None:
        self._agent = agent

    def list(self, **kwargs):  # noqa: A003 - mirrors the pyoncat resource API
        self._agent.run_calls += 1
        self._agent.run_kwargs = kwargs
        if self._agent.run_error is not None:
            raise self._agent.run_error
        return list(self._agent.run_result)


class FakeAgent:
    """A scriptable replacement for :class:`pyoncat.ONCat`.

    Knobs (set before opening a page / calling a workflow):
      * ``tokened`` -- what ``has_stored_token()`` reports.
      * ``facility_error`` -- exception raised by ``Facility.list()`` (or None).
      * ``emit_challenge`` -- whether ``login()`` invokes the verification handler.
      * ``login_mode`` -- ``"success"`` | ``"cancel"`` | ``"error"``.
      * ``logout_error`` -- exception raised by ``logout()`` (or None).
      * ``run_result`` -- runs returned by ``Run.list()`` (default empty).
      * ``run_error`` -- exception raised by ``Run.list()`` (or None).
    Observations: ``facility_calls``, ``login_calls``, ``logout_calls``,
    ``login_seen_token`` (token visible to pyoncat at the moment ``login`` ran),
    ``run_calls``, ``run_kwargs`` (the last kwargs passed to ``Run.list()``).
    """

    def __init__(self) -> None:
        self.tokened = False
        self.facility_error = None
        self.emit_challenge = True
        self.login_mode = "success"
        self.logout_error = None
        self.run_result = []
        self.run_error = None

        self.verification_handler = None
        self.token_getter = None
        self.token_setter = None

        self.facility_calls = 0
        self.login_calls = 0
        self.logout_calls = 0
        self.login_seen_token = "unset"
        self.run_calls = 0
        self.run_kwargs = None

        self.challenge = types.SimpleNamespace(
            verification_uri="https://oncat.example/verify",
            verification_uri_complete="https://oncat.example/verify?user_code=WXYZ-1234",
            user_code="WXYZ-1234",
        )

    @property
    def Facility(self) -> _Facility:  # noqa: N802 - mirrors the pyoncat resource API
        return _Facility(self)

    @property
    def Run(self) -> _Run:  # noqa: N802 - mirrors the pyoncat resource API
        return _Run(self)

    def has_stored_token(self) -> bool:
        return self.tokened

    def login(self, cancel_event=None):
        self.login_calls += 1
        self.login_seen_token = self.token_getter() if self.token_getter else None
        if self.emit_challenge and self.verification_handler is not None:
            self.verification_handler(self.challenge)
        if self.login_mode == "cancel":
            if cancel_event is not None:
                cancel_event.wait(timeout=5)
            raise pyoncat.DeviceAuthorizationCancelled("cancelled")
        if self.login_mode == "error":
            raise pyoncat.DeviceAuthorizationExpired("device code expired")
        # success
        if self.token_setter is not None:
            self.token_setter({"access_token": "fake"})
        self.tokened = True

    def logout(self):
        self.logout_calls += 1
        if self.logout_error is not None:
            raise self.logout_error
        self.tokened = False
