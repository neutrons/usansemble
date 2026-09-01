"""Tests for the RunsSelector composite widget.

``RunsSelector`` packages pyoncatng's ``OncatLogin`` + ``IPTSTable``. The tests
use NiceGUI's in-process ``user`` simulation; the ``fake_agent`` fixture patches
``pyoncatng.core.service.build_agent`` so the login card (and the table it feeds)
run against a scriptable agent. A test reaches the live element through
``user.find`` and scripts ``Run.list`` before loading.
"""

import json

import pytest
from nicegui.testing import User
from pyoncatng.widgets.iptstable import IPTSTable
from pyoncatng.widgets.login import OncatLogin

from usansemble.widgets.runs_selector import (
    CLEAR_BUTTON_LABEL,
    FETCH_BUTTON_LABEL,
    FETCHED_MESSAGE,
    ID_COLUMN,
    NO_SELECTION_MESSAGE,
    PROCESSING_VARIABLES,
    SELECTION_HELP,
    TITLE_COLUMN,
    RunsSelector,
)

# A sample run as returned by ONCat with a flat, dot-path projection. USANS runs
# expose metadata under datafiles.raw.metadata.entry.*.
SAMPLE_RUN = {
    "id": 33221,
    "datafiles.raw.metadata.entry.title": "Align:0 stop rheometer",
    "datafiles.raw.metadata.entry.start_time": "2020-11-24T06:33:53.879457667-05:00",
    "datafiles.raw.metadata.entry.total_counts": 258881,
}


def _selector(user: User) -> RunsSelector:
    return next(iter(user.find(RunsSelector).elements))


def _row(run_id: int) -> dict:
    """A table row as ``IPTSTable`` builds it, for the given run number."""
    return {
        "ID": run_id,
        "Title": "Align:500 10min cure with SI",
        "Start Time": "2020-11-23T20:31:23.874765-05:00",
        "Total Counts": 261607,
    }


def _stub_selection(selector: RunsSelector, rows: list) -> None:
    """Make the table report ``rows`` as selected.

    ``IPTSTable.selected_rows`` round-trips to AG Grid in the browser, which the
    in-process simulation cannot do, so it is replaced with an async stub.
    """

    async def _selected_rows():
        return list(rows)

    selector.table.selected_rows = _selected_rows


async def test_runs_selector_renders(user: User, fake_agent) -> None:
    fake_agent.tokened = False
    await user.open("/runs")
    await user.should_see(kind=RunsSelector)
    await user.should_see(kind=OncatLogin)
    await user.should_see(kind=IPTSTable)
    await user.should_see("IPTS:")
    await user.should_see("Load")
    await user.should_see("Connect")


async def test_runs_selector_exposes_login_and_table(user: User, fake_agent) -> None:
    await user.open("/runs")
    selector = _selector(user)
    assert isinstance(selector.login, OncatLogin)
    assert isinstance(selector.table, IPTSTable)
    # The table shares the login's agent; both are the injected fake.
    assert selector.agent is selector.login.agent
    assert selector.table._agent is fake_agent
    assert selector.table._processing_variables == list(PROCESSING_VARIABLES)


async def test_runs_selector_load_populates_table(user: User, fake_agent) -> None:
    await user.open("/runs")
    selector = _selector(user)
    table = selector.table
    fake_agent.run_result = [SAMPLE_RUN]
    table._input.value = "24703"

    await table._on_load()

    # The IPTS number was normalized and the fixed facility/instrument were sent.
    assert fake_agent.run_kwargs["experiment"] == "IPTS-24703"
    assert fake_agent.run_kwargs["facility"] == "SNS"
    assert fake_agent.run_kwargs["instrument"] == "USANS"
    # The child RunTable carries the mapped row.
    assert table._table.options["rowData"] == [
        {
            "ID": 33221,
            "Title": "Align:0 stop rheometer",
            "Start Time": "2020-11-24T06:33:53.879457667-05:00",
            "Total Counts": 258881,
        }
    ]


