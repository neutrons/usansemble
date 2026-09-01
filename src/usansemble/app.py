"""The usansemble single-page app.

For now the page mounts a :class:`~usansemble.widgets.runs_selector.RunsSelector`
so a user can sign in to ONCat and browse a USANS experiment's runs. This is the
first step of the intended assemble-config wizard (sign in / pick runs -> assign
roles -> export usansred JSON); the later steps land as their widgets are built.
"""

from nicegui import ui

from usansemble.widgets.runs_selector import RunsSelector


@ui.page("/")
def index() -> None:
    """The landing page: a titled RunsSelector."""
    with ui.column().classes("q-pa-md").style("width: 100%; max-width: 1000px"):
        ui.label("usansemble").classes("text-h5")
        ui.markdown(
            "Sign in to ONCat, then enter an IPTS number (e.g. **24703**) and click "
            "**Load** to fetch its USANS runs. Use the table's selection gestures "
            "to choose runs, then click **Fetch Runs** to capture them; assigning "
            "them to roles and exporting a `usansred` configuration will come next."
        )
        RunsSelector(facility="SNS", instrument="USANS")
