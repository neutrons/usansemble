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
    selector = _selector(user)

    # Nothing is loaded yet, so there is nothing to fetch.
    assert selector._fetch_button.enabled is False
    # The button belongs to the RunsSelector column, not the table card, so it
    # renders below the table.
    assert selector._fetch_button.parent_slot.parent is selector


@pytest.mark.usefixtures("fake_agent")
async def test_fetch_button_follows_the_selection(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    _stub_selection(selector, [_row(33221)])
    await selector._on_selection_change()
    assert selector._fetch_button.enabled is True

    _stub_selection(selector, [])
    await selector._on_selection_change()
    assert selector._fetch_button.enabled is False


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

    selector.fetched_runs.clear()

    assert [row[ID_COLUMN] for row in selector.fetched_runs] == [33221]


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

    # The button guards against this, but a Load that drops the selection may
    # not fire selectionChanged, so an empty fetch must not discard the runs.
    _stub_selection(selector, [])
    await selector._on_fetch()

    assert [row[ID_COLUMN] for row in selector.fetched_runs] == [33221]
    await user.should_see(NO_SELECTION_MESSAGE)


def test_fetch_sorts_on_the_table_key_column() -> None:
    # IPTSTable prepends the key column itself, so a rename there would silently
    # break the sort; ID_COLUMN aliases that constant.
    assert ID_COLUMN == "ID"
    assert ID_COLUMN not in [label for label, _ in PROCESSING_VARIABLES]
