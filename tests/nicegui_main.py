"""NiceGUI main file executed by the ``user`` fixture to register test pages.

``nicegui.testing`` runs this module via ``runpy`` under the name ``__main__``,
so ``ui.run`` is reached (a ``storage_secret`` is supplied so ``app.storage.user``
works during the simulation). The page body builds the widget lazily, at request
time, so a test can patch the ONCat agent (via the ``fake_agent`` fixture) before
opening the page.
"""

from nicegui import ui

from usansemble.widgets.runs_selector import RunsSelector


@ui.page("/runs")
def runs_page() -> None:
    # Explicit client_id avoids depending on the config-default fallback; the
    # fake_agent fixture supplies the agent behind the login card.
    RunsSelector(client_id="0123456489", facility="SNS", instrument="USANS")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(storage_secret="test secret")
