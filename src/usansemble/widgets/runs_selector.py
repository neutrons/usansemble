"""A composite NiceGUI widget: sign in to ONCat and browse an experiment's runs.

``RunsSelector`` packages the arrangement that pyoncatng's ``tutorial-iptstable``
demo wires up inline -- an :class:`~pyoncatng.widgets.login.OncatLogin` card above
an :class:`~pyoncatng.widgets.iptstable.IPTSTable` -- as a single reusable widget.
The user signs in, types an IPTS number, and the table fills with that
experiment's runs for a fixed facility/instrument (USANS by default).

It is the first building block of usansemble: later steps of the config-assembly
flow consume the authenticated agent and the runs selected here. The selection
itself is read through ``IPTSTable`` (``selected_rows()`` /
``on_selection_change()``); on top of AG Grid's stock click gestures
(click/Ctrl+click/Shift+click) this widget adds a **double-click** that selects
every run sharing the double-clicked run's title, since the runs of one USANS
measurement share a title -- see :data:`_SELECT_BY_TITLE_JS`.

A **Fetch Runs** button below the table captures the current selection. AG Grid
returns selected rows in the order the selection was built, so the captured rows
are sorted by increasing run number before being stored. Consumers read them
through :attr:`RunsSelector.fetched_runs` or subscribe with
:meth:`RunsSelector.on_runs_fetched`. A **Clear Selection** button beside it
deselects all highlighted rows. Both buttons are enabled only while the table
holds a selection; clearing the selection or loading another IPTS disables them
again.
"""

import copy
import json
from typing import Any, Callable, List, Optional

from nicegui import ui
from pyoncatng.configuration import get_data

# ``IPTSTable`` always prepends its key column (the run number) to the caller's
# processing variables, so the ID column name is not in PROCESSING_VARIABLES
# below; alias the widget's own constant to stay in step with it.
from pyoncatng.widgets.iptstable import KEY_COLUMN as ID_COLUMN
from pyoncatng.widgets.iptstable import IPTSTable, Row
from pyoncatng.widgets.login import OncatLogin

PROCESSING_VARIABLES = (
    ("Title", "datafiles.raw.metadata.entry.title"),
    ("Start Time", "datafiles.raw.metadata.entry.start_time"),
    ("Total Counts", "datafiles.raw.metadata.entry.total_counts"),
)

# The column whose value groups the runs of one measurement. In ``IPTSTable`` the
# column name is also the header label and the row-dict key, so this is the field
# to match on in the grid's row data.
TITLE_COLUMN = PROCESSING_VARIABLES[0][0]

# Client-side AG Grid ``onCellDoubleClicked`` handler: double-clicking a cell
# selects every row sharing that row's title, replacing the previous selection;
# holding Ctrl (or Cmd on macOS) unions the matches into the previous selection
# instead. It has to run in the browser because NiceGUI's AG Grid event payload
# drops the underlying MouseEvent, so the server never sees the Ctrl modifier.
# NiceGUI turns an options key prefixed with ":" into a real JS function.
_SELECT_BY_TITLE_JS = f"""
(params) => {{
    const field = {json.dumps(TITLE_COLUMN)};
    const wanted = params.data ? params.data[field] : undefined;
    if (wanted == null) return;
    const additive = !!(params.event && (params.event.ctrlKey || params.event.metaKey));
    const nodes = [];
    params.api.forEachNode((node) => {{
        if (node.data && node.data[field] === wanted) nodes.push(node);
    }});
    if (!additive) params.api.deselectAll();
    params.api.setNodesSelected({{ nodes: nodes, newValue: true, source: "api" }});
}}
"""

# Gesture cheat-sheet captioning the table. The single-click gestures come from AG
# Grid's multi-row selection, the double-click ones from _SELECT_BY_TITLE_JS. Both
# additive gestures name Ctrl *and* Cmd: the handler accepts metaKey and AG Grid
# treats Cmd as Ctrl on macOS, so Mac users should see the gesture documented.
SELECTION_HELP = (
    "Click selects a run · Ctrl/Cmd+click toggles · Shift+click selects a range · "
    "Double-click selects every run with the same title · "
    "Ctrl/Cmd+double-click adds them to the selection"
)

# The button capturing the selection, and the two outcomes it reports.
FETCH_BUTTON_LABEL = "Fetch Runs"
CLEAR_BUTTON_LABEL = "Clear Selection"
FETCHED_MESSAGE = "Fetched {n} run(s)."
NO_SELECTION_MESSAGE = "Select at least one run first."