@pytest.mark.usefixtures("fake_agent")
async def test_runs_selector_installs_title_double_click_handler(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    # The handler is a client-side AG Grid option (NiceGUI compiles a ":"-prefixed
    # key into a JS function), so only its presence and shape can be checked here.
    handler = selector.table._table.options[":onCellDoubleClicked"]
    assert "onCellDoubleClicked" not in selector.table._table.options
    # Ctrl (and Cmd on macOS) switches from replacing to appending to the selection.
    assert "ctrlKey" in handler
    assert "metaKey" in handler
    # Invalid cell events must leave the existing selection unchanged.
    assert "if (wanted == null) return;" in handler
    # Replacing clears first; both branches end by selecting the matching rows.
    assert "deselectAll" in handler
    assert "setNodesSelected" in handler


@pytest.mark.usefixtures("fake_agent")
async def test_title_double_click_handler_targets_the_title_column(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    # Guards against a PROCESSING_VARIABLES reorder silently pointing the gesture
    # at the wrong column.
    assert TITLE_COLUMN == "Title"
    assert json.dumps(TITLE_COLUMN) in selector.table._table.options[":onCellDoubleClicked"]


@pytest.mark.usefixtures("fake_agent")
async def test_runs_selector_shows_selection_help(user: User) -> None:
    await user.open("/runs")
    await user.should_see(SELECTION_HELP)

    # The caption belongs to the table card, so it stays with the table if the
    # surrounding layout changes.
    selector = _selector(user)
    assert selector._selection_help.parent_slot.parent is selector.table


async def test_runs_selector_on_connection_change_is_forwarded(user: User, fake_agent) -> None:
    fake_agent.tokened = False
    await user.open("/runs")
    selector = _selector(user)
    seen: list[bool] = []
    selector.on_connection_change(seen.append)

    # Firing the login's state notification reaches callbacks registered on the
    # composite widget (the pass-through contract).
    selector.login._update_connection_status()

    assert seen == [selector.login.is_connected]


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_button_starts_disabled(user: User) -> None:
    await user.open("/runs")
    await user.should_see(FETCH_BUTTON_LABEL)
    await user.should_see(CLEAR_BUTTON_LABEL)
    selector = _selector(user)

    # Nothing is loaded yet, so there is nothing to fetch.
    assert selector._fetch_button.enabled is False
    assert selector._clear_button.enabled is False
    # Both buttons belong to the RunsSelector column, not the table card, so
    # they render below the table next to each other.
    assert selector._selection_buttons.parent_slot.parent is selector
    assert selector._fetch_button.parent_slot.parent is selector._selection_buttons
    assert selector._clear_button.parent_slot.parent is selector._selection_buttons


@pytest.mark.usefixtures("fake_agent")
async def test_clear_selection_deselects_rows_and_disables_fetch(user: User, monkeypatch) -> None:
    await user.open("/runs")
    selector = _selector(user)
    calls = []

    async def deselect_all(name):
        calls.append(name)

    monkeypatch.setattr(selector.table._table, "run_grid_method", deselect_all)
    selector._fetch_button.set_enabled(True)

    await selector._on_clear_selection()

    assert calls == ["deselectAll"]
    assert selector._fetch_button.enabled is False
    assert selector._clear_button.enabled is False


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_button_follows_the_selection(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    _stub_selection(selector, [_row(33221)])
    await selector._on_selection_change()
    assert selector._fetch_button.enabled is True
    assert selector._clear_button.enabled is True

    _stub_selection(selector, [])
    await selector._on_selection_change()
    assert selector._fetch_button.enabled is False
    assert selector._clear_button.enabled is False


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_runs_sorts_by_increasing_id(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    # AG Grid returns the rows in the order the selection was built, which is
    # not necessarily run-number order.
    _stub_selection(selector, [_row(33219), _row(33221), _row(33220)])

    await selector._on_fetch()

    assert [row[ID_COLUMN] for row in selector.fetched_runs] == [33219, 33220, 33221]


@pytest.mark.usefixtures("fake_agent")
async def test_fetched_runs_is_a_copy(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    _stub_selection(selector, [_row(33221)])
    await selector._on_fetch()

    # Both levels: dropping a row from the returned list, and editing a row in
    # it, must leave the captured runs untouched.
    returned = selector.fetched_runs
    returned[0][TITLE_COLUMN] = "mutated"
    returned.clear()

    assert [row[ID_COLUMN] for row in selector.fetched_runs] == [33221]
    assert selector.fetched_runs[0][TITLE_COLUMN] != "mutated"


@pytest.mark.usefixtures("fake_agent")
async def test_fetched_runs_copies_nested_values(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    # A row carries whatever the ONCat projection returned, which a metadata path
    # may report as a list rather than a scalar.
    row = _row(33221)
    row["Total Counts"] = [1, 2, 3]
    _stub_selection(selector, [row])
    await selector._on_fetch()

    selector.fetched_runs[0]["Total Counts"].append(4)

    assert selector.fetched_runs[0]["Total Counts"] == [1, 2, 3]


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_callbacks_get_independent_rows(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    seen: list[list[dict]] = []
    selector.on_runs_fetched(seen.append)
    _stub_selection(selector, [_row(33221)])
    await selector._on_fetch()

    # A callback editing its payload must not change what later readers see.
    seen[0][0][TITLE_COLUMN] = "mutated"

    assert selector.fetched_runs[0][TITLE_COLUMN] != "mutated"


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_runs_notifies_and_reports(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    seen: list[list[dict]] = []
    selector.on_runs_fetched(seen.append)
    _stub_selection(selector, [_row(33221), _row(33220)])

    await selector._on_fetch()

    assert [row[ID_COLUMN] for row in seen[0]] == [33220, 33221]
    await user.should_see(FETCHED_MESSAGE.format(n=2))


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_runs_without_a_selection_keeps_the_previous_runs(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    _stub_selection(selector, [_row(33221)])
    await selector._on_fetch()

    # The buttons guard against this, but a Load that drops the selection may
    # not fire selectionChanged, so an empty fetch must not discard the runs.
    _stub_selection(selector, [])
    await selector._on_fetch()

    assert [row[ID_COLUMN] for row in selector.fetched_runs] == [33221]
    # Both buttons reflect the corrected state, not just the one that was clicked.
    assert selector._fetch_button.enabled is False
    assert selector._clear_button.enabled is False
    await user.should_see(NO_SELECTION_MESSAGE)


@pytest.mark.usefixtures("fake_agent")
async def test_loading_new_runs_disables_the_fetch_button(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)
    _stub_selection(selector, [_row(33221)])
    await selector._on_selection_change()
    await selector._on_fetch()
    assert selector._fetch_button.enabled is True

    # A Load rebuilds the grid, dropping the selection; the row numbers now
    # address different runs, so the button must not stay enabled.
    selector._on_table_rebuilt()

    assert selector._fetch_button.enabled is False
    # The runs captured before the reload are kept.
    assert [row[ID_COLUMN] for row in selector.fetched_runs] == [33221]


@pytest.mark.usefixtures("fake_agent")
async def test_table_rebuild_is_wired_to_grid_ready(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    # NiceGUI rebuilds the grid on every update, so gridReady is the event that
    # signals the selection was dropped.
    handlers = [
        listener.handler for listener in selector.table._table._event_listeners.values() if listener.type == "gridReady"
    ]
    assert selector._on_table_rebuilt in handlers


def test_fetch_sorts_on_the_table_key_column() -> None:
    # IPTSTable prepends the key column itself, so a rename there would silently
    # break the sort; ID_COLUMN aliases that constant.
    assert ID_COLUMN == "ID"
    assert ID_COLUMN not in [label for label, _ in PROCESSING_VARIABLES]
