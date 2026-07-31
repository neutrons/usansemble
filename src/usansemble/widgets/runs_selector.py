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
"""

import json
from typing import Callable, Optional

from nicegui import ui
from pyoncatng.configuration import get_data
from pyoncatng.widgets.iptstable import IPTSTable
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

    def on_connection_change(self, callback: Callable[[bool], None]) -> None:
        """Register a callback fired with the connected bool on every change.

        A thin pass-through to :meth:`OncatLogin.on_connection_change` so
        consumers can react to sign-in without reaching into ``login``.
        """
        self._login.on_connection_change(callback)

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
