"""A NiceGUI widget for assigning a role to each fetched run.

``RoleCastTable`` collects the runs captured by **Fetch Runs** in a pyoncatng
:class:`~pyoncatng.widgets.runtable.RunTable`. Each fetch adds its runs to the
table; runs already there are kept. A new run starts as a sample, or with the
role of the runs sharing its name. The user selects any subset of rows and
clicks **Set as Sample**, **Set as Background** or **Set as Empty Cell** to
reassign them. A role button reassigns every run sharing a name with a selected
run, since the runs of one USANS measurement share a name. **Remove Runs**
removes only the selected runs. The buttons are enabled only while the table
holds a selection.

A :class:`~usansemble.role_cast.RoleCast` is the single source of truth: the grid
is a view of it, redrawn from :meth:`RoleCast.as_rows` after every change. A
redraw rebuilds the grid, which drops the selection and disables the buttons
again. Runs are listed by decreasing run number, as in the ``RunsSelector``
table.
"""

import functools
from collections.abc import Callable, Sequence
from typing import Any

from nicegui import ui
from pyoncatng.widgets.runtable import Row, RunTable

from usansemble.enums import ROLE_LABELS, MeasurementType
from usansemble.role_cast import (
    ID_COLUMN,
    NAME_COLUMN,
    ROLE_COLUMN,
    THICKNESS_COLUMN,
    TRANSMISSION_COLUMN,
    RoleCast,
    RunAssignment,
)

COLUMNS = (ID_COLUMN, NAME_COLUMN, ROLE_COLUMN, THICKNESS_COLUMN, TRANSMISSION_COLUMN)

# One button per role, in the order they are laid out.
SAMPLE_BUTTON_LABEL = "Set as Sample"
BACKGROUND_BUTTON_LABEL = "Set as Background"
EMPTY_CELL_BUTTON_LABEL = "Set as Empty Cell"
ROLE_BUTTON_LABELS = {
    MeasurementType.SAMPLE: SAMPLE_BUTTON_LABEL,
    MeasurementType.BACKGROUND: BACKGROUND_BUTTON_LABEL,
    MeasurementType.EMPTY_CELL: EMPTY_CELL_BUTTON_LABEL,
}

REMOVE_BUTTON_LABEL = "Remove Runs"

ASSIGNED_MESSAGE = "Assigned {n} run(s) as {role}."
REMOVED_MESSAGE = "Removed {n} run(s)."


class RoleCastTable(ui.column):
    """A table of fetched runs, with buttons assigning a role to the selected ones.

    Params
    ------
    table_height : str, optional
        CSS height applied to the table (AG Grid needs a concrete height).
        Defaults to ``"400px"``.
    """

    def __init__(self, *, table_height: str = "400px") -> None:
        super().__init__()
        self._table_height = table_height
        self._cast = RoleCast()
        self._callbacks: list[Callable[[list[RunAssignment]], None]] = []
        self._build_ui()

    # -- public integration surface ----------------------------------------

    @property
    def table(self) -> RunTable:
        """The embedded run table."""
        return self._table

    @property
    def cast(self) -> RoleCast:
        """The role assignment model behind the table.

        This is the live model, not a copy. Changing it directly does not
        redraw the table; use :meth:`add_runs` or the buttons instead.
        """
        return self._cast

    @property
    def assignments(self) -> list[RunAssignment]:
        """Deep copies of the current assignments, by decreasing run number."""
        return self._cast.assignments

    def add_runs(self, rows: Sequence[Row]) -> None:
        """Add the runs in ``rows`` to the table, keeping the runs already shown.

        Takes the rows :meth:`RunsSelector.on_runs_fetched` delivers, so it can
        be registered directly as that callback.
        """
        self._cast.add_runs(rows)
        self._refresh()
        self._set_status("")
        self._notify()

    def on_assignment_change(self, callback: Callable[[list[RunAssignment]], None]) -> None:
        """Register a callback fired with the assignments after every change.

        It fires after :meth:`add_runs` and after each button click. Each
        callback receives its own deep copy of the assignments. Callbacks are
        synchronous, matching ``RunsSelector.on_runs_fetched``.
        """
        self._callbacks.append(callback)

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        self.classes("w-full")
        with self:
            self._table = (
                RunTable(columns=COLUMNS, key_column=ID_COLUMN, rows=[])
                .classes("w-full")
                .style(f"height: {self._table_height}")
            )
            with ui.row().classes("items-center") as self._buttons_row:
                self._role_buttons = {
                    role: ui.button(label, on_click=functools.partial(self._on_assign, role))
                    for role, label in ROLE_BUTTON_LABELS.items()
                }
                self._remove_button = ui.button(REMOVE_BUTTON_LABEL, on_click=self._on_remove)
            self._status = ui.label("").classes("text-xs text-gray-500")
        self._set_status("")
        self._set_selection_buttons_enabled(False)
        self._table.on_selection_change(self._on_selection_change)
        # Every redraw goes through NiceGUI's aggrid update, which destroys and
        # recreates the grid; the selection is dropped without a
        # selectionChanged event, so the buttons are reset on gridReady instead.
        self._table.on("gridReady", self._on_table_rebuilt)

    # -- state --------------------------------------------------------------

    def _refresh(self) -> None:
        """Redraw the grid from the model.

        The redraw drops the selection, so the buttons are disabled here too
        rather than only when the browser reports ``gridReady``.
        """
        self._table.set_rows(self._cast.as_rows())
        self._set_selection_buttons_enabled(False)

    def _notify(self) -> None:
        for callback in self._callbacks:
            callback(self.assignments)

    def _set_status(self, text: str) -> None:
        """Show (or clear, when ``text`` is empty) the status line."""
        self._status.set_text(text)
        self._status.set_visibility(bool(text))

    def _set_selection_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable the role buttons and **Remove Runs** together.

        Every button acts on the selection, so they are enabled and disabled
        as one.
        """
        for button in (*self._role_buttons.values(), self._remove_button):
            button.set_enabled(enabled)

    # -- event handlers -----------------------------------------------------

    async def _on_selection_change(self, _event: Any = None) -> None:
        """Enable the buttons only while the table has a selection."""
        rows = await self._table.get_selected_rows()
        self._set_selection_buttons_enabled(bool(rows))

    def _on_table_rebuilt(self, _event: Any = None) -> None:
        """Disable the buttons whenever the grid is rebuilt."""
        self._set_selection_buttons_enabled(False)

    async def _on_assign(self, role: MeasurementType, _event: Any = None) -> None:
        """Give ``role`` to every run sharing a name with a selected run."""
        rows = await self._table.get_selected_rows()
        if not rows:
            # Reaching here means the enabled state was stale, so correct it.
            self._set_selection_buttons_enabled(False)
            return
        assigned = self._cast.assign((row[ID_COLUMN] for row in rows), role)
        self._refresh()
        self._set_status(ASSIGNED_MESSAGE.format(n=len(assigned), role=ROLE_LABELS[role]))
        self._notify()

    async def _on_remove(self, _event: Any = None) -> None:
        """Remove the selected runs, and only those, and redraw the table."""
        rows = await self._table.get_selected_rows()
        if not rows:
            # Reaching here means the enabled state was stale, so correct it.
            self._set_selection_buttons_enabled(False)
            return
        removed = self._cast.remove(row[ID_COLUMN] for row in rows)
        self._refresh()
        self._set_status(REMOVED_MESSAGE.format(n=len(removed)))
        self._notify()