def _copy_rows(rows: List[Row]) -> List[Row]:
    """Deep-copy a row list, so nothing in it is shared with the caller.

    Row values are scalars today (run number, title, timestamp, counts), but a
    row holds whatever the ONCat projection returned (``IPTSTable.rows_from_runs``
    copies ``run.get(path)`` verbatim), and a metadata path may yield a list or a
    nested dict. Copying in depth keeps the boundary intact whatever the columns
    are configured to fetch. It is the same boundary pyoncatng's ``RunTable``
    draws around its own rows, in depth rather than one level.
    """
    return copy.deepcopy(list(rows))


class RunsSelector(ui.column):
    """An ``OncatLogin`` card above an ``IPTSTable``, packaged as one widget.

    Params
    ------
    client_id : str, optional
        Explicit ONCat client ID for the login card. When both ``client_id`` and
        ``key`` are omitted, the ID is read from the ``[login.oncat]`` section of
        the pyoncatng configuration (``get_data("login.oncat", "client_id")``).
    key : str, optional
        Config key used by ``OncatLogin`` to look up the client ID as
        ``<key>_id`` in the ``[login.oncat]`` section.
    facility : str, optional
        Facility passed to the ``IPTSTable``. Defaults to ``"SNS"``.
    instrument : str, optional
        Instrument passed to the ``IPTSTable``. Defaults to ``"USANS"``.
    table_height : str, optional
        CSS height applied to the table (AG Grid needs a concrete height).
        Defaults to ``"600px"``.
    login_orientation : str, optional
        Orientation of the login card's buttons, ``"row"`` or ``"column"``.
        Defaults to ``"row"``.
    """

    def __init__(
        self,
        *,
        client_id: Optional[str] = None,
        key: Optional[str] = None,
        facility: str = "SNS",
        instrument: str = "USANS",
        table_height: str = "600px",
        login_orientation: str = "row",
    ) -> None:
        super().__init__()
        # Fall back to the configured client ID only when the caller gives no
        # explicit credential, mirroring the tutorial's OncatLogin construction.
        if client_id is None and key is None:
            client_id = get_data("login.oncat", "client_id")
        self._client_id = client_id
        self._key = key
        self._facility = facility
        self._instrument = instrument
        self._table_height = table_height
        self._login_orientation = login_orientation
        self._fetched_runs: List[Row] = []
        self._fetch_callbacks: List[Callable[[List[Row]], None]] = []
        self._build_ui()

    # -- public integration surface ----------------------------------------

    @property
    def login(self) -> OncatLogin:
        """The embedded ONCat login card."""
        return self._login

    @property
    def table(self) -> IPTSTable:
        """The embedded IPTS run table."""
        return self._table

    @property
    def agent(self):
        """The authenticated ONCat agent, for consumers to query."""
        return self._login.agent

    @property
    def fetched_runs(self) -> List[Row]:
        """The runs captured by the last **Fetch Runs**, by increasing run number.

        Each **Fetch Runs** click replaces this with whatever is highlighted at
        the time; nothing else does. Loading another IPTS or signing out leaves
        the last capture in place, so it stays available to the later steps of
        the config-assembly flow until the user fetches again.

        Deep copies of the stored rows, so mutating the result cannot change the
        captured selection. Empty until the button is first clicked with a
        selection.
        """
        return _copy_rows(self._fetched_runs)

    def on_connection_change(self, callback: Callable[[bool], None]) -> None:
        """Register a callback fired with the connected bool on every change.

        A thin pass-through to :meth:`OncatLogin.on_connection_change` so
        consumers can react to sign-in without reaching into ``login``.
        """
        self._login.on_connection_change(callback)

    def on_runs_fetched(self, callback: Callable[[List[Row]], None]) -> None:
        """Register a callback fired with the fetched runs on every fetch.

        The callback receives the same sorted list :attr:`fetched_runs` returns.
        Callbacks are synchronous, matching ``on_connection_change``.
        """
        self._fetch_callbacks.append(callback)

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        self.classes("w-full")
        with self:
            # The agent is created once by the login card and reused; passing it
            # to the table now is fine even though it starts disconnected -- it
            # becomes usable after sign-in.
            self._login = OncatLogin(
                client_id=self._client_id,
                key=self._key,
                orientation=self._login_orientation,
            )
            self._table = (
                IPTSTable(
                    agent=self._login.agent,
                    facility=self._facility,
                    instrument=self._instrument,
                    processing_variables=PROCESSING_VARIABLES,
                )
                .classes("w-full")
                .style(f"height: {self._table_height}")
            )
            self._enable_title_double_click()
            self._add_selection_help()
            self._add_fetch_button()

    def _enable_title_double_click(self) -> None:
        """Make a double-click select every row sharing the clicked row's title.

        The gesture is a property of the AG Grid options, so it can be installed
        on the ``IPTSTable`` instance without subclassing it. ``IPTSTable`` keeps
        the grid private, hence the reach into ``_table``; should pyoncatng grow a
        public hook for this, only this method needs to change.
        """
        grid = self._table._table
        grid.options[":onCellDoubleClicked"] = _SELECT_BY_TITLE_JS
        # Push the new option in case the widget is built after the client connected.
        grid.update()

    def _add_selection_help(self) -> None:
        """Caption the table with the click gestures it supports.

        ``IPTSTable`` is a ``ui.card`` and NiceGUI elements are re-enterable
        context managers, so this appends the caption as the card's last child --
        below the table, inside the card.
        """
        with self._table:
            self._selection_help = ui.label(SELECTION_HELP).classes("text-xs text-gray-500")

    def _add_fetch_button(self) -> None:
        """Add the selection buttons and status line below the table.

        Built in the ``RunsSelector`` column rather than inside the table card,
        so they sit under the card. Both buttons stay disabled until the table
        has a selection; their enabling is driven by the table's
        selection-change hook.
        """
        with ui.row().classes("items-center") as self._selection_buttons:
            self._fetch_button = ui.button(FETCH_BUTTON_LABEL, on_click=self._on_fetch)
            self._fetch_button.set_enabled(False)
            self._clear_button = ui.button(CLEAR_BUTTON_LABEL, on_click=self._on_clear_selection)
            self._clear_button.set_enabled(False)
        self._fetch_status = ui.label("").classes("text-xs text-gray-500")
        self._fetch_status.set_visibility(False)
        self._table.on_selection_change(self._on_selection_change)
        # A Load replaces the rows through NiceGUI's aggrid update method, which
        # destroys and recreates the grid rather than patching it; the selection
        # is dropped without a selectionChanged event, so the button has to be
        # reset on the rebuild instead. ``gridReady`` fires on every rebuild.
        # ``IPTSTable`` keeps its grid private, hence the reach into ``_table``.
        self._table._table.on("gridReady", self._on_table_rebuilt)

    # -- fetching -----------------------------------------------------------

    def _set_fetch_status(self, text: str) -> None:
        """Show (or clear, when ``text`` is empty) the fetch status line."""
        self._fetch_status.set_text(text)
        self._fetch_status.set_visibility(bool(text))

    def _set_selection_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable both selection buttons together.

        Every path that reacts to the selection goes through here, so the two
        buttons cannot drift into disagreeing about whether a selection exists.
        """
        self._fetch_button.set_enabled(enabled)
        self._clear_button.set_enabled(enabled)

    async def _on_selection_change(self, _event: Any = None) -> None:
        """Enable the selection buttons only while the table has a selection."""
        rows = await self._table.selected_rows()
        self._set_selection_buttons_enabled(bool(rows))

    def _on_table_rebuilt(self, _event: Any = None) -> None:
        """Disable the selection buttons whenever the grid is rebuilt.

        Loading another IPTS replaces the rows, so any highlighted row numbers
        now address different runs and the selection must not be fetchable.
        Already-fetched runs are kept: they were captured deliberately, and the
        status line still describes them.
        """
        self._set_selection_buttons_enabled(False)

    async def _on_clear_selection(self, _event: Any = None) -> None:
        """Deselect every highlighted row and disable fetching immediately."""
        await self._table._table.run_grid_method("deselectAll")
        self._set_selection_buttons_enabled(False)

    async def _on_fetch(self, _event: Any = None) -> None:
        """Capture the selected runs, ordered by increasing run number.

        ``selected_rows()`` reaches AG Grid's ``getSelectedRows``, which returns
        the rows in the order the selection was built (Ctrl+click order, or the
        order the title double-click handler selected them), so the rows are
        sorted here. ``int`` keeps the ordering numeric should ONCat ever report
        the run number as a string.
        """
        rows = await self._table.selected_rows()
        if not rows:
            # Reaching here means the enabled state was stale, so correct it and
            # report the reason. Any previously fetched runs are left intact.
            self._set_selection_buttons_enabled(False)
            self._set_fetch_status(NO_SELECTION_MESSAGE)
            return
        self._fetched_runs = sorted(_copy_rows(rows), key=lambda row: int(row[ID_COLUMN]))
        self._set_fetch_status(FETCHED_MESSAGE.format(n=len(self._fetched_runs)))
        for callback in self._fetch_callbacks:
            callback(self.fetched_runs)
