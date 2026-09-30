"""The usansemble single-page app.

The page mounts a :class:`~usansemble.widgets.runs_selector.RunsSelector`, so a
user can sign in to ONCat and pick a USANS experiment's runs, above a
:class:`~usansemble.widgets.role_cast_table.RoleCastTable` that receives the
fetched runs for role assignment. These are the first two steps of the intended
assemble-config wizard (sign in / pick runs -> assign roles -> export usansred
JSON); the export step lands once its widget is built.
"""

from nicegui import ui

from usansemble.widgets.role_cast_table import RoleCastTable
from usansemble.widgets.runs_selector import RunsSelector


@ui.page("/")
def index() -> None:
    """The landing page: a titled RunsSelector feeding a RoleCastTable."""
    with ui.column().classes("q-pa-md").style("width: 100%; max-width: 1000px"):
        ui.label("usansemble").classes("text-h5")
        ui.markdown(
            "Sign in to ONCat, then enter an IPTS number (e.g. **24703**) and click "
            "**Load** to fetch its USANS runs. Use the table's selection gestures "
            "to choose runs, then click **Fetch Runs** to add them to the role "
            "table below. A new run starts as a sample, or with the role of the "
            "runs already there with the same name: select runs in the role table "
            "and click **Set as Background** or **Set as Empty Cell** to reassign "
            "them, or **Set as Sample** to reassign them back. Each of these "
            "buttons reassigns every run with the same name as a selected run. "
            "**Remove Runs** removes only the selected runs. "
            "Exporting a `usansred` configuration will come next."
        )
        selector = RunsSelector(facility="SNS", instrument="USANS")
        role_table = RoleCastTable()
        selector.on_runs_fetched(role_table.add_runs)
