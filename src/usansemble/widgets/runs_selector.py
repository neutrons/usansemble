"""A composite NiceGUI widget: sign in to ONCat and browse an experiment's runs.

``RunsSelector`` packages the arrangement that pyoncatng's ``tutorial-iptstable``
demo wires up inline -- an :class:`~pyoncatng.widgets.login.OncatLogin` card above
an :class:`~pyoncatng.widgets.iptstable.IPTSTable` -- as a single reusable widget.
The user signs in, types an IPTS number, and the table fills with that
experiment's runs for a fixed facility/instrument (USANS by default).

It is the first building block of usansemble: later steps of the config-assembly
flow consume the authenticated agent and (eventually) the selected runs exposed
here. Row *selection* is not yet part of ``IPTSTable``, so this version displays
the runs; a selection accessor will be added when that capability lands upstream.
"""

from typing import Callable, Optional

from nicegui import ui
from pyoncatng.configuration import get_data
from pyoncatng.widgets.iptstable import IPTSTable
from pyoncatng.widgets.login import OncatLogin


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
                )
                .classes("w-full")
                .style(f"height: {self._table_height}")
            )
